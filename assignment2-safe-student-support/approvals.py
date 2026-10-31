"""Programme changes wait here until a person approves or rejects them."""

from datetime import datetime
from pathlib import Path

import audit
import store


def _students(data_dir):
    return store.read_json(Path(data_dir) / "students.json", [])


def _own(actor_id, data_dir):
    for row in _students(data_dir):
        if row["student_id"] == actor_id:
            return row
    return None


def request_change(actor_id, target_id, new_programme, data_dir):
    """Create a pending approval. This does not edit the student record."""
    if not actor_id or not target_id or actor_id.lower() != target_id.lower():
        audit.record(
            data_dir,
            actor_id or "unknown",
            "programme_change",
            target_id,
            "blocked",
            "not_executed",
        )
        return {
            "ok": False,
            "blocked": True,
            "executed": False,
            "tool": "request_programme_change",
        }
    student = _own(actor_id, data_dir)
    if student is None:
        return {
            "ok": False,
            "error": "student_not_found",
            "executed": False,
            "tool": "request_programme_change",
        }
    if not new_programme:
        return {
            "ok": False,
            "error": "missing_programme",
            "executed": False,
            "tool": "request_programme_change",
        }
    path = Path(data_dir) / "approvals.json"
    rows = store.read_json(path, [])
    approval_id = f"APR-{len(rows) + 1:03d}"
    rows.append(
        {
            "id": approval_id,
            "student_id": actor_id,
            "action": "programme_change",
            "new_programme": new_programme,
            "current_programme": student["programme"],
            "status": "pending",
            "requested_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    store.write_json(path, rows)
    audit.record(
        data_dir,
        actor_id,
        "programme_change",
        actor_id,
        "pending",
        f"waiting_for_staff {approval_id}",
    )
    return {
        "ok": True,
        "pending": True,
        "executed": False,
        "tool": "request_programme_change",
        "approval_id": approval_id,
        "current_programme": student["programme"],
        "new_programme": new_programme,
    }


def all_rows(data_dir):
    return store.read_json(Path(data_dir) / "approvals.json", [])


def decide(approval_id, decision, approver, data_dir):
    """The only place that may change a programme, and only after approval."""
    path = Path(data_dir) / "approvals.json"
    rows = store.read_json(path, [])
    item = next((row for row in rows if row["id"] == approval_id), None)
    if item is None:
        return {"ok": False, "error": "not_found"}
    if item["status"] != "pending":
        return {"ok": False, "error": "already_decided", "status": item["status"]}
    if decision not in ("approve", "reject"):
        return {"ok": False, "error": "bad_decision"}

    now = datetime.now().isoformat(timespec="seconds")
    if decision == "reject":
        item["status"] = "rejected"
        item["approver"] = approver
        item["decided_at"] = now
        store.write_json(path, rows)
        audit.record(
            data_dir,
            item["student_id"],
            "programme_change",
            item["student_id"],
            "rejected",
            "not_executed",
            approver=approver,
        )
        return {
            "ok": True,
            "status": "rejected",
            "executed": False,
            "message": f"{approval_id} rejected. The programme was not changed.",
        }

    students_path = Path(data_dir) / "students.json"
    students = store.read_json(students_path, [])
    updated = False
    for student in students:
        if student["student_id"] == item["student_id"]:
            student["programme"] = item["new_programme"]
            updated = True
    if not updated:
        return {"ok": False, "error": "student_not_found", "executed": False}
    item["status"] = "approved"
    item["approver"] = approver
    item["decided_at"] = now
    store.write_json(students_path, students)
    store.write_json(path, rows)
    audit.record(
        data_dir,
        item["student_id"],
        "programme_change",
        item["student_id"],
        "approved",
        "programme_updated",
        approver=approver,
    )
    return {
        "ok": True,
        "status": "approved",
        "executed": True,
        "programme": item["new_programme"],
        "message": f"{approval_id} approved. Programme is now {item['new_programme']}.",
    }
