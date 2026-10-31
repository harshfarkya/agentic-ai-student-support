"""Audit log. Records who asked, what was attempted, the decision, and the result."""

from datetime import datetime
from pathlib import Path

import store


def record(data_dir, actor, action, target, decision, result, approver=None):
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "actor": actor,
        "action": action,
        "target": target,
        "decision": decision,
        "result": result,
    }
    if approver:
        entry["approver"] = approver
    path = Path(data_dir) / "audit.json"
    rows = store.read_json(path, [])
    rows.append(entry)
    store.write_json(path, rows)
    return entry


def all_rows(data_dir):
    return store.read_json(Path(data_dir) / "audit.json", [])
