#!/usr/bin/zsh

set -k

# === Configuration — edit before running ===
export LABEL='20260519'
export ENV_NAME=prod
export DB_HOST=localhost
export DB_USER=adp
export DB_NAME=adp-dev
# Passwords come from the caller; this file says prod at the top, and secrets
# do not belong in the repository even when the environment is not.
: "${USERNAME:?export USERNAME before sourcing this file}"
: "${PASSWORD:?export PASSWORD before sourcing this file}"
: "${PGPASSWORD:?export PGPASSWORD before sourcing this file}"
export USERNAME PASSWORD PGPASSWORD
export PYENV_VER=kt312b
export BACKUP_DIR=dist/backup/${LABEL}
export PROD_DUMP=dist/backup/adp-prod-2026-01-05.dump
# ===========================================
mkdir -p "${BACKUP_DIR}"


# pyenv
clean_pyenv(){
    pyenv deactivate || true
    pyenv virtualenv-delete -f "${PYENV_VER}" || true
    pyenv virtualenv 3.12 "${PYENV_VER}"
    pyenv activate "${PYENV_VER}"
    python -m pip install --upgrade pip
    pyenv shell
}

# Poetry
poetry_install_all(){
    poetry install --all-extras --all-groups
}

clean_db(){
    # db utils: cleanup
    psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
}

create_superuser(){
    # db utils: create super user
    DJANGO_SUPERUSER_PASSWORD=${PASSWORD} python manage.py createsuperuser --email superadmin@aa.lt --noinput
}

restore_db_GPX(){
    GPX=$1
    # db utils: restore TEST db with migration and super user
    clean_db
    pg_restore -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -Fc "${BACKUP_DIR}/adp-${LABEL}-${GPX}.dump"
}

dump_db_GPX(){
    GPX=$1
    pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -Fc -f "${BACKUP_DIR}/adp-${LABEL}-${GPX}.dump"
}