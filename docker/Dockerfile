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
    libglib2.0-dev \
    libglib2.0-0 \
    libgirepository-1.0-1 \
    npm \
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
RUN pip install gunicorn==23.0.0 poetry --no-cache-dir
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --only main

WORKDIR /app/webpack
RUN npm install

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
ENV VITRINA_LOCALE_PATH="/app/locale"

EXPOSE 8000
