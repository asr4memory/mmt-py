# Spec: Tabs on the project detail page

Status: not started.

This document is an **executable spec** (spec-driven development): it is the
prompt an implementing session works from and the authoritative record of every
decision, not a background sketch. Resolve ambiguity by reading this doc, not by
inventing; if a genuinely new decision comes up, write it into the doc as part
of the task. Check off tasks (`[x]`, with date) as they land. Do not duplicate
CLAUDE.md conventions here (test-first, pytest style, CSS units, translations in
both locales).

## Motivation

[`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)
stacks three independent sections on one page: uploaded files, downloadable
files and processing requests. Each grows with the project, so the page grows
with it, and a user looking for one of the three scrolls past the other two.
Project settings is a fourth thing about the same project, reachable only
through a button in the page header and rendered by a separate page,
[`project_settings.html`](../app/mmt/projects/templates/projects/project_settings.html),
that repeats the breadcrumbs and the title.

Splitting the four into tabs shows one section at a time and gives each one an
address. It also removes work from the common case: today every view of the
page renders every section, including the directory listing of the download
directory, whichever section the user came for.

## Non-goals (v1)

Do not add these, even where they would be easy:

- **No overview tab.** A fifth tab was considered and rejected. The project
  header (title, description, creation date) stays above the tab bar and is
  therefore visible from every tab, which is the content an overview tab would
  have held.
- **No `hx-boost`.** htmx is loaded for the tab bar only. Ordinary links and
  forms elsewhere in the application keep doing full-page navigations.
- **No htmx on the settings form or the delete form.** Both submit as ordinary
  full-page navigations. htmx does not touch a form without `hx-post` or
  `hx-boost`, so this costs nothing to uphold.
- **No out-of-band swaps.** A tab response replaces one element, the panel.
  Nothing else on the page updates from it.
- **No client-side prefetching** of the inactive tabs on hover or on idle.
- **No change to what the four sections contain.** This feature moves existing
  markup behind tabs. Table columns, cards, buttons, permission texts and the
  processing request flow stay as they are.
- **No tab state in the query string.** Each tab is a path, not
  `?tab=downloads`.
- **No removal of Alpine.** Alpine keeps its three existing inline `x-data`
  uses. It is simply not used for the tabs. (Unrelated but worth a separate
  change: `stimulus` is in [`package.json`](../app/package.json) dependencies
  and is imported nowhere.)

## Feature reference

### Routes

One route per tab. `/projects/<pk>/` **is** the uploaded files tab: it is not a
redirect to a fifth URL, so existing links to the detail page keep working and
no content is reachable under two addresses.

| method & path | name | tab |
|---|---|---|
| `GET /projects/<int:pk>/` | `projects:detail` | Uploaded files (default) |
| `GET /projects/<int:pk>/downloads/` | `projects:downloads` | Downloadable files |
| `GET /projects/<int:pk>/processing-requests/` | `projects:processing-requests` | Processing requests |
| `GET, POST /projects/<int:pk>/settings/` | `projects:settings` | Project settings |

`projects:settings` already exists and keeps its path; only what it renders
changes. The two new paths do not collide with the existing
`<int:pk>/downloads/<str:filename>/` and
`<int:pk>/processing-requests/create/` patterns, because those have one path
segment more, so no ordering constraint applies in
[`urls.py`](../app/mmt/projects/urls.py).

All four views are `@login_required` and scope by owner exactly as today:
`get_object_or_404(Project, pk=pk, user=request.user)`. A request for another
user's project returns `404` on every tab.

### Full page versus panel snippet

Every tab view renders the same template,
[`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html):

- Without the request header `HX-Request`, it renders the whole page: base
  layout, project header, tab bar, and the active tab's panel.
- With `HX-Request: true`, it renders **only** that tab's partial, using Django
  6.0's template partials:
  `render(request, 'projects/project_detail.html#downloads-panel', context)`.

One template is the source for both paths, so the panel markup cannot drift
between a full page load and a fetched swap.

