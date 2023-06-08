# 2022-11-26 11:27 Test Partner API

pass insert tmp/staging.data.gov.lt/api/kepykla
pass tmp/staging.data.gov.lt/api/kepykla
apikey=$(pass tmp/staging.data.gov.lt/api/kepykla)
server=https://staging.data.gov.lt/partner/api/1
auth="Authorization: ApiKey $apikey"

pass insert tmp/localhost/vitrina/api/ivpk
pass tmp/localhost/vitrina/api/ivpk
apikey=$(pass tmp/localhost/vitrina/api/ivpk)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
http $server/categories $auth
http $server/licences $auth


# 2022-12-01 11:55 Test partner api


apikey=$(pass tmp/staging.data.gov.lt/api/kepykla)
server=https://staging.data.gov.lt/partner/api/1
auth="Authorization: ApiKey $apikey"


apikey=$(pass tmp/localhost/vitrina/api/ivpk)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"


http $server/catalogs $auth
http $server/categories $auth
http $server/licences $auth
http $server/datasets $auth


# 2022-12-05 18:25 Test Partner API

apikey=$(pass tmp/staging.data.gov.lt/api/kepykla)
server=https://staging.data.gov.lt/partner/api/1
auth="Authorization: ApiKey $apikey"

apikey=$(pass tmp/localhost/vitrina/api/ivpk)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
http $server/categories $auth
http $server/licences $auth
http $server/datasets/ $auth
http $server/datasets/ $auth | jq -r ".[] | .title"
http $server/datasets/ $auth | jq -r ".[] | .title" | wc -l
http $server/datasets/ $auth | jq ".[] | {id: .id, title: .title}"

http $server/datasets/1223/ $auth
http $server/datasets/id/abc/ $auth

http $server/datasets/1223/distributions/ $auth
http $server/datasets/id/abc/distributions/ $auth

http $server/datasets/1223/distributions/8624/ $auth
http $server/datasets/id/abc/distributions/8624/ $auth

http $server/datasets/1223/structure/ $auth
http $server/datasets/id/abc/structure/ $auth

http POST $server/datasets/ $auth <<EOF
{

    "internalId": "INTERNAL",
    "published": true,
    "title": "Dataset from API",
    "description": "Good description",
    "language": ["lt"],
    "keyword": ["keyword"]
}
EOF


http --multipart POST $server/datasets/2062/distributions/ $auth \
    title="Data CSV" \
    url=https://example.com/data.csv

http --multipart POST $server/datasets/2062/distributions/ $auth \
    title="More Data CSV" \
    file@../manifest/manifest.csv


# 2022-12-07 17:33 Test Partner API

apikey=$(pass tmp/localhost/vitrina/api/ivpk)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
http $server/categories $auth
http $server/licences $auth
http $server/datasets $auth
http $server/datasets $auth | jq -r ".[] | .title"
http $server/datasets $auth | jq -r ".[] | .title" | wc -l
http $server/datasets $auth | jq ".[] | {id: .id, title: .title}"

http $server/datasets/1223 $auth
http $server/datasets/id/abc $auth

http $server/datasets/1223/distributions $auth
http $server/datasets/id/abc/distributions $auth

http $server/datasets/1223/distributions/8624 $auth
http $server/datasets/id/abc/distributions/8624 $auth

http $server/datasets/1223/structure $auth
http $server/datasets/id/abc/structure $auth

http POST $server/datasets $auth <<EOF
{

    "internalId": "INTERNAL2",
    "published": true,
    "title": "Dataset from API 2",
    "description": "Good description",
    "language": ["lt"],
    "keyword": ["keyword"]
}
EOF
#| "id": "2064",


http --multipart POST $server/datasets/2064/distributions $auth \
    title="Data CSV" \
    url=https://example.com/data.csv
#| "id": 12782,

http --multipart POST $server/datasets/2064/distributions $auth \
    title="More Data CSV" \
    file@../manifest/manifest.csv
#| "id": 12783,
#| "id": 12784,

# https://atviriduomenys.readthedocs.io/katalogas.html#metaduomenu-atnaujinimas
http PATCH $server/datasets/2064/distributions/12782 $auth <<EOF
{
    "url": "https://example.com/data2.csv"
}
EOF

apikey=$(pass tmp/staging.data.gov.lt/api/kepykla)
server=https://staging.data.gov.lt/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/datasets $auth
#| "id": 1857,
http $server/datasets/1867/distributions $auth
#| "id": 3079,
http PATCH $server/datasets/1867/distributions/3079 $auth <<EOF
{
    "url": "https://example.com/data.csv"
}
EOF


