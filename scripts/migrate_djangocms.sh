#!/bin/bash

set -euo pipefail

# tail: anything an app prints while loading would otherwise land in the value
# and send us to the "unknown state" branch, where the container refuses to boot.
upgrade_state="$(python3 manage.py djangocms_upgrade_state --skip-checks | tail -n1)"

case "${upgrade_state}" in
    pending)
        echo "Migrating legacy djangocms-blog data to djangocms-stories."
        DJANGOCMS_BLOG_MIGRATION=1 python3 manage.py migrate djangocms_blog --skip-checks -v 2
        DJANGOCMS_BLOG_MIGRATION=1 python3 manage.py migrate djangocms_stories --skip-checks -v 2
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
