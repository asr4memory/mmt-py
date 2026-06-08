# CLAUDE.md

## Backend testing
Always run tests with `manage.py test`, not pytest.

## Frontend testing
Run with `npx vitest run` from `app/`. Config is in `app/vitest.config.js`. Test files live alongside source files as `*.test.js`.

## Git
Do not add Co-Authored-By lines to commit messages.

## Backend translations

Django translation files are in `locale/de/LC_MESSAGES/django.po`. After editing, compile with `python manage.py compilemessages`.

Whenever you introduce a new translatable string in a Django template or Python file, immediately add the German translation to `django.po` and run `compilemessages`.

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
