# Changelog

## [2026.9.23]

### Added
- The file details of a video state whether a web version of the video exists

### Changed
- The player on the file detail page and the player of the transcript editor play back the web version of a video when it exists, and the original file otherwise
- The stream endpoint serves the version that the `version` query parameter names, `original` by default or `web`. A request for the web version of a file that has none is answered with 404 instead of with the original file, and an unknown version is answered with 400
- The browser keeps a streamed media file for up to a day. The stream response carries an `ETag` and a `Last-Modified` header, a conditional request for an unchanged file is answered with 304, and a range request whose `If-Range` names a different version of the file is answered with the whole file

## [2026.9.22.1]

### Added
- The word popover of the transcript editor has a "Split segment after this word" action. It is disabled on the last word of a segment and inside a mention or a redaction

### Fixed
- The media shortcuts are suppressed only for the keys the focused element uses, so a focused button or slider no longer disables all of them, and they keep working after a click on the video

### Internal
- The NER container is limited to 2 CPUs and the celery container to 1.5, and the NER request timeout is 15 minutes

## [2026.9.22]

### Added
- The document bar of the transcript editor has a rename button. It opens the label in an input, Enter or leaving the input commits the new label, Escape cancels, and an empty label is discarded. The renamed transcript is written by the save button together with the content, and discarding the changes restores the saved label

### Changed
- The save status of the transcript editor shows "Unsaved changes" instead of the number of changed segments, because the label is unsaved state as well
- The transcript update endpoint takes a `PATCH` request with `label`, `content` or both, and writes only the fields the body names. Both fields are validated before either is written, and a body that names neither is answered with 400
- The "Transcription started." message is an info message instead of a success message
- The German password reset email addresses the user with "Sie"

### Fixed
- The last row of a table has no border below it. The unused `tfoot` rule that drew a line above the footer was removed

### Internal
- `locustfile.py` defines a Locust load test that requests the welcome page; the README states how to run it against a deployment
- The app image takes node from the official image instead of the NodeSource apt repository and caches the build in ghcr instead of the Actions cache, as the ASR and NER builds already do
- The README names `uv run pytest` as the command that runs the tests

## [2026.9.20]

### Added
- The segment popover of the transcript editor has a "Merge into previous segment" action, disabled on the first segment
- The named entity legend has a checkbox per entity type, so single types can be hidden while the highlighting is on
- A processing request can ask for the media files to be made available on Audio-Visual.Digital, and for existing transcripts to be aligned with the media files

### Changed
- The "Jump to playback" button is always enabled, instead of only while the segment being played is out of view
- The "Make available" field is named `make_available_on_ohd`, and the action table has one column per platform, "OHD" and "AVD"

### Fixed
- Leaving the input of a word without changing its text no longer marks the word as edited

### Internal
- The set of processing actions is defined once, in an `ACTIONS` list; the form, the admin, the check constraint and the templates are derived from it
- Biome was updated to 2.5.14 and the assets were reformatted
- The backend suite hashes passwords with MD5 and reuses the test database; after a migration, rebuild it once with `uv run pytest --create-db`
- The frontend test files that need no DOM declare the node environment
- djlint indents templates with 4 spaces, the djlint default and the indentation of most of the templates, and all templates were reformatted with it. The app tests workflow checks the template formatting with `djlint --check`, and the djLint VSCode extension formats templates on save
- The app tests workflow starts the MySQL of the runner image instead of a service container and installs the system packages in the background

## [2026.9.19]

### Changed
- The enrichment section of the transcript detail page has one button, "Recognize named entities", instead of the two buttons that chose a batching mode. Enrichment always batches by speaker turn, and the section names the model and the entity types. The resulting transcript is labelled `(NER)` instead of `(NER, turns)`
- A word inserted in the transcript editor takes a third of the time range of its neighbour, so it lies inside the segment and does not overlap another word. Its placeholder text is an ellipsis, and its input opens with that text selected
- A word inserted between two words of the same mention, or of the same redaction, joins it, so the run stays contiguous. At either end of a run, or between two runs, it stays unlinked
- A word that was renamed or split by hand gets a score of 1, because the confidence of the recognizer no longer applies. The parts of a split word divide the time range of the original word in proportion to their character lengths

