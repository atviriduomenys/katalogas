### Reload database from MySQL schema

docker run -it --rm \
    --network katalogas_default \
    dimitri/pgloader:latest \
    pgloader \
        mysql://adp:secret@mysql/adp-dev \
        postgresql://adp:secret@postgres/adp-dev

docker-compose run -T --rm -e PGPASSWORD=secret postgres \
    psql -h postgres -U adp adp-dev <<EOF
BEGIN TRANSACTION;
  ALTER SCHEMA "public" RENAME TO "public-orig";
  ALTER SCHEMA "adp-dev" RENAME TO "public";
  DROP SCHEMA "public-orig" CASCADE;
COMMIT;
EOF

pg_dump -Fc -h localhost -U adp adp-dev > var/postgres_adp.dump


### Load test data

# Drop all data in database
docker-compose run -T --rm -e PGPASSWORD=secret postgres \
    psql -h postgres -U adp adp-dev <<EOF
BEGIN TRANSACTION;
  DROP SCHEMA "public" CASCADE;
  CREATE SCHEMA "public";
COMMIT;
EOF

# Load database dump
pg_restore -Fc -h localhost -U adp -d adp-dev < var/postgres_adp.dump

psql -h localhost -U adp -d adp-dev <<EOF
-- Move FK from cms_page to adp_cms_page and drop cms_page,
-- because cms_page is used by Django CMS.
ALTER TABLE "cms_attachment"
    DROP CONSTRAINT "fkb61y6xtsjm3lph7jvqwvna336";
ALTER TABLE ONLY "cms_attachment"
    ADD CONSTRAINT "fkb61y6xtsjm3lph7jvqwvna336"
        FOREIGN KEY (cms_page_id)
        REFERENCES adp_cms_page(id)
        ON UPDATE RESTRICT ON DELETE RESTRICT;
-- Drop duplicate constraint.
ALTER TABLE "cms_attachment"
    DROP CONSTRAINT "fkd24jc8oag6itrip826odio0d";
DROP TABLE "cms_page";
EOF

# Run migrations, this might take aboult 10 minutes to complete.
# It is recommended to save final result in a dump file and next time load the
# dump file, to avoid running all the migrations again.
poetry run python manage.py migrate sites
poetry run python manage.py migrate

# Another set of migrations implemented as scripts
poetry run python scripts/migrate_files.py \
    --distribution-path var/data/ \
    --cms-path var/data/files/ \
    --structure-path var/data/structure/
poetry run python scripts/migrate_pages.py
poetry run python scripts/migrate_news.py

# Reset all passwords to 'secret'
poetry run python manage.py shell
from vitrina.users.models import User
user = User()
user.set_password('secret')
User.objects.update(password=user.password)
exit()

# Save database dump 
pg_dump -Fc -h localhost -U adp adp-dev > var/postgres_adp-dev.dump
du -sh var/postgres_adp-dev-am.dump
#| 57M     var/postgres_adp-dev-am.dump


### Configure psql client
cat >> ~/.pgpass <<'EOF'
localhost:5432:adp-dev:adp:secret
EOF
chmod 0600 ~/.pgpass
psql -h localhost -U adp adp-dev
\q