# 2022-12-16 14:27 Check dist update api

apikey=$(pass tmp/staging.data.gov.lt/api/kepykla)
server=https://staging.data.gov.lt/partner/api/1
auth="Authorization: ApiKey $apikey"
http $server/datasets $auth | jq -c ".[] | [.id, .title]"
#| [1857,"Patiekalų receptai"]
dataset=1857

http --multipart POST $server/datasets/$dataset/distributions $auth \
    title="Data" \
    url=https://example.com/data.csv
#| {
#|     "id": 4462,
#|     "title": "Data",
#|     "type": "URL",
#|     "version": 1
#| }
dist=4462

http --multipart PUT $server/datasets/$dataset/distributions $auth \
    title=Data \
    url=https://example.com/data.csv
#| {
#|     "id": 4463,
#|     "title": "Data",
#|     "type": "URL",
#|     "version": 1
#| }
dist=4463

http $server/datasets/$dataset/distributions $auth
http $server/datasets/$dataset/distributions/$dist $auth
#| HTTP/1.1 500 
#| 
#| {
#|     "details": {
#|         "msg": "value"
#|     },
#|     "time": "2022-12-16T14:45:16.458121",
#|     "type": "Error"
#| }
http $server/datasets/$dataset/distributions $auth | jq -c ".[] | [.id, .type, .url]"
#| [4462,"URL","Data"]

http PATCH $server/datasets/$dataset/distributions/$dist $auth <<EOF
{"url": "https://example.com/data.json"}
EOF


# 2023-01-03 18:56 Test Partner API

apikey=$(pass tmp/localhost/vitrina/api/ivpk | head -n 1)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
#| {
#|     "detail": "Baigėsi Jūsų API rakto galiojimas. Raktą galite atsinaujinti savo organizacijos tvarkytojų sąraše: http://example.com/orgs/12/members/"
#| }

pass edit tmp/localhost/vitrina/api/ivpk
pass tmp/localhost/vitrina/api/ivpk
pass tmp/localhost/vitrina/api/ivpk | head -n 1

apikey=$(pass tmp/localhost/vitrina/api/ivpk | head -n 1)
server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
#| HTTP/1.1 200 OK


# 2023-01-10 11:24 Check expired API key handling

docker-compose ps
docker-compose up -d

poetry run python manage.py runserver

poetry run python manage.py shell <<EOF
from vitrina.orgs.models import Organization, Representative
from django.contrib.contenttypes.models import ContentType
from vitrina.api.models import ApiKey
org = Organization.objects.get(title__startswith="Informacinės visuomenės")
ct = ContentType.objects.get_for_model(org)
print(
    *(
        key
        for key in (
            ApiKey.objects.filter(
                representative__content_type=ct,
                representative__object_id=org.id,
                representative__user__email='mantas.zimnickas@ivpk.lt',
            ).
            values_list('api_key', flat=True)
        )
    ),
    sep='\n',
)
EOF

poetry run python manage.py shell <<EOF
from vitrina.api.models import ApiKey
print(
    *(
        key
        for key in (
            ApiKey.objects.filter(
                api_key__contains="***",
            ).
            values_list('api_key', flat=True)
        )
    ),
    sep='\n',
)
EOF

apikey=$(poetry run python manage.py shell <<EOF
from vitrina.orgs.models import Organization, Representative
from django.contrib.contenttypes.models import ContentType
from vitrina.api.models import ApiKey
org = Organization.objects.get(title__startswith="Informacinės visuomenės")
ct = ContentType.objects.get_for_model(org)
print(
    *(
        key[-36:]
        for key in (
            ApiKey.objects.filter(
                representative__content_type=ct,
                representative__object_id=org.id,
                representative__user__email='mantas.zimnickas@ivpk.lt',
            ).
            values_list('api_key', flat=True)
        )
    ),
    sep='\n',
)
EOF
)
echo $apikey

apikey=***
apikey=***

apikey=$(poetry run python manage.py shell <<EOF
from vitrina.api.models import ApiKey
key = ApiKey.objects.get(api_key="DUPLICATE-49-***")
key.api_key = "***"
key.enabled = False
key.save()
print(key.api_key)
EOF
)
echo $apikey


apikey=$(pass tmp/localhost/vitrina/api/ivpk | head -1)

server=:8000/partner/api/1
auth="Authorization: ApiKey $apikey"

http $server/catalogs $auth