### Fixed
- Deleting a word, a mention or a segment also removes the mentions, redactions and entities that nothing references any more
- The waveform is re-rendered when a word of the active segment is renamed, inserted or deleted
- The playback speed control no longer flickers during playback. It is a component of its own, so the re-render of the player on every `timeupdate` no longer rewrites the attributes of the select and of its options
- Editing the text of a word into several words splits it on any run of whitespace, so a double space no longer produces an empty word

### Internal
- The waveform JSON endpoint sends `Last-Modified` and `Cache-Control: private, max-age=300`, and answers a current `If-Modified-Since` with 304. The conditional check runs after the ownership check
- The transcript store is split into one composable per tier. `updateWord` was renamed to `applyWordEdit` and dispatches to `deleteWord`, `renameWord` or `splitWord`
- The ids written by the frontend spell the uuid without dashes, like the ids written by the backend
- The app dependencies were updated, and `stimulus`, `@vue/devtools-api` and the `main` field were removed from `package.json`
- A git tag `v*` triggers a separate workflow that builds the app image under the release version and fails if that image tag exists. The master workflow writes `latest` and the commit hash, and the ASR, NER and nginx workflows build the same way
- Added a spec for ASR completion notifications and a spec for the service status page

## [2026.9.18]

### Added
- The color swatch of a speaker in the sidebar of the transcript editor is a color input. Picking a color changes the color of that speaker, and the segments that reference the speaker are marked dirty so the change is saved
- The transcript table of an uploaded file has an edit column linking to the transcript editor. The column is shown only to a user with the `transcripts.change_transcript` permission
- The form that starts a new transcription on the uploaded file page has the subheading "New transcription" above it
- The ASR service answers `GET /health` with its status and its version, and the container health check calls that endpoint instead of opening a TCP connection to port 8000
- The transcription result of the ASR service names the whisper model it was produced with, in a `model` field beside `language`. The service version is 0.3.0

### Changed
- The volume of the media player is set with a vertical slider that the mute button reveals on hover and on focus, replacing the two step buttons. The controls of the toolbar use the focus ring of the project, and the fullscreen button is the last control of the row

### Internal
- The `u-ml-auto` utility class is declared only in the spacing utilities; the second declaration in the typography utilities is gone
- Added a spec for resources and metadata

## [2026.9.15.3]

### Changed
- The header of the waveform shows only the timecode range of the active segment, without the segment id and the duration

### Internal
- A media store owns the media element and its play, pause and seek commands, replacing the forwarding chain between components
- The timecode value and range components are merged into one `timecode` block with a `--stacked` modifier

## [2026.9.15.2]

### Internal
- The app tests workflow runs the backend and the frontend job in parallel, and the frontend job runs the typecheck as well as the Vitest tests
- `typescript` is pinned to `^5.9.3`, because `vue-tsc` cannot run against TypeScript 7

## [2026.9.15]

### Added
- The media box of the transcript editor has a seekable progress bar along its lower edge. Dragging it moves the playback position, and the filled part shows how much of the file has been played
- The current playback time is shown over the media box in a compact clock format, `1:23` or `2:47:33`, followed by the total duration of the file
- The document bar shows the total duration of the media file in parentheses after the file name
- A jump button in the transcript header scrolls the segment that is being played into the middle of the viewport. It is enabled only while that segment is outside the visible part of the transcript. During a pause between two segments the target is the segment that was played last. The keyboard shortcut is `J`, listed in the shortcut section of the sidebar

### Changed
- The audio player no longer uses the native browser controls; playback is operated by the toolbar, the progress bar and the keyboard shortcuts. The media bar is 7rlh high for audio and for video of any aspect ratio: a video that does not fill the box is letterboxed, an audio file shows a box of the same size

### Fixed
- The language and the model column of the transcript table show an em dash when the transcript content holds a JSON `null` for the value. MySQL unquotes a JSON null to the string `null`, which was printed as the literal text `null`

