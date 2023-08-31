# Run docker compose with all the services
docker-compose ps
docker-compose up -d
docker-compose stop mysql

# Attache image to docker compose
docker network ls
#| 015d09f350c7   katalogas_default   bridge    local

# Run vitrina service
docker run -it --rm -p 8000:8000 \
    --name katalogas \
    --network katalogas_default \
    -e DATABASE_URL=postgres://adp:secret@postgres:5432/adp-dev \
    -e SEARCH_URL=elasticsearch7://elasticsearch:9200/haystack \
    -e SECRET_KEY=insecure-secret-key \
    -e ALLOWED_HOSTS=localhost \
    -e VIISP_PROXY_AUTH=https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy \
    -e VIISP_AUTHORIZE_URL=https://test.epaslaugos.lt/portal/external/services/authentication/v2 \
    -e DEBUG=true \
    vitrina:latest \
    gunicorn vitrina.wsgi -b 0.0.0.0:8000

# Inspect container if needed
docker exec -it katalogas bash
python -c 'import vitrina.settings; print(vitrina.settings)'
#| <module 'vitrina.settings' from '/opt/venv/lib/python3.10/site-packages/vitrina/settings.py'>
cat /opt/venv/lib/python3.10/site-packages/vitrina/settings.py
exit
