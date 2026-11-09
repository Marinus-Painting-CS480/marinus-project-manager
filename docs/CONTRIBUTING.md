# Contributing

## Workflow

1. Pick or get assigned a ticket on the board. Tell Brad before claiming an unassigned one.
2. Create a branch from the latest `main`: `feature/W3-123-short-name` (week, ticket number, short name).
3. Make small changes. Merge vertical slices often rather than one big PR at the end of the week.
4. Run the checks below locally.
5. Open a PR that references the ticket. Include what changed, migration notes, screenshots for UI changes (phone and desktop), tests, and how you verified it.
6. Get approval from someone **other than the author**. Changes to login, permissions or money need a backend reviewer.
7. Merge. `main` must always run.

## Checks before opening a PR

```bash
# backend
cd backend
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
pytest

# frontend
cd frontend
npm run lint && npm run format:check && npm run build
```

## Conventions

**Backend**
- One router per app in `apps/<app>/api.py`; schemas next to the endpoints that use them.
- Every endpoint that returns protected data needs a test proving the wrong role is blocked.
- Multi-table changes go in `services.py` inside `transaction.atomic()`.
- Never edit a migration that's already on `main`. Add a new one.
- Update `docs/DATA_MODEL.md` in the same PR as any model change.

**Frontend**
- Backend calls live in one place (e.g. `src/api/`).
- No hard-coded UI text: add keys to both the English and Spanish translation files.
- Mobile-first Tailwind; use the shared color names from `src/index.css`.
- File names: `PascalCase.jsx` for components/pages, `camelCase.js` for everything else.

**API field names** use `snake_case` on both sides (e.g. `estimate_due_date`), exactly as shown in `/api/docs`.

## Data and secrets

- Never commit `.env`, real customer data, photos, or credentials.
- Use made-up data in tests, fixtures and screenshots.