## [2026.9.14]

### Added
- The details block of the transcript detail page lists the language, the model, and the number of speakers, segments, words, mentions, entities and redactions of the transcript. A number that cannot be derived, because the key is absent from the content or does not hold a list or a map, is shown as an em dash
- The transcript table of a project shows the language, the model and the segment count of each transcript. The three values are read from the content column by the database, so the list does not load the content of every transcript

### Changed
- The app uses date-based versioning (DateVer): a release version is `YYYY.M.D`, the date of the release, with an optional counter appended for a second release on the same day, for example `2026.9.14` or `2026.9.14.2`. The previous scheme was semantic versioning, so this release follows 2.24.4. `release.sh` rejects any other format. The NER and ASR services keep semantic versioning

### Internal
- The mmt-transcript format gained an optional top-level `model` field holding the name of the speech recognition model the transcript was produced with, for example `whisper-large-v3`. It is carried over from a top-level `model` key of the whisper input and preserved by the editor on save; content without the key validates as before, with the field defaulting to `null`
- `language` and `model` reject the empty string, so `null` is the only way of recording that the value is unknown. The conversion from whisper input strips both values and stores an empty result as `null`

## [2.24.4] - 2026-09-13

### Changed
- The header navigation and the footer link list wrap onto several lines when the viewport is too narrow for one line, instead of widening the page
- Text inputs and textareas are at most as wide as their container, and the button groups of the processing request form wrap, so the form fits a narrow screen
- The uploaded files table of a project scrolls sideways within its own element when it is wider than the viewport. A shadow at the left or right edge marks that content is hidden beyond it
- The export section of the transcript detail page lists the four formats as a row of download links naming the format and the file extension, followed by one note that the mmt-transcript JSON is the stored document and the only download that is not redacted. The per-format rows with a heading and a description are gone

### Internal
- The `nginx` service of the compose file uses the image named by `MMT_NGINX_IMAGE` instead of building the image from `nginx/`, like the other services
- The new `cluster` composition lays out a wrapping row of items with a gap, and the `u-scroll-x` and `u-list-plain` utilities were added. The `action-row` component was removed

## [2.24.3] - 2026-09-12

### Added
- The reverse proxy is built as its own image, `ghcr.io/asr4memory/mmt-nginx`, from the new `nginx/` directory, which also holds the configuration template that was previously bind-mounted from `docker/nginx/`. The nginx workers run as uid 999, the uid of the app user, so the proxy can read user files that are readable by their owner only. `create-mmt-nginx` takes the image tag as its argument like the other deploy scripts

### Removed
- The whole-file upload endpoint and the upload queue that used it. Every upload goes through the chunked upload, which has been enabled for all users since the `chunked_upload` feature flag was added to the set of flags enabled for everyone. The flag name is removed and a migration deletes its per-user rows; the feature flag mechanism itself stays for future flags. `date-fns` is no longer a dependency

## [2.24.2] - 2026-09-12

### Changed
- The transcript editor reports the result of a save as a message above the document bar: a success message after the server accepted the transcript, and an error message with the reason when the request failed. Previously a failed save was only written to the browser console
- While a save request is in flight, the document bar shows "Saving…" in place of the changed-segment count, and the save and discard buttons are disabled until the request has finished
- The save status in the document bar no longer shows a coloured dot next to the label

### Fixed
- After a successful save, the editor removes the dirty flags from the changed segments and words in place instead of replacing the whole segment list, so only the segments that were changed re-render

### Internal
- The `ner` service uses `gliner2` 2.0 with its `local` extra, which resolves a dependency conflict of the previous version; the service version is 0.5.2 and the `asr` service version is 0.1.1

## [2.24.1] - 2026-09-08

### Fixed
- Streaming and downloading a media file through the app no longer reads the whole file into memory before the first byte is sent. Under ASGI, Django consumes a synchronous response iterator completely before sending, so a large video delayed playback by the time it took to read the file and could exceed the memory limit of the web container, which killed the worker. The file is now read by an asynchronous iterator in chunks of one megabyte, so memory stays at one chunk and a client that disconnects stops the read

