"""Workflow Studio: template validation, dry-run and maker-checker publishing.

A workflow definition is a versioned directed graph. The validator enforces the
rules from the TRD (section 5.2): exactly one start, at least one terminal,
every stage reachable from start, every non-terminal has a path to a terminal,
transitions reference existing stages, task stages name a real role, and
conditions use only whitelisted predicates. Publication is maker-checker:
the approver must differ from the proposer, and published versions are immutable.
"""
import json
from typing import Any

from sqlalchemy.orm import Session

from ..clock import Clock
from ..models import User, WorkflowDefinition
from .audit import append_event


ROLE_CATALOGUE = {
    "SCRUTINY_OFFICER", "EVC_COORDINATOR", "SAC_SHC_MEMBER", "REGIONAL_OFFICER",
    "COMPLIANCE_OFFICER", "SYSTEM_ADMIN",
}

WHITELISTED_PREDICATES = {
    "no_open_deficiency", "open_deficiency", "docs_verified",
    "evc_report_received", "shc_recommendation_recorded", "visit_confirmed",
}


def _validate_condition(condition: Any, errors: list[str]) -> None:
    if condition is None:
        return
    if not isinstance(condition, dict):
        errors.append("A condition must be an object")
        return
    for combinator in ("all", "any"):
        if combinator in condition:
            clauses = condition[combinator]
            if not isinstance(clauses, list):
                errors.append(f"'{combinator}' must be a list of conditions")
            else:
                for clause in clauses:
                    _validate_condition(clause, errors)
            return
    if "not" in condition:
        _validate_condition(condition["not"], errors)
        return
    if "pred" in condition:
        if condition["pred"] not in WHITELISTED_PREDICATES:
            errors.append(f"Predicate '{condition['pred']}' is not whitelisted")
        return
    errors.append("A condition must use all/any/not or a whitelisted pred")


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    stages = graph.get("stages", [])
    transitions = graph.get("transitions", [])
    start = graph.get("start")

    if not stages:
        return {"valid": False, "errors": ["The graph has no stages"], "warnings": [], "checks": []}

    stage_codes = [s.get("code") for s in stages]
    stage_by_code = {s.get("code"): s for s in stages}
    terminal_codes = {s.get("code") for s in stages if s.get("type") == "terminal"}

    # Exactly one start
    start_count = sum(1 for s in stages if s.get("code") == start)
    if not start or start_count != 1:
        errors.append("The graph must name exactly one existing start stage")

    # At least one terminal
    if not terminal_codes:
        errors.append("The graph must have at least one terminal stage")

    # Transitions reference existing stages
    for transition in transitions:
        if transition.get("from") not in stage_by_code:
            errors.append(f"Transition from unknown stage '{transition.get('from')}'")
        if transition.get("to") not in stage_by_code:
            errors.append(f"Transition to unknown stage '{transition.get('to')}'")
        _validate_condition(transition.get("when"), errors)
        if transition.get("requires_reason") and transition.get("to") in stage_by_code:
            # return/revert must target an earlier stage
            try:
                if stage_codes.index(transition["to"]) >= stage_codes.index(transition["from"]):
                    warnings.append(f"Return transition {transition['from']}->{transition['to']} should target an earlier stage")
            except ValueError:
                pass

    # Task stages need a real role
    for stage in stages:
        if stage.get("type") != "terminal":
            role = stage.get("role")
            if not role:
                errors.append(f"Task stage '{stage.get('code')}' has no responsible role")
            elif role not in ROLE_CATALOGUE:
                errors.append(f"Stage '{stage.get('code')}' uses role '{role}' which is not in the role catalogue")

    # Reachability from start
    adjacency: dict[str, list[str]] = {code: [] for code in stage_codes}
    for transition in transitions:
        if transition.get("from") in adjacency and transition.get("to") in stage_by_code:
            adjacency[transition["from"]].append(transition["to"])

    reachable: set[str] = set()
    if start in stage_by_code:
        stack = [start]
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(adjacency.get(node, []))
    for code in stage_codes:
        if code not in reachable:
            errors.append(f"Stage '{code}' is not reachable from the start stage")

    # Every non-terminal stage can reach a terminal
    for code in stage_codes:
        if code in terminal_codes:
            continue
        seen: set[str] = set()
        stack = [code]
        reaches_terminal = False
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in terminal_codes:
                reaches_terminal = True
                break
            stack.extend(adjacency.get(node, []))
        if not reaches_terminal:
            errors.append(f"Stage '{code}' has no path to a terminal stage")

    checks = [
        {"label": "Exactly one start stage", "ok": bool(start) and start_count == 1},
        {"label": "At least one terminal stage", "ok": bool(terminal_codes)},
        {"label": "All stages reachable from start", "ok": all(c in reachable for c in stage_codes)},
        {"label": "Every stage reaches a terminal", "ok": not any("no path to a terminal" in e for e in errors)},
        {"label": "Transitions reference valid stages", "ok": not any("unknown stage" in e for e in errors)},
        {"label": "Task stages have catalogued roles", "ok": not any("role catalogue" in e or "no responsible role" in e for e in errors)},
        {"label": "Conditions use whitelisted predicates", "ok": not any("not whitelisted" in e or "whitelisted pred" in e for e in errors)},
    ]
    return {"valid": not errors, "errors": errors, "warnings": warnings, "checks": checks}


