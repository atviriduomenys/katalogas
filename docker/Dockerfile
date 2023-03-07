FROM python:3.10-slim as builder

WORKDIR /app

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS="yes"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

COPY dist requirements.txt /app/

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip wheel --no-cache-dir \
 && /opt/venv/bin/pip install gunicorn==20.1.0 --no-cache-dir \
 && /opt/venv/bin/pip install -r requirements.txt --no-cache-dir \
 && /opt/venv/bin/pip install vitrina-*.tar.gz --no-cache-dir

FROM python:3.10-slim

COPY --from=builder /opt/venv /opt/venv
COPY scripts /app/scripts
COPY static /app/static

EXPOSE 8000
WORKDIR /app

ENV DJANGO_SETTINGS_MODULE="vitrina.settings"
ENV STATIC_ROOT="/app/static"
ENV DEBUG="false"
ENV PATH="/opt/venv/bin:$PATH"

CMD ["gunicorn", "vitrina.wsgi", "-b", "0.0.0.0:8000"]