## [2.24.0] - 2026-09-07

### Internal
- Media files can be served by an nginx container in front of the app instead of passing through Django. The view runs the same permission check and answers with an empty body and an `X-Accel-Redirect` header naming an internal location; nginx serves the file and handles `Range` requests itself. This is switched on by `X_ACCEL_LOCATION`, which is unset by default, so development and any deployment without the proxy serve the files as before. The proxy configuration, the compose service and the `create-mmt-nginx` deployment script are in the repository
- The Celery beat schedule files of a local development run are now in .dockerignore

## [2.23.1] - 2026-09-01

### Internal
- The app test workflow updates the apt index before it installs the system dependencies, because the package index of the runner image refers to package versions that the mirror has already replaced, and the installation then fails with a 404

## [2.23.0] - 2026-09-01

### Changed
- The name an uploaded file is stored under is transliterated to ASCII with `anyascii`, lowercased and reduced to `[a-z0-9._-]`, so that an administrator can type and copy every name in a directory listing. `რთ.mp4` is stored as `rt.mp4`. Files already on disk are not renamed
- The web interface names an uploaded file by the name the user submitted rather than by the name on disk, on the upload detail page, in the file and transcription job tables of a project and on the transcript pages. The details block of the upload detail page shows the stored name under "Filename on disk" whenever the two differ, and a download is served under the submitted name
- The uploaded file changelist in the Django admin, and the inline on the project page, show the stored name and the submitted name in their own columns

### Fixed
- The `Content-Disposition` header of a download is built with Django's `content_disposition_header`, so a non-ASCII filename is encoded per RFC 8187 instead of being written as an RFC 2047 word, which browsers do not read in this header

### Internal
- The `table__wrap` element of the table component was replaced with a `u-break-anywhere` utility class, because breaking a long word inside a cell is not specific to tables

## [2.22.0] - 2026-08-30

### Added
- A transcript can be exported as whisperX JSON, WebVTT or SubRip from an export section on its detail page. Every export applies the redactions of the transcript: a redacted word is written as `XXX`, so it keeps its timings and the segment keeps its word count

### Changed
- The main column of the transcript detail page is ordered by what each action does to the document, and the download of the stored content moved into the export section as its first row
- The title and the breadcrumbs of the transcript detail page name the type of the transcript, because a label such as "ASR" identifies nothing on its own

### Fixed
- The name an uploaded file is stored under is shortened to 200 bytes, so that it still fits the filesystem limit of 255 bytes after the duplicate suffix and the `.mp4` of the web version have been appended

## [2.21.0] - 2026-08-25

### Added
- The mmt-transcript format has a `redactions` map that holds the passages of a transcript that must not be published, and every word carries a `redactionId` that either references an entry in that map or is null. The words of one redaction have to lie in a single segment and next to each other, the map is a required part of the format, and both are documented in `docs/mmt-transcript-format.md`
- The transcript editor marks a word as redacted from the word popover, extends and shortens the redaction word by word to either side within its segment, removes it again, and records a free-text reason for it. A redacted word is shown with a line through it, so that the entity colour and the dirty-word underline of the same word stay visible

### Fixed
- The upload speed samples are trimmed in place instead of being copied into a discarded array, so the sample list no longer grows for the whole duration of an upload and every progress event only scans the current window

### Internal
- The temporary files Django writes during an upload are stored in the system temp directory instead of the volume that holds the user files, because `FILE_UPLOAD_MAX_MEMORY_SIZE` is compared against the whole multipart body and every chunk took the temporary file path anyway
- Removed the unused `django-storages` and `watchdog` dependencies, and updated the Python and JavaScript dependencies of the app

## [2.20.1] - 2026-08-13

### Internal
- The project admin list shows the number of files of a project, the total size of those files and their total duration, and each of these columns can be sorted. The three values are also shown on the project detail page, and the field `downloadable_files_count` is labelled "Downloads"
- The title column of the project admin list has a minimum width, so that a short title does not squeeze the column
- The uploaded files admin shows the user of the file's project as a column and offers that user as a filter

