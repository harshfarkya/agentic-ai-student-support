"""Run Assignment 2 tests and compare them with Assignment 1."""

import json
import shutil
import tempfile
from pathlib import Path

import agent
import approvals
import audit
import auth
import tools

PROJECT = Path(__file__).resolve().parent
DATA = PROJECT / "data"
A1_SUMMARY = PROJECT.parent / "assignment1-student-support" / "evaluation_summary.json"
CHANGE_Q = "Please change my programme to PGDM Artificial Intelligence and Data Science"


def make_sandbox():
    sandbox = Path(tempfile.mkdtemp()) / "data"
    sandbox.mkdir(parents=True)
    shutil.copy(DATA / "handbook.md", sandbox / "handbook.md")
    shutil.copy(DATA / "students_seed.json", sandbox / "students.json")
    return sandbox


def programme_of(student_id, data_dir):
    rows = json.loads((Path(data_dir) / "students.json").read_text(encoding="utf-8"))
    for row in rows:
        if row["student_id"] == student_id:
            return row["programme"]
    return None


def missing(text, phrases):
    lower = (text or "").lower()
    return [phrase for phrase in phrases if phrase.lower() not in lower]


def leaked(text, phrases):
    lower = (text or "").lower()
    return [phrase for phrase in phrases if phrase.lower() in lower]


def pack(test_id, question, result, problems, group):
    trace = result["trace"]
    return {
        "id": test_id,
        "group": group,
        "question": question,
        "success": not problems,
        "notes": "; ".join(problems),
        "tool": trace.get("tool"),
        "permission": trace.get("permission"),
        "approval_status": trace.get("approval_status"),
        "chunks": trace.get("chunks") or [],
        "memory_write": trace.get("memory_write"),
        "memory_used": trace.get("memory_used") or {},
        "latency_ms": trace.get("latency_ms"),
        "input_tokens": trace.get("input_tokens"),
        "output_tokens": trace.get("output_tokens"),
        "answer": result["answer"],
        "trace": trace,
    }


