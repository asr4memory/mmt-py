# syntax=docker/dockerfile:1
ARG PYTHON_VERSION="3.13.11"

FROM python:"${PYTHON_VERSION}"-slim-trixie AS build

ARG VERSION="0.1.0"
# Weights baked into the image; must match the runtime WHISPERX_MODEL.
ARG WHISPERX_MODEL="large-v3"
# Alignment models are per language and downloaded on first use otherwise.
ARG ALIGN_LANGUAGES="de en"
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
    UV_PYTHON=python3.13 \
    UV_PROJECT_ENVIRONMENT=/app

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
    --locked \
    --no-dev \
    --extra whisperx \
    --no-install-project

# Pre-download the whisper, VAD and alignment weights into the image so the
# container starts without a network dependency on Hugging Face. Loading on
# the CPU is enough to populate the cache; the GPU is only used at runtime.
ENV PATH=/app/bin:$PATH \
    HF_HOME=/model_cache
RUN WHISPERX_MODEL="${WHISPERX_MODEL}" ALIGN_LANGUAGES="${ALIGN_LANGUAGES}" \
    python -c "\
import os, whisperx; \
whisperx.load_model(os.environ['WHISPERX_MODEL'], 'cpu', compute_type='int8'); \
[whisperx.load_align_model(language_code=l, device='cpu') \
 for l in os.environ['ALIGN_LANGUAGES'].split()]"

##########################################################################

FROM python:"${PYTHON_VERSION}"-slim-trixie

ARG VERSION="0.1.0"
ARG WHISPERX_MODEL="large-v3"

LABEL org.opencontainers.image.title="MMT ASR"
LABEL org.opencontainers.image.description="MMT automatic speech recognition service"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.authors="Marc Altmann <m.altmann@fu-berlin.de>"
LABEL org.opencontainers.image.source="https://github.com/asr4memory/mmt-py"

SHELL ["sh", "-exc"]

# ctranslate2 (whisperx's transcription backend) dlopens libcudnn and libcublas
# by soname and does not depend on the nvidia-*-cu12 wheels that torch installs.
# Without this path it fails at load_model with "Unable to load libcudnn_ops.so.9".
ENV PATH=/app/bin:$PATH \
    LD_LIBRARY_PATH=/app/lib/python3.13/site-packages/nvidia/cudnn/lib:/app/lib/python3.13/site-packages/nvidia/cublas/lib \
    HF_HOME=/model_cache \
    WHISPERX_MODEL="${WHISPERX_MODEL}" \
    SPOOL_DIR=/spool

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
    ffmpeg \
    netcat-traditional

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

COPY --from=build --chown=app:app /app /app
COPY --from=build --chown=app:app /model_cache /model_cache
COPY --chown=app:app . /app/asr

RUN install -d -o app -g app /spool

USER app
WORKDIR /app/asr
VOLUME /spool

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD nc -vz -w 2 localhost 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "api:app"]

RUN <<EOT
python -V
python -Im site
EOT
