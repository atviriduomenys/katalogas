# Check running services
docker-compose ps

# Start docker services in background
docker-compose up -d

# Stop docker services
docker-compose down


### Troubleshooting

# Sometimes you can get permission errors on docker volumesn mounter tovar
# diretory. You can fix that with this:
sudo chown -R $UID:$GID var


# 2023-01-12 16:07 Build docker file

poetry lock
poetry export -o requirements.txt
grep -o -E '^[^ ]+' requirements.txt
poetry build
docker build .
#| error checking context: can't stat 'postgres'
sudo rm -r postgres

docker build .
#| Successfully built 0d61c8a93095

docker images
#| REPOSITORY         TAG             IMAGE ID       CREATED        SIZE
#| <none>             <none>          0d61c8a93095   8 weeks ago    260MB

docker build -t vitrina:$(git rev-parse --short HEAD) .
#| Successfully built 0d61c8a93095
#| Successfully tagged vitrina:8d542b6
docker images
#| REPOSITORY         TAG             IMAGE ID       CREATED        SIZE
#| vitrina            8d542b6         0d61c8a93095   8 weeks ago    260MB


# 2023-01-25 13:47 Continue with dockerization

docker images
#| REPOSITORY         TAG             IMAGE ID       CREATED        SIZE
#| vitrina            8d542b6         0d61c8a93095   2 months ago   260MB

git status
git co docker
git fetch
git log ..origin/devel --oneline
git log ..origin/devel --oneline | wc -l
#| 156

git rebase origin/devel
#| CONFLICT (content): Merge conflict in poetry.lock
#| Auto-merging pyproject.toml

git co --ours -- poetry.lock
git add poetry.lock
git rebase --continue
#| [detached HEAD aae1412] Dockerfile (in progress)
#|  4 files changed, 47 insertions(+), 13 deletions(-)
#|  create mode 100644 .dockerignore
#|  create mode 100644 Dockerfile
#| Successfully rebased and updated refs/heads/docker.
git status
#| On branch docker
git log ..origin/devel --oneline
git push --force-with-lease
#| To github.com:atviriduomenys/katalogas.git
#|  + 3d10153...e7d20df docker -> docker (forced update)


# 2023-01-25 16:15 Recreate image after rebase

git status
poetry lock
git status
git diff
git diff | wc -l
#| 3138
poetry export -o requirements.txt
grep -o -E '^[^ ]+' requirements.txt
grep -o -E '^[^ ]+' requirements.txt | wc -l
#| 71
poetry build
cp -a dist requirements.txt docker/
docker build -t vitrina:$(git rev-parse --short HEAD) docker
#| Successfully built b76276ced580
#| Successfully tagged vitrina:e7d20df
docker images
#| REPOSITORY         TAG             IMAGE ID       CREATED          SIZE
#| vitrina            e7d20df         b76276ced580   25 seconds ago   294MB


# 2023-01-29 09:58 Rebuild docker image

git status
poetry lock
git status
poetry export -o docker/requirements.txt
poetry build
rm -rf docker/dist
mv dist docker/
docker build -t vitrina:$(git rev-parse --short HEAD) -t vitrina:latest docker
#| Successfully built b76276ced580
#| Successfully tagged vitrina:3b877a0
#| Successfully tagged vitrina:latest
docker images
#| REPOSITORY         TAG             IMAGE ID       CREATED        SIZE
#| vitrina            3b877a0         b76276ced580   3 days ago     294MB
#| vitrina            e7d20df         b76276ced580   3 days ago     294MB
#| vitrina            latest          b76276ced580   3 days ago     294MB
#| vitrina            8d542b6         0d61c8a93095   2 months ago   260MB

poetry run python manage.py runserver


# 2023-01-29 11:05 Rebuild docker image

git status
poetry update
git status
git diff
poetry export -o docker/requirements.txt
# https://github.com/python-poetry/poetry/issues/3586
# poetry build -o docker/dist
poetry build
rm -rf docker/dist
mv dist docker/
docker build -t vitrina:$(git rev-parse --short HEAD) -t vitrina:latest docker


# 2023-01-29 19:29 Rebuild docker image with static files

git status
poetry update
poetry export -o docker/requirements.txt
# https://github.com/python-poetry/poetry/issues/3586
# poetry build -o docker/dist
poetry build
(cd webpack && npm install && npm run build)
poetry run python manage.py collectstatic --no-input --clear
rsync -a --delete dist var/static docker/
docker build -t vitrina:$(git rev-parse --short HEAD) -t vitrina:latest docker


# 2023-02-02 18:12 Rebuild docker image with scripts

git status
poetry update
git add poetry.lock
git commit -m "Upgrade dependencies (poetry update)"
poetry export -o docker/requirements.txt
# https://github.com/python-poetry/poetry/issues/3586
# poetry build -o docker/dist
poetry build
(cd webpack && npm install)
(cd webpack && npm run build)
poetry run python manage.py collectstatic --no-input --clear
rsync -a --delete scripts dist var/static docker/
docker build -t vitrina:$(git rev-parse --short HEAD) -t vitrina:latest docker


# 2023-05-18 08:52 Issue with mysql

docker-compose ps
docker-compose up -d
docker-compose ps
docker-compose stop mysql
docker-compose ps


# 2023-08-16 16:16 Run docker locally

docker network ls
#| 015d09f350c7   katalogas_default   bridge    local

docker run -it --rm vitrina:latest gunicorn --help
#| --error-logfile FILE, --log-file FILE  The Error log file to write to. [-]

docker run -it --rm -p 8000:8000 \
    --name katalogas \
    --network katalogas_default \
    -e DATABASE_URL=postgres://adp:secret@postgres:5432/adp-dev \
    -e SEARCH_URL=elasticsearch7://elasticsearch:9200/haystack \
    -e SECRET_KEY=insecure-secret-key \
    -e ALLOWED_HOSTS=localhost \
    -e VIISP_PROXY_AUTH=https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy \
    -e VIISP_AUTHORIZE_URL=https://test.epaslaugos.lt/portal/external/services/authentication/v2 \
    vitrina:latest \
    gunicorn vitrina.wsgi -b 0.0.0.0:8000

docker exec -it katalogas bash
python -c 'import vitrina.settings; print(vitrina.settings)'
#| <module 'vitrina.settings' from '/opt/venv/lib/python3.10/site-packages/vitrina/settings.py'>
cat /opt/venv/lib/python3.10/site-packages/vitrina/settings.py | grep LOCALE
#| LOCALE_PATHS = [BASE_DIR / 'vitrina/locale/']
exit


docker run -it --rm vitrina:latest bash
ls -l /app/static
exit