def dry_run(graph: dict[str, Any]) -> dict[str, Any]:
    """Walk a synthetic case greedily from the start; report the path reached."""
    validation = validate_graph(graph)
    if not validation["valid"]:
        return {"ok": False, "path": [], "message": "Fix validation errors before a dry-run", "validation": validation}
    stage_by_code = {s.get("code"): s for s in graph.get("stages", [])}
    transitions = graph.get("transitions", [])
    terminal = {s.get("code") for s in graph.get("stages", []) if s.get("type") == "terminal"}
    path: list[str] = []
    current = graph.get("start")
    visited: set[str] = set()
    steps = 0
    while current and current not in terminal and steps < 50:
        path.append(current)
        visited.add(current)
        # pick the first forward transition that does not require a reason (a return)
        nxt = next((t for t in transitions if t.get("from") == current and not t.get("requires_reason") and t.get("to") not in visited), None)
        if nxt is None:
            return {"ok": False, "path": path, "message": f"Dry-run stuck at '{current}' with no forward transition", "validation": validation}
        current = nxt.get("to")
        steps += 1
    if current in terminal:
        path.append(current)
        return {"ok": True, "path": path, "message": f"Synthetic case reached terminal stage '{current}' in {len(path) - 1} transition(s)", "validation": validation}
    return {"ok": False, "path": path, "message": "Dry-run did not reach a terminal stage", "validation": validation}


def serialize_definition(definition: WorkflowDefinition, proposer: str | None = None, approver: str | None = None) -> dict[str, Any]:
    return {
        "id": definition.id,
        "template_code": definition.template_code,
        "version": definition.version,
        "status": definition.status,
        "graph": json.loads(definition.graph_json),
        "proposed_by": proposer,
        "approved_by": approver,
        "reject_reason": definition.reject_reason,
        "updated_at": definition.updated_at.isoformat(),
    }


def create_draft(db: Session, actor: User, template_code: str, graph: dict[str, Any], request_id: str) -> WorkflowDefinition:
    now = Clock.now()
    latest = db.query(WorkflowDefinition).filter(WorkflowDefinition.template_code == template_code).order_by(WorkflowDefinition.version.desc()).first()
    version = (latest.version + 1) if latest else 1
    definition = WorkflowDefinition(
        template_code=template_code,
        version=version,
        status="DRAFT",
        graph_json=json.dumps(graph),
        proposed_by=actor.id,
        created_at=now,
        updated_at=now,
    )
    db.add(definition)
    db.flush()
    append_event(db, actor.id, "WORKFLOW_DRAFT_CREATED", "workflow_definition", str(definition.id), after={"template": template_code, "version": version}, request_id=request_id)
    db.commit()
    db.refresh(definition)
    return definition


def submit_for_approval(db: Session, actor: User, definition: WorkflowDefinition, request_id: str) -> None:
    graph = json.loads(definition.graph_json)
    validation = validate_graph(graph)
    if not validation["valid"]:
        raise ValueError("The graph fails validation and cannot be submitted")
    definition.status = "SUBMITTED_FOR_APPROVAL"
    definition.updated_at = Clock.now()
    append_event(db, actor.id, "WORKFLOW_SUBMITTED", "workflow_definition", str(definition.id), after={"status": definition.status}, request_id=request_id)
    db.commit()


def publish(db: Session, approver: User, definition: WorkflowDefinition, request_id: str) -> None:
    if definition.status != "SUBMITTED_FOR_APPROVAL":
        raise ValueError("Only a submitted definition can be published")
    if definition.proposed_by == approver.id:
        raise ValueError("The approver must be different from the proposer (maker-checker)")
    # Retire the currently published version of the same template.
    for other in db.query(WorkflowDefinition).filter(
        WorkflowDefinition.template_code == definition.template_code,
        WorkflowDefinition.status == "PUBLISHED",
    ).all():
        other.status = "RETIRED"
        other.updated_at = Clock.now()
    definition.status = "PUBLISHED"
    definition.approved_by = approver.id
    definition.updated_at = Clock.now()
    append_event(db, approver.id, "WORKFLOW_PUBLISHED", "workflow_definition", str(definition.id), after={"template": definition.template_code, "version": definition.version, "approved_by": approver.id}, request_id=request_id)
    db.commit()


def reject(db: Session, approver: User, definition: WorkflowDefinition, reason: str, request_id: str) -> None:
    if definition.status != "SUBMITTED_FOR_APPROVAL":
        raise ValueError("Only a submitted definition can be rejected")
    if definition.proposed_by == approver.id:
        raise ValueError("The approver must be different from the proposer (maker-checker)")
    definition.status = "REJECTED"
    definition.approved_by = approver.id
    definition.reject_reason = reason
    definition.updated_at = Clock.now()
    append_event(db, approver.id, "WORKFLOW_REJECTED", "workflow_definition", str(definition.id), reason=reason, after={"status": "REJECTED"}, request_id=request_id)
    db.commit()
