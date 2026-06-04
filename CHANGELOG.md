# Changelog

## [2.9.6] - 2026-06-04

### Added
- The transcript editor now shows a subheading bar with file metadata (filename, duration, language) and save/discard actions with an unsaved-changes indicator
- View toggles for named entity highlighting and edit markers have been added to the transcript editor sidebar
- Transcript segments now have a speaker selector dropdown

## [2.9.5] - 2026-06-03

### Added
- The upload page now lists which file types can be uploaded

### Internal
- Updated the content type rejection test to use a type that is still unaccepted after PDF was added

## [2.9.4] - 2026-06-03

### Added
- File uploads now accept document and data formats (CSV, JSON, VTT, SRT, RTF, PDF, TXT, ODT, ODS)

## [2.9.3] - 2026-06-03

### Added
- The transcript editor now shows a legend for named entity types (PER, LOC, ORG, DATE), each in its respective color with a tooltip describing the type

## [2.9.2] - 2026-06-02

### Fixed
- Fixed a Vue compiler error in the transcript editor caused by a duplicate `:class` attribute on transcript words

## [2.9.1] - 2026-06-02

### Added
- Named entities are now displayed in the transcript editor

### Changed
- Enriching a transcript now redirects to the uploaded file
- Edited words in the transcript editor are now marked with a thick underline

### Fixed
- Fixed `DjangoViteAssetNotFoundError` on the resume upload page caused by the `resume_upload_form` asset missing from the Vite config

### Internal
- Updated redis package to 8.0 and other dependencies
- CI now runs the test suite against the built Vite manifest (`VITE_DEV_MODE=false` plus `collectstatic`) so missing asset entries are caught automatically

## [2.9.0] - 2026-06-01

### Added
- Large files are now uploaded in chunks, allowing uploads to resume after an interruption (behind a feature flag)

### Internal
- Updated Sentry SDK

## [2.8.1] - 2026-05-28

### Fixed
- Fixed `recent_upload_activity` admin tag always returning false after a completed upload

## [2.8.0] - 2026-05-26

### Added
- Transcripts can now be enriched with named entity recognition (NER) via a new "Enrich transcript" button on the transcript detail page — the enriched result is saved as a new transcript

## [2.7.1] - 2026-05-21

### Internal
- Added staff-only `/sentry-debug/` route to verify Sentry integration

## [2.7.0] - 2026-05-20

### Added
- New standalone NER microservice for named entity extraction, based on GLiNER2 and FastAPI
- Waveform extraction is now triggered automatically on transcript creation if no waveform exists yet
- Waveform indicator added to the uploaded files list in the project admin

### Internal
- Extracted waveform data into a dedicated `Waveform` model, separated from `UploadedFile`
- Audio duration is now extracted and stored as an independent task, separate from waveform extraction
- Renamed Docker images to `mmt-app` and `mmt-ner`
- Added CI workflows for NER tests and Docker builds

## [2.6.3] - 2026-05-19

### Fixed
- Fixed OOM-induced container restarts when opening a transcript in the admin — waveform data is now deferred when loading the uploaded file dropdown

### Internal
- Added pytest and pytest-django as test runner

## [2.6.2] - 2026-05-18

### Internal
- Replaced hypercorn with uvicorn

## [2.6.1] - 2026-05-12

### Internal
- Added procps to Dockerfile
- Removed unnecessary Docker files

## [2.6.0] - 2026-05-12

### Added
- DPA can now be downloaded as a PDF (generated with Weasyprint)
- Email notification sent when a DPA is created

### Internal
- Added Docker startup scripts and example env file
- Updated dependencies

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
