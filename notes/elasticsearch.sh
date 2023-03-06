# 2022-09-30 22:43 Elastic search issue

docker-compose logs elasticsearch
#| ElasticsearchException[failed to bind service]; nested:
#|     AccessDeniedException[/usr/share/elasticsearch/data/nodes];
#| Likely root cause: java.nio.file.AccessDeniedException:
#|     /usr/share/elasticsearch/data/nodes
#| java.base/sun.nio.fs.UnixFileSystemProvider.createDirectory(UnixFileSystemProvider.java:389)

ls -ld var/elasticsearch
#| drwxr-xr-x 2 root root 4096 2022-09-30 22:21 var/elasticsearch

sudo chown -R $UID:$GID var/elasticsearch

ls -ld var/elasticsearch
#| drwxr-xr-x 2 sirex sirex 4096 2022-09-30 22:21 var/elasticsearch

docker-compose restart elasticsearch
docker-compose ps


# 2022-09-30 22:43 Another elasticsearch issue

poetry run python manage.py rebuild_index --noinput
#| [ERROR/MainProcess] Failed indexing 1001 - 2000 (retry 5/5):
#|   The model 'None' combined with model_attr 'title' returned None,
#|   but doesn't allow a default or null value.

# Fix: Add null=True to title field in search_indexes.py or filter out null
# values.


# 2022-10-17 18:03 How to delete ElasticSearch indices?

# https://www.elastic.co/guide/en/elasticsearch/reference/7.17/cat-indices.html
http -b ":9200/_cat/indices?v=true&s=index"

# https://www.elastic.co/guide/en/elasticsearch/reference/7.17/indices-delete-index.html
http -b DELETE ":9200/haystack"


# 2022-10-19 12:24 ElasticSearch returns 500 error

docker-compose logs --tail 10 elasticsearch
#| katalogas-elasticsearch-1  | {
#|     "type": "server",
#|     "timestamp": "2022-10-19T09:25:32,440Z",
#|     "level": "WARN",
#|     "component": "o.e.c.r.a.DiskThresholdMonitor",
#|     "cluster.name": "docker-cluster",
#|     "node.name": "12f7709f9f13",
#|     "message": "
#|         flood stage disk watermark [95%] exceeded on
#|             [JAIsvrdtTw-hj278muyAnw]
#|             [12f7709f9f13]
#|             [/usr/share/elasticsearch/data/nodes/0]
#|         free: 9.7gb[4.2%],
#|         all indices on this node will be marked read-only
#|     ",
#|     "cluster.uuid": "waXSCUQYRLOZdQJ-psUE5w",
#|     "node.id": "JAIsvrdtTw-hj278muyAnw"
#| }
df -h .
#| /dev/nvme0n1p2  228G  207G  9,8G  96% /
sudo du -sh var/*
#| 353.0M var/postgres
#| 219.0M var/mysql
#| 200.0M var/postgres_adp-dev_anonymized.sql
#|  51.0M var/postgres_adp-dev_anonymized.dump
#|  51.0M var/postgres_adp-dev.dump
#|  24.0M var/static
#|   1,6M var/media
#|   0.9M var/elasticsearch

df -h /var/lib/docker
#| Filesystem      Size  Used Avail Use% Mounted on
#| /dev/nvme0n1p2  228G  207G  9,8G  96% /

sudo du -sh /var/lib/docker
#| 4,9G    /var/lib/docker

docker ps
docker inspect katalogas-elasticsearch-1
#| "UpperDir": "/var/lib/docker/overlay2/0f1529794caa1800f7f66a7b4c7bf53f2773a8b78ad011b4183b384dd55
docker exec -it katalogas-elasticsearch-1 bash
df -h
#| Filesystem      Size  Used Avail Use% Mounted on
#| overlay         228G  207G  9.8G  96% /
#| /dev/nvme0n1p2  228G  207G  9.8G  96% /etc/hosts
exit

# SOLUTION
#   It looks, that it was caused by free disk space being less than 5%.

poetry run python manage.py rebuild_index --noinput --using=test
