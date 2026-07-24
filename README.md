# Auth Service

A lightweight, self-contained authentication micro-service built with **FastAPI**, **PostgreSQL**, and **Redis**. It handles user registration, email-based verification, login, opaque access/refresh tokens, password reset, and email change flows.

> **Project status:** This project is currently **frozen** — it is not under active development while the author focuses on system programming. It is still a solid reference implementation and starting point for a production auth service. See [Known Issues](#known-issues) below before relying on it in production.

## Features

- Email + password registration with an email verification code (sent via SMTP)
- Login flow protected by a second-factor email code
- Opaque access tokens (stored in Redis) and hashed refresh tokens (stored in PostgreSQL)
- Refresh token rotation with reuse/suspicious-activity detection
- Password reset via email verification code
- Email change via email verification code
- Rate-limited / attempt-limited verification codes (max 5 attempts, 10-minute TTL)
- Background email delivery via a [SAQ](https://github.com/tobymao/saq) task queue (Redis-backed), with retry logic and a dead-letter queue for permanently failing jobs
- Structured logging via [structlog](https://www.structlog.org/)
- Async SQLAlchemy 2.0 ORM + Alembic migrations
- Argon2 password hashing with timing-attack mitigation

## Tech Stack

| Component        | Technology                          |
|-------------------|--------------------------------------|
| Web framework     | FastAPI + Uvicorn                   |
| Database          | PostgreSQL (async, via SQLAlchemy 2.0 + asyncpg) |
| Migrations        | Alembic                             |
| Cache / sessions  | Redis                               |
| Task queue        | SAQ (Simple Async Queue)            |
| Email delivery    | aiosmtplib + Jinja2 templates       |
| Password hashing  | argon2-cffi                         |
| Validation        | Pydantic v2                         |
| Logging           | structlog                           |

## Project Structure

```
auth_service/
├── migrations/                  # Alembic migration environment and versions
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   ├── main.py                  # FastAPI app instance and lifespan setup
│   ├── config.py                # Environment-variable-based configuration
│   ├── database.py              # Async SQLAlchemy engine/session factory
│   ├── global_models.py         # Shared declarative Base model
│   ├── logger.py                # structlog configuration
│   ├── exceptions.py            # App-wide exception base classes/handlers
│   ├── auth/
│   │   ├── router.py            # All /auth/* HTTP routes
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── models.py            # User / RefreshToken ORM models
│   │   ├── queries.py           # Database access layer
│   │   ├── dependencies.py      # FastAPI dependencies (current user, etc.)
│   │   ├── constants.py
│   │   ├── exceptions.py        # Auth/email/token-specific exceptions
│   │   ├── redis_helpers.py     # Verification code + token helpers
│   │   ├── services/            # Business logic (registration, tokens, credentials)
│   │   ├── utils/                # Email sending + password hashing utilities
│   │   └── templates/email/     # Jinja2 HTML email templates
│   └── workers/
│       ├── queue.py             # SAQ queue instance
│       ├── settings.py          # SAQ worker settings/entrypoint
│       ├── logging_config.py
│       └── tasks/email.py       # Background email-sending tasks
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Requirements

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- An SMTP account/server for sending transactional emails

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/band-lang/auth_service.git
cd auth_service
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
cp .env.docker.example .env.docker # For docker container
```

See [`.env.example`](.env.example) for the full list of required variables (database URIs, Redis connection, SMTP credentials, token lifetimes, etc.).

### 4. Start PostgreSQL and Redis

If you don't already have them running locally, the quickest option is Docker:

```bash
docker run -d --name auth-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=auth_service -p 5432:5432 postgres:16
docker run -d --name auth-redis -p 6379:6379 redis:7
```

(A ready-made `docker-compose.yml` is included for convenience — see [Running with Docker](#running-with-docker) below.)

### 5. Apply database migrations

```bash
alembic upgrade head
```

### 6. Run the API server

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

### 7. Run the background worker

Verification, password-reset, email-change, and suspicious-activity emails are all sent asynchronously by a SAQ worker. Run it in a separate terminal:

```bash
saq src.workers.settings.settings
```

## Running with Docker

A `Dockerfile` and `docker-compose.yml` are provided to run the API, worker, PostgreSQL, and Redis together.

First, create the env file **from the Docker-specific example** (note: this is different from the plain `.env.example` used for local, non-Docker development — the hostnames differ):

```bash
cp .env.docker.example .env
```

Then fill in your real SMTP credentials in `.env` (`MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_FROM`) — without them, verification/reset/change emails will fail to send. Everything else (database and Redis connection strings) already points at the right in-network hostnames and needs no changes.

```bash
docker compose up --build
```

This starts:
- `postgres` — PostgreSQL database. On first start (empty volume), the official Postgres image automatically creates the user and database from the `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` values in `docker-compose.yml` — **you don't need to create a Postgres user or database manually.**
- `redis` — Redis cache/queue
- `api` — the FastAPI application (port `8000`). It waits for postgres/redis to pass their health checks, runs `alembic upgrade head` automatically, then starts Uvicorn.
- `worker` — the SAQ background worker that actually sends the emails

If you ever want to start completely fresh (e.g. to test migrations from scratch), remove the named volume along with the containers:

```bash
docker compose down -v
```

## Running Migrations

Create a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe your change"
```

Apply migrations:

```bash
alembic upgrade head
```

Roll back the last migration:

```bash
alembic downgrade -1
```

## Running Tests

```bash
pytest
```

Make sure `TEST_DATABASE_URI` in your `.env` points to a dedicated test database, so tests never run against your development or production data.

## API Overview

All routes are mounted under the `/auth` prefix.

| Method | Path                        | Description                                              |
|--------|------------------------------|-----------------------------------------------------------|
| GET    | `/auth/`                    | Health check                                              |
| GET    | `/auth/protected`            | Example endpoint requiring a valid access token           |
| POST   | `/auth/users`                | Register a new user (sends a verification code by email)  |
| POST   | `/auth/login/request`        | Log in with email + password (sends a verification code)  |
| POST   | `/auth/tokens`               | Confirm the verification code and issue access/refresh tokens |
| POST   | `/auth/tokens/refresh`       | Rotate an access/refresh token pair                        |
| DELETE | `/auth/tokens/revoke`        | Revoke a refresh token and its associated access token     |
| POST   | `/auth/password/reset`       | Request a password reset code by email                    |
| PATCH  | `/auth/password/reset/confirm` | Confirm the code and set a new password                 |
| POST   | `/auth/email/change`         | Request an email change code                               |
| PATCH  | `/auth/email/change/confirm` | Confirm the code and update the account email              |

Full request/response schemas are available via the auto-generated Swagger UI at `/docs` once the server is running.

## Security Notes

- Passwords are hashed with Argon2 (`argon2-cffi`); a dummy hash is verified on unknown-user login attempts to reduce timing side-channels.
- Access tokens are random opaque strings stored server-side in Redis (not JWTs), so they can be revoked instantly.
- Refresh tokens are stored as SHA-256 hashes in PostgreSQL; the raw token is only ever returned to the client once.
- Verification codes are rate-limited to 5 attempts and expire after 10 minutes.
- Reused/revoked refresh tokens trigger a "suspicious activity" email notification to the account owner.

## Known Issues

- **You can find all known issues in chapter "issues"**

## Contributing

Contributions, bug fixes, and improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the terms of the [MIT License](LICENSE).
