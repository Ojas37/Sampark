"""Deterministic, grounded obligation extraction.

The extractor reads a document's page text and proposes obligation candidates
and validity fields. Each candidate must quote a verbatim span that is present
on the cited page (grounding check); ungrounded candidates are discarded.
Relative deadlines ("within N days of issue") are resolved against the document
date by deterministic code, never by a model. This path runs fully offline so
the demo is reproducible; an optional LLM second opinion can sit behind it.
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..clock import Clock
from ..models import (
    Document,
    ExtractionRun,
    Institution,
    ObligationCandidate,
    Undertaking,
    User,
)
from .audit import append_event


# --- Rule patterns -----------------------------------------------------------
# Each rule knows how to find a clause and how to label the obligation it implies.
_RELATIVE_DUE = re.compile(r"within\s+(\d{1,4})\s+(day|days|month|months)\s+(?:of|from)\s+(issue|the\s+date\s+of\s+issue|issuance)", re.IGNORECASE)
_ABSOLUTE_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_WORDS = re.compile(r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", re.IGNORECASE)

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

# Keyword -> (category, description template, responsible party, base confidence)
_OBLIGATION_RULES = [
    ("lease deed", "UNDERTAKING", "Submit the registered lease deed for the permanent campus", "INSTITUTION", 0.88),
    ("lease", "UNDERTAKING", "Submit the registered lease document for the campus", "INSTITUTION", 0.82),
    ("land", "UNDERTAKING", "Provide proof of land ownership or long-term lease", "INSTITUTION", 0.8),
    ("faculty", "CONDITION", "Appoint faculty to meet the prescribed student-faculty ratio", "INSTITUTION", 0.78),
    ("fire safety", "CONDITION", "Submit a valid fire safety certificate", "INSTITUTION", 0.85),
    ("fire", "CONDITION", "Submit a valid fire safety certificate", "INSTITUTION", 0.8),
    ("building", "CONDITION", "Submit the occupancy / building completion certificate", "INSTITUTION", 0.82),
    ("affiliation", "CONDITION", "Obtain and submit the affiliating body approval", "INSTITUTION", 0.8),
    ("undertaking", "UNDERTAKING", "Submit the signed undertaking as stated in the letter", "INSTITUTION", 0.84),
    ("affidavit", "UNDERTAKING", "Submit the notarised affidavit as required", "INSTITUTION", 0.83),
    ("bank guarantee", "CONDITION", "Furnish the bank guarantee / FDR as specified", "INSTITUTION", 0.86),
    ("annual report", "CONDITION", "File the mandatory annual report", "INSTITUTION", 0.77),
]

# Validity fields: keyword -> field name
_VALIDITY_RULES = [
    ("lease expiry", "lease_expiry"),
    ("lease valid", "lease_expiry"),
    ("valid up to", "validity_expiry"),
    ("valid until", "validity_expiry"),
    ("expiry", "validity_expiry"),
    ("expires on", "validity_expiry"),
]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.;])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_absolute(text: str) -> date | None:
    match = _ABSOLUTE_DATE.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    words = _DATE_WORDS.search(text)
    if words:
        try:
            return date(int(words.group(3)), _MONTHS[words.group(2).lower()], int(words.group(1)))
        except (ValueError, KeyError):
            return None
    return None


def _resolve_relative(sentence: str, doc_date: date | None) -> tuple[date | None, str | None]:
    """Resolve 'within N days/months of issue' against the document date (deterministic)."""
    match = _RELATIVE_DUE.search(sentence)
    if not match:
        return None, None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    expression = f"within {amount} {unit} of issue"
    if doc_date is None:
        return None, expression
    days = amount * 30 if unit.startswith("month") else amount
    return doc_date + timedelta(days=days), expression


def compute_sha256(pages: list[str]) -> str:
    return hashlib.sha256("\x1e".join(pages).encode("utf-8")).hexdigest()


def extract_candidates(pages: list[str], doc_date: date | None) -> tuple[list[dict[str, Any]], int]:
    """Return (candidates, discarded_count). Pure function, deterministic."""
    candidates: list[dict[str, Any]] = []
    discarded = 0
    seen_descriptions: set[str] = set()

    for page_index, page_text in enumerate(pages, start=1):
        normalised_page = re.sub(r"\s+", " ", page_text).lower()
        for sentence in _split_sentences(page_text):
            lower = sentence.lower()

            # Obligations
            for keyword, category, description, party, base_conf in _OBLIGATION_RULES:
                if keyword in lower and description not in seen_descriptions:
                    # Grounding: the quoted span must be present on the page.
                    if re.sub(r"\s+", " ", sentence).lower() not in normalised_page:
                        discarded += 1
                        continue
                    due_date, expression = _resolve_relative(sentence, doc_date)
                    if due_date is None and expression is None:
                        absolute = _parse_absolute(sentence)
                        if absolute and (doc_date is None or absolute >= doc_date):
                            due_date = absolute
                    confidence = base_conf
                    if due_date is not None:
                        confidence = min(0.97, confidence + 0.05)
                    candidates.append({
                        "kind": "obligation",
                        "category": category,
                        "description": description,
                        "responsible_party": party,
                        "due_date": due_date,
                        "due_expression": expression,
                        "field_name": None,
                        "field_value": None,
                        "source_page": page_index,
                        "source_quote": sentence,
                        "confidence": round(confidence, 2),
                        "grounded": True,
                    })
                    seen_descriptions.add(description)
                    break  # one obligation per sentence

            # Validity fields
            for keyword, field_name in _VALIDITY_RULES:
                if keyword in lower:
                    if re.sub(r"\s+", " ", sentence).lower() not in normalised_page:
                        discarded += 1
                        continue
                    value = _parse_absolute(sentence)
                    if value is None:
                        continue
                    key = f"{field_name}:{value.isoformat()}"
                    if key in seen_descriptions:
                        continue
                    candidates.append({
                        "kind": "validity",
                        "category": "VALIDITY",
                        "description": f"{field_name.replace('_', ' ').title()}: {value.isoformat()}",
                        "responsible_party": "INSTITUTION",
                        "due_date": None,
                        "due_expression": None,
                        "field_name": field_name,
                        "field_value": value.isoformat(),
                        "source_page": page_index,
                        "source_quote": sentence,
                        "confidence": 0.9,
                        "grounded": True,
                    })
                    seen_descriptions.add(key)
                    break
    return candidates, discarded


def run_extraction(db: Session, document: Document, actor: User, request_id: str) -> ExtractionRun:
    started = datetime.now()
    pages = json.loads(document.pages_json)
    candidates, discarded = extract_candidates(pages, document.doc_date)
    latency_ms = max(1, int((datetime.now() - started).total_seconds() * 1000))

    # Clear previous pending candidates for a clean re-run (accepted ones are kept).
    db.query(ObligationCandidate).filter(
        ObligationCandidate.document_id == document.id,
        ObligationCandidate.status == "PENDING",
    ).delete()

    run = ExtractionRun(
        document_id=document.id,
        provider="rule_based",
        model="flowwise-rules-v1",
        status="COMPLETED",
        candidates_total=len(candidates),
        candidates_grounded=len(candidates),
        candidates_discarded=discarded,
        latency_ms=latency_ms,
        created_at=Clock.now(),
    )
    db.add(run)
    db.flush()
    for item in candidates:
        db.add(ObligationCandidate(
            run_id=run.id,
            document_id=document.id,
            kind=item["kind"],
            category=item["category"],
            description=item["description"],
            responsible_party=item["responsible_party"],
            due_date=item["due_date"],
            due_expression=item["due_expression"],
            field_name=item["field_name"],
            field_value=item["field_value"],
            source_page=item["source_page"],
            source_quote=item["source_quote"],
            confidence=item["confidence"],
            grounded=item["grounded"],
            status="PENDING",
        ))
    append_event(
        db, actor.id, "EXTRACTION_RUN", "document", str(document.id),
        after={"candidates": len(candidates), "discarded": discarded, "provider": "rule_based"},
        request_id=request_id,
    )
    db.commit()
    db.refresh(run)
    return run


def accept_candidate(db: Session, candidate: ObligationCandidate, actor: User, request_id: str, edit: dict[str, Any] | None = None) -> Undertaking | None:
    if candidate.status == "ACCEPTED":
        raise ValueError("This candidate was already accepted")
    document = db.get(Document, candidate.document_id)
    edited = False
    if edit:
        if edit.get("description"):
            candidate.description = edit["description"]
            edited = True
        if edit.get("due_date"):
            candidate.due_date = date.fromisoformat(edit["due_date"])
            edited = True
    candidate.status = "ACCEPTED"
    candidate.reviewed_by = actor.id
    candidate.edited = edited

    created: Undertaking | None = None
    if candidate.kind == "obligation":
        institution_id = document.institution_id if document else None
        if institution_id is None:
            institution = db.query(Institution).order_by(Institution.id).first()
            institution_id = institution.id if institution else None
        due_at = datetime.combine(candidate.due_date or (Clock.now().date() + timedelta(days=30)), datetime.min.time())
        provenance = f"Doc #{candidate.document_id} p.{candidate.source_page} · run #{candidate.run_id}"
        created = Undertaking(
            institution_id=institution_id,
            application_id=document.application_id if document else None,
            title=candidate.description,
            due_at=due_at,
            status="NOT_DUE",
            source=provenance[:80],
        )
        db.add(created)
    append_event(
        db, actor.id, "OBLIGATION_ACCEPTED", "obligation_candidate", str(candidate.id),
        after={"description": candidate.description, "edited": edited, "kind": candidate.kind, "page": candidate.source_page},
        request_id=request_id,
    )
    db.commit()
    return created


def reject_candidate(db: Session, candidate: ObligationCandidate, actor: User, request_id: str) -> None:
    candidate.status = "REJECTED"
    candidate.reviewed_by = actor.id
    append_event(
        db, actor.id, "OBLIGATION_REJECTED", "obligation_candidate", str(candidate.id),
        after={"description": candidate.description}, request_id=request_id,
    )
    db.commit()
