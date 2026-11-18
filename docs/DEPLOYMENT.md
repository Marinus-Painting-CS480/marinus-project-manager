# Deployment

The whole app is **one Django site**: Django serves the API (`/api`), the admin (`/admin`)
and the built React app (every other URL). There is no separate frontend server in
production, so the session cookie and CSRF work exactly as they do locally.

```
https://app.marinus.llc
   ├── /api/...      Django Ninja (JSON)
   ├── /admin/       Django admin
   ├── /assets/...   React build files (served by WhiteNoise)
   └── /anything     React app (index.html), e.g. /projects/12, /p/<token>, /w/<token>
```

Hosting is not final yet (see ARCHITECTURE.md). Option A is the playbook's cPanel host;
option B is any host that runs Python (Render, Railway, a VPS). Only configuration differs.

## Before the first deploy (checklist)

- [ ] Host offers **Python 3.12+** (cPanel: *Software → Setup Python App*).
- [ ] A **MySQL 8** database and user can be created.
- [ ] HTTPS certificate for the domain (cPanel: *SSL/TLS Status → Run AutoSSL*).
- [ ] A folder **outside the public web root** for uploaded photos (`MEDIA_ROOT`).
- [ ] Backups include the database **and** the photo folder; a restore has been rehearsed.

## Production environment variables

Set these in the host's settings (cPanel: *Setup Python App → Environment variables*).
Never commit them.

| Variable | Example |
|---|---|
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | `app.marinus.llc` |
| `CSRF_TRUSTED_ORIGINS` | `https://app.marinus.llc` |
| `DATABASE_URL` | `mysql://dbuser:dbpassword@localhost:3306/dbname` |
| `SITE_URL` | `https://app.marinus.llc` (used in customer links and emails) |
| `MEDIA_ROOT` | `/home/<user>/marinus-media` |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` (or leave console until SMTP works; Copy Link always works) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | your mail account |

## Build the frontend

On your computer (cPanel often has no Node.js):

```bash
cd frontend
npm ci
npm run build        # creates frontend/dist
```

`frontend/dist` is git-ignored, so upload it to the server at
`<repo>/frontend/dist` (zip it, upload with File Manager, extract).

## Option A: cPanel (app.marinus.llc)

1. **Get the code**: *Git Version Control → Create*, clone
   `https://github.com/Marinus-Painting-CS480/marinus-project-manager.git` into
   `/home/<user>/marinus-project-manager`.
2. **Database**: *MySQL Databases* → create database + user, add the user to the database
   with ALL PRIVILEGES. Use them in `DATABASE_URL`.
3. **Python app**: *Setup Python App → Create Application*
   - Python version: 3.12 (or newest offered)
   - Application root: `marinus-project-manager/backend`
   - Application URL: `app.marinus.llc`
   - Application startup file: `passenger_wsgi.py`, entry point: `application`
   - Add the environment variables above, then **Save**.
4. **Install and set up**: copy the "Enter to the virtual environment" command shown at
   the top of the app page, run it in *Terminal*, then:
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   python manage.py check --deploy
   ```
5. Upload `frontend/dist` (see above), then click **Restart** on the Python app page.
6. Visit `https://app.marinus.llc/api/health` → `{"status": "ok"}`, then
   `https://app.marinus.llc/` → the React app.

## Option B: Render / Railway / VPS

- Build command:
  `cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt gunicorn && python manage.py collectstatic --noinput`
- Start command: `cd backend && python manage.py migrate && gunicorn config.wsgi --bind 0.0.0.0:$PORT`
- Attach a **persistent disk** for `MEDIA_ROOT` (many hosts erase files on each deploy).
- Use a managed MySQL database and set `DATABASE_URL`.

## Updating after a merge to `main`

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Rebuild and re-upload `frontend/dist` if the frontend changed, then restart
(cPanel: **Restart** button, or `touch tmp/restart.txt` inside `backend/`).

## Rolling back

Check out the previous release tag, repeat the update steps, and restore the database
backup only if a migration must be undone. Tag every release: `git tag v0.x && git push --tags`.