## [2.20.0] - 2026-08-11

### Added
- The mmt-transcript format has an `entities` map that holds the canonical entities of a transcript, and every mention carries an `entityId` that either references an entry in that map or is null. The map is a required part of the format and is documented in `docs/mmt-transcript-format.md`

### Changed
- Chunked upload is enabled for every user instead of only for users with the corresponding feature flag
- A file with the media type `application/mxf` is categorized as video, so an MXF file is handled like the other video formats

### Internal
- `FeatureFlag.ENABLED_FOR_ALL` lists the flags that are enabled for every user regardless of per-user rows, so a feature can be released to everyone with a single entry
- The word and character mapping of the NER service was moved from the windowing module into the new `words.py`, and `align.py` was renamed to `windowing.py`
- Updated Python to 3.14.7 and 3.13.14, Django to 6.0.8, and the dependencies of all three applications

## [2.19.1] - 2026-08-03

### Fixed
- A transcription that cannot be submitted, because the ASR service is unreachable for example, is marked as failed instead of staying pending. A pending job is never resubmitted and blocks any further transcription of that file, so such a job could not be restarted by the user. An unreachable service is reported as "The transcription service could not be reached." and logged with the exception
- A transcript created by the ASR service also triggers the generation of the 480p web video and the waveform, which are needed to edit it
- The transcript editor renders an empty waveform when the waveform endpoint answers with an error, instead of crashing on the error body parsed as a waveform
- Only the table columns that hold arbitrary text, such as a filename, break within a word, so that the other columns are not squeezed

### Internal
- The transcription sweep logs an unreachable ASR service as a single warning line instead of a full traceback per job
- The ASR spec records the behaviour of a submission that fails

## [2.19.0] - 2026-08-03

### Added
- An audio or video file can be transcribed by the ASR service from its detail page. The form offers the languages WhisperX has an alignment model for and, as the default, automatic language detection, plus an option for speaker diarization. The app submits the job to the service, a periodic sweep polls every unfinished job, and the result is stored as a new transcript labelled "ASR". A file can have only one unfinished transcription at a time. The feature is shown and can be started only when an ASR service is configured through `ASR_API_URL`, which has no default value
- The uploaded file detail page lists the transcriptions of that file with their status, their progress while they run, the error message of a failed one, and a link to the transcript of a finished one
- The project detail page lists the transcriptions that are still running, and its file table shows the number of transcripts per file

### Changed
- The uploaded file and the transcript detail page show their details in a sidebar next to the main column instead of above the content, and both pages use the wide container
- The state of an upload is shown as a note in the main column instead of as a remark next to the status pill. The note for a file that is still being processed reloads the page once processing has finished
- An assembled file whose server and client checksum disagree has the status "corrupt" instead of "complete". Such a file is not played back and cannot get a transcript, but it stays downloadable so it can be inspected locally

### Fixed
- The size on the download detail page has a tooltip with the exact byte count again; it read a variable that does not exist in that template and was therefore empty

### Internal
- The `Transcribers` group created by `creategroups` also gets the transcription job permissions
- Celery beat runs in the worker container and is configured with the sweep schedule; `ASR_API_URL` is passed to the app and worker in both the compose file and the deployment scripts
- The upload status polling was extracted from an inline `x-data` expression in the template into the `upload_status_poller` Alpine component in TypeScript, with unit tests
- The metadata panel of the uploaded file and the transcript detail page lives in `_metadata.html`, and the transcription table of the project detail page in `_transcription_jobs_table.html`
- The transcript `content` field is deferred on the transcription jobs joined into the uploaded file detail page
- Updated the frontend and development dependencies
- Added a spec and an architecture note for canonical entities

## [2.18.2] - 2026-07-31

### Changed
- The processing requests on the project detail page are listed in a table instead of cards. The table shows the creation and update date, the status, the number of files, the language and the four processing options

