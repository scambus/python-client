# Release Process

How releases are created and published.

## Versioning

We use [Semantic Versioning](https://semver.org/):

- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

## Creating a Release

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit changes
4. Create and push a tag: `git tag v1.2.3 && git push origin v1.2.3`
5. GitHub Actions will automatically build and publish to PyPI

## Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.2.3] - 2025-01-15

### Added
- New feature description

### Fixed
- Bug fix description
```
