# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Known Issues
- Email-change confirmation currently sends the verification code only to the old email address instead of also verifying the new one.

## [0.1.0] - Initial release

### Added
- User registration with email verification codes
- Login flow with email-based second factor
- Opaque access tokens (Redis-backed) and hashed refresh tokens (PostgreSQL-backed)
- Refresh token rotation with reuse detection and suspicious-activity email alerts
- Password reset via email verification code
- Email change via email verification code
- Background email delivery via a SAQ task queue with retry and dead-letter handling
- Alembic migrations for `users` and `refresh_tokens` tables
- Structured logging via structlog