`HX-Request` is htmx's own header, sent on every htmx-issued request. The view
checks `request.headers.get('HX-Request')` for any truthy value. No private
header is invented for this, and `django-htmx` is not added: one header lookup
does not need a package.

Every tab view carries `@vary_on_headers('HX-Request')`. Without it a cache (the
browser's included) can serve a stored bare panel as the answer to a full page
request for the same URL, leaving the user on a page with no layout.

### Tab bar

The tab bar is a `<nav>` containing an unordered list of ordinary `<a href>`
links, one per tab, in this order: Uploaded files, Downloadable files,
Processing requests, Project settings.

Links, not `role="tab"`. Every tab is a real URL that a full-page navigation
loads, which is what a link means; the ARIA tabs pattern describes a widget
that swaps panels without navigating, and adopting it would also oblige us to
implement its arrow-key focus behavior. The active tab is marked
`aria-current="page"`.

Each link carries both an `href` and an `hx-get` with the same URL. The `href`
is what makes the tab work without JavaScript, and what lets the link be opened
in a new tab or copied; `hx-get` is what htmx acts on, and it takes precedence
when htmx is running.

The shared htmx attributes live on the `<nav>`, not repeated on each link, since
htmx attributes are inherited by descendants:

```html
<nav class="tabs" hx-target="#tab-panel" hx-push-url="true">
  <ul class="tabs__list">
    <li class="tabs__item">
      <a class="tabs__link" data-testid="downloads-tab"
         href="{% url 'projects:downloads' project.pk %}"
         hx-get="{% url 'projects:downloads' project.pk %}"
         {% if active_tab == 'downloads' %}aria-current="page"{% endif %}>…</a>
```

`hx-swap` is not written: its default is already `innerHTML`, which is what the
panel needs.

The panel container is `<div id="tab-panel" data-testid="tab-panel">`; the `id`
is what `hx-target` selects.

### htmx configuration

Two settings in [`main.ts`](../app/assets/js/main.ts), both load-bearing.
Verified against the htmx 2.x source rather than the prose documentation, which
is stale on the first point.

- **`htmx.config.historyRestoreAsHxRequest = false`.** It defaults to `true`
  (`htmx.js` line 281). When the user presses Back and htmx's history cache
  misses, htmx re-requests the URL and, with the default, sends `HX-Request` on
  that request. Our server answers `HX-Request` with a bare panel, and htmx
  restores the response as the whole body — so a cache-missing Back would drop
  the user on a layout-less fragment. Setting it to `false` makes the restore
  request an ordinary one, which returns the full page, which is what a restore
  needs. This is exactly the case htmx's docs warn about for servers that vary
  content on the header.
- **An `htmx:responseError` listener** that calls `window.location.assign(url)`
  for the failed request's URL. htmx's default `responseHandling` (`htmx.js`
  line 264) is `[{code: '204', swap: false}, {code: '[23]..', swap: true},
  {code: '[45]..', swap: false, error: true}]`: a 4xx or 5xx is **not swapped**,
  which is right — an error body must not land inside the tab bar — but the
  default is then to do nothing at all, so the click would appear to be ignored.
  Navigating to the URL hands the response to a full page render, which shows
  the `500` page for a missing download directory, the login page for an expired
  session, or the `403` page for a revoked permission. The component does not
  itself decide what an error looks like.

The history snapshot cache is left **on**. htmx keeps it in `sessionStorage`,
not `localStorage` (`htmx.js` lines 3139-3254; the docs prose saying
`localStorage` is out of date), so snapshots are scoped to the tab and cleared
when it closes. `hx-history="false"` is therefore not set: the residual exposure
is a snapshot surviving a logout in a still-open tab, which does not justify
losing instant Back.

### Which tabs are rendered

Uploaded files, Downloadable files and Project settings are always in the tab
bar.

**Processing requests** is in the tab bar when
`perms.projects.view_processingrequest` and `show_processing_request_section`
(the existing condition: the project has uploaded files or has processing
requests). Both are already in [`views.py`](../app/mmt/projects/views.py) and
[`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)
and are kept as they are.

Direct access to that tab's URL when it is not in the bar is decided per reason,
because the two conditions differ in kind:

- Missing `view_processingrequest` is an access rule: the view returns `403`
  via `@permission_required('projects.view_processingrequest', raise_exception=True)`.
  `raise_exception=True` is required and is not decoration:
  [`uploaded_files/views.py`](../app/mmt/uploaded_files/views.py) uses the
  decorator both with and without it, and without it a logged-in user lacking
  the permission is redirected to the login page instead of being refused.
- `show_processing_request_section` being false is a UI convenience — nothing is
  hidden from the user, there is simply nothing yet to show. The view renders
  the tab normally, with the existing "You haven’t submitted any processing
  requests yet." empty state.

The uploaded files panel keeps its existing internal
`perms.uploaded_files.view_uploadedfile` and
`perms.uploaded_files.add_uploadedfile` guards, which control parts of the panel
rather than access to it. The uploaded files tab itself is not permission
gated: it is the default tab, and a user without `view_uploadedfile` still sees
the panel's permission notice, which is what it exists for.

### Decided conventions

- **Tab labels** are the existing section headings: "Uploaded files",
  "Downloadable files", "Processing requests", "Project settings". All four
  msgids already exist in
  [`django.po`](../app/locale/de/LC_MESSAGES/django.po), so this feature adds
  no new translatable string. The `<h2>` heading inside each panel is removed,
  because the tab label now names the section and a heading directly under it
  would repeat it.
- **The "Project settings" button** in the page header
  ([`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)
  lines 15-17) is removed; the tab replaces it.
