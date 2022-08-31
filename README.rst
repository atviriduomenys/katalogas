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

    docker-compose up
    poetry run python manage.py migrate


To log into adminer use credentials in docker-compose.yml::

    System: PostgreSQL
    Server: postgres
    Username: adp
    Password: secret
    Database: adp-dev