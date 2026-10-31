"""Retrieve the best matching handbook section. The full file is not returned."""

import re
from pathlib import Path

STOP = {
    "the", "and", "for", "you", "your", "can", "may", "what", "how", "why",
    "is", "am", "are", "was", "were", "this", "that", "with", "from", "have",
    "has", "not", "but", "please", "about", "into", "does", "did", "will",
    "would", "could", "should", "because", "been", "being", "they", "them",
    "my", "me", "we", "our", "on", "in", "of", "to", "a", "an", "or", "if",
    "it", "its", "be", "do", "who", "whom", "which", "when", "where",
}


def tokens(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [word for word in words if word not in STOP and len(word) > 2]


def load_chunks(data_dir):
    text = (Path(data_dir) / "handbook.md").read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## ", text)
    chunks = []
    for part in parts[1:]:
        lines = part.strip().splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        chunk_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        chunks.append({"id": chunk_id, "title": title, "text": body})
    return chunks


def retrieve(question, data_dir):
    q_tokens = set(tokens(question))
    scored = []
    for chunk in load_chunks(data_dir):
        overlap = q_tokens & set(tokens(chunk["title"] + " " + chunk["text"]))
        if len(overlap) >= 2:
            scored.append((len(overlap), chunk))
    if not scored:
        return []
    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0][0]
    return [chunk for score, chunk in scored if score == best][:2]
