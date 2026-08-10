.. default-role:: literal

Data catalogue
##############


Lithuania's open data catalogue (data.gov.lt).


Contributing
************

- All development changes goes to `devel` branch, `main` is reserved for
  production releases.

- Follow TDD_ (Test Driven Development) principle.

- Follow DDD_ (Documentation Driven Development) principle.

- Follow `GitHub Flow`_ principle.

.. _TDD: https://en.wikipedia.org/wiki/Test-driven_development
.. _DDD: https://gist.github.com/zsup/9434452
.. _GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow

System packages
***************

You can install system dependencies using your OS package manager, or use Nix
for a reproducible development environment. Nix is optional.

**Using Nix (optional, recommended):**

This project uses Nix flakes to manage system development dependencies. `Install
the Nix package manager`_ first, then use `nix develop` to enter the dev shell
which provides Python, Poetry, Node.js, and all required system libraries.

.. _Install the Nix package manager: https://wiki.nixos.org/wiki/Nix_Installation_Guide

Install Nix (single-user, recommended for non-NixOS systems):

.. code:: sh

    curl -L https://nixos.org/nix/install | sh

Or for multi-user installation (requires `sudo`):

.. code:: sh

    curl -L https://nixos.org/nix/install | sh -s -- --daemon

Enable flakes (add to `~/.config/nix/nix.conf`):

.. code:: sh

    mkdir -p ~/.config/nix
    echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf

Enter the development shell (bash by default):

.. code:: sh

    nix develop

Alternative use your prefered shell:

.. code:: sh

    nix develop -c zsh

**Installing Nix via your distribution's package manager:**

Alternatively, you can install Nix from your distro's repositories instead of
using the official installer script. This avoids piping a remote script to
shell. Distro packages may lag behind upstream Nix versions; the project
requires flakes support.

**Debian / Ubuntu:**

.. code:: sh

    sudo apt install nix-setup-systemd
    sudo adduser $(whoami) nix-users

After logging out and back in, enable the unstable channel and update:

.. code:: sh

    nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
    nix-channel --update

**Arch Linux:**

.. code:: sh

    sudo pacman -S nix

After installing via your distro package manager, you still need to enable
flakes (see above) before running `nix develop`.

All subsequent commands in this README assume you are inside the `nix develop`
shell.

**Using your OS package manager:**

Alternatively, install the packages listed in `flake.nix` manually using your
OS package manager.

**Required system packages (must use native OS package manager):**

The following packages cannot be managed by Nix and must be installed using
your OS package manager (apt, dnf, pacman, etc.):

- `docker` and `docker compose` — Docker requires systemd/service manager
  integration and root privileges to run the daemon. Nix can only provide the
  Docker CLI, not the running service.

Install Docker using your distribution's package manager and ensure your user
is in the `docker` group:

.. code:: sh

    sudo usermod -aG docker $USER

Then log out and back in for the group change to take effect.


Development environment
***********************

All commands assume you have an active `nix develop` or `poetry env activate`
shell.

From project root directory start with copying over `.env.example` to `.env`:

.. code:: sh

    cp .env.example .env

From project root directory run:

.. code:: sh

    docker compose up -d

If elasticsearch does not start and raises `AccessDeniedException` on
`createDirectory()`, try this:

.. code:: sh

    sudo chown -R $UID:$GID var/elasticsearch

Then we can run:

.. code:: sh

    poetry install
    python manage.py migrate --skip-checks
    python manage.py rebuild_index --noinput
    python manage.py createinitialrevisions

`--skip-checks` disables Django's system checks. It is needed because the URL
check queries the Site table before migrations run on a fresh database (a
django-cms bootstrapping quirk).

To generate static files run (build the webpack bundles first so
`collectstatic` picks them up):

.. code:: sh

    cd webpack
    npm install
    npm run build
    cd ..
    python manage.py collectstatic

To run the development server:

.. code:: sh

    python manage.py runserver

To add new language translations (replace en with desired language):

.. code:: sh

    python manage.py makemessages -av1

To generate or update .mo files when .po file is ready:

.. code:: sh

    python manage.py compilemessages

To log into adminer open http://localhost:9000/ in your browser and use credentials in `docker-compose.yml`::

    System: PostgreSQL
    Server: postgres
    Username: adp
    Password: secret
    Database: adp-dev

Scripts that are run periodically:

- Script that adds holiday dates to database:

  .. code:: sh

      python scripts/add_holiday_dates.py


To set up a viisp social account provider:

- Create a viisp_key object in admin panel as a superuser:

  The contents of viisp_key object needs to be an rsa key encoded in base64.
  Example of a fake key can be found in test resources.

- Create viisp provider in admin panel as a superuser:

  The data should be as follows:
  Provider: Viisp
  Name: viisp
  Client_id: viisp
  Sites: Choose the site that matches SITE_ID in settings and points to current domain.
  The host machine should be connected to vpn or whitelisted to be able to access test env of viisp provider.
  All other fields should be left unchanged.

- Create a viisp_token_key object in admin panel as a superuser:

  The contents of viisp_token_key object needs to be a token generated with fernet:

    from cryptography.fernet import Fernet
    key = Fernet.generate_key()

To use google analytics go to http://127.0.0.1:8000/admin/extra_settings/setting/ add setting GOOGLE_ANALYTICS_ID
and set provided google analytics id.

Testing
*******

Docker services (PostgreSQL and Elasticsearch) must be running before executing
tests:

.. code:: sh

    docker compose up -d

Run all tests:

.. code:: sh

    pytest -vvra --tb=short

Run a single test:

.. code:: sh

    pytest -vvra --tb=short tests/orgs/test_views.py::test_search_with_query_that_matches_one

.. note::

    Running the full test suite takes approximately 30 minutes on a fast
    computer, primarily because tests interact with Elasticsearch for search
    indexing.
