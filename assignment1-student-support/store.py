"""Small JSON helpers used by the agent."""

import json
import threading
from pathlib import Path

LOCK = threading.Lock()


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with LOCK:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    with LOCK:
        path.write_text(text, encoding="utf-8")


def append_jsonl(path, item):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(item, ensure_ascii=False)
    with LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