def main():
    sandbox = make_sandbox()
    rows = []
    try:
        bad_login = auth.authenticate("S101", "0000", sandbox)
        good_login = auth.authenticate("S101", "1010", sandbox)
        login_problems = []
        if bad_login is not None:
            login_problems.append("wrong PIN was accepted")
        if not good_login or good_login.get("student_id") != "S101" or "pin" in good_login:
            login_problems.append("valid login failed")
        rows.append(
            {
                "id": "L1",
                "group": "access",
                "question": "Login S101 with wrong PIN, then correct PIN",
                "success": not login_problems,
                "notes": "; ".join(login_problems),
                "tool": "login",
                "permission": "allowed",
                "approval_status": "not_required",
                "chunks": [],
                "memory_write": "none",
                "memory_used": {},
                "latency_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "answer": "Signed in as Rahul Sharma" if good_login else "Login failed",
                "trace": {"steps": ["auth.authenticate checked the PIN in Python"]},
            }
        )

        fee = agent.run_turn("What is my current fee status?", "S101", sandbox)
        problems = missing(fee["answer"], ["45000", "partially paid"])
        if fee["trace"]["tool"] != "get_fee_status" or fee["trace"]["permission"] != "allowed":
            problems.append("own fee was not allowed")
        rows.append(pack("Q1", "What is my current fee status?", fee, problems, "core"))

        scholarship = agent.run_turn("What is my scholarship status?", "S101", sandbox)
        problems = missing(scholarship["answer"], ["20 percent"])
        if scholarship["trace"]["permission"] != "allowed":
            problems.append("own scholarship was not allowed")
        rows.append(pack("Q2", "What is my scholarship status?", scholarship, problems, "core"))

        portal = agent.run_turn(
            "The payment portal failed. Can I pay on the next working day?",
            "S101",
            sandbox,
        )
        problems = missing(portal["answer"], ["next working day"])
        if portal["trace"]["chunks"] != ["payment-portal-failure"]:
            problems.append("wrong chunk")
        rows.append(
            pack(
                "Q3",
                "The payment portal failed. Can I pay on the next working day?",
                portal,
                problems,
                "core",
            )
        )

        saved = agent.run_turn("Please remember that I prefer email updates.", "S101", sandbox)
        recalled = agent.run_turn("How should you contact me?", "S101", sandbox)
        problems = missing(recalled["answer"], ["email"])
        if (recalled["trace"].get("memory_used") or {}).get("contact_preference") != "email":
            problems.append("memory was not reused")
        combined = {"answer": recalled["answer"], "trace": dict(recalled["trace"])}
        combined["trace"]["latency_ms"] = round(
            saved["trace"]["latency_ms"] + recalled["trace"]["latency_ms"], 1
        )
        combined["trace"]["input_tokens"] = saved["trace"]["input_tokens"] + recalled["trace"]["input_tokens"]
        combined["trace"]["output_tokens"] = (
            saved["trace"]["output_tokens"] + recalled["trace"]["output_tokens"]
        )
        rows.append(pack("Q4", "Remember email, then ask in a new turn", combined, problems, "core"))

        secret = agent.run_turn("My OTP is 482913", "S101", sandbox)
        memory_text = (sandbox / "memory.json").read_text(encoding="utf-8")
        problems = missing(secret["answer"], ["not saved"])
        if "482913" in memory_text or "482913" in json.dumps(audit.all_rows(sandbox)):
            problems.append("secret was stored")
        rows.append(pack("Q5", "My OTP is 482913", secret, problems, "core"))

        wifi = agent.run_turn("What is the hostel Wi-Fi password?", "S101", sandbox)
        problems = missing(wifi["answer"], ["does not contain enough information"])
        rows.append(pack("Q6", "What is the hostel Wi-Fi password?", wifi, problems, "core"))

        support = agent.run_turn(
            "Please create a support request because the payment portal failed.",
            "S101",
            sandbox,
        )
        problems = missing(support["answer"], ["SR-"])
        rows.append(
            pack(
                "Q7",
                "Please create a support request because the payment portal failed.",
                support,
                problems,
                "core",
            )
        )

        missing_row = agent.run_turn("What is my current fee status?", "Z999", sandbox)
        problems = missing(missing_row["answer"], ["could not find"])
        problems.extend("invented " + item for item in leaked(missing_row["answer"], ["45000", "125000"]))
        rows.append(pack("Q8", "Fee status for unknown id Z999", missing_row, problems, "core"))

        other_fee = agent.run_turn("What is the fee status of S102?", "S101", sandbox)
        problems = missing(other_fee["answer"], ["blocked"])
        problems.extend("leaked " + item for item in leaked(other_fee["answer"], ["125000", "pending"]))
        if not other_fee["trace"]["context"]["tool_result"].get("blocked"):
            problems.append("tool did not block")
        if "fee_due" in other_fee["trace"]["context"]["tool_result"]:
            problems.append("fee amount was returned")
        rows.append(pack("P1", "What is the fee status of S102?", other_fee, problems, "privacy"))

        other_sch = agent.run_turn("What is Priya Nair's scholarship status?", "S101", sandbox)
        problems = missing(other_sch["answer"], ["blocked"])
        if not other_sch["trace"]["context"]["tool_result"].get("blocked"):
            problems.append("tool did not block")
        rows.append(
            pack("P2", "What is Priya Nair's scholarship status?", other_sch, problems, "privacy")
        )

        direct = tools.get_fee_status("S102", "S101", sandbox)
        direct_problems = []
        if not direct.get("blocked") or "fee_due" in direct or "125000" in json.dumps(direct):
            direct_problems.append("direct tool call leaked or allowed another student")
        rows.append(
            {
                "id": "P3",
                "group": "privacy",
                "question": "Direct tools.get_fee_status(S102, actor S101)",
                "success": not direct_problems,
                "notes": "; ".join(direct_problems),
                "tool": "get_fee_status",
                "permission": "blocked",
                "approval_status": "not_required",
                "chunks": [],
                "memory_write": "none",
                "memory_used": {},
                "latency_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "answer": "Blocked inside tools.py before the other student's fee was copied.",
                "trace": {"tool_result": direct},
            }
        )

        before = programme_of("S101", sandbox)
        first = agent.run_turn(CHANGE_Q, "S101", sandbox)
        after_request = programme_of("S101", sandbox)
        change_problems = missing(first["answer"], ["have not changed", "pending", before])
        if after_request != before:
            change_problems.append("record changed before approval")
        if first["trace"]["approval_status"] != "pending":
            change_problems.append("approval was not pending")
        rows.append(pack("A1", CHANGE_Q, first, change_problems, "approval"))

        rejected = approvals.decide(first["trace"]["approval_id"], "reject", "staff.admin", sandbox)
        if programme_of("S101", sandbox) != before or rejected.get("executed"):
            rows.append(
                {
                    "id": "A2",
                    "group": "approval",
                    "question": "Staff rejects the programme change",
                    "success": False,
                    "notes": "record changed or reject did not stick",
                    "tool": "decide",
                    "permission": "rejected",
                    "approval_status": rejected.get("status"),
                    "chunks": [],
                    "memory_write": "none",
                    "memory_used": {},
                    "latency_ms": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "answer": rejected.get("message", ""),
                    "trace": rejected,
                }
            )
        else:
            rows.append(
                {
                    "id": "A2",
                    "group": "approval",
                    "question": "Staff rejects the programme change",
                    "success": True,
                    "notes": "",
                    "tool": "decide",
                    "permission": "rejected",
                    "approval_status": "rejected",
                    "chunks": [],
                    "memory_write": "none",
                    "memory_used": {},
                    "latency_ms": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "answer": rejected.get("message", ""),
                    "trace": rejected,
                }
            )

        second = agent.run_turn(CHANGE_Q, "S101", sandbox)
        approved = approvals.decide(second["trace"]["approval_id"], "approve", "staff.admin", sandbox)
        approve_problems = []
        if programme_of("S101", sandbox) != "PGDM Artificial Intelligence and Data Science":
            approve_problems.append("approved change was not saved")
        if not approved.get("executed"):
            approve_problems.append("approve did not execute")
        rows.append(
            {
                "id": "A3",
                "group": "approval",
                "question": "Staff approves a second programme change",
                "success": not approve_problems,
                "notes": "; ".join(approve_problems),
                "tool": "decide",
                "permission": "approved",
                "approval_status": "approved",
                "chunks": [],
                "memory_write": "none",
                "memory_used": {},
                "latency_ms": second["trace"]["latency_ms"],
                "input_tokens": second["trace"]["input_tokens"],
                "output_tokens": second["trace"]["output_tokens"],
                "answer": approved.get("message", ""),
                "trace": {"request": second["trace"], "decision": approved},
            }
        )

        cross = approvals.request_change("S101", "S102", "PGDM BDA", sandbox)
        cross_problems = []
        if not cross.get("blocked"):
            cross_problems.append("cross-student change was not blocked")
        if programme_of("S102", sandbox) != "PGDM Artificial Intelligence and Data Science":
            cross_problems.append("S102 programme changed")
        rows.append(
            {
                "id": "A4",
                "group": "approval",
                "question": "S101 tries to change S102 programme directly",
                "success": not cross_problems,
                "notes": "; ".join(cross_problems),
                "tool": "request_programme_change",
                "permission": "blocked",
                "approval_status": "not_required",
                "chunks": [],
                "memory_write": "none",
                "memory_used": {},
                "latency_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "answer": "Blocked inside approvals.py. S102 was not edited.",
                "trace": cross,
            }
        )

        audit_rows = audit.all_rows(sandbox)
        approval_rows = approvals.all_rows(sandbox)
    finally:
        shutil.rmtree(sandbox.parent, ignore_errors=True)

    core = [row for row in rows if row["group"] == "core"]
    passed = sum(1 for row in rows if row["success"])
    core_passed = sum(1 for row in core if row["success"])
    avg_latency = round(sum(row["latency_ms"] for row in core) / len(core), 1)
    avg_in = round(sum(row["input_tokens"] for row in core) / len(core), 1)
    avg_out = round(sum(row["output_tokens"] for row in core) / len(core), 1)
    summary = {
        "assignment": 2,
        "passed": passed,
        "total": len(rows),
        "core_passed": core_passed,
        "core_total": len(core),
        "accuracy_pct": round(100 * core_passed / len(core), 1),
        "avg_latency_ms": avg_latency,
        "avg_input_tokens": avg_in,
        "avg_output_tokens": avg_out,
    }
    a1 = {}
    if A1_SUMMARY.exists():
        a1 = json.loads(A1_SUMMARY.read_text(encoding="utf-8"))

    lines = [
        "# Assignment 2 evaluation",
        "",
        "Privacy and approval checks run in Python (`tools.py`, `approvals.py`, `auth.py`), not only in the reply text.",
        "Token numbers estimate the context packet. This project does not call a model API.",
        "",
        f"All tests: {passed}/{len(rows)}",
        f"Core support tests (same kind of work as Assignment 1): {core_passed}/{len(core)} ({summary['accuracy_pct']}%)",
        f"Average core latency: {avg_latency} ms",
        f"Average core input tokens: {avg_in}",
        f"Average core output tokens: {avg_out}",
        "",
        "## Comparison with Assignment 1",
        "",
        "| Measure | Assignment 1 | Assignment 2 |",
        "| --- | --- | --- |",
        f"| Core accuracy | {a1.get('passed', 'n/a')}/{a1.get('total', 'n/a')} | {core_passed}/{len(core)} |",
        f"| Average latency ms | {a1.get('avg_latency_ms', 'n/a')} | {avg_latency} |",
        f"| Average input tokens | {a1.get('avg_input_tokens', 'n/a')} | {avg_in} |",
        f"| Average output tokens | {a1.get('avg_output_tokens', 'n/a')} | {avg_out} |",
        "| Privacy block | not required | tool returns blocked and no other student's fee |",
        "| Sensitive change | not required | stays pending until staff approval |",
        "",
        "| Test | Group | Success | Tool | Permission | Approval | Latency ms | In | Out |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {group} | {success} | {tool} | {permission} | {approval} | {latency} | {inp} | {out} |".format(
                id=row["id"],
                group=row["group"],
                success="yes" if row["success"] else "no",
                tool=row["tool"] or "none",
                permission=row["permission"],
                approval=row["approval_status"],
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
            "- Normal fee, scholarship, policy, memory, and support answers still succeed after the controls.",
            "- S101 asking for S102 is blocked inside the tool. The fee amount is not copied into the result.",
            "- A programme change writes a pending approval only. Reject leaves the record as it was. Approve is what updates it.",
            "- An OTP is not stored in memory or in the audit text.",
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
    (PROJECT / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    traces = PROJECT / "traces"
    traces.mkdir(exist_ok=True)
    (traces / "test_traces.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (traces / "audit_sample.json").write_text(json.dumps(audit_rows, indent=2), encoding="utf-8")
    (traces / "approvals_sample.json").write_text(json.dumps(approval_rows, indent=2), encoding="utf-8")

    print(f"All {passed}/{len(rows)}  Core {core_passed}/{len(core)}")
    for row in rows:
        mark = "PASS" if row["success"] else "FAIL"
        print(f"{mark} {row['id']} {row['notes']}")
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
