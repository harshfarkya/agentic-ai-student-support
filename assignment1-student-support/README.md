# Assignment 1 — Student Support Agent

A small chat agent for common student questions: fees, scholarships, the payment-portal rule, and support requests.

Python standard library only. No API key.

## How to run

```text
cd C:\Users\harsh\OneDrive\Documents\Accounting\assignment1-student-support
python app.py
```

Open http://127.0.0.1:8765

Refresh the evaluation table:

```text
python evaluate.py
```

That writes `evaluation.md` and `traces/test_traces.json`.

## Architecture

```text
Question
  -> plan (fee tool, scholarship tool, support tool, memory, or handbook)
  -> keep only the context that step needs
  -> answer from that context
  -> save a contact preference only when it is safe
  -> write a trace
```

| File | Role |
| --- | --- |
| `app.py` | Chat page |
| `agent.py` | Decides the step and builds the answer |
| `tools.py` | Fee status, scholarship status, create support request |
| `retrieval.py` | Picks one handbook section |
| `memory.py` | Saves email / phone / sms only |
| `data/students.json` | Sample student records |
| `data/handbook.md` | Policy document |
| `evaluate.py` | Test questions, latency, token estimate |

Chat history is not sent into the next answer. A new session clears the screen only. The contact preference stays in `data/memory.json`.

Token counts estimate the size of the context packet and the answer (about 4 characters per token). They are not from a model API.

## Demo questions

Use student id `S101` unless noted.

1. What is my current fee status?
2. What is my scholarship status?
3. The payment portal failed. Can I pay on the next working day?
4. Please remember that I prefer email updates.
5. Click **New session**, then ask: How should you contact me?
6. My OTP is 482913 — check Saved memory. The OTP must be absent.
7. What is the hostel Wi-Fi password?
8. Please create a support request because the payment portal failed.
9. Change the student id to `Z999` and ask the fee question again.

Sample ids: `S101` Rahul Sharma, `S102` Priya Nair.
