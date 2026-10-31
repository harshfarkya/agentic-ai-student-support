"""Login check. The PIN is compared here in Python, not by the answer text."""

from pathlib import Path

import audit
import store


def _find(student_id, data_dir):
    rows = store.read_json(Path(data_dir) / "students.json", [])
    for row in rows:
        if row["student_id"].lower() == (student_id or "").lower():
            return row
    return None


def authenticate(student_id, pin, data_dir):
    student_id = (student_id or "").strip()
    row = _find(student_id, data_dir)
    if row is None or str(row.get("pin")) != str(pin or "").strip():
        audit.record(
            data_dir,
            student_id or "unknown",
            "login",
            student_id or "unknown",
            "denied",
            "bad_credentials",
        )
        return None
    audit.record(data_dir, row["student_id"], "login", row["student_id"], "allowed", "signed_in")
    return {
        "student_id": row["student_id"],
        "name": row["name"],
        "programme": row["programme"],
    }


def profile(student_id, data_dir):
    """Own name and programme only. Fee, scholarship, and PIN are not included."""
    row = _find(student_id, data_dir)
    if row is None:
        return None
    return {
        "student_id": row["student_id"],
        "name": row["name"],
        "programme": row["programme"],
    }
