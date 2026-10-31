"""Long-term memory. Only a contact preference is stored. Secrets are refused."""

import re
from datetime import datetime
from pathlib import Path

import store

SECRET_RE = re.compile(
    r"(\botp\b\s*(is|:)?\s*\d{4,8})"
    r"|(\bpassword\b\s*(is|:)\s*\S+)"
    r"|(\bcvv\b\s*(is|:)?\s*\d{3,4})"
    r"|(\baadhaa?r\b\s*(number\s*)?(is|:)?\s*\d{4,})",
    re.I,
)


def is_secret(text):
    return bool(SECRET_RE.search(text or ""))


def redact(text):
    return SECRET_RE.sub("[secret removed]", text or "")


def extract_preference(text):
    q = (text or "").lower()
    if "email" in q:
        return "email"
    if "phone" in q or "call me" in q:
        return "phone"
    if "sms" in q or "text message" in q:
        return "sms"
    return None


def _path(data_dir):
    return Path(data_dir) / "memory.json"


def relevant(student_id, data_dir):
    """Return only the saved preference for this student, not the whole file."""
    all_mem = store.read_json(_path(data_dir), {})
    rec = all_mem.get(student_id) or {}
    if rec.get("contact_preference"):
        return {"contact_preference": rec["contact_preference"]}
    return {}


def save_preference(student_id, preference, data_dir):
    path = _path(data_dir)
    all_mem = store.read_json(path, {})
    rec = all_mem.get(student_id) or {}
    rec["contact_preference"] = preference
    rec["updated"] = datetime.now().isoformat(timespec="seconds")
    all_mem[student_id] = rec
    store.write_json(path, all_mem)


def dump_student(student_id, data_dir):
    all_mem = store.read_json(_path(data_dir), {})
    return all_mem.get(student_id) or {}
