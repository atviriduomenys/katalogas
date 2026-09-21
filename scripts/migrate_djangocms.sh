#!/bin/bash

set -euo pipefail

# Temporary: #2795 deletes this once no database reports a pending or legacy state.
# Moves no data - only refuses a database the django-cms 4.1 tool has not migrated.

# --skip-checks: the URL system check queries Site before migrations run, and fails on a fresh database.
# tail: anything printed while apps load would otherwise end up in the state.
upgrade_state="$(python3 manage.py djangocms_upgrade_state --skip-checks | tail -n1)"

case "${upgrade_state}" in
    pending)
        echo "Legacy blog data has not been moved to djangocms-stories yet. That stage runs from" >&2
        echo "the django-cms 4.1 migration tool, not from this image (see" >&2
        echo "notes/migrations/djangocms/diegimas.md, step 3). Refusing." >&2
        exit 1
        ;;
    legacy_pages)
        echo "The page tree is still on the django-cms 3 schema. It has to go through the" >&2
        echo "3 -> 4 conversion first (see notes/migrations/djangocms/README.md); migrating now would" >&2
        echo "move the schema past the point where that conversion can run. Refusing." >&2
        exit 1
        ;;
    inconsistent)
        echo "Legacy blog tables remain after the stories data migration; refusing to continue." >&2
        exit 1
        ;;
    complete|fresh)
        ;;
    *)
        echo "Unknown django CMS upgrade state: ${upgrade_state}" >&2
        exit 1
        ;;
esac

python3 manage.py migrate --skip-checks -v 2
