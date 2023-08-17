cd ~/dev/data/katalogas

git -C ../manifest status
git -C ../manifest co master
git -C ../manifest pull

docker-compose down
docker-compose up -d
docker-compose ps
docker-compose stop mysql

poetry run python scripts/manifest_export.py --help
poetry run python scripts/manifest_export.py --manifest-path ../manifest/

poetry run python scripts/manifest_import.py --manifest-path ../manifest/