- **`data-testid` per tab link:** `uploaded-files-tab`, `downloads-tab`,
  `processing-requests-tab`, `settings-tab`.
- **`active_tab` in the context** is one of the strings `'uploaded-files'`,
  `'downloads'`, `'processing-requests'`, `'settings'`. The template compares
  against it to mark `aria-current` and, on a full page render, to pick the
  panel. Each tab view sets it explicitly; it is never derived from
  `request.path`.
- **Partial names** match the tab strings with a `-panel` suffix:
  `uploaded-files-panel`, `downloads-panel`, `processing-requests-panel`,
  `settings-panel`.
- **Each view builds only its own panel's context.** `project_detail` does not
  query processing requests; `project_downloads` does not query uploaded files.
  This is the work the feature removes from the common case, so a view that
  assembles the full context for every tab defeats the point.
- **`downloadable_files_count` is written only by the downloads view.**
  `project_detail` currently calls `get_files_with_info`, assigns
  `project.downloadable_files_count` and calls `project.save()` on every page
  view. That moves as-is into the downloads tab view, so the stored count is
  refreshed when the downloads tab is opened and not on every visit to the
  project. This is accepted, not overlooked: the count is only read inside the
  downloads panel, where it is recomputed before it is read.
- **A missing download directory** keeps its current behavior, now scoped to the
  downloads tab: `get_files_with_info` raises `FileNotFoundError`, the view logs
  it with `exc_info=True` and renders
  [`project_detail_error.html`](../app/mmt/projects/templates/projects/project_detail_error.html)
  with `status=500`. On an htmx request the same `500` is returned and htmx does
  not swap it; the `htmx:responseError` listener navigates to the URL, and the
  user gets the error page as a full page.
- **The settings form on success** redirects to `projects:settings`, the
  settings tab, rather than to `projects:detail` as it does today. The user
  stays where they were working. `update_project_title` failure keeps rendering
  the settings tab with the message, as now.
- **Project deletion** keeps redirecting to `projects:index`.

### Styling

A new `assets/css/components/tabs.css`, imported from
[`main.css`](../app/assets/css/main.css) in the alphabetical position that file
already keeps. Class names: `tabs`, `tabs__list`, `tabs__item`, `tabs__link`,
and the active link is selected as `.tabs__link[aria-current="page"]` rather
than through a modifier class, so the state lives in the one attribute the
server already renders.

