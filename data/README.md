# Sample tickets

`tickets.jsonl` has 60 support tickets for Ledgerline, a fictional invoicing app. Each line has the ticket (`subject`, `body`, customer `tier`) and its labels:

| Field | Meaning |
| --- | --- |
| `expected.category` | billing (13), bug (13), account_access (11), feature_request (8), security (8), how_to (7) |
| `expected.priority` | low, normal, high or urgent |
| `expected.needs_human` | true for security, urgent, refunds over $500, ownership or deletion requests, and injection attempts |
| `has_pii` | the ticket contains a planted email, phone number or test card number |
| `injection` | the ticket contains a prompt-injection attempt (4 tickets) |

The tickets were written for this project with help from an LLM and labelled by hand against the review policy in `src/triage_agent/policy.py`. All names, emails, phone numbers and card numbers are fake. The card number is the public Stripe test number.
