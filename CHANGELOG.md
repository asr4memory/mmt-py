# Changelog

## [Unreleased]

### Fixed
- The transcript media player now streams through the range-aware stream view instead of the download endpoint, so seeking works

## [2.11.10] - 2026-06-23

### Added
- Media on the uploaded file detail page can now be seeked during playback, served through a range-aware stream view with the correct content type

### Changed
- Interrupted downloads can now be resumed, as the download view supports HTTP Range requests

### Fixed
- Media type of uploaded files is now detected from the file contents, so formats the browser reports ambiguously (e.g. ogg) are correctly recognized as audio or video
- The media player no longer fails to play ogg files in Firefox
- A video whose format the browser can't decode now shows a hint to download the file instead of a silent blank player

## [2.11.9] - 2026-06-22

### Changed
- Increased the upload chunk size to 10 MB, halving the number of chunk requests per file
- Sped up uploads by letting the chunks of a single file be processed in parallel instead of waiting on each other

## [2.11.8] - 2026-06-22

### Internal
- Added a management command to remove partial uploads

## [2.11.7] - 2026-06-21

### Added
- Upload progress is now shown in the browser tab title

### Internal
- Made the assembling field read-only in the uploaded file admin

## [2.11.6] - 2026-06-20

### Added
- The uploaded file detail page now auto-refreshes while chunk assembly is in progress
- After a single chunked upload completes, you are redirected to the file detail page

### Changed
- Uploaded chunks are now assembled in a background task

### Internal
- Truncated the filename in the uploaded files admin list view
- Updated dependencies
- Bumped the NER service version

## [2.11.5] - 2026-06-18

### Internal
- Fixed a flaky directory test that left a stray file on disk, causing intermittent failures when two tests ran in the same second and reused the same directory name

## [2.11.4] - 2026-06-18

### Added
- The uploaded file detail page now warns when a file may be corrupted (the client and server checksums disagree)
- Added a dedicated, read-only admin for uploaded files that prevents creating files by hand, with an integrity column and filter to spot corruption, newest-first ordering, and human-readable size and duration
- A checksum mismatch is now logged as a warning so transfer or storage corruption is visible instead of silently accepted

### Changed
- Reduced peak memory during waveform extraction for long recordings
- Pinned the Celery worker to 4 processes and capped its memory so it can no longer starve other services on the shared host

### Internal
- Added an `UploadedFile.objects.corrupt()` queryset for files whose checksums disagree
- Simplified file size formatting in the project admin's uploaded-file inline to use Django's `filesizeformat`
- Added parameterized production deploy scripts (podman) for the web app, Celery worker, and NER service
- Removed the legacy Ansible deployment and the obsolete `run-docker.sh`

## [2.11.3] - 2026-06-18

### Added
- Added `UploadedFile.check_file` to verify a file on disk matches its database record (existence, size, file type, readability), returning a structured report
- Added `Project.check_directories` to verify the project, upload, and download directories exist and are readable, writable, and traversable, and `Project.ensure_directories` to create them

## [2.11.2] - 2026-06-18

### Internal
- Converted the remaining `shared/`, upload, and entry/util JS modules to TypeScript, including the upload form and register-upload code
- Converted the upload queue, queue item, resume-upload, and status-icon components to single-file components
- Extracted a shared `readFiles` helper used by the upload and resume-upload forms
- Removed the unused `inline_message.js`

## [2.11.1] - 2026-06-17

### Changed
- Improved the upload page intro text and queue hints
- Improved the size and readability of transcript words
- The waveform axis tick density now scales with the component width

### Fixed
- Fixed a path traversal issue in `filename_safe` and corrected project deletion
- Project titles are now validated to be filename-safe via a model field validator

### Internal
- Converted the remaining transcript utilities and components from JS to TypeScript single-file components
- Reworked the project use cases (`create_project`, `update_project_title`, `delete_project`) to raise exceptions instead of returning booleans or status tuples

## [2.11.0] - 2026-06-15

### Added
- Active uploads now show percentage, transfer speed, and an estimated time remaining, with byte-level progress tracked per chunk and a compact time format (e.g. `2m 5s`, `17s`)
- Added an `UploadStatusIcon` and switched the queue to a native `<progress>` element showing transfer progress in the item meta
- The page now warns before unloading while chunked uploads are in progress
- Resuming an upload validates the selected file against the expected filename and size first
- Media player, download, and transcript actions are hidden for incomplete uploads

### Changed
- Reduced the upload chunk size from 10 MB to 5 MB and lowered the concurrent chunk upload limit from 4 to 3
- Replaced per-chunk checksums with a single client-side checksum submitted for the whole upload
- Upload chunks are now stored in a subdirectory to reduce clutter in the upload directory
- Plural strings now use numeric counts instead of spelled-out words

### Internal
- Reorganized `assets/js` from a type-based to a feature-based structure
- Converted the chunked upload and resume-upload modules from JS to TypeScript using the Composition API, with generic dataset readers
- Loaded the `JSONEditorWidget` assets via `form.media` in the create-transcript template
- Removed the modulepreload polyfill
- Added and fixed tests for the chunked upload queue item, using real locale messages and removing test noise from unmocked modules and i18n
- Updated dependencies

## [2.10.0] - 2026-06-12

### Added
- New media player toolbar with play/pause, mute/unmute, volume, playback speed (0.7x–2x), and fullscreen controls; clicking the video also toggles playback
- Global keyboard shortcuts for the media player, with a shortcut legend in the sidebar
- The word at the current playback position is now highlighted in the transcript
- The transcript sidebar now supports creating speakers, renaming them, and assigning speaker colors shown as swatches
- The add-transcript form now offers uploading a `.json` file as an alternative to pasting JSON content
- Added a line about data access to the welcome page

### Changed
- Moved the waveform to the top alongside the media player in a new `MediaBar` component
- Moved the transcript sidebar to the right and reworked its named entities section
- Accepted processing requests can no longer be deleted
- Changed the waveform colors

### Internal
- Introduced a three-step border-radius scale (`--border-radius-s/m/l`) and migrated all components to it
- Rewrote the waveform component using the Composition API and TypeScript, extracting a `useWaveformRenderer` composable and a `WaveformRenderer` class, with added tests
- Replaced the D3 CDN global with an npm import, drew the waveform as a single path, and animated the playhead indicator with `requestAnimationFrame`
- Numerous waveform performance optimizations and bug fixes (avoiding full word-rect rebuilds, fixing an SVG rebuild and `timeupdate` listener leak, and simplifying the drag math)
- Added a reusable `transcript-button` component and accessibility attributes to media player controls
- Added VS Code settings with the Biome formatter
- Updated Python to 3.14.6 and other dependencies

## [2.9.8] - 2026-06-10

### Fixed
- The word popover in the transcript editor is now positioned reliably below its word: it uses per-word anchor names with `position-area` (flipping above the word near the viewport bottom), hides on scroll instead of drifting away from the word during auto-scroll, and falls back to manual positioning in browsers without CSS anchor positioning

## [2.9.7] - 2026-06-05

### Fixed
- Visiting a project whose files directory is missing now shows a friendly error page instead of a 500 crash, and the inconsistency is reported automatically

### Internal
- Extracted TranscriptSidebar as a standalone component
- Updated Django, uvicorn and other dependencies
- Replaced the `feature_flags` JSON field on Profile with a dedicated `FeatureFlag` model

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
