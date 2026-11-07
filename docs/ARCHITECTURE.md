# Architecture

## Overview

```
Browser (phone or desktop)
   │  http://localhost:5173
   ▼
Vite dev server (React + Tailwind)
   │  /api/* is forwarded to Django
   ▼
Django (localhost:8000)
   ├── /api/...    Django Ninja endpoints (JSON)
   ├── /api/docs   live API documentation
   ├── /admin      Django admin (office back-office)
   └── MySQL       docker-compose (localhost:3306)
```

The browser only ever talks to one origin. In development Vite forwards `/api` to Django; when we deploy, Django will serve the built React files itself. Because it's one origin, login should use Django's normal **session cookies** with **CSRF protection**, not tokens stored in the browser.

## Backend (Django + Django Ninja)

**What exists:** `config/api.py` holds the single `NinjaAPI` object with a health check. `apps/accounts` holds the custom `User` model.

**Conventions to follow as you build:**
- **One router per app** in `apps/<app>/api.py`, registered in `config/api.py` with `api.add_router(...)`.
- **Schemas** (Ninja `Schema` classes) define the exact fields going in and out. They validate input automatically and appear in `/api/docs`, which is the contract the frontend relies on.
- **Permissions are enforced on the server.** Every endpoint that returns protected data must check the user's role or filter the query to what that user may see (e.g. employees only get their assigned work orders). Hiding a button in React is never a permission check. Consider making login required by default (`NinjaAPI(auth=django_auth)`) once login exists.
- **Errors** return JSON with a proper status code: 401 not signed in, 403 not allowed, 404 not found, 422 invalid input.
- **Business logic** that touches several tables (e.g. proposal approval → snapshot → work order) goes in a `services.py` module inside the app and runs in a database transaction.
- **Django admin** is for office staff to manage reference data (users, quality tiers). Day-to-day work happens in the React app.

### Roles (from the playbook)

| Role | Sees |
|---|---|
| `owner` | Everything, including financials. Admin access. |
| `estimator` | All projects, estimates, financials |
| `employee` | Only work orders assigned to them; no prices |
| `subcontractor` | Assigned scope plus their own labor budget/hours; no customer price |

Customers do **not** have accounts. They use private, unguessable links.

## Frontend (React + Tailwind, JavaScript)

**What exists:** `src/App.jsx` is a placeholder page that calls `/api/health`. Tailwind is set up in `src/index.css` with shared colors.

**Agreed tools (installed, not yet wired up):**

| Need | Library |
|---|---|
| Pages and URLs | React Router |
| Loading and saving data | TanStack Query |
| Forms and validation | React Hook Form + Zod |
| English/Spanish | i18next + react-i18next |

**Conventions to follow as you build:**
- **Keep every backend call in one place** (e.g. `src/api/`), not scattered `fetch` calls in components. Non-GET requests must send Django's CSRF token (`X-CSRFToken` header, read from the `csrftoken` cookie).
- **No hard-coded UI text:** every label lives in the English and Spanish translation files. Free text typed by users (instructions, notes) is shown exactly as written and is never auto-translated.
- **Styling:** Tailwind utility classes with the shared colors in `src/index.css` (`bg-brand`, `text-ink`, `border-line`, …). Design mobile-first: start with the phone layout, then add `sm:`/`md:` changes.

## Local data and files

- MySQL runs in Docker. Each developer has their own database.
- Uploaded photos should be stored under `backend/media/` (git-ignored) and served only through permission-checked endpoints, never as public files.
- Emails print to the backend terminal instead of being sent.

## Not decided yet

- Hosting (cPanel vs. a managed host). The app is set up so this only changes configuration.
- Production email provider and photo storage location.
