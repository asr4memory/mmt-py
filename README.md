Django version of the Media Management Tool

The software is still experimental. You can upload video or audio files. In the future, you can create automatic transcriptions based on the uploaded files.


## Requirements

- Python 3.12 (tested with 3.12, likely runs with older or newer versions)
- Node.js
- Docker

## Development

The development environment can be started with uv:

```bash
uv run manage.py runserver
```

In another terminal, start the Vite development server:

```bash
npm run dev
```

Tests can be run wiht:

```bash
uv run pytest
```
