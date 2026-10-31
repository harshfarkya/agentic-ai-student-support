"""Agent loop: plan, select only the needed context, then answer."""

import json
import time
from pathlib import Path

import memory
import retrieval
import store
import tools

DATA = Path(__file__).resolve().parent / "data"


def estimate_tokens(text):
    """Rough size of text. About 4 characters per token. Not an API report."""
    return max(1, (len(text or "") + 3) // 4)


def plan(question):
    q = question.lower()
    if "support request" in q or "support ticket" in q:
        return "support"
    if "scholarship" in q and any(word in q for word in ("status", "my ", "do i", "am i")):
        return "scholarship"
    if any(phrase in q for phrase in ("fee status", "my fee", "my fees", "fee due", "fees due")):
        return "fee"
    if any(
        phrase in q
        for phrase in (
            "contact me",
            "contact preference",
            "how should you contact",
            "how will you contact",
            "what do you remember",
            "what did i ask",
        )
    ):
        return "recall"
    if "remember" in q or "i prefer" in q:
        return "remember"
    return "policy"


def compose_fee(context):
    result = context.get("tool_result") or {}
    if result.get("error") == "student_not_found":
        return (
            "I could not find that student record, so I cannot confirm the fee status. "
            "Check the student id and try again."
        )
    if not result.get("ok"):
        return "The fee tool failed, so I am not guessing the fee status."
    return (
        f"Fee status for {result['student_id']} ({result['name']}): {result['fee_status']}. "
        f"Amount due for {result['term']}: INR {result['fee_due']}."
    )


def compose_scholarship(context):
    result = context.get("tool_result") or {}
    if result.get("error") == "student_not_found":
        return (
            "I could not find that student record, so I cannot confirm the scholarship status."
        )
    if not result.get("ok"):
        return "The scholarship tool failed, so I am not guessing the scholarship status."
    return (
        f"Scholarship status for {result['student_id']} ({result['name']}): "
        f"{result['scholarship']}."
    )


def compose_support(context):
    result = context.get("tool_result") or {}
    if result.get("error") == "student_not_found":
        return "I could not find that student, so the support request was not created."
    if result.get("error") == "secret_not_stored":
        return "I did not create a support request because the message contains a secret."
    if not result.get("ok"):
        return "The support tool failed, so no request was created."
    return (
        f"Support request {result['request_id']} has been created for {result['student_id']}."
    )


def compose_recall(context):
    saved = (context.get("memory") or {}).get("contact_preference")
    if not saved:
        return "I do not have a saved contact preference for you yet."
    return f"You asked to be contacted by {saved}."


def compose_policy(context):
    chunks = context.get("policy") or []
    if not chunks:
        return "The student handbook does not contain enough information to answer this."
    lines = [f"{chunk['title']}: {chunk['text']}" for chunk in chunks]
    return "From the student handbook:\n" + "\n".join(lines)


def run_turn(question, student_id, data_dir=None):
    data_dir = Path(data_dir or DATA)
    start = time.perf_counter()
    question = (question or "").strip()
    student_id = (student_id or "").strip()

    steps = []
    tool_name = None
    tool_ok = None
    chunks = []
    memory_used = {}
    memory_write = "none"
    context = {}

    if not question:
        intent = "empty"
        answer = "Please type a question."
        steps.append("plan: empty")
    elif memory.is_secret(question):
        intent = "secret"
        context = {"question": memory.redact(question)}
        answer = (
            "That looks like a password, OTP, or similar secret. "
            "I have not saved it to memory."
        )
        memory_write = "skipped_secret"
        steps.extend(
            [
                "plan: secret statement",
                "retrieval: skipped",
                "tool: none",
                "memory_write: skipped_secret",
                "context: redacted question only",
                "chat history excluded",
            ]
        )
    else:
        intent = plan(question)
        steps.append(f"plan: {intent}")
        context = {"question": question}

        if intent == "recall":
            memory_used = memory.relevant(student_id, data_dir)
            if memory_used:
                context["memory"] = memory_used
            steps.append(
                "memory: loaded contact preference" if memory_used else "memory: nothing saved"
            )
            steps.extend(["retrieval: skipped", "tool: none", "chat history excluded"])
            answer = compose_recall(context)
        elif intent == "remember":
            preference = memory.extract_preference(question)
            steps.extend(["retrieval: skipped", "tool: none"])
            if preference:
                memory.save_preference(student_id, preference, data_dir)
                memory_write = "saved_contact_preference"
                context["saved"] = {"contact_preference": preference}
                answer = (
                    f"Saved your contact preference as {preference}. "
                    "It will still be there in a new session. I stored only that preference, not the full message."
                )
            else:
                memory_write = "nothing_to_save"
                answer = "I did not find a contact preference to save. You can say: I prefer email."
            steps.extend([f"memory_write: {memory_write}", "chat history excluded"])
        elif intent == "fee":
            tool_name = "get_fee_status"
            tool_result = tools.get_fee_status(student_id, data_dir)
            tool_ok = bool(tool_result.get("ok"))
            context["tool_result"] = tool_result
            steps.extend(
                [
                    "retrieval: skipped",
                    f"tool: get_fee_status ({'ok' if tool_ok else 'error'})",
                    "context: question + fee tool result",
                    "chat history excluded",
                ]
            )
            answer = compose_fee(context)
        elif intent == "scholarship":
            tool_name = "get_scholarship_status"
            tool_result = tools.get_scholarship_status(student_id, data_dir)
            tool_ok = bool(tool_result.get("ok"))
            context["tool_result"] = tool_result
            steps.extend(
                [
                    "retrieval: skipped",
                    f"tool: get_scholarship_status ({'ok' if tool_ok else 'error'})",
                    "context: question + scholarship tool result",
                    "chat history excluded",
                ]
            )
            answer = compose_scholarship(context)
        elif intent == "support":
            tool_name = "create_support_request"
            tool_result = tools.create_support_request(student_id, question, data_dir)
            tool_ok = bool(tool_result.get("ok"))
            context["tool_result"] = {
                key: value
                for key, value in tool_result.items()
                if key != "issue"
            }
            steps.extend(
                [
                    "retrieval: skipped",
                    f"tool: create_support_request ({'ok' if tool_ok else 'error'})",
                    "context: question + support tool result",
                    "chat history excluded",
                ]
            )
            answer = compose_support({"tool_result": tool_result})
        else:
            chunks = retrieval.retrieve(question, data_dir)
            if chunks:
                context["policy"] = [
                    {"id": chunk["id"], "title": chunk["title"], "text": chunk["text"]}
                    for chunk in chunks
                ]
            steps.extend(
                [
                    "retrieval: "
                    + (", ".join(chunk["id"] for chunk in chunks) if chunks else "no matching chunk"),
                    "tool: none",
                    "context: question + matching handbook section only",
                    "chat history excluded",
                ]
            )
            answer = compose_policy(context)

    context_text = json.dumps(context, ensure_ascii=False)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    trace = {
        "question": memory.redact(question) if memory.is_secret(question) else question,
        "student_id": student_id,
        "intent": intent,
        "steps": steps,
        "tool": tool_name,
        "tool_ok": tool_ok,
        "chunks": [chunk["id"] for chunk in chunks],
        "memory_used": memory_used,
        "memory_write": memory_write,
        "latency_ms": latency_ms,
        "input_tokens": estimate_tokens(context_text) if context else 1,
        "output_tokens": estimate_tokens(answer),
        "context": context,
    }
    store.append_jsonl(data_dir / "traces.jsonl", trace)
    return {"answer": answer, "trace": trace}
