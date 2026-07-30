# API architecture

Status: **draft**, written alongside
[`specs/2026-07-30-read-only-api.md`](../specs/2026-07-30-read-only-api.md).

This note records where the HTTP API sits in the application and why it is built
the way it is. The spec records what is built; this note records the structural
decisions that outlive any single feature.

## Position in the application

The application serves two kinds of client from one Django project:

1. **The HTML interface.** Django views in `mmt/projects`, `mmt/uploaded_files`,
   `mmt/transcripts` and `mmt/my_account`, authenticated with a session cookie
   through django-allauth, rendering server-side templates with Vue components
   mounted into them.
2. **The HTTP API.** Django Ninja operations in `mmt/api`, authenticated with a
   personal API token, returning JSON.

Both read the same models through the same ownership rules. The API is not a
separate service, not a separate deployment and not a separate database; it is a
second presentation layer over the same domain.

```
             session cookie                     Bearer token
                   |                                 |
            +------v------+                   +------v------+
            | HTML views  |                   | mmt.api     |
            | per app     |                   | routers     |
            +------+------+                   +------+------+
                   |                                 |
                   +--------------+------------------+
                                  |
                          +-------v--------+
                          | Django models  |
                          | and services   |
                          +-------+--------+
                                  |
                    +-------------+-------------+
                    |                           |
              +-----v-----+              +------v------+
              |  MariaDB  |              | user_files  |
              +-----------+              | on disk     |
                                         +-------------+
```

The existing JSON endpoints in the HTML apps (`transcripts.detail_json`,
`uploaded_files.status`, `uploaded_files.waveform_json`) are **not** part of the
API. They are the browser application's own endpoints: session-authenticated,
shaped for one component, and free to change whenever that component changes.
They stay where they are. The distinction that matters is the client and the
compatibility promise, not the content type: `/api/v1/` has external clients and
a version in its path, the in-app endpoints have neither.

## Why Django Ninja

- Response schemas are declared as Pydantic models. Pydantic is already a
  dependency and already used for the mmt-transcript schema in
  `mmt/transcripts/mmt_schema.py`, so the project does not gain a second
  validation library.
- The OpenAPI document is generated from those declarations rather than
  maintained by hand, so a route and its documentation cannot drift apart.
- Operations are plain functions with type-annotated parameters, close to the
  Django function-based views the project already uses everywhere. Django REST
  Framework's class hierarchy of viewsets, serializers and permission classes
  would be a second, unrelated style of writing a view.
- Authentication is one class with one method, which is what a token scheme
  needs.

## Layering inside `mmt.api`

```
routers/      one module per resource; routes, ownership queryset, permission check
schemas.py    response shapes only
auth.py       token authentication
permissions.py  the model-permission check used by the routers
api.py        the NinjaAPI instance and router registration
```

The API app holds no models and no business logic. Anything an operation needs
beyond reading a queryset belongs in the app that owns the model, where the HTML
views can use it too. When an API operation grows logic that its HTML
counterpart also needs, the logic moves into the owning app rather than being
duplicated or imported out of `mmt.api`.

Response schemas live only in `mmt/api/schemas.py`. They are a published
contract with external clients, so a field is added or removed deliberately;
they are not generated from the models with `ModelSchema`, because that would
turn any model field addition into an unreviewed API change.

## Authorisation is two checks, always in the same order

Ownership first, permission second:

1. **Ownership** is enforced in the queryset, never as a check after fetching.
   `Transcript.objects.filter(uploaded_file__project__user=user)` is the same
   path the HTML views take. A miss is answered `404`, so identifiers of other
   users' objects are indistinguishable from identifiers that do not exist.
2. **Model permission** uses the existing Django permissions
   (`transcripts.view_transcript` and so on) and the existing groups. A user's
   reach through the API is by construction the same as through the interface,
   and a permission change affects both at once. A miss is answered `403`.

There is no separate permission system for the API and no per-token scope. If
scopes are ever added, they narrow what a token may do within its owner's
permissions; they never widen it.

## Tokens

Tokens are stored as a SHA-256 digest in a unique indexed column. The secret is
32 bytes from `secrets.token_urlsafe`, so it is not subject to dictionary
attack and does not need a slow password hasher; authentication is one indexed
equality lookup. The plaintext exists in exactly one response, at creation.

A token identifies a user, not an application. It carries the full read access
of its owner, it can be revoked individually, and it can expire. Revocation is a
timestamp rather than a row deletion, so the record of a token that once existed
survives its revocation.

`last_used_at` is written at most once per hour per token. A read-only API that
wrote a row on every request would put a write load on the database proportional
to polling frequency.

## Synchronous now

Every operation is a synchronous `def`. Django Ninja supports `async def`
operations, and some models already carry async helpers (`aproject_directory`,
`afile_path`), but a router mixing both invites a synchronous ORM call inside an
async operation, which blocks the event loop without any visible error. The
project runs under uvicorn with an ASGI application, so switching individual
routers later is possible; it is a deliberate change with its own tests, not a
default.

## Versioning and compatibility

The version is in the path (`/api/v1/`) from the first release. Within a
version:

- Adding a field to a response, adding an optional query parameter, or adding a
  route is compatible and needs no version change.
- Removing or renaming a field, changing a field's type, changing a status code,
  or changing the meaning of a value is incompatible and needs `/api/v2/`, run
  in parallel with `/api/v1/` until clients have moved.

The OpenAPI document at `/api/v1/openapi.json` is the machine-readable form of
this contract, and it is unauthenticated: it describes routes and shapes, not
data.

## Errors

One shape everywhere: `{"detail": "<message>"}`. The messages are English and
are not translated. The API's clients are programs; a locale-dependent error
string would be a value that clients cannot match on. The user-visible strings
of the token management pages in the account interface **are** translated, since
those are read by people.

## Testing

API tests go over HTTP with the Django test client rather than calling operation
functions directly. Authentication, the permission check, pagination and the
error shape only exist on the full request path, and those are the parts most
likely to break.
