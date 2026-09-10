#!/bin/bash

set -euo pipefail

# Lives only as long as the django-cms 5 upgrade does. Once no database reports
# a pending or legacy state, #2795 deletes this file and the entrypoints call
# migrate directly again. Both entrypoints share it meanwhile, so the state check
# cannot drift between them.

# --skip-checks, here and in every manage.py call below: the URL system check
# queries the Site table before migrations have run, so on a fresh database it
# fails with Site.DoesNotExist. A django-cms bootstrapping problem, not ours.
#
# tail: anything an app prints while loading would otherwise land in the value
# and send us to the "unknown state" branch, where the container refuses to boot.
upgrade_state="$(python3 manage.py djangocms_upgrade_state --skip-checks | tail -n1)"

case "${upgrade_state}" in
    pending)
        echo "Migrating legacy djangocms-blog data to djangocms-stories."
        DJANGOCMS_BLOG_MIGRATION=1 python3 manage.py migrate djangocms_blog --skip-checks -v 2
        DJANGOCMS_BLOG_MIGRATION=1 python3 manage.py migrate djangocms_stories --skip-checks -v 2
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
