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
From project root directory start with copying over `.env.example` to `.env`::

    cp .env.example .env

From project root directory run::

    docker-compose up -d

If elasticsearch does not start and raises `AccessDeniedException` on
`createDirectory()`, try this::

    sudo chown -R $UID:$GID var/elasticsearch

Then we can run::

    poetry install
    poetry run python manage.py migrate --skip-checks
    poetry run python manage.py rebuild_index --noinput
    poetry run python manage.py createinitialrevisions

``--skip-checks`` bypasses the URL system check that queries the Site table
before migrations run on a fresh database (a django-cms bootstrapping quirk).

To generate static files run::

    poetry run python manage.py collectstatic
    cd webpack
    npm install
    npm run build

To run the development server::

    poetry run python manage.py runserver

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


To set up a viisp social account provider:

- Create a viisp_key object in admin panel as a superuser::

  The contents of viisp_key object needs to be an rsa key encoded in base64.
  Example of a fake key can be found in test resources.


- Create viisp provider in admin panel as a superuser::

  The data should be as follows:
  Provider: Viisp
  Name: viisp
  Client_id: viisp
  Sites: Choose the site that matches SITE_ID in settings and points to current domain.
  The host machine should be connected to vpn or whitelisted to be able to access test env of viisp provider.
  All other fields should be left unchanged.

- Create a viisp_token_key object in admin panel as a superuser::

  The contents of viisp_token_key object needs to be a token generated with fernet:

    from cryptography.fernet import Fernet
    key = Fernet.generate_key()

To use google analytics go to http://127.0.0.1:8000/admin/extra_settings/setting/ add setting GOOGLE_ANALYTICS_ID
and set provided google analytics id.
