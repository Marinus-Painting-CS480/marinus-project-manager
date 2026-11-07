# Marinus Painting Project Manager

CS 480 team project for managing Marinus Painting job details, estimates, customer approvals, and work orders.

**Stack:** React + Tailwind (JavaScript, Vite) · Django + Django Ninja (Python) · MySQL. Everything runs locally for now.

This repository is a **barebones starting point**: the pieces are installed and connected, and the features are yours to build. Before writing code (or asking an AI tool to), read:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the pieces fit together and the conventions to follow
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md): tables, built and planned
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md): branches, PRs, reviews
- [docs/AI_GUIDELINES.md](docs/AI_GUIDELINES.md): rules for AI-assisted coding

## What's here

```
backend/            Django project
  config/           settings, URLs, and the Ninja API (api.py)
  apps/accounts/    custom User model (email, name, role, language)
  tests/            pytest tests
frontend/           React app (Vite + Tailwind)
  src/App.jsx       placeholder page that checks the backend is reachable
  src/index.css     Tailwind setup and shared colors
docker-compose.yml  local MySQL database
docs/               team docs
```

Already working:
- Django connected to MySQL, with the admin at `/admin`
- A custom `User` model with roles and a language preference
- Django Ninja serving `GET /api/health`, with live docs at `/api/docs`
- React + Tailwind, with Vite forwarding `/api` requests to Django

Installed but not wired up yet (the team's agreed tools): React Router, TanStack Query, React Hook Form + Zod, i18next/react-i18next.

## First-time setup

Install these first:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.12+](https://www.python.org/downloads/)
- [Node.js 24 LTS](https://nodejs.org/)

### 1. Start the database

From the repository root, with Docker Desktop running:

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python manage.py migrate
python manage.py createsuperuser # your own local admin account
python manage.py runserver
```

The backend runs at http://localhost:8000. API docs: http://localhost:8000/api/docs. Admin: http://localhost:8000/admin.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The page should say **Backend: connected**.

## Everyday commands

| Task | Command |
|---|---|
| Start database | `docker compose up -d` |
| Stop database | `docker compose down` |
| Wipe database and start fresh | `docker compose down -v`, then `docker compose up -d` and `python manage.py migrate` |
| Backend tests | `cd backend && pytest` |
| Backend lint / format | `ruff check .` / `ruff format .` |
| New migration after a model change | `python manage.py makemigrations` |
| Frontend lint / format | `npm run lint` / `npm run format` |
| Frontend production build | `npm run build` |
