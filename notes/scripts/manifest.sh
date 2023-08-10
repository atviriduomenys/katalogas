cd ~/dev/data/katalogas

git -C ../manifest status
git -C ../manifest co master
git -C ../manifest pull

docker-compose down
docker-compose up -d
docker-compose ps
docker-compose stop mysql

poetry run python scripts/manifest_export.py --help
poetry run python scripts/manifest_export.py --manifest-path ../manifest
#| django.db.utils.ProgrammingError: column organization.name does not exist
#| LINE 1: ...anization"."image_id", "organization"."provider", "organizat...

