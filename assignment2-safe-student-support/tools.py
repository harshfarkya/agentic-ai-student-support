"""Student tools. Private reads are allowed only when actor and target match."""

from pathlib import Path

import audit
import memory
import store


def _find(student_id, data_dir):
    rows = store.read_json(Path(data_dir) / "students.json", [])
    for row in rows:
        if row["student_id"].lower() == (student_id or "").lower():
            return row
    return None


def list_public(data_dir):
    rows = store.read_json(Path(data_dir) / "students.json", [])
    return [{"student_id": row["student_id"], "name": row["name"]} for row in rows]


def _blocked(actor_id, target_id, action, data_dir):
    if actor_id and target_id and actor_id.lower() == str(target_id).lower():
        return None
    audit.record(
        data_dir,
        actor_id or "unknown",
        action,
        target_id,
        "blocked",
        "not_executed",
    )
    return {
        "ok": False,
        "blocked": True,
        "tool": action,
    }


def get_fee_status(target_id, actor_id, data_dir):
    try:
        blocked = _blocked(actor_id, target_id, "get_fee_status", data_dir)
        if blocked:
            return blocked
        row = _find(actor_id, data_dir)
        if not row:
            audit.record(data_dir, actor_id, "get_fee_status", actor_id, "allowed", "student_not_found")
            return {"ok": False, "error": "student_not_found", "tool": "get_fee_status"}
        audit.record(data_dir, actor_id, "get_fee_status", actor_id, "allowed", "returned_own_fee_status")
        return {
            "ok": True,
            "tool": "get_fee_status",
            "student_id": row["student_id"],
            "name": row["name"],
            "fee_status": row["fee_status"],
            "fee_due": row["fee_due"],
            "term": row["term"],
        }
    except Exception:
        return {"ok": False, "error": "tool_error", "tool": "get_fee_status"}


def get_scholarship_status(target_id, actor_id, data_dir):
    try:
        blocked = _blocked(actor_id, target_id, "get_scholarship_status", data_dir)
        if blocked:
            return blocked
        row = _find(actor_id, data_dir)
        if not row:
            audit.record(
                data_dir,
                actor_id,
                "get_scholarship_status",
                actor_id,
                "allowed",
                "student_not_found",
            )
            return {"ok": False, "error": "student_not_found", "tool": "get_scholarship_status"}
        audit.record(
            data_dir,
            actor_id,
            "get_scholarship_status",
            actor_id,
            "allowed",
            "returned_own_scholarship_status",
        )
        return {
            "ok": True,
            "tool": "get_scholarship_status",
            "student_id": row["student_id"],
            "name": row["name"],
            "scholarship": row["scholarship"],
        }
    except Exception:
        return {"ok": False, "error": "tool_error", "tool": "get_scholarship_status"}


def create_support_request(target_id, actor_id, issue, data_dir):
    try:
        blocked = _blocked(actor_id, target_id, "create_support_request", data_dir)
        if blocked:
            return blocked
        if memory.is_secret(issue):
            audit.record(
                data_dir, actor_id, "create_support_request", actor_id, "blocked", "secret_not_stored"
            )
            return {"ok": False, "error": "secret_not_stored", "tool": "create_support_request"}
        row = _find(actor_id, data_dir)
        if not row:
            return {"ok": False, "error": "student_not_found", "tool": "create_support_request"}
        path = Path(data_dir) / "support_requests.json"
        rows = store.read_json(path, [])
        request_id = f"SR-{len(rows) + 1:03d}"
        rows.append(
            {
                "request_id": request_id,
                "student_id": row["student_id"],
                "issue": issue,
            }
        )
        store.write_json(path, rows)
        audit.record(
            data_dir, actor_id, "create_support_request", actor_id, "allowed", f"created {request_id}"
        )
        return {
            "ok": True,
            "tool": "create_support_request",
            "request_id": request_id,
            "student_id": row["student_id"],
        }
    except Exception:
        return {"ok": False, "error": "tool_error", "tool": "create_support_request"}
