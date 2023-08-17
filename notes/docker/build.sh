# Build translation (.mo) files
poetry run python manage.py compilemessages

# Build static files
(cd webpack && npm install)
(cd webpack && npm run build)
poetry run python manage.py collectstatic --no-input --clear

# Build python package
poetry export -o docker/requirements.txt
# https://github.com/python-poetry/poetry/issues/3586
# poetry build -o docker/dist
poetry build

# Add all assets to docker context
rsync -a --delete scripts dist var/static vitrina/locale docker/

# Build docker image
docker build -t vitrina:$(git rev-parse --short HEAD) -t vitrina:latest docker

# Check image content (if needed)
docker run -ti --rm vitrina:latest bash
exit
