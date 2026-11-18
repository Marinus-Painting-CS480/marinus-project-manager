# API overview

The exact contract (every field and type) is the live docs at
**http://localhost:8000/api/docs**. This page is the map. All paths start with `/api`.
The React helpers for every endpoint are in `frontend/src/api/client.js`.

**Rules for the frontend**
- Call `GET /auth/csrf` once on app start; send `X-CSRFToken` on every non-GET request
  (`client.js` does this).
- Sign-in uses the session cookie. `401` = not signed in, `403` = role not allowed,
  `404` = not found (also returned for jobs you are not assigned to), `409` = not allowed in
  the current status, `410` = link revoked/expired, `422` = invalid input.
- Money is a **string** like `"1250.00"`. Field names are `snake_case`.
- Totals are always calculated by the server. Never send totals.

## Auth and users
| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/auth/csrf` | anyone | sets the CSRF cookie |
| POST | `/auth/login` | anyone | `{email, password}` → current user |
| POST | `/auth/logout` | signed in | |
| GET / PATCH | `/auth/me` | signed in | current user / change `locale` (`en`, `es`) |
| GET | `/users?role=employee` | office | crew picker |

## Intake (owner, estimator)
| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/customers` | search (`?search=`), create |
| GET, PUT | `/customers/{id}` | |
| GET | `/projects` | dashboards; `?status=`, `?search=`, `?ordering=due_date` (estimator queue) |
| GET | `/projects/summary` | count per status |
| POST | `/projects` | create with nested `areas[].scope_items[]` (new or existing customer) |
| GET, PUT | `/projects/{id}` | detail / **Save Draft** (send the whole form) |
| POST | `/projects/{id}/submit` | **Submit for Estimate** |
| DELETE | `/projects/{id}` | owner, drafts only |
| POST | `/projects/{id}/photos` | multipart: `files` (many), optional `area_id`, `caption` |
| GET | `/photos/{id}/file` | the image (office, or crew assigned to the job) |
| PATCH, DELETE | `/photos/{id}` | move to another area, caption / delete |

## Estimating and proposals (owner, estimator)
| Method | Path | Purpose |
|---|---|---|
| GET | `/quality-tiers` | active tiers (edit wording in `/admin`) |
| POST | `/projects/{id}/estimate` | open/create estimate (pre-filled from scope) |
| GET, PUT | `/estimates/{id}` | tier, labor %, terms, lines → server totals and margin |
| POST | `/estimates/{id}/proposals` | freeze a new version, returns the private link **once** |
| POST | `/proposals/{id}/link` | Copy Link (makes a new link; old one stops working) |
| POST | `/proposals/{id}/email` | Send by Email (also returns the link) |
| POST | `/proposals/{id}/revoke` | |

## Work orders
| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/work-orders` | all roles | office: all; crew: only assigned |
| GET | `/work-orders/{id}` | all roles | role-shaped detail (`financials` only for office) |
| PATCH | `/work-orders/{id}` | office | schedule/status; response has `warnings` |
| PUT | `/work-orders/{id}/assignments` | office | full crew list + person in charge + sub budgets |
| POST | `/work-orders/{id}/notes` | office | change note (signed scope never changes) |
| POST | `/work-orders/{id}/customer-link` | office | new customer link |

## Customer pages (no account)
| Method | Path | React page | Purpose |
|---|---|---|---|
| GET | `/public/proposals/{token}` | `/p/:token` | proposal to review |
| POST | `/public/proposals/{token}/approve` | `/p/:token` | `{signer_name, signature, selected_optional_item_ids, accept_terms}` → creates the work order |
| GET | `/public/work-orders/{token}` | `/w/:token` | scope, tier, schedule, crew names |