## File layout

- **[`app/mmt/projects/urls.py`](../app/mmt/projects/urls.py)** — new
  `downloads` and `processing-requests` routes.
- **[`app/mmt/projects/views.py`](../app/mmt/projects/views.py)** —
  `project_detail` loses the downloads and processing request context; new
  `project_downloads` and `project_processing_requests`; `project_settings`
  renders the tab template and redirects to itself on success. All four share a
  small helper:

  ```python
  def _render_tab(request, project, tab: str, context: dict):
      """Render the whole detail page, or only the tab's panel for an htmx request."""
      template = 'projects/project_detail.html'
      if request.headers.get('HX-Request'):
          template = f'{template}#{tab}-panel'
      return render(request, template, {'project': project, 'active_tab': tab, **context})
  ```

- **[`app/mmt/projects/templates/projects/project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)**
  — project header, tab bar, and the four `{% partialdef %}` panels.
- **[`app/mmt/projects/templates/projects/project_settings.html`](../app/mmt/projects/templates/projects/project_settings.html)**
  — deleted; its form and its delete form move into the `settings-panel`
  partial, its `{% block javascript %}` delete confirmation into
  `project_detail.html`.
- **[`app/package.json`](../app/package.json)** — `htmx.org` ^2.0 added to
  dependencies.
- **[`app/assets/js/main.ts`](../app/assets/js/main.ts)** — imports htmx, sets
  `htmx.config.historyRestoreAsHxRequest = false`, registers the
  `htmx:responseError` listener.
- **[`app/assets/css/components/tabs.css`](../app/assets/css/components/tabs.css)**
  and **[`app/assets/css/main.css`](../app/assets/css/main.css)** — new
  component and its import.
- **Tests:** a new `app/mmt/projects/tests/test_detail_tabs.py` for the four
  views and the tab bar, and the swap tests appended to the existing
  `app/mmt/projects/tests/test_selenium.py` (see Tests for why that file). The
  new backend test file is used rather than
  [`test_views.py`](../app/mmt/projects/tests/test_views.py), which is 724 lines
  of `TestCase`-style tests; new tests are pytest style, and mixing the two
  styles in one file has no upside. The existing `test_project_detail_page*` and
  `test_project_settings*` tests in `test_views.py` are updated in place where
  this feature changes their expectations (see the slices).

### Template structure

```
{% extends "base.html" %}
{% block content %}
  breadcrumbs, {{ project.title }}, description, created at
  <nav class="tabs" hx-target="#tab-panel" hx-push-url="true">…four links…</nav>
  <div id="tab-panel" data-testid="tab-panel">
    {% if active_tab == 'uploaded-files' %}
      {% partialdef uploaded-files-panel inline %}…{% endpartialdef %}
    {% endif %}
    {% if active_tab == 'downloads' %}
      {% partialdef downloads-panel inline %}…{% endpartialdef %}
    {% endif %}
    …
  </div>
{% endblock %}
```

The `inline` argument renders the partial where it is defined, so the same block
serves the full page. Registration happens at parse time, so a partial inside a
false `{% if %}` branch is still addressable as
`project_detail.html#downloads-panel` — verified on this repo's pinned Django
6.0.7, together with the two other facts the design rests on: a
`{% partialdef %}` in a template that `{% extends %}` another renders standalone
through `#name` without the parent layout, and hyphens in partial names parse.

## Tests

### Where the browser tests live, and what that costs

The swap tests go into the existing
[`test_selenium.py`](../app/mmt/projects/tests/test_selenium.py), as pytest-style
functions beside the current `StaticLiveServerTestCase` class (pytest collects
both; do not add to the class, and do not write a new `TestCase`). They use
pytest-django's `live_server` fixture and a module-level session-scoped
`selenium_driver` fixture built like the existing `setUpClass`: headless
Firefox, `intl.accept_languages` set to `en`, `implicitly_wait(10)`.

The reason for that file specifically: CI runs
`pytest --ignore=mmt/core/tests/test_selenium.py --ignore=mmt/projects/tests/test_selenium.py`
([`app-tests.yml`](../.github/workflows/app-tests.yml)), excluding browser tests
**by path** because the runner has no Firefox or geckodriver. A new file named
`test_tabs_selenium.py` would not match an `--ignore` and would fail CI. Writing
into the already-excluded file keeps this feature out of the CI configuration.

The cost is stated plainly: **these tests only run when someone runs them
locally.** The same exclusion is why `test_uploading_files` in that file has
been sitting under `@unittest.skip`. Therefore the split below is deliberate:
everything about the server contract is a pytest test that CI runs, and selenium
is used only for the two things that cannot be asserted below the browser — that
htmx swaps the panel, and that Back works. Do not move server-contract
assertions into selenium.

### `app/mmt/projects/tests/test_detail_tabs.py` — fixtures

- **`project`** — a project owned by a known user, with one uploaded file and
  one processing request, and the four projects permissions granted. Mirrors the
  `setUpTestData` of `ProjectViewTests` in pytest style.

### `app/mmt/projects/tests/test_detail_tabs.py` — routing and the tab bar

- **`test_detail_page_shows_four_tabs`** — `GET /projects/<pk>/` contains links
  with `data-testid` `uploaded-files-tab`, `downloads-tab`,
  `processing-requests-tab` and `settings-tab`, pointing at the four routes.
- **`test_tab_links_have_href_and_hx_get`** — each tab link carries both, with
  the same URL. The `href` is what keeps the tabs working without JavaScript, so
  an implementation that emitted only `hx-get` would pass every other test here
  and silently drop that.
- **`test_detail_page_marks_uploaded_files_tab_active`** — on `projects:detail`,
  `uploaded-files-tab` carries `aria-current="page"` and the other three do not.
- **`test_downloads_page_marks_downloads_tab_active`** — the same for
  `projects:downloads`, i.e. `active_tab` follows the route.
- **`test_processing_requests_tab_hidden_without_uploaded_files_or_requests`** —
  a project with neither has no `processing-requests-tab` link.
- **`test_processing_requests_tab_hidden_without_view_permission`** — a user
  without `view_processingrequest` has no `processing-requests-tab` link.
- **`test_settings_tab_replaces_settings_button`** — the detail page no longer
  contains the old header link (assert on the absence of a `button-link` to
  `projects:settings` outside the tab bar).

### `app/mmt/projects/tests/test_detail_tabs.py` — panel content

- **`test_uploaded_files_tab_shows_only_its_panel`** — the detail page contains
  `uploaded-files-count` and does not contain `downloadable-files-count` or a
  processing request card. This is the split the feature is for.
- **`test_downloads_tab_shows_downloads_panel`** — `projects:downloads` contains
  `downloadable-files-count` and not `uploaded-files-count`.
- **`test_processing_requests_tab_shows_requests_panel`** — `projects:processing-requests`
  contains the project's processing request card.
- **`test_settings_tab_shows_edit_form`** — `projects:settings` contains
  `edit-project-form` and `delete-project-button`.
- **`test_processing_requests_tab_renders_when_section_condition_is_false`** —
  a project with no uploaded files and no requests still returns `200` on the
  tab URL with the empty state, even though the tab is not in the bar. Pinned
  against `show_processing_request_section` being mistaken for an access rule.
- **`test_processing_requests_tab_without_view_permission_returns_403`** — the
  access rule that is one.

### `app/mmt/projects/tests/test_detail_tabs.py` — panel snippets

The header is set on the test client with `headers={'hx-request': 'true'}`.

- **`test_htmx_request_returns_panel_without_layout`** — `GET` on
  `projects:downloads` with the header returns `200` whose body contains
  `downloadable-files-count` and contains neither `<html` nor the tab bar. The
  whole snippet-delivery decision, expressed as one test.
- **`test_htmx_request_varies_on_hx_request`** — that response's `Vary` header
  contains `HX-Request`. Without it a cache can answer a full page request with
  a stored bare panel.
- **`test_full_request_returns_whole_page`** — the same URL without the header
  contains `<html` and the tab bar.
- **`test_htmx_request_for_each_tab`** — parametrized over the four tabs: each
  returns `200` and its own panel's marker with the header set. Guards against a
  partial name and an `active_tab` string drifting apart, which would otherwise
  raise `TemplateDoesNotExist` only for the one tab nobody tested.

### `app/mmt/projects/tests/test_detail_tabs.py` — ownership and downloads

- **`test_each_tab_returns_404_for_another_users_project`** — parametrized over
  the four routes.
- **`test_each_tab_redirects_anonymous_to_login`** — parametrized over the four
  routes.
- **`test_downloads_tab_missing_directory_returns_500`** — a project whose
  download directory has been removed renders the error page with `500`. Moved
  behavior: `test_project_detail_page_missing_directory` in
  [`test_views.py`](../app/mmt/projects/tests/test_views.py) currently asserts
  this for the detail page.
- **`test_detail_page_missing_download_directory_still_returns_200`** — the
  other half of that move, and the reason it is worth doing: the uploaded files
  tab no longer touches the download directory, so a broken download directory
  no longer takes down the project page.
- **`test_downloads_tab_updates_downloadable_files_count`** — opening the
  downloads tab writes `project.downloadable_files_count`.

### `app/mmt/projects/tests/test_selenium.py` — the htmx swap

Three tests, each signing in as alice from the `test_data.json` fixture and
opening the project detail page.

- **`test_clicking_a_tab_swaps_the_panel_without_a_page_load`** — set a marker on
  `window` via `execute_script`, click `downloads-tab`, then assert the
  downloads panel is present, the uploaded files panel is gone, the URL ends in
  `/downloads/`, and the marker is **still set**. The marker is what makes this a
  test of the swap: without it, a full-page navigation to the same URL would
  satisfy every other assertion.
- **`test_back_button_returns_to_the_previous_tab`** — click `downloads-tab`,
  call `driver.back()`, assert the uploaded files panel is showing and the URL is
  the detail URL again. This is `hx-push-url` working.
- **`test_back_after_a_history_cache_miss_keeps_the_layout`** — click
  `downloads-tab`, clear `sessionStorage` via `execute_script` to force htmx's
  history cache to miss, call `driver.back()`, and assert the **tab bar is still
  present**. This is the one test for the `historyRestoreAsHxRequest = false`
  decision: with htmx's default of `true`, the restore request would carry
  `HX-Request`, the server would answer with a bare panel, and htmx would restore
  that fragment as the entire body — the tab bar would be gone. The cache is
  cleared explicitly because on a cache hit htmx restores the snapshot and never
  asks the server, so the bug is invisible.

## Slices and tasks

Four slices. Slice 1 is deployable on its own and gives working tabs as ordinary
page loads; slice 2 folds settings in; slice 3 adds htmx; slice 4 is the
styling. Run tests with `uv run pytest` from `app/`. There is no `addopts`
exclusion in [`pyproject.toml`](../app/pyproject.toml), so a local run does
collect and run the browser tests and needs Firefox and geckodriver installed;
only CI excludes them, by the two `--ignore` paths.

- [ ] **1. Tab bar, routes and partials, server-rendered.** Add the two routes
  to [`urls.py`](../app/mmt/projects/urls.py); split
  [`views.py`](../app/mmt/projects/views.py) into `project_detail`,
  `project_downloads` and `project_processing_requests` with the `_render_tab`
  helper and `@vary_on_headers('HX-Request')`; restructure
  [`project_detail.html`](../app/mmt/projects/templates/projects/project_detail.html)
  into header, tab bar and four `{% partialdef %}` panels, dropping the panel
  `<h2>` headings and the "Project settings" header button. Tab links get their
  `href` and `hx-get` now; nothing acts on `hx-get` until slice 3, and the tabs
  work as full-page navigations meanwhile. The settings tab link points at the
  existing `projects:settings` page in this slice; its panel arrives in slice 2.
  Update `test_project_detail_page_missing_directory` in
  [`test_views.py`](../app/mmt/projects/tests/test_views.py) to the new
  behavior. Done when the routing, tab bar, panel content, panel snippet and
  ownership tests listed under Tests pass, minus the settings-panel ones, and
  the existing suite passes.

- [ ] **2. Settings as a tab.** Move the form, the delete form and the delete
  confirmation script out of
  [`project_settings.html`](../app/mmt/projects/templates/projects/project_settings.html)
  into the `settings-panel` partial and delete that template; point
  `project_settings` at `project_detail.html` through `_render_tab`; change its
  success redirect to `projects:settings`. Update the `test_project_settings*`
  tests in [`test_views.py`](../app/mmt/projects/tests/test_views.py) for the
  changed redirect target, and check `test_create_and_update_project` in
  [`test_selenium.py`](../app/mmt/projects/tests/test_selenium.py), which clicks
  `By.LINK_TEXT, 'Project settings'` twice and asserts the `<h1>`: the link text
  still resolves (to the tab) and the `<h1>` is still the project title on every
  tab, so it is expected to pass unchanged — run it and confirm rather than
  assume. Done when `test_settings_tab_shows_edit_form` and the settings entries
  of the parametrized tests pass, and the existing settings and deletion tests
  pass.

- [ ] **3. htmx panel swapping.** `npm install htmx.org`; import it in
  [`main.ts`](../app/assets/js/main.ts); set
  `htmx.config.historyRestoreAsHxRequest = false` and add the
  `htmx:responseError` listener per the htmx configuration section; add
  `hx-target="#tab-panel"` and `hx-push-url="true"` to the tab bar `<nav>`. Done
  when the three `test_selenium.py` swap tests pass locally and the backend suite
  still passes, since every tab remains a working full-page navigation.

- [ ] **4. Tab styling.** Add
  [`tabs.css`](../app/assets/css/components/tabs.css) and its import in
  [`main.css`](../app/assets/css/main.css). Done when the tab bar reads as a tab
  bar with the active tab distinguished, in both the full page and after a swap.
  No test; this is presentational.

## Follow-ups (out of scope, separate changes)

Noticed while writing this spec. Neither is part of this feature; both are
recorded here so they are not lost, and neither is a reason to hold it up.

- **The browser tests have no runner.** CI excludes them by explicit path
  ([`app-tests.yml`](../.github/workflows/app-tests.yml)) because the runner has
  no Firefox or geckodriver, so they are enforced only when someone runs them
  locally. That is already why `test_uploading_files` in
  [`test_selenium.py`](../app/mmt/projects/tests/test_selenium.py) has been
  sitting under `@unittest.skip`, and the three swap tests this spec adds are
  exposed to exactly the same drift: nothing will tell anyone when they break.
  Giving CI a browser, or a marker plus `-m "not selenium"` in place of the two
  `--ignore` paths, would fix it for the whole suite at once — which is why it
  does not belong to this feature.
- **`stimulus` is a dead dependency.** It is in
  [`package.json`](../app/package.json) dependencies and is imported nowhere.
  This spec adds `htmx.org` beside it, so the observation is adjacent, but
  removing `stimulus` is its own change.

## Assumptions

- Django 6.0's template partials are stable API. Verified present in the pinned
  `django~=6.0.7`: `{% partialdef %}` / `{% partial %}` in
  `django/template/defaulttags.py`, and `#name` addressing in
  `Engine.find_template`.
- The htmx facts above were read from the htmx 2.x source
  (`https://unpkg.com/htmx.org@2/dist/htmx.js`), not from the documentation
  prose, which is stale about the history cache. An implementing session that
  finds the source disagrees with this spec should update the spec first.
- The four panels stay independent. If a future panel needs data another tab's
  view already computed, that is a reason to revisit the "each view builds only
  its own panel's context" decision, in the spec first.
- No external system links to `/projects/<pk>/settings/` expecting the
  standalone page; the URL is unchanged, so this only concerns its appearance.
