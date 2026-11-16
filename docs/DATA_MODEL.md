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

### `projects` app
| Table | Fields | Notes |
|---|---|---|
| Customer | name, email, phone | customers have no login |
| Project | customer, title, site_address, project_type (`interior`/`exterior`/`both`), status, notes, important_instructions, requested_start_date, requested_end_date, estimate_due_date, created_by | status: `draft` → `waiting_for_estimate` → `estimating` → `proposal_sent` → `approved` (or `cancelled`) |
| Area | project, name, sequence | room / elevation / component |
| ScopeItem | area, description, prep, products, color, sheen, dimensions, included (false = exclusion), optional, unit, quantity, sequence | |
| Photo | project, area (optional), file, content_type, size, caption, uploaded_by, uploaded_at | stored under `MEDIA_ROOT`, served only via `/api/photos/{id}/file` |

### `estimates` app
| Table | Fields | Notes |
|---|---|---|
| QualityTier | name, description, version, active, sequence | wording approved by Marinus, edited in admin |
| Estimate | project (one per project), tier, labor_allocation_percent (default 30), terms, prepared_by | |
| EstimateItem | estimate, scope_item (optional, for grouped prices), description, unit_price, quantity, optional, estimated_material_cost, sequence | line_total = unit_price × quantity |
| Proposal | estimate, version, token_hash, status (`sent`/`approved`/`revoked`/`superseded`), snapshot (JSON), base_total, expires_at, created_by | snapshot is customer-safe: no costs or margin |
| Approval | proposal (one-to-one), signer_name, signature, signed_at, ip_address, user_agent, selected_item_ids, accepted_snapshot, final_amount | never edited |

### `workorders` app
| Table | Fields | Notes |
|---|---|---|
| WorkOrder | project, approval (one-to-one = exactly one work order per approval), status (`awaiting_assignment`/`scheduled`/`in_progress`/`completed`), start_date, arrival_time, estimated_working_days, allowed_work_window, completion_deadline, customer_token_hash | scope comes from `approval.accepted_snapshot` |
| WorkOrderAssignment | work_order, user, is_person_in_charge, labor_budget, estimated_hours, assigned_at | unique (work_order, user); budget/hours shown only to that subcontractor and office |
| ChangeNote | work_order, author, note, created_at | changes after signature |

### `audit` app
| Table | Fields | Notes |
|---|---|---|
| AuditLog | actor (empty for customer links), action, record_type, record_id, old_values, new_values, created_at | proposal sent/approved, links rotated, crew and schedule changes |

### Rules to keep in mind
- An approved proposal's snapshot is **never edited**. Later changes are notes or a new approval.
- Exactly **one** work order per approved proposal, even if "approve" is submitted twice. Enforce with a unique constraint plus a transaction.
- Proposal links store a **hash** of the token, never the raw token.
- Money is stored as `DecimalField`, never float.