### Internal
- Added a `TimestampedModel` base class with `created_at` and `updated_at`, which every model except `User` now inherits; `User` records its creation time in `date_joined`. Rows that existed before are backfilled with the migration timestamp, and profiles with the `date_joined` of their user
- The project, transcript, uploaded file and processing request admin pages show `created_at` and `updated_at`
- Test fixtures set both timestamps explicitly, because `loaddata` saves with `raw=True` and therefore does not fill `auto_now_add` and `auto_now` fields
- Moved `generate_file_md5` from `uploaded_files.media` to `core.utils`, because it hashes an arbitrary file and is not media-specific
- Exceptions raised in tests are no longer sent to Sentry
- Added specs and architecture notes for the transcript export and the read-only API

## [2.18.1] - 2026-07-28

### Changed
- The web video and the waveform are only generated once an uploaded file has its first transcript, instead of right after every upload, because both are only used while editing a transcript. A file whose transcript was created before the upload finished gets them at the end of the assembly

### Fixed
- Deleting an uploaded file also removes the derived 480p web video from disk, which was left behind before

### Internal
- The transcript `content` field is deferred in the views and admin pages that do not read it
- Ran a ruff import sorting and formatting sweep over the whole app
- The app tests workflow installs ffmpeg, which the media tests require

## [2.18.0] - 2026-07-28

### Added
- A video upload is transcoded to a 480p H.264/AAC MP4 in a background job after the upload has been assembled. Inline playback streams that derived file when it exists and the original otherwise, so a video in a container or codec the browser cannot decode still plays and less data is transferred. Downloads and transcription keep using the stored original

### Internal
- Renamed `analysis.py` to `media.py`, which now holds every ffmpeg and ffprobe helper, including the new `transcode_to_web_video`
- The media type is detected in `task_assemble_chunks` instead of in a task of its own, because the decision whether to enqueue the web video transcode depends on it, and the separate `task_update_media_type` was removed
- The uploaded file admin change page shows the `has_web_video` field

## [2.17.1] - 2026-07-27

### Changed
- The project card shows a "Created at" label in front of the creation date, underlines its title while the card is hovered or contains the focus, and truncates titles longer than two lines

### Internal
- Removed the segment-level `text` field from the mmt transcript format; the words are the only representation of what was said, so no consumer can read a stale copy of an edited or redacted passage. Transcripts stored while the field existed no longer validate and have to be deleted
- The upload count on the project card is annotated onto the project list query instead of being counted once per card
- The NER health check is configured per deployment, as run flags in `deploy/create-mmt-ner` and as a compose healthcheck for the development environment, because Podman does not apply an image `HEALTHCHECK`
- The NER mapping tests call `word_candidates` directly, and the `to_word_spans` wrapper, which had no caller outside the tests, was removed
- Updated the NER dependencies and changed their version constraints to compatible-release specifiers
- Added a spec for redacted and anonymized sections, and updated the ASR app integration spec with the implemented transcript language and with where a transcription job appears in the UI
- Celery beat schedule files are ignored by git

## [2.17.0] - 2026-07-25

### Added
- An ASR (automatic speech recognition) service that transcribes audio and video and performs speaker diarization, packaged as a container image with a shared model cache volume, a deploy script, and CI workflows

### Changed
- The bottom margin of the notice component was reduced

### Fixed
- The transcript label field on the create-transcript page is no longer marked optional and now displays validation errors when it is left empty

### Internal
- Moved the transcript language out of the `Transcript.language` model field into the mmt transcript content, where it is read from the fetched content and written back on save so editing preserves it
- The NER `/extract` endpoint accepts windowing parameters per request
- Added specs for the ASR service, the ASR app integration, and the transcript language in content

## [2.16.0] - 2026-07-20

### Added
- An interrupted chunked upload is now detected and resumed automatically when the same file is uploaded again; it continues from the chunks already stored on the server instead of starting over

