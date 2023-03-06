# 2022-10-20 08:50 Test news import

mkdir var/images
poetry run python scripts/migrate_news.py var/images
poetry run python manage.py runserver


# 2022-12-21 18:39 Test news and cms pages

ls var/data

poetry run python scripts/migrate_files.py \
    --distribution-path var/data/ \
    --cms-path var/data/files/ \
    --structure-path var/data/structure/
poetry run python scripts/migrate_pages.py var/data/files
poetry run python scripts/migrate_news.py

nmcli c up ivpk
rsync -avz adp-prod:/srv/production/data/872096ac-ea21-493d-882b-c628fee25f10 var/data
ls var/data
du -sh var/data/*
#|  52K  var/data/872096ac-ea21-493d-882b-c628fee25f10
#|  44M  var/data/files
#| 235M  var/data/structure
nmcli c down ivpk

poetry run python scripts/migrate_files.py \
    --distribution-path var/data/ \
    --cms-path var/data/files/ \
    --structure-path var/data/structure/

poetry run python manage.py runserver
