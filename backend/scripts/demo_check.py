import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from backend.app.main import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.json() == {"status": "ok"} and health.headers.get("X-Request-ID"), health.text
    login = client.post("/api/v1/auth/login", json={"email": "system_admin@demo.test", "password": "demo1234"})
    assert login.status_code == 200, login.text
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    reset = client.post("/api/v1/demo/reset", headers=admin_headers, json={})
    assert reset.status_code == 200, reset.text
    summary = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert summary.status_code == 200 and summary.json()["total"] == 40, summary.text
    plan = client.post("/api/v1/evc/plans", headers=admin_headers, json={})
    assert plan.status_code == 200, plan.text
    proposal = plan.json()
    assert proposal["scheduled_count"] > 0 and proposal["violations"] == [], proposal
    assert all(len(item["panel"]) == item["panel_size"] for item in proposal["assignments"] if item["scheduled"])
    plan_id = proposal["plan_id"]
    stored_plan = client.get(f"/api/v1/evc/plans/{plan_id}", headers=admin_headers)
    assert stored_plan.status_code == 200 and stored_plan.json()["status"] == "PROPOSED", stored_plan.text
    baseline = client.get(f"/api/v1/evc/plans/{plan_id}/baseline", headers=admin_headers)
    assert baseline.status_code == 200 and baseline.json()["metrics"]["scheduled_count"] >= 0, baseline.text
    confirmed = client.post(f"/api/v1/evc/plans/{plan_id}/confirm", headers=admin_headers, json={})
    assert confirmed.status_code == 200 and confirmed.json()["confirmed_count"] == proposal["scheduled_count"], confirmed.text
    simulation = client.post(
        "/api/v1/simulations",
        headers=admin_headers,
        json={"additional_scrutiny_officers": {"NR": 2}, "replications": 30, "working_days": 120, "seed": 42},
    )
    assert simulation.status_code == 200, simulation.text
    metrics = simulation.json()
    assert metrics["scenario"]["NR"]["SCRUTINY"]["p90_hours"] <= metrics["baseline"]["NR"]["SCRUTINY"]["p90_hours"], metrics
    audit = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert audit.status_code == 200 and audit.json()["valid"], audit.text

    officer_login = client.post("/api/v1/auth/login", json={"email": "scrutiny_officer@demo.test", "password": "demo1234"})
    applicant_login = client.post("/api/v1/auth/login", json={"email": "institution_applicant@demo.test", "password": "demo1234"})
    officer = {"Authorization": f"Bearer {officer_login.json()['access_token']}"}
    applicant = {"Authorization": f"Bearer {applicant_login.json()['access_token']}"}
    cases = client.get("/api/v1/applications?q=FW-2026-0002", headers=officer)
    assert cases.status_code == 200 and len(cases.json()) == 1, cases.text
    case = cases.json()[0]
    blocked = client.post(
        f"/api/v1/applications/{case['id']}/transitions",
        headers={**officer, "Idempotency-Key": "missing-reason"},
        json={"event": "ISSUE_DEFICIENCY", "expected_version": case["version"]},
    )
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "REASON_REQUIRED", blocked.text
    unrelated = client.get("/api/v1/applications?q=FW-2026-0005", headers=officer)
    assert unrelated.status_code == 200 and unrelated.json() == [], unrelated.text
    other_institution = client.get("/api/v1/applications", headers=admin_headers).json()
    other_case = next(item for item in other_institution if item["reference_no"] == "FW-2026-0004")
    denied = client.get(f"/api/v1/applications/{other_case['id']}", headers=applicant)
    assert denied.status_code == 404, denied.text
    issue = client.post(
        f"/api/v1/applications/{case['id']}/observations",
        headers={**officer, "Idempotency-Key": "demo-deficiency"},
        json={"category": "DOCUMENTATION", "remarks": "Synthetic demo deficiency for the workflow check."},
    )
    assert issue.status_code == 200, issue.text
    retry = client.post(
        f"/api/v1/applications/{case['id']}/observations",
        headers={**officer, "Idempotency-Key": "demo-deficiency"},
        json={"category": "DOCUMENTATION", "remarks": "Synthetic demo deficiency for the workflow check."},
    )
    assert retry.status_code == 200, retry.text
    open_items = client.get(f"/api/v1/applications/{case['id']}/observations", headers=applicant).json()
    assert len(open_items) == 1, open_items
    response = client.post(
        f"/api/v1/applications/{case['id']}/responses",
        headers={**applicant, "Idempotency-Key": "demo-response"},
        json={"observation_id": open_items[0]["id"], "text": "Synthetic response submitted for review."},
    )
    assert response.status_code == 200, response.text
    current = client.get(f"/api/v1/applications/{case['id']}", headers=officer).json()
    complete = client.post(
        f"/api/v1/applications/{case['id']}/transitions",
        headers={**officer, "Idempotency-Key": "demo-complete"},
        json={"event": "COMPLETE_SCRUTINY", "expected_version": current["version"]},
    )
    assert complete.status_code == 200 and complete.json()["stage"] == "EVC", complete.text
    holders = client.get(f"/api/v1/applications/{case['id']}/sla", headers=officer).json()["segments"]
    assert [segment["holder"] for segment in holders] == ["AICTE_OFFICER", "INSTITUTION", "AICTE_OFFICER", "AICTE_OFFICER"]

    audit = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert audit.status_code == 200 and audit.json()["valid"], audit.text
    tamper = client.post("/api/v1/demo/tamper", headers=admin_headers, json={})
    assert tamper.status_code == 200, tamper.text
    verification = client.get("/api/v1/audit/verify", headers=admin_headers).json()
    assert not verification["valid"] and verification["first_bad_index"] == 0, verification
    client.post("/api/v1/demo/reset", headers=admin_headers, json={})
    print("Demo check passed: seeded reset, login, deficiency loop, SLA holder changes and audit tamper detection.")


if __name__ == "__main__":
    main()
