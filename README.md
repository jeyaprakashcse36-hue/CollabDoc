# CollabDocs API

A Django REST Framework backend for collaborative workspaces and documents. It supports workspace membership and roles, document CRUD and version history, threaded comments, tags, request logging, and document audit records.

## Stack

- Python 3.11+ (recommended)
- Django 5.2.6
- Django REST Framework 3.16.1
- PostgreSQL 16 (Docker Compose)
- JWT authentication via Simple JWT

## Features

- UUID primary keys for the seven CollabDocs models; Django's built-in `User` is used for authentication.
- Workspace creation and owner-as-admin membership are performed in one `transaction.atomic()` block.
- Document create/update and version creation are in the same atomic block.
- Unique workspace/user membership and unique document/version-number constraints.
- Threaded comments, tags, and document version history.
- `post_save` AuditLog records for document create/update, with signal registration in `AppConfig.ready()`.
- Request middleware logs HTTP method, path, status code, and duration.
- Query optimizations with `select_related`, `prefetch_related`, `Q` OR search, `icontains`, `in`, `gte`, `lte`, `values_list`, and `Count` annotations.
- Role-based workspace permissions and a staff-only audit-log endpoint.

## Setup (Windows PowerShell)

1. Install Python 3.11+ and Docker Desktop.
2. From the project root, copy the example environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Edit `.env`. Set a strong local `SECRET_KEY` and a database password. Do not commit `.env`.
4. Start PostgreSQL:

   ```powershell
   docker compose up -d
   ```

5. Create and activate a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

6. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Apply migrations and check the project:

   ```powershell
   python manage.py check
   python manage.py migrate
   python manage.py runserver
   ```

The API is available at `http://127.0.0.1:8000/api/`. PostgreSQL is published on port `5433` by default. The `.env` file must be in the same directory as `manage.py`.

## Environment variables

See `.env.example`. The application reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` from the environment.

## Authentication

Register a user, then obtain a JWT pair:

- `POST /api/users/` — register
- `POST /api/token/` — obtain access and refresh tokens
- `POST /api/token/refresh/` — refresh the access token

For protected endpoints, set Postman Authorization to **Bearer Token** and use the `access_token` value.

## Main API routes

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/users/` | Register a user |
| POST | `/api/token/` | Obtain JWT tokens |
| POST | `/api/token/refresh/` | Refresh JWT |
| GET, POST | `/api/workspaces/` | List/create workspaces |
| GET, PUT/PATCH, DELETE | `/api/workspaces/{workspace_id}/` | Retrieve/update/delete a workspace |
| GET, POST | `/api/workspaces/{workspace_id}/members/` | List/add workspace members |
| GET, PUT/PATCH, DELETE | `/api/workspaces/{workspace_id}/members/{membership_id}/` | Retrieve/update/remove membership |
| GET, POST | `/api/documents/` | List/create documents |
| GET, PUT/PATCH, DELETE | `/api/documents/{document_id}/` | Retrieve/update/delete a document |
| GET | `/api/documents/{document_id}/versions/` | List document versions, newest first |
| GET, POST | `/api/documents/{document_id}/comments/` | List/create comments |
| GET, PUT/PATCH, DELETE | `/api/documents/{document_id}/comments/{comment_id}/` | Retrieve/update/delete a comment |
| GET, POST | `/api/tags/` | List/create tags |
| GET, PUT/PATCH, DELETE | `/api/tags/{tag_id}/` | Retrieve/update/delete a tag |
| GET | `/api/audit-logs/` | List audit records (staff users only) |

## Document query parameters

- `search=term` searches title **or** content case-insensitively.
- `status=draft,published` filters by one or more statuses.
- `created_from=YYYY-MM-DD` filters with `created_at__date__gte`.
- `created_to=YYYY-MM-DD` filters with `created_at__date__lte`.
- `workspace_ids=<uuid>,<uuid>` filters by accessible workspace IDs using `values_list`.

Examples:

```text
GET /api/documents/?search=collab
GET /api/documents/?status=draft,published
GET /api/documents/?created_from=2026-10-01&created_to=2026-10-31
GET /api/documents/?workspace_ids=YOUR_WORKSPACE_UUID
```

## Seed/demo data

No seed fixture is required to start the API. Create a user, workspace, tag, document, and comment through the endpoints. Workspace creation automatically adds the creator as an administrator. Document creation automatically creates version 1; each successful document update creates the next version.

## Tests and verification

Run:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Import `postman/CollabDocs.postman_collection.json` into Postman. Configure the collection variables and run the requests in order. The duplicate membership scenario is expected to return a client error (normally 400 from serializer validation or 409 if the database constraint catches a race).

## Transaction rollback demo

To demonstrate atomicity safely in a local disposable database, temporarily cause the `DocumentVersion.objects.create(...)` call in `DocumentViewSet.create()` to raise an `IntegrityError`, then POST a document. Confirm that the API returns a conflict and no document remains in the database. Restore the original code immediately and rerun `python manage.py check`. Do not perform this experiment on production data.

## Demo video (5–10 minutes)

1. Show PostgreSQL running with `docker compose ps`.
2. Show migrations and `python manage.py check` passing.
3. Register/login and demonstrate workspace creation plus owner-admin membership.
4. Create a tagged document and show version 1; update it and show version history.
5. Demonstrate search/status/date filters and `member_count`, `version_count`, `comment_count`, and `document_count`.
6. Create a comment/reply and show threaded reply count.
7. Show request logs in the Django terminal and corresponding AuditLog rows.
8. Explain the transaction rollback test and show the result from the disposable local database.

## GitHub hygiene

Commit `.env.example`, not `.env`. The `.gitignore` excludes `.env`, virtual environments, Python bytecode, and local test artifacts. Before pushing, inspect `git status` and search for credentials.
