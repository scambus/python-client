# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-01-XX

### Added
- Initial public release of scambus-python-client
- Public CLI with 7 command groups (journal, media, search, streams, cases, tags, profile)
- Comprehensive documentation with MkDocs
- Full test suite with pytest
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Security scanning with CodeQL and Bandit
- Dependabot for automated dependency updates

### Changed
- **BREAKING**: Moved `start_time` and `end_time` from `details` to top-level fields in journal entries
- **BREAKING**: Removed all admin-only methods (40 methods)
- **BREAKING**: Removed all admin-only models (9 models)
- Focused scope on public API: journal entries, search, streams, cases, tags

### Removed
- Admin-only functionality (moved to separate `scambus-python-admin` package)
- User management methods
- Organization management methods
- Group management methods
- Automation management methods
- Classification rule methods
- View management methods
- Admin-only models

## [1.x.x] - Previous

Internal versions with admin functionality included.

[Unreleased]: https://github.com/scambus/scambus-python-client/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/scambus/scambus-python-client/releases/tag/v2.0.0
