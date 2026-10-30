"""Generated letters with SHA-256 fingerprint and a QR verification code.

A letter is rendered to PDF with ReportLab, hashed, and stored under a random
verification token. The QR encodes a public verification URL. The public page
reports only document type, issue date, status and whether an uploaded file
matches the stored hash: no personal or sensitive content is exposed. This is
tamper evidence for the demo, not a legal signature.
"""
import hashlib
import io
import secrets
from datetime import datetime

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas
from sqlalchemy.orm import Session

from ..clock import Clock
from ..config import settings
from ..models import Application, Institution, Letter, User
from .audit import append_event


LETTER_TITLES = {
    "deficiency_notice": "DEFICIENCY NOTICE",
    "evc_schedule": "EXPERT VISIT COMMITTEE SCHEDULE",
    "confirmation_letter": "CONFIRMATION LETTER",
}


def _render_pdf(title: str, reference_no: str, lines: list[str], verify_url: str, fingerprint: str) -> bytes:
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 9)
    pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.drawString(20 * mm, height - 15 * mm, "SYNTHETIC DOCUMENT · SMART INDIA HACKATHON DEMO · NOT AN OFFICIAL AICTE LETTER")

    pdf.setFillColorRGB(0.12, 0.23, 0.37)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(20 * mm, height - 30 * mm, "AICTE FlowWise")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(20 * mm, height - 36 * mm, "All India Council for Technical Education (synthetic demo)")

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(20 * mm, height - 52 * mm, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(20 * mm, height - 60 * mm, f"Reference: {reference_no}")
    pdf.drawString(20 * mm, height - 66 * mm, f"Issued: {Clock.now().strftime('%Y-%m-%d %H:%M UTC')}")

    text = pdf.beginText(20 * mm, height - 82 * mm)
    text.setFont("Helvetica", 10.5)
    for line in lines:
        text.textLine(line)
    pdf.drawText(text)

    # Simulated signature block (labelled)
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(20 * mm, 55 * mm, "Authorised signatory (simulated signature block — demo only)")
    pdf.line(20 * mm, 52 * mm, 90 * mm, 52 * mm)

    # QR code for verification
    qr = qrcode.make(verify_url)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    pdf.drawImage(ImageReader(qr_buffer), 150 * mm, 30 * mm, 40 * mm, 40 * mm)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(150 * mm, 27 * mm, "Scan to verify authenticity")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(20 * mm, 20 * mm, f"SHA-256: {fingerprint}")
    pdf.drawString(20 * mm, 16 * mm, f"Verify: {verify_url}")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def generate_letter(db: Session, actor: User, application: Application, letter_type: str, body_lines: list[str], request_id: str) -> Letter:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(16)[:24]
    reference_no = f"LTR-{application.reference_no}-{secrets.token_hex(2).upper()}"
    verify_url = f"{settings.public_base_url}/verify/{token}"

    institution = db.get(Institution, application.institution_id)
    lines = [
        f"To: {institution.name if institution else 'the institution'}",
        f"Case: {application.reference_no} ({application.application_type.replace('_', ' ')})",
        "",
    ] + body_lines

    # First render without the real fingerprint, hash the bytes, then the stored
    # hash is of the final file so verification of an uploaded copy is exact.
    draft = _render_pdf(LETTER_TITLES.get(letter_type, "OFFICIAL LETTER"), reference_no, lines, verify_url, "pending")
    fingerprint = hashlib.sha256(draft).hexdigest()
    final = _render_pdf(LETTER_TITLES.get(letter_type, "OFFICIAL LETTER"), reference_no, lines, verify_url, fingerprint)
    final_hash = hashlib.sha256(final).hexdigest()

    file_path = settings.storage_dir / f"{token}.pdf"
    file_path.write_bytes(final)

    letter = Letter(
        application_id=application.id,
        letter_type=letter_type,
        reference_no=reference_no,
        verify_token=token,
        sha256=final_hash,
        status="valid",
        file_path=str(file_path),
        issued_by=actor.id,
        issued_at=Clock.now(),
    )
    db.add(letter)
    db.flush()
    append_event(db, actor.id, "LETTER_GENERATED", "letter", reference_no, after={"type": letter_type, "sha256": final_hash, "token": token}, request_id=request_id)
    db.commit()
    db.refresh(letter)
    return letter


def verify_letter(db: Session, token: str, uploaded_sha256: str | None = None) -> dict:
    letter = db.query(Letter).filter(Letter.verify_token == token).first()
    if letter is None:
        return {"found": False}
    result = {
        "found": True,
        "letter_type": letter.letter_type,
        "reference_no": letter.reference_no,
        "issued_at": letter.issued_at.isoformat(),
        "status": letter.status,
        "stored_sha256": letter.sha256,
    }
    if uploaded_sha256 is not None:
        result["match"] = uploaded_sha256.lower() == letter.sha256.lower()
    return result
