# AI coding guidelines

This project is a chance to learn the stack. AI tools are welcome, but you own what you merge: you must be able to explain the code and you must have tested it yourself.

## Rules

1. **Understand before you paste.** If you can't explain what a line does, ask the AI to explain it or look it up before committing it.
2. **Give the AI the context first:** README.md, docs/ARCHITECTURE.md, docs/DATA_MODEL.md, docs/CONTRIBUTING.md, this file, and the files you're changing.
3. **One ticket at a time.** Ask it to implement only that ticket's acceptance criteria.
4. **No new frameworks, tables, roles, apps or endpoints** unless the ticket calls for them or the team agreed first. Prefer the agreed libraries listed in ARCHITECTURE.md.
5. **Permissions live on the server.** Every endpoint that returns protected data must check the role or filter the query, and needs a test proving the wrong role is blocked.
6. **Never paste secrets, `.env` contents, real customer names/addresses/phone numbers, or photos** into an AI tool.
7. **Review AI output for:** missing permission checks, invented field names (compare with `/api/docs` and DATA_MODEL.md), hard-coded English text, floats used for money, and edits to old migrations.

## Copy-ready prompt

> You are helping a student developer on the Marinus Painting app: a Django + Django Ninja backend (Python, MySQL) and a React + Tailwind frontend (JavaScript, Vite). Read README.md, docs/ARCHITECTURE.md, docs/DATA_MODEL.md, docs/CONTRIBUTING.md and docs/AI_GUIDELINES.md before writing code. Implement only ticket [ID] and its acceptance criteria, and explain your changes so I can learn from them. Follow the existing conventions and use the agreed libraries. Do not add a new framework, library, database table, role, or endpoint without proposing it first. Enforce all permissions on the server and add tests proving unauthorized roles are blocked. Provide a changed-file list, migration impact, tests, manual verification steps, and any assumptions. Never use production credentials or real customer data.
