# Data model

This is the single source of truth for tables. Update it in the same PR as the migration. Don't create tables that aren't described here without proposing them first.

## Built

### `accounts.User`
| Field | Notes |
|---|---|
| email | unique, used to sign in; stored lowercase and matched case-insensitively |
| name | |
| role | `owner`, `estimator`, `employee`, `subcontractor` |
| locale | `en` or `es`, the user's UI language |
| is_active | inactive users cannot sign in |
| is_staff | can use the Django admin |

## Planned (from the playbook)

| Table | Key fields | Owner (week) |
|---|---|---|
| customers | name, email, phone | Ernesto (W2) |
| projects | customer, title, site address, interior/exterior type, status, notes, important instructions, requested dates, estimate due date | Ernesto (W2) |
| areas | project, name, sequence | Ernesto (W2) |
| scope_items | area, description, prep, products, color, sheen, dimensions, included/excluded, optional, unit/quantity | Joel (W2–3) |
| photos | project, area, file path, uploader, timestamp | Joel / Ernesto (W3) |
| quality_tiers | name, approved description, active, version | Joel (W3) |
| estimates / estimate_items | project, tier, prices, quantities, optional selections, cost estimates | Joel (W4) |
| proposals / approvals | version, token hash, status, accepted snapshot, total, signer, signed_at, signature evidence | Joel (W4–5) |
| work_orders | project, approved proposal, scheduled dates, allowed days | Ernesto (W4) |
| work_order_assignments | work order, user, is_person_in_charge, assigned_at | Joel / Ernesto (W3–4) |
| change_notes / audit_logs | actor, timestamp, record, prior/new values | (W5) |

### Rules to keep in mind
- An approved proposal's snapshot is **never edited**. Later changes are notes or a new approval.
- Exactly **one** work order per approved proposal, even if "approve" is submitted twice. Enforce with a unique constraint plus a transaction.
- Proposal links store a **hash** of the token, never the raw token.
- Money is stored as `DecimalField`, never float.
