"""Tools the agent can call. Each tool returns data or a clear error."""

from pathlib import Path

import memory
import store


def _students(data_dir):
    return store.read_json(Path(data_dir) / "students.json", [])


def _find(student_id, data_dir):
    for row in _students(data_dir):
        if row["student_id"].lower() == (student_id or "").lower():
            return row
    return None


def list_public(data_dir):
    return [
        {"student_id": row["student_id"], "name": row["name"]}
        for row in _students(data_dir)
    ]


def get_fee_status(student_id, data_dir):
    try:
        row = _find(student_id, data_dir)
        if not row:
            return {"ok": False, "error": "student_not_found", "tool": "get_fee_status"}
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


def get_scholarship_status(student_id, data_dir):
    try:
        row = _find(student_id, data_dir)
        if not row:
            return {
                "ok": False,
                "error": "student_not_found",
                "tool": "get_scholarship_status",
            }
        return {
            "ok": True,
            "tool": "get_scholarship_status",
            "student_id": row["student_id"],
            "name": row["name"],
            "scholarship": row["scholarship"],
        }
    except Exception:
        return {"ok": False, "error": "tool_error", "tool": "get_scholarship_status"}


def create_support_request(student_id, issue, data_dir):
    try:
        if memory.is_secret(issue):
            return {
                "ok": False,
                "error": "secret_not_stored",
                "tool": "create_support_request",
            }
        row = _find(student_id, data_dir)
        if not row:
            return {
                "ok": False,
                "error": "student_not_found",
                "tool": "create_support_request",
            }
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
        return {
            "ok": True,
            "tool": "create_support_request",
            "request_id": request_id,
            "student_id": row["student_id"],
            "issue": issue,
        }
    except Exception:
        return {"ok": False, "error": "tool_error", "tool": "create_support_request"}
