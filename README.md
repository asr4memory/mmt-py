Django version of the Media Management Tool

The software is still experimental. You can upload video or audio files. In the future, you can create automatic transcriptions based on the uploaded files.


## Requirements

- Python 3.13
- Node.js
- Docker

- Libraries e.g. for Debian:
  - default-libmysqlclient-dev
  - pkg-config

## Development

The development environment can be started with uv:

```bash
uv run manage.py runserver
```

In another terminal, start the Vite development server:

```bash
npm run dev
```

Tests can be run with:

```bash
uv run manage.py test
```
