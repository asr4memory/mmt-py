# syntax=docker/dockerfile:1
ARG PYTHON_VERSION="3.13.11"

FROM python:"${PYTHON_VERSION}"-slim-trixie AS build

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

##########################################################################

FROM python:"${PYTHON_VERSION}"-slim-trixie

SHELL ["sh", "-exc"]

# ctranslate2 (whisperx's transcription backend) dlopens libcudnn and libcublas
# by soname and does not depend on the nvidia-*-cu12 wheels that torch installs.
# Without this path it fails at load_model with "Unable to load libcudnn_ops.so.9".
#
# Every cache is pointed at the /model_cache volume, not only the Hugging Face
# one. The alignment models of the five torchaudio languages (among them de and
# en) are not Hugging Face repositories: they are downloaded by torch.hub into
# TORCH_HOME, which otherwise resolves to $HOME/.cache/torch, so they would be
# downloaded again for every container. XDG_CACHE_HOME covers the libraries that
# derive their cache from it, pyannote among them.
ENV PATH=/app/bin:$PATH \
    LD_LIBRARY_PATH=/app/lib/python3.13/site-packages/nvidia/cudnn/lib:/app/lib/python3.13/site-packages/nvidia/cublas/lib \
    HF_HOME=/model_cache \
    TORCH_HOME=/model_cache/torch \
    XDG_CACHE_HOME=/model_cache \
    PYANNOTE_CACHE=/model_cache/pyannote \
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
COPY --chown=app:app . /app/asr

# No model weights are in the image: the gated diarization models must not be
# redistributed, and a baked model is only used when it matches the runtime
# WHISPERX_MODEL. HF_HOME is a volume, populated by prefetch.py or by the
# first job that needs a model.
RUN install -d -o app -g app /spool /model_cache

USER app
WORKDIR /app/asr
VOLUME /spool /model_cache

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD nc -vz -w 2 localhost 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "api:app"]

RUN <<EOT
python -V
python -Im site
EOT

# Last, because the version differs for every release: an instruction that reads
# VERSION invalidates the build cache of everything below it, and the layers
# below would be the apt install and the copied environment with torch and the
# CUDA wheels, roughly 4 GB that every host would then pull again. Here only the
# image metadata changes between two releases of otherwise identical content.
ARG VERSION="0.0.0"

LABEL org.opencontainers.image.title="MMT ASR"
LABEL org.opencontainers.image.description="MMT automatic speech recognition service"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.authors="Marc Altmann <m.altmann@fu-berlin.de>"
LABEL org.opencontainers.image.source="https://github.com/asr4memory/mmt-py"
