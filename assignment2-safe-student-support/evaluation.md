# Assignment 2 evaluation

Privacy and approval checks run in Python (`tools.py`, `approvals.py`, `auth.py`), not only in the reply text.
Token numbers estimate the context packet. This project does not call a model API.

All tests: 16/16
Core support tests (same kind of work as Assignment 1): 8/8 (100.0%)
Average core latency: 11.7 ms
Average core input tokens: 43.2
Average core output tokens: 28.0

## Comparison with Assignment 1

| Measure | Assignment 1 | Assignment 2 |
| --- | --- | --- |
| Core accuracy | 8/8 | 8/8 |
| Average latency ms | 6.3 | 11.7 |
| Average input tokens | 43.2 | 43.2 |
| Average output tokens | 28.0 | 28.0 |
| Privacy block | not required | tool returns blocked and no other student's fee |
| Sensitive change | not required | stays pending until staff approval |

| Test | Group | Success | Tool | Permission | Approval | Latency ms | In | Out |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | access | yes | login | allowed | not_required | 0 | 0 | 0 |
| Q1 | core | yes | get_fee_status | allowed | not_required | 17.7 | 55 | 23 |
| Q2 | core | yes | get_scholarship_status | allowed | not_required | 14.6 | 53 | 21 |
| Q3 | core | yes | none | not_applicable | not_required | 2.0 | 87 | 57 |
| Q4 | core | yes | none | not_applicable | not_required | 16.9 | 48 | 43 |
| Q5 | core | yes | none | blocked | not_required | 13.7 | 9 | 21 |
| Q6 | core | yes | none | not_applicable | not_required | 0.7 | 13 | 18 |
| Q7 | core | yes | create_support_request | allowed | not_required | 3.3 | 48 | 13 |
| Q8 | core | yes | get_fee_status | allowed | not_required | 24.7 | 33 | 28 |
| P1 | privacy | yes | get_fee_status | blocked | not_required | 16.8 | 30 | 14 |
| P2 | privacy | yes | get_scholarship_status | blocked | not_required | 17.4 | 35 | 16 |
| P3 | privacy | yes | get_fee_status | blocked | not_required | 0 | 0 | 0 |
| A1 | approval | yes | request_programme_change | allowed_to_request | pending | 21.1 | 157 | 78 |
| A2 | approval | yes | decide | rejected | rejected | 0 | 0 | 0 |
| A3 | approval | yes | decide | approved | approved | 42.0 | 157 | 78 |
| A4 | approval | yes | request_programme_change | blocked | not_required | 0 | 0 | 0 |

## Observations

- Normal fee, scholarship, policy, memory, and support answers still succeed after the controls.
- S101 asking for S102 is blocked inside the tool. The fee amount is not copied into the result.
- A programme change writes a pending approval only. Reject leaves the record as it was. Approve is what updates it.
- An OTP is not stored in memory or in the audit text.

## Sample answers

### L1

Signed in as Rahul Sharma

### Q1

Fee status for S101 (Rahul Sharma): Partially paid. Amount due for Semester 3: INR 45000.

### Q2

Scholarship status for S101 (Rahul Sharma): Merit scholarship 20 percent approved.

### Q3

From the student handbook:
Payment portal failure: If the payment portal fails, the student may pay on the next working day without a late penalty. The student should raise a support request on the same day and quote the error.

### Q4

You asked to be contacted by email.

### Q5

That looks like a password, OTP, or similar secret. I have not saved it to memory.

### Q6

The student handbook does not contain enough information to answer this.

### Q7

Support request SR-001 has been created for S101.

### Q8

I could not find that student record, so I cannot confirm the fee status. Check the student id and try again.

### P1

Request blocked. You can view only your own fee record.

### P2

Request blocked. You can view only your own scholarship record.

### P3

Blocked inside tools.py before the other student's fee was copied.

### A1

I have not changed your programme. It is still PGDM Big Data Analytics. Approval APR-001 is pending staff review. A change of course or programme alters the official student record. It is allowed once per academic year and only before week 4 of the semester. The change is completed only after staff approval.

### A2

APR-001 rejected. The programme was not changed.

### A3

APR-002 approved. Programme is now PGDM Artificial Intelligence and Data Science.

### A4

Blocked inside approvals.py. S102 was not edited.
