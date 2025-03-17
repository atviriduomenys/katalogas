FROM python:3.11-slim AS builder

COPY . /app/
WORKDIR /app

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS="yes"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
    npm

RUN pip install --upgrade pip wheel --no-cache-dir
RUN pip install gunicorn==20.1.0 poetry --no-cache-dir
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction

WORKDIR /app/webpack
RUN npm install

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
ENV VITRINA_LOCALE_PATH="/app/locale"

RUN apt-get install -y --no-install-recommends npm
WORKDIR /app/webpack
RUN npm install
RUN npm run build || true

WORKDIR /app
