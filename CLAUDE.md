# CLAUDE.md

## Communication

Prefer acting on reasonable defaults over asking follow-up questions; only stop to ask when a choice is genuinely blocking and you cannot resolve it yourself. Keep responses short and to the point.

Stay within the scope of what was asked. If you notice a related problem elsewhere, mention it instead of fixing it, and leave it for a separate change.

## Writing register

This applies to all text: chat responses, code comments, docstrings, API descriptions, documentation, commit messages, plan docs.

Write plain, literal technical prose. State the mechanism, not a figure of speech for it. No idioms, no casual tech slang, no metaphors, no personification of code.

Examples of what to avoid, and what to write instead:

- "any character overlap claims the whole word" → "a word is part of a span if at least one of its characters lies within the character range"
- "highest score wins" → "the span with the higher score is kept, the other is discarded"
- "the encoder tops out at ~512 tokens" → "the encoder accepts at most 512 tokens"
- "max_len silently drops everything beyond the limit" → "max_len truncates the input beyond the limit without raising an error"
- "callers do not need to chunk their input" → "the caller does not have to split the input"

Complete sentences and precise terms are preferred over brevity. Do not compress prose into fragments or arrow chains.

## Development workflow

Always write tests first, before implementing. When changing existing behavior, change the tests before changing the implementation.

When fixing a bug, first write a test that fails because of the bug, then fix the bug so the test passes.

Test the real boundary, not cosmetic layers in front of it. Skip tests for purely presentational code that can't change behavior or access.

Work in slices when applicable. Make major changes as small, independently deployable slices so the project can be deployed often.

## Backend testing
Run tests with `uv run pytest` from `app/`.

The suite is migrating from Django `TestCase` style to pytest style. Always write new tests in pytest style: plain functions with `assert`, `@pytest.mark.django_db` or the `db` fixture instead of `TestCase` inheritance, and fixtures (`client`, `admin_client`, conftest fixtures) instead of `setUp`/`setUpTestData`. Do not write new `TestCase` classes. Old-style tests are converted gradually; when substantially editing an old-style test file, prefer converting it to pytest style.

## Frontend testing
Run with `npx vitest run` from `app/`. Config is in `app/vitest.config.js`. Test files live alongside source files as `*.test.js`.

## Git
Do not add Co-Authored-By lines to commit messages.

Commit messages do not have to be long. A short subject line is usually enough; only add a body when the commit is really large or its rationale is not obvious.

## Releases
Version bumps, release commits, and tagging are handled by the `release.sh` script. Do not do these manually. When preparing a release, only add the changelog entry under `CHANGELOG.md`.

## Backend translations

Django translation files are in `locale/de/LC_MESSAGES/django.po`. After editing, compile with `python manage.py compilemessages`.

Whenever you introduce a new translatable string in a Django template or Python file, immediately add the German translation to `django.po` and run `compilemessages`.

The compiled `.mo` files are gitignored and produced by the Docker build, so only `django.po` is committed. Running `compilemessages` locally lets the development server pick up the translation, but the resulting `.mo` never appears as a tracked change.

## CSS units

Use `rlh` as the base unit. Do not use pixels.

## CSS property order

Write properties within a rule in alphabetical order.

## Frontend translations

Translations use vue-i18n. Locale files are in `assets/js/locales/en.js` and `de.js`.

- In templates: `$t('key')` or `$t('key', { param: value })` for interpolation
- Keys with parameters use `{param}` syntax (e.g. `"Uploading file {current} of {total}"`)
- Keys are grouped by feature (e.g. `queue.uploading`)
- Always add keys to both locale files
