"""Run the Assignment 1 test questions and write evaluation.md."""

import json
import shutil
import tempfile
from pathlib import Path

import agent
import memory

PROJECT = Path(__file__).resolve().parent
DATA = PROJECT / "data"


def make_sandbox():
    sandbox = Path(tempfile.mkdtemp()) / "data"
    sandbox.mkdir(parents=True)
    shutil.copy(DATA / "handbook.md", sandbox / "handbook.md")
    shutil.copy(DATA / "students.json", sandbox / "students.json")
    return sandbox


def contains_all(text, phrases):
    lower = (text or "").lower()
    return [phrase for phrase in phrases if phrase.lower() not in lower]


def contains_any_banned(text, phrases):
    lower = (text or "").lower()
    return [phrase for phrase in phrases if phrase.lower() in lower]


def row_from(test_id, question, result, ok, notes):
    trace = result["trace"]
    return {
        "id": test_id,
        "question": question,
        "success": ok,
        "notes": notes,
        "tool": trace.get("tool"),
        "chunks": trace.get("chunks"),
        "memory_write": trace.get("memory_write"),
        "memory_used": trace.get("memory_used"),
        "latency_ms": trace.get("latency_ms"),
        "input_tokens": trace.get("input_tokens"),
        "output_tokens": trace.get("output_tokens"),
        "answer": result["answer"],
        "trace": trace,
    }


def finish(test_id, question, result, problems):
    return row_from(test_id, question, result, not problems, "; ".join(problems))


