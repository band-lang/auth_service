# Contributing to Auth Service

Thanks for your interest in contributing! This project is currently in a **frozen** state (the maintainer is focused on other work), but issues and pull requests are still welcome and will be reviewed as time allows.

## Getting Started

1. Fork the repository and clone your fork locally.
2. Follow the setup steps in the [README](README.md#getting-started) to get the service running locally.
3. Create a new branch for your change:
   ```bash
   git checkout -b fix/short-description
   ```

## Development Guidelines

- Keep changes focused — one logical change per pull request.
- Match the existing code style (type hints, async/await, Pydantic models for I/O boundaries).
- Add or update an Alembic migration if you change any SQLAlchemy model in `src/auth/models.py` or `src/global_models.py`:
  ```bash
  alembic revision --autogenerate -m "describe your change"
  ```
- Add tests for new behavior where practical, and make sure the full suite passes before opening a PR:
  ```bash
  pytest
  ```
- Update the README/docs if you change setup steps, environment variables, or public API behavior.

## Reporting Bugs

When filing an issue, please include:
- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs (with secrets/PII redacted)
- Your Python version and OS

## Known Priority Issue

The email-change flow currently only sends a verification code to the *old* email address. A correct fix should also verify ownership of the *new* address before applying the change. This is a great first contribution if you're looking for somewhere to start — see the [Known Issues](README.md#known-issues) section of the README.

## Pull Request Checklist

- [ ] Code follows the existing style and passes `pytest`
- [ ] New/changed models have a corresponding Alembic migration
- [ ] README/docs updated if behavior or setup changed
- [ ] No secrets, credentials, or `.env` files included in the diff

## Code of Conduct

Be respectful and constructive. Disagreements about code are fine; personal attacks are not.
