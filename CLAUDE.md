# CLAUDE.md

## Testing
Always run tests with `manage.py test`, not pytest.

## Git
Do not add Co-Authored-By lines to commit messages.

## Backend translations

Django translation files are in `locale/de/LC_MESSAGES/django.po`. After editing, compile with `python manage.py compilemessages`.

## Frontend translations

Translations use vue-i18n. Locale files are in `assets/js/locales/en.js` and `de.js`.

- In templates: `$t('key')` or `$t('key', { param: value })` for interpolation
- Keys with parameters use `{param}` syntax (e.g. `"Uploading file {current} of {total}"`)
- Keys are grouped by feature (e.g. `queue.uploading`)
- Always add keys to both locale files

