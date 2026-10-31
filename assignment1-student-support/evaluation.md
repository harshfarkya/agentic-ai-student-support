# Assignment 1 evaluation

Token numbers are estimates of the context packet and the answer (about 4 characters per token). This project does not call a model API.

Accuracy: 8/8 (100.0%)
Average latency: 6.3 ms
Average input tokens: 43.2
Average output tokens: 28.0

| Test | Success | Tool | Handbook chunk | Memory | Latency ms | In tokens | Out tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | yes | get_fee_status | none | none | 13.7 | 55 | 23 |
| Q2 | yes | get_scholarship_status | none | none | 0.4 | 53 | 21 |
| Q3 | yes | none | payment-portal-failure | none | 21.4 | 87 | 57 |
| Q4 | yes | none | none | {"contact_preference": "email"} | 13.4 | 48 | 43 |
| Q5 | yes | none | none | skipped_secret | 0.0 | 9 | 21 |
| Q6 | yes | none | none | none | 0.3 | 13 | 18 |
| Q7 | yes | create_support_request | none | none | 0.7 | 48 | 13 |
| Q8 | yes | get_fee_status | none | none | 0.2 | 33 | 28 |

## Observations

- Fee and scholarship answers come from tools. The portal answer uses one handbook section, not the whole file.
- A later question can use the saved email preference without sending the earlier chat.
- An OTP is redacted and is not written to memory. The email preference stays.
- A missing student id returns a tool error. The agent does not invent a fee.
- Questions the handbook does not cover are refused instead of guessed.

## Sample answers

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
