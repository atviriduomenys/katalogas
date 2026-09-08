FROM python:3.11-slim AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS="yes"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends  \
    libcairo2-dev  \
    libcairo2  \
    pkg-config \
    python3-dev \
    gcc \
    g++ \
    cmake \
    make \
    libboost-all-dev \
    libsnappy-dev \
    libgflags-dev \
    libgoogle-glog-dev \
    libglib2.0-dev \
    libglib2.0-0 \
    libgirepository-1.0-1 \
    npm \
    gettext \
    redis-server \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libffi-dev \
    libmagic1 \
    libxml2 \
    libxslt1.1 \
    fonts-liberation \
    fonts-liberation2 \
    fonts-dejavu-core \
    fonts-dejavu-extra && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip wheel --no-cache-dir
RUN pip install gunicorn==23.0.0 poetry==2.4.1 --no-cache-dir
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --only main --no-root

# Disable spinta's logging setup: setup_logging() reconfigures the ROOT logger to
# DEBUG and attaches a rotating file handler (~/.spinta_logs), hijacking the app's logging.
RUN CONFIG_PY="$(python -c 'import spinta.types.config as m; print(m.__file__)')" && \
    grep -q '^[[:space:]]*setup_logging(config)' "$CONFIG_PY" && \
    sed -i 's/^\([[:space:]]*\)setup_logging(config)/\1# setup_logging(config)  # disabled in image/' "$CONFIG_PY" && \
    echo "Patched spinta logging in: $CONFIG_PY" && \
    grep -n 'setup_logging(config)' "$CONFIG_PY"

COPY webpack/package.json webpack/package-lock.json ./webpack/
RUN cd webpack && npm ci

COPY . .
RUN poetry install --no-interaction --only main && \
    mkdir -p /out/root-dist && \
    mv /usr/local/lib/python3.11/site-packages/vitrina.pth \
       /usr/local/lib/python3.11/site-packages/vitrina-*.dist-info /out/root-dist/

ENV VITRINA_LOCALE_PATH="/app/vitrina/locale"
ARG DATABASE_URL="postgres://build:build@127.0.0.1:5432/build"
ARG VIISP_AUTHORIZE_URL="https://build.invalid"
ARG VIISP_PROXY_AUTH="https://build.invalid"
ARG VIISP_PID="build"
ARG OAUTH_SERVER_HOST="https://build.invalid"
ARG OAUTH_CLIENT_SECRET="build"
ARG OAUTH_CLIENT_NAME="build"
RUN redis-server --daemonize yes --save '' && \
    until redis-cli ping > /dev/null 2>&1; do sleep 0.2; done && \
    python manage.py collectstatic --noinput && \
    (cd webpack && npm run build) && \
    python manage.py compilemessages && \
    python manage.py collectstatic --noinput

RUN set -eu; \
    for entry in $(cd webpack && node -e 'console.log(Object.keys(require("./webpack.config.js").entry).join(" "))'); do \
        [ -f "vitrina/static/js/$entry.js" ] || { echo "missing webpack entry: vitrina/static/js/$entry.js" >&2; exit 1; }; \
    done; \
    for css in bundle.css wizard.css; do \
        [ -f "vitrina/static/css/$css" ] || { echo "missing stylesheet: vitrina/static/css/$css" >&2; exit 1; }; \
    done; \
    cms_version="$(python -c 'import cms; print(cms.__version__)')"; \
    for asset in "var/static/cms/css/$cms_version/cms.base.css" \
                 "var/static/cms/js/dist/$cms_version/bundle.toolbar.min.js" \
                 "var/static/css/csp-utilities.css" \
                 "vitrina/locale/en/LC_MESSAGES/django.mo"; do \
        [ -f "$asset" ] || { echo "missing build output: $asset" >&2; exit 1; }; \
    done

RUN mkdir -p /out && cp -a /app /out/app && rm -rf /out/app/webpack/node_modules


FROM python:3.11-slim AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS="yes"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VITRINA_LOCALE_PATH="/app/vitrina/locale"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libfontconfig1 \
    libmagic1 \
    fonts-liberation \
    fonts-liberation2 \
    fonts-dejavu-core \
    fonts-dejavu-extra && \
    rm -rf /var/lib/apt/lists/*

COPY --link --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --link --from=builder /out/root-dist/ /usr/local/lib/python3.11/site-packages/
COPY --link --from=builder /usr/local/bin /usr/local/bin
COPY --link --from=builder /out/app /app

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "vitrina.wsgi", "--log-file=-"]
