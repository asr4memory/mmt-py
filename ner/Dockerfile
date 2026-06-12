# syntax=docker/dockerfile:1
ARG PYTHON_VERSION="3.14.6"

FROM python:"${PYTHON_VERSION}"-slim-trixie AS build

ARG VERSION="0.1.0"
ENV DEBIAN_FRONTEND=noninteractive

SHELL ["sh", "-exc"]

RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential
EOT

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.14 \
    UV_PROJECT_ENVIRONMENT=/app

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
    --locked \
    --no-dev \
    --no-install-project

# Pre-download model weights into the image so the container starts
# without a network dependency on Hugging Face.
ENV PATH=/app/bin:$PATH \
    HF_HOME=/model_cache
RUN --mount=type=secret,id=HF_TOKEN \
    HF_TOKEN=$(cat /run/secrets/HF_TOKEN) \
    python -c "from gliner2 import GLiNER2; GLiNER2.from_pretrained('fastino/gliner2-multi-v1')"

##########################################################################

FROM python:"${PYTHON_VERSION}"-slim-trixie

ARG VERSION="0.1.0"

LABEL org.opencontainers.image.title="MMT NER"
LABEL org.opencontainers.image.description="MMT Named entity recognition service"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.authors="Marc Altmann <m.altmann@fu-berlin.de>"
LABEL org.opencontainers.image.source="https://github.com/asr4memory/mmt-py"

SHELL ["sh", "-exc"]

ENV PATH=/app/bin:$PATH \
    HF_HOME=/model_cache

RUN <<EOT
groupadd -r app
useradd -r -d /app -g app -N app
EOT

STOPSIGNAL SIGINT

RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    netcat-traditional

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

COPY --from=build --chown=app:app /app /app
COPY --from=build --chown=app:app /model_cache /model_cache
COPY --chown=app:app . /app/ner

USER app
WORKDIR /app/ner

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD nc -vz -w 2 localhost 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "api:app"]

RUN <<EOT
python -V
python -Im site
EOT
