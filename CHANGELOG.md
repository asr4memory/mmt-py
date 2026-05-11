# Changelog

## [2.5.6] - 2026-05-11

### Internal
- Reduced hypercorn worker count from 4 to 2 to prevent OOM-induced container restarts

## [2.5.5] - 2026-05-11

### Changed
- Removed redundant `UploadedFile.transferred` field; upload status is now derived solely from `has_file`

### Internal
- Deferred waveform field loading in queries that don't access it, reducing InnoDB off-page reads
- Switched waveform word playback to `requestAnimationFrame` for smoother timing
- Renamed feature flag
- Fixed issue in release.sh

## [2.5.4] - 2026-05-05

### Fixed
- Fixed a Dockerfile bug

### Internal
- Improved Dockerfile
- Added tests for email tasks
- Added GitHub Actions release workflow
- Added release script

## [2.5.3] - 2026-05-05

### Added
- Feature flag mechanism on user profiles, configurable via the admin interface
- Upload activity message on the admin dashboard

### Changed
- Updated Django to 6.0.5

### Fixed
- Improved GitHub Actions workflows (updated action versions, fixed uv setup)

### Internal
- Expanded view and model test coverage
- Refactored project detail view
