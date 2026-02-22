# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Authentication:** Integrated Firebase for secure Email/Password and Google OAuth login flows. Implemented password resets and full backend JWT security.
- **User Profiles:** Users can manage settings, upload avatars, and view generation usage stats.
- **Project Management:** Added "My Projects" dashboard featuring project duplication, metadata updates, thumbnail previews, and a 30-day soft-delete.
- **Generator Wizard:** Revamped the layout generation UI into a comprehensive multi-step workflow. Users can now input complex room size rules and track generation live via Background Processing updates.
- **Backend Architecture:** Refactored FastAPI with advanced error handlers, SlowAPI rate-limiting middleware, structured logging, and Pydantic BaseSettings integration.
- **DevOps:** Migrated to CI/CD via fully-featured GitHub Actions pipelines. Dockerized the backend stack via Dockerfile and Compose setups. Introduced Pytest endpoint health checking.
