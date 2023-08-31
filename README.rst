Data catalogue
##############


Lithuania's open data catalogue (data.gov.lt).


Contributing
************

- All development changes goes to ``devel`` branch, ``main`` is reserved for
  production releases.

- Follow TDD_ (Test Driven Development) principle.

- Follow DDD_ (Documentation Driven Development) principle.

- Follow `GitHub Flow`_ principle.

.. _TDD: https://en.wikipedia.org/wiki/Test-driven_development
.. _DDD: https://gist.github.com/zsup/9434452
.. _GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow


Development environment
***********************

From project root directory run::

    docker-compose up -d

If elasticsearch does not start and raises `AccessDeniedException` on
`createDirectory()`, try this::

    sudo chown -R $UID:$GID var/elasticsearch

Then we need to install pgloader (https://pgloader.readthedocs.io/en/latest/install.html#docker-images) and migrate MySQL database to PostgreSQL::

    docker run -it --rm \
        --network katalogas_default \
        dimitri/pgloader:latest \
        pgloader \
            mysql://adp:secret@mysql/adp-dev \
            postgresql://adp:secret@postgres/adp-dev


By default pgloader creates a schema with the same name as in source database. So after this command we need to switch to public schema::

    docker-compose run -T --rm -e PGPASSWORD=secret postgres psql -h postgres -U adp adp-dev <<EOF
    BEGIN TRANSACTION;
      ALTER SCHEMA "public" RENAME TO "public-orig";
      ALTER SCHEMA "adp-dev" RENAME TO "public";
      DROP SCHEMA "public-orig" CASCADE;
    COMMIT;
    EOF

Then we can run::

    poetry install
    poetry run python manage.py migrate
    poetry run python manage.py rebuild_index --noinput
    poetry run python manage.py createinitialrevisions

To generate static files run::

    poetry run python manage.py collectstatic
    cd webpack
    npm install
    npm run build


To migrate files, news posts and pages to Django CMS rerun server and run::

    poetry run python scripts/migrate_files.py \
        --distribution-path var/data/ \
        --cms-path var/data/files/ \
        --structure-path var/data/structure/

    poetry run python scripts/migrate_news.py
    poetry run python scripts/migrate_pages.py

To add new language translations (replace en with desired language)::

    poetry run python manage.py makemessages -av1

To generate or update .mo files when .po file is ready::

    poetry run python manage.py compilemessages

To log into adminer open http://localhost:9000/ in your browser and use credentials in docker-compose.yml::

    System: PostgreSQL
    Server: postgres
    Username: adp
    Password: secret
    Database: adp-dev

Scripts that are run periodically:

- Script that adds holiday dates to database::

    poetry run python scripts/add_holiday_dates.py


To set up a visp social account provider:

- Create a viisp_key object in admin panel as a superuser::

  The contents of viisp_key object needs to be an rsa key encoded in base64.
  Example of a fake key can be found in test resources.


- Create visp provider in admin panel as a superuser::

  The data should be as follows:
  Provider: Viisp
  Name: viisp
  Client_id: viisp
  Sites: Choose the site that matches SITE_ID in settings and points to current domain.
  The host machine should be connected to vpn or whitelisted to be able to access test env of viisp provider.
  All other fields should be left unchanged.

 Create a viisp_token_key object in admin panel as a superuser::
 The contents of viisp_token_key object needs be a token generated with fernet:
 
    from cryptography.fernet import Fernet
    key = Fernet.generate_key