### Changed
- The dedicated resume-upload page was removed; to continue an interrupted upload, upload the same file again and it resumes automatically
- File types are shown as a translated category label instead of the raw MIME type
- Files using the `application/ogg` container are now treated as video
- Data tables and file-status pills were restyled, and the notice boxes were replaced with a new note component

### Internal
- Documented spec-driven development and added specs for web video, the poster image, frame extraction, and resumable uploads
- The upload chunk size is injected via the template instead of being read from API responses
- Centralized the server URL paths in a routes module
- Extracted the SVG icons into a dedicated directory
- Tokenized the font weights and collapsed them to normal and bold
- Pinned TypeScript to the 5.x line so vue-tsc works
- Split the oversized uploaded-file model tests into topic-focused files
- Updated dependencies

## [2.15.5] - 2026-07-16

### Changed
- The registration hint on the login page no longer mentions logging in with an alternative account, since the social login section below it already explains that

### Fixed
- The registration page is no longer horizontally scrollable; the spam protection field is now hidden without being positioned off screen

## [2.15.4] - 2026-07-16

### Changed
- The social login section on the login page now explains that an existing Oral-History.Digital account can be used instead of a separate MMT account, and each provider is shown as a button with the provider logo

### Internal
- The surface CSS variables are named by role: `--surface-hover` for the hover tint and `--surface-rule` / `--surface-rule-strong` for rule weights

## [2.15.3] - 2026-07-15

### Added
- Each row of the downloadable files list has a download link

### Internal
- Fixed and expanded the CI badges in the README

## [2.15.2] - 2026-07-15

### Changed
- Downloadable files are now listed in case-insensitive alphabetical order by name

### Internal
- The NER healthcheck is defined once in the image and inherited by compose and podman, and now queries the `/health` endpoint with curl instead of netcat

## [2.15.1] - 2026-07-12

### Added
- The NER service accepts an optional `threshold` parameter on `/extract` that sets the minimum confidence a mention must reach to be returned
- The NER service exposes a `/health` endpoint

### Changed
- The entity label descriptions used by the NER model were rewritten as positive statements that only state what an entity is
- The window size used when splitting long NER batches was tuned to fit the model's context
- The uploaded-file columns in the admin inline and in the changelist now show the same fields

### Internal
- Added an NER evaluation harness with two annotated transcripts
- Documented the NER API in the OpenAPI schema and expanded the NER README with a local setup walkthrough
- Test workflows now only run on pushes to master
- Updated Django and other dependencies

## [2.15.0] - 2026-07-05

### Added
- Word and segment popovers were redesigned into labelled sections, and the mention type is now an editable select
- New mention-editing actions: tag a word as a new entity, extend a mention's span left/right, reduce its span, and remove a whole entity mention

### Changed
- Raised the maximum upload size to 10 MB

### Internal
- Cleaned up popup styles and unified class names under the popup block
- Updated dependencies

## [2.14.1] - 2026-07-04

### Added
- The word popover now shows details about a word's named-entity mention: the full mention text, its type, and the NER confidence

### Changed
- Named-entity mentions spanning multiple words now render as a single contiguous highlighted pill

## [2.14.0] - 2026-07-03

### Added
- Named-entity mentions are now first-class objects with a confidence score, replacing the per-word NER fields; they are stored as a map keyed by mention id
- Enrichment can now be run per speaker turn or per segment, selectable via separate enrich buttons
- Error and warning messages now persist with a close button instead of auto-dismissing

### Changed
- The NER service now exposes a format-agnostic `/extract` endpoint that returns mentions aligned to word spans, and requests are batched by speaker turn or segment; long batches are windowed to fit the model's context

### Internal
- Removed the `/enrich` endpoint and the transcript-schema mirror from the NER service
- Added z-index scale tokens and applied them to the app's layered components
- The validator now rejects orphaned mentions and bounds mention scores to [0, 1]
- Dropped the `version` field from `package.json` in favor of `pyproject.toml`
- Updated dependencies

## [2.13.6] - 2026-06-30

### Changed
- Django messages are now restyled with level-specific icons

