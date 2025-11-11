# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-11-11

### Added

#### Package Distribution
- Package name: `scambus` (simplified from `scambus-client`)
- CLI tool automatically included with `pip install scambus`
- Import name remains `scambus_client` for backwards compatibility

#### Core Client Features
- Initial release of Scambus Python client
- `ScambusClient` class for API interactions
- API key authentication support
- Comprehensive error handling with custom exceptions

#### Journal Entries (Scam Reporting)
- Create detection journal entries
- Create phone call journal entries with in-progress activity support
- Create email journal entries
- Create text conversation journal entries
- Create note journal entries
- List and query journal entries with advanced filtering
- Get journal entry details
- Complete in-progress activities

#### Identifiers
- List identifiers with type filtering
- Get identifier details
- Search identifiers
- Create bank account identifiers
- Identifier lookup objects for journal entries

#### Cases
- Create investigation cases
- List cases with status/priority/category filters
- Get case details
- Update case properties
- Delete cases
- Case comment management (create, list, update, delete)

#### Tags
- List tags
- Create tags with full configuration
- Get tag details
- Update tags
- Delete tags
- Tag value management (create, update, delete, list)
- Get effective tags for entities
- Get tag history

#### Media & Evidence
- Upload media files
- Upload media from buffers
- Get media details
- Support for attaching media to journal entries

#### Export Streams
- Create journal entry streams
- Create identifier streams
- List streams with filters and pagination
- Get stream details
- Delete streams
- Consume stream messages
- Stream recovery after failures
- Backfill historical data for identifier streams
- Get recovery status and stream recovery info

#### Search
- Search identifiers by query and type
- Search cases by query and status
- Advanced journal entry querying with filters

#### Notifications
- List notifications (with unread filtering and pagination)
- Get notification details
- Mark notifications as read (single and bulk)
- Get unread notification count
- Dismiss notifications (single and bulk)

#### Session Management
- List active sessions
- Revoke sessions

#### Passkeys
- List passkeys
- Delete passkeys
- Get 2FA status
- Toggle 2FA

#### Real-time Features
- WebSocket client for real-time notifications
- Async notification handlers
- Custom message type handlers
- Automatic reconnection support

#### CLI Tool
- `scambus` command-line tool
- Device authorization flow for authentication
- API key authentication
- Journal entry creation commands (detection, phone-call, email, text-conversation, note)
- Journal entry listing and querying
- Media upload
- Case management commands
- Search commands
- Stream management commands
- Notification and profile management
- Tag management

### Developer Features
- Comprehensive test suite with pytest
- Type hints throughout the codebase
- Pre-commit hooks for code quality
- Black, Ruff, isort for code formatting
- MyPy for type checking
- Bandit for security scanning
- MkDocs documentation
- Examples directory with usage samples
- GitHub Actions CI/CD workflows
- Automated PyPI publishing on tag

### Documentation
- Comprehensive README with examples
- API reference documentation
- CLI reference documentation
- Quick start guide
- Multiple usage examples for all major features
- WebSocket examples for real-time notifications

[Unreleased]: https://github.com/scambus/scambus-python-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/scambus/scambus-python-client/releases/tag/v0.1.0
