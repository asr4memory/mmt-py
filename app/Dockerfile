ARG PYTHON_VERSION="3.14.0"

# syntax=docker/dockerfile:1
FROM python:"${PYTHON_VERSION}"-slim-trixie AS build

ARG NODE_VERSION="24"
ARG VERSION="1.7.14"
ENV DEBIAN_FRONTEND=noninteractive
ENV APPROOT="/app"

LABEL org.opencontainers.image.authors="m.altmann@fu-berlin.de"
LABEL base.name="mmt"
LABEL base.version="${VERSION}"

# The following does not work in Podman unless you build in Docker
# compatibility mode: <https://github.com/containers/podman/issues/8477>
# You can manually prepend every RUN script with `set -ex` too.
SHELL ["sh", "-exc"]

### Start build prep.
### This should be a separate build container for better reuse.

RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    curl \
    libmariadb-dev \
    pkg-config
# Install Nodejs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
\. "$HOME/.nvm/nvm.sh"
nvm install ${NODE_VERSION}
EOT

# Security-conscious organizations should package/review uv themselves.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# - Silence uv complaining about not being able to use hard links,
# - tell uv to byte-compile packages for faster application startups,
# - prevent uv from accidentally downloading isolated Python builds,
# - pick a Python (use `/usr/bin/python3.13` on uv 0.5.0 and later),
# - and finally declare `/app` as the target for `uv sync`.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.14 \
    UV_PROJECT_ENVIRONMENT=/app

### End build prep -- this is where your app Dockerfile should start.

# Synchronize DEPENDENCIES without the application itself.
# This layer is cached until uv.lock or pyproject.toml change, which are
# only temporarily mounted into the build container since we don't need
# them in the production one.
# You can create `/app` using `uv venv` in a separate `RUN`
# step to have it cached, but with uv it's so fast, it's not worth
# it, so we let `uv sync` create it for us automagically.
RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
    --locked \
    --no-dev \
    --no-install-project

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=package-lock.json,target=package-lock.json,rw \
    --mount=type=bind,source=package.json,target=package.json,rw \
    --mount=type=bind,source=vite.config.js,target=vite.config.js \
    --mount=type=bind,source=assets,target=assets \
    npm install && npm run build


##########################################################################

FROM python:"${PYTHON_VERSION}"-slim-trixie

ARG VERSION="1.7.14"

LABEL org.opencontainers.image.title="MMT"
LABEL org.opencontainers.image.description="Media Management Tool Docker image"
LABEL org.opencontainers.image.ref.name="mmt:latest"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.authors="Marc Altmann <m.altmann@fu-berlin.de>"
LABEL org.opencontainers.image.source="https://github.com/asr4memory/mmt-py"

SHELL ["sh", "-exc"]

# Optional: add the application virtualenv to search path.
ENV APPROOT="/app"
ENV PATH=/app/bin:$PATH

# Don't run your app as root.
RUN <<EOT
groupadd -r app
useradd -r -d /app -g app -N app
EOT

# See <https://hynek.me/articles/docker-signals/>.
STOPSIGNAL SIGINT

# Note how the runtime dependencies differ from build-time ones.
# Notably, there is no uv either!
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    default-mysql-client-core \
    gettext \
    libmariadb3 \
    libxml2 \
    nano \
    netcat-traditional

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

# COPY entrypoint.sh /

# Copy the pre-built `/app` directory to the runtime container
# and change the ownership to user app and group app in one step.
COPY --from=build --chown=app:app /app /app

# If your application is NOT a proper Python package that got
# pip-installed above, you need to copy your application into
# the container HERE:
COPY --chown=app:app . /app/django-app

# Copy pre-built vite assets into app directory.
COPY --from=build --chown=app:app /vite_assets_dist /app/django-app/vite_assets_dist

# Create user_files directory
# TODO: Make this configurable?
RUN mkdir /app/django-app/user_files && \
    chown app:app /app/django-app/user_files

COPY ["./entrypoint.sh", "/"]
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD nc -vz -w 2 localhost 8000

CMD hypercorn mmt.asgi:application --bind '0.0.0.0:8000'

USER app
WORKDIR ${APPROOT}

# Strictly optional, but I like it for introspection of what I've built
# and run a smoke test that the application can, in fact, be imported.
RUN <<EOT
python -V
python -Im site
# python -Ic 'import the_app' # -> manage.py check
EOT