### Fixed
- The transcript detail page now shows the delete button to users with delete permission, and the enrich button is gated on the change permission the action actually requires
- The enrich action now requires the change permission, and the transcript JSON endpoint returns consistent 404/403 responses

## [2.13.5] - 2026-06-29

### Internal
- Moved the allauth account page container into the shared entrance/manage layouts so it is defined once instead of repeated in every account template

## [2.13.4] - 2026-06-29

### Changed
- The email verification and password reset confirmation pages now render inside a container

## [2.13.3] - 2026-06-29

### Changed
- Redesigned the button component with a token-driven depth and shadow recipe and primary/secondary/danger/small variants; the document bar save/discard buttons and the previously unstyled enrich button now use it
- The speaker legend's add/cancel buttons now use the shared button component, and its glyph buttons were replaced with icon-button SVGs
- The password change page now renders inside a container

### Internal
- Made the icon-button component self-contained
- Removed the unused `RegisterForm` and utils module along with dead contrib.auth registration templates
- The dev web and celery containers now wait for the database to be healthy before starting

## [2.13.2] - 2026-06-28

### Internal
- Compile translations and collect static files at Docker build time instead of on every container start, so containers boot faster and worker containers no longer redo this work
- Tightened `.dockerignore` to keep tests, tooling and the local `.env` out of the image

## [2.13.1] - 2026-06-28

### Internal
- Consolidated the CSS custom properties into a three-tier system (primitives, semantic, scale), replacing the overlapping `colors`/`tokens`/`other`/`typography` files; primitives are now named by lightness and each value has a single definition

## [2.13.0] - 2026-06-28

### Added
- Each segment's timecode now opens a popover where you can edit its start and end times and run segment actions
- Speakers can now be deleted, with an inline confirmation; their references on segments and words are cleared

### Changed
- Clicking a segment's timecode activates that segment and seeks the waveform to it
- Double-clicking a segment's timecode seeks the media to it and starts playback
- Timecodes are shown as a stacked start/end range, with the end time dimmed and revealed on hover or focus
- The transcript header (document and media bars) is now sticky and gains a shadow once scrolled
- The word popover shows confidence with a native meter bar, and its label was renamed to "Confidence"
- The waveform now uses a sans-serif font

### Internal
- Tightened the mmt-transcript schema
- Extracted the speaker list into a `SpeakerLegend` component, the save status into its own component, and renamed the transcript subhead to a document bar
- Consolidated pill variants and derived status, confidence and pill colors from shared intent tokens, and regularized the gray scale
- Removed an unused `popover.css`

## [2.12.1] - 2026-06-26

### Changed
- Word actions in the transcript editor now open from a button that appears when hovering a word, instead of on hover, and the popover stays open until you dismiss it
- Transcript settings now live in a slide-in drawer instead of a fixed sidebar
- Each segment's actions and metadata moved into a left gutter column so the transcript text flows uninterrupted, with words shown in a serif font
- The transcript subheading file name now links to the uploaded file
- The speaker selector now offers a "None" option, and is hidden for segments when no speakers exist

### Internal
- Extracted the transcript word popover into its own `WordPopover` component, rendered on demand, and moved positioning to Floating UI
- Word and segment ids are now strings only, and the segment header was renamed to a left-side meta `<aside>`

## [2.12.0] - 2026-06-25

### Added
- Transcript imports are now validated on upload; only Whisper/WhisperX transcripts with word-level timestamps are accepted, and unsupported files are rejected with a clear error

### Changed
- Transcripts are now stored in a normalized mmt-transcript format with stable ids for segments, words and speakers, and a dedicated speaker list (id, name, color)
- Transcript content is validated when saved from the editor

### Internal
- Introduced the mmt-transcript Pydantic schema and normalize transcript content to it on ingestion
- Added a `normalize_transcripts` management command to bulk-upgrade existing transcripts
- Made the NER service round-trip the mmt-transcript format
- Dropped the frontend transcript conversion layer; speakers are now keyed by id
- Excluded Python files from the vite watch folders
- Added an enriched example transcript JSON
- Updated dependencies

## [2.11.11] - 2026-06-23

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
