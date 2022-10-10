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
    make

To log into adminer open http://localhost:9000/ in your browser and use credentials in docker-compose.yml::

    System: PostgreSQL
    Server: postgres
    Username: adp
    Password: secret
    Database: adp-dev