def main():
    sandbox = make_sandbox()
    rows = []
    try:
        fee = agent.run_turn("What is my current fee status?", "S101", sandbox)
        problems = contains_all(fee["answer"], ["45000", "partially paid"])
        if fee["trace"]["tool"] != "get_fee_status":
            problems.append("wrong tool")
        rows.append(finish("Q1", "What is my current fee status?", fee, problems))

        scholarship = agent.run_turn("What is my scholarship status?", "S101", sandbox)
        problems = contains_all(scholarship["answer"], ["20 percent"])
        if scholarship["trace"]["tool"] != "get_scholarship_status":
            problems.append("wrong tool")
        rows.append(finish("Q2", "What is my scholarship status?", scholarship, problems))

        portal = agent.run_turn(
            "The payment portal failed. Can I pay on the next working day?",
            "S101",
            sandbox,
        )
        problems = contains_all(portal["answer"], ["next working day"])
        if portal["trace"]["chunks"] != ["payment-portal-failure"]:
            problems.append("wrong chunk " + str(portal["trace"]["chunks"]))
        if portal["trace"]["tool"] is not None:
            problems.append("tool should not be used")
        rows.append(
            finish(
                "Q3",
                "The payment portal failed. Can I pay on the next working day?",
                portal,
                problems,
            )
        )

        saved = agent.run_turn("Please remember that I prefer email updates.", "S101", sandbox)
        recalled = agent.run_turn("How should you contact me?", "S101", sandbox)
        problems = contains_all(recalled["answer"], ["email"])
        if saved["trace"]["memory_write"] != "saved_contact_preference":
            problems.append("preference was not saved")
        if (recalled["trace"].get("memory_used") or {}).get("contact_preference") != "email":
            problems.append("new turn did not use saved memory")
        combined = {
            "answer": recalled["answer"],
            "trace": dict(recalled["trace"]),
        }
        combined["trace"]["latency_ms"] = round(
            saved["trace"]["latency_ms"] + recalled["trace"]["latency_ms"], 1
        )
        combined["trace"]["input_tokens"] = (
            saved["trace"]["input_tokens"] + recalled["trace"]["input_tokens"]
        )
        combined["trace"]["output_tokens"] = (
            saved["trace"]["output_tokens"] + recalled["trace"]["output_tokens"]
        )
        rows.append(
            finish("Q4", "Remember email, then ask in a new turn", combined, problems)
        )

        secret = agent.run_turn("My OTP is 482913", "S101", sandbox)
        memory_text = (sandbox / "memory.json").read_text(encoding="utf-8")
        problems = contains_all(secret["answer"], ["not saved"])
        if "482913" in memory_text or "482913" in secret["trace"]["question"]:
            problems.append("secret was stored")
        if "email" not in memory_text:
            problems.append("older preference was lost")
        rows.append(finish("Q5", "My OTP is 482913", secret, problems))

        wifi = agent.run_turn("What is the hostel Wi-Fi password?", "S101", sandbox)
        problems = contains_all(wifi["answer"], ["does not contain enough information"])
        if wifi["trace"]["chunks"]:
            problems.append("unexpected chunk")
        rows.append(finish("Q6", "What is the hostel Wi-Fi password?", wifi, problems))

        support = agent.run_turn(
            "Please create a support request because the payment portal failed.",
            "S101",
            sandbox,
        )
        problems = contains_all(support["answer"], ["SR-"])
        if support["trace"]["tool"] != "create_support_request":
            problems.append("wrong tool")
        rows.append(
            finish(
                "Q7",
                "Please create a support request because the payment portal failed.",
                support,
                problems,
            )
        )

        missing = agent.run_turn("What is my current fee status?", "Z999", sandbox)
        problems = contains_all(missing["answer"], ["could not find"])
        banned = contains_any_banned(missing["answer"], ["45000", "125000"])
        problems.extend(f"invented {item}" for item in banned)
        if missing["trace"]["tool"] != "get_fee_status" or missing["trace"]["tool_ok"]:
            problems.append("tool error was not reported")
        rows.append(finish("Q8", "Fee status for unknown id Z999", missing, problems))
    finally:
        shutil.rmtree(sandbox.parent, ignore_errors=True)

    passed = sum(1 for row in rows if row["success"])
    avg_latency = round(sum(row["latency_ms"] for row in rows) / len(rows), 1)
    avg_in = round(sum(row["input_tokens"] for row in rows) / len(rows), 1)
    avg_out = round(sum(row["output_tokens"] for row in rows) / len(rows), 1)
    summary = {
        "assignment": 1,
        "passed": passed,
        "total": len(rows),
        "accuracy_pct": round(100 * passed / len(rows), 1),
        "avg_latency_ms": avg_latency,
        "avg_input_tokens": avg_in,
        "avg_output_tokens": avg_out,
    }

    lines = [
        "# Assignment 1 evaluation",
        "",
        "Token numbers are estimates of the context packet and the answer (about 4 characters per token). This project does not call a model API.",
        "",
        f"Accuracy: {passed}/{len(rows)} ({summary['accuracy_pct']}%)",
        f"Average latency: {avg_latency} ms",
        f"Average input tokens: {avg_in}",
        f"Average output tokens: {avg_out}",
        "",
        "| Test | Success | Tool | Handbook chunk | Memory | Latency ms | In tokens | Out tokens |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        memory_note = row["memory_write"]
        if row["memory_used"]:
            memory_note = json.dumps(row["memory_used"])
        lines.append(
            "| {id} | {success} | {tool} | {chunks} | {memory} | {latency} | {inp} | {out} |".format(
                id=row["id"],
                success="yes" if row["success"] else "no",
                tool=row["tool"] or "none",
                chunks=", ".join(row["chunks"]) or "none",
                memory=memory_note,
                latency=row["latency_ms"],
                inp=row["input_tokens"],
                out=row["output_tokens"],
            )
        )
    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Fee and scholarship answers come from tools. The portal answer uses one handbook section, not the whole file.",
            "- A later question can use the saved email preference without sending the earlier chat.",
            "- An OTP is redacted and is not written to memory. The email preference stays.",
            "- A missing student id returns a tool error. The agent does not invent a fee.",
            "- Questions the handbook does not cover are refused instead of guessed.",
            "",
            "## Sample answers",
            "",
        ]
    )
    for row in rows:
        lines.append(f"### {row['id']}")
        lines.append("")
        lines.append(row["answer"])
        lines.append("")
        if not row["success"]:
            lines.append("Failed checks: " + row["notes"])
            lines.append("")

    (PROJECT / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    (PROJECT / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    traces = PROJECT / "traces"
    traces.mkdir(exist_ok=True)
    (traces / "test_traces.json").write_text(
        json.dumps([row["trace"] for row in rows], indent=2), encoding="utf-8"
    )
    print(f"Accuracy {passed}/{len(rows)}")
    for row in rows:
        mark = "PASS" if row["success"] else "FAIL"
        print(f"{mark} {row['id']} {row['notes']}")
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
