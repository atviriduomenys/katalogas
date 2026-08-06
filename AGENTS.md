# AGENTS.md — Katalogas (data.gov.lt)

Lithuania's open data catalogue. Django 4.2 / Python 3.11 / django-cms / PostgreSQL 14 / Elasticsearch 7.

## Specifications implemented

Katalogas implements three interrelated specifications developed by VSSA (Valstybės skaitmeninių sprendimų agentūra) for the European Interoperability Framework:

- **[DCAT-AP-LT](https://ivpk.github.io/DCAT-AP-LT/)** — Lithuania's DCAT-AP profile for describing data catalogs, datasets, data services, and distributions. Based on BregDCAT-AP → (DCAT-AP, CPSV-AP) → (DCAT, CPSV).
- **[DSA (Duomenų struktūros aprašas)](https://ivpk.github.io/dsa/1.1/)** — Data Structure Description specification. Extends DCAT by adding Models, Properties, and Data Types to describe dataset content/structure.
- **[UAPI](https://ivpk.github.io/uapi/)** — Universal Data Provisioning Interface (UDTS). Domain-agnostic OpenAPI specification for interoperable data services. Katalogas generates UAPI-compliant OpenAPI specs by combining DSA manifests of each dataset within a Data Service.

### Spec-to-model mapping

| DCAT-AP-LT class                    | Django model                              | App                    |
| ----------------------------------- | ----------------------------------------- | ---------------------- |
| `dcat:Catalog`                      | `Dataset` (subclass=`catalog`)            | `vitrina/datasets/`    |
| `dcataplt:InformationSystem`        | `Dataset` (subclass=`information_system`) | `vitrina/datasets/`    |
| `dcat:Dataset`                      | `Dataset` (subclass=`dataset`)            | `vitrina/datasets/`    |
| `dcat:DataSeries`                   | `Dataset` (subclass=`series`)             | `vitrina/datasets/`    |
| `dcat:DataService`                  | `Dataset` (subclass=`service`)            | `vitrina/datasets/`    |
| `dcat:Distribution`                 | `DatasetDistribution`                     | `vitrina/resources/`   |
| `foaf:Agent` / `dcat:publisher`     | `Organization`                            | `vitrina/orgs/`        |
| `dcat:theme` / `skos:ConceptScheme` | `Category`                                | `vitrina/classifiers/` |
| `dct:Frequency`                     | `Frequency`                               | `vitrina/classifiers/` |
| `dct:LicenseDocument`               | `Licence`                                 | `vitrina/classifiers/` |
| `dct:Standard` / `cpsv:Rule`        | `Rule`                                    | `vitrina/classifiers/` |
| `eli:LegalResource`                 | `ApplicableLegislation`                   | `vitrina/classifiers/` |
| `dct:Location`                      | `SpatialCoverage` / `AreaOfManagement`    | `vitrina/classifiers/` |
| `dcat:contactPoint`                 | `Contact`                                 | `vitrina/datasets/`    |
| `foaf:Document`                     | `Documentation`                           | `vitrina/datasets/`    |
| `dqv:QualityAnnotation`             | `QualityAnnotation`                       | `vitrina/datasets/`    |
| `dqv:QualityMeasurement`            | `QualityMeasurement`                      | `vitrina/datasets/`    |
| `prov:Activity`                     | `Activity`                                | `vitrina/classifiers/` |
| `dct:ProvenanceStatement`           | `ProvenanceStatement`                     | `vitrina/classifiers/` |
| `dcat:Relationship`                 | `DatasetRelation` / `Relation`            | `vitrina/datasets/`    |
| `adms:Identifier`                   | `Dataset.identifier` fields               | `vitrina/datasets/`    |
| `dcat:mediaType`                    | `MediaType` / `Format`                    | `vitrina/resources/`   |
| `dcat:checksum` / `spdx:Checksum`   | `DatasetDistribution` checksum fields     | `vitrina/resources/`   |
| `dcataplt:Importance`               | `Concept` (schema=`dcataplt:Importance`)  | `vitrina/classifiers/` |
| `dcataplt:Type`                     | `Concept` (schema=`dcataplt:Type`)        | `vitrina/classifiers/` |

| DSA concept         | Django model                                       | App                    |
| ------------------- | -------------------------------------------------- | ---------------------- |
| Model               | `Model`                                            | `vitrina/structure/`   |
| Property            | `Property`                                         | `vitrina/structure/`   |
| Data type           | `Metadata.type` + `type_args`                      | `vitrina/structure/`   |
| Base (inheritance)  | `Base`                                             | `vitrina/structure/`   |
| Enum / EnumItem     | `Enum` / `EnumItem`                                | `vitrina/structure/`   |
| Param / ParamItem   | `Param` / `ParamItem`                              | `vitrina/structure/`   |
| Prefix (namespace)  | `Prefix`                                           | `vitrina/structure/`   |
| Version             | `Version` / `MetadataVersion`                      | `vitrina/structure/`   |
| Maturity level      | `Metadata.level` / `level_given` / `average_level` | `vitrina/structure/`   |
| Access level        | `Metadata.access`                                  | `vitrina/structure/`   |
| Metadata visibility | `Metadata.visibility`                              | `vitrina/structure/`   |
| Status              | `Status`                                           | `vitrina/classifiers/` |

### Spinta

Katalogas uses **[Spinta](https://github.com/atviriduomenys/spinta)** — a companion project responsible for publishing data as UAPI-compliant Data Services. Spinta reads DSA manifests from Katalogas and serves data via REST API. Configured via `SPINTA_EXECUTABLE`, `SPINTA_PATH`, `SPINTA_SERVER_URL` in `.env`.

## Repo structure

- `vitrina/` — Django app, each sub-directory is a Django app (datasets, orgs, users, requests, resources, classifiers, ...)
- `tests/` — mirrors `vitrina/` structure; `conftest.py` provides shared fixtures
- `webpack/` — frontend asset bundle (npm, webpack, Bulma, Alpine.js, htmx, jQuery)

## Quick start

```sh
cp .env.example .env
docker compose up -d              # postgres, elasticsearch 7, redis, celery
poetry install
poetry run python manage.py migrate --skip-checks   # --skip-checks needed for django-cms Site bootstrapping
poetry run python manage.py rebuild_index --noinput
poetry run python manage.py createinitialrevisions
cd webpack && npm install && npm run build && cd ..
poetry run python manage.py collectstatic
poetry run python manage.py runserver
```

Nix dev shell available (`nix develop`) — provides Python, Poetry, Node, and all system libs.

## Testing

- Services must be running: `docker compose up -d`
- `poetry run pytest -vvra --tb=short` — full suite ~30 min (Elasticsearch bottleneck)
- Single test: `poetry run pytest -vvra --tb=short tests/path/to/test.py::test_name`
- Use pytest style test functions, not `unittest.TestCase` classes.
- Follow TDD: write the test first, verify it fails, then implement the fix.
- `@pytest.mark.haystack` marks tests needing ES search index
- `tests/conftest.py` auto-manages unmanaged models, temp media roots, clears cache, mocks translation
- CI uses `docker-compose-test.yml` (PostgreSQL only; ES/Redis are GH Actions services)

## Code quality

- Always run both checks before committing:

### Check (must pass)

```sh
poetry run ruff check .
poetry run ruff format --diff --check .
```

### Auto-fix

```sh
poetry run ruff check . --fix
poetry run ruff format .
```

- No typechecker configured

## GitHub

- Use `gh` to access GitHub (issues, PRs, releases, etc.)
- When working with issues from another repository, use `gh --repo owner/repo` flag (e.g. `gh --repo atviriduomenys/spinta issue view 123`)

## Branch & commit conventions

- `devel` — all development; `main` — production releases only
- TDD + GitHub Flow
- Commit messages: `#issue_number Short description` or `dvms-XXXX Short description` (e.g. `#2716 data last updated`, `dvms-514 don't allow to upload xhtml files`)

## Key framework details

- `DJANGO_SETTINGS_MODULE=vitrina.settings` (set in `pytest.ini` and `manage.py`)
- `AUTH_USER_MODEL = vitrina_users.User` (email-based, no username)
- Custom Haystack engine: `vitrina.datasets.search_backends.ElasticSearchEngine`
- `HAYSTACK_CONNECTIONS` has `default` and `test` — `conftest.py` swaps to test index for `@pytest.mark.haystack`
- Celery: `vitrina.celery` app, Redis broker (db 3), `DatabaseScheduler`, auto-discover tasks
- django-reversion on all models (except those in `NOT_VERSIONED_MODELS`)
- django-flags feature flags (e.g. `publish_button` enabled in tests)
- Django CSP enforced with report-only strict policy; `CSPScopeMiddleware` relaxes it on admin/CMS
- File upload: whitelist-based in `FILER_MIME_TYPE_WHITELIST`, denial-of-known-dangerous via `FILER_ADD_FILE_VALIDATORS`
- Translations: `poetry run python manage.py makemessages -av1` / `compilemessages`; VU translation API
- Use `pp` (from `pprintpp`) for debug printing — injected into builtins by `manage.py` and `conftest.py`

## Notable settings (`.env`)

- `SEARCH_URL=elasticsearch7://127.0.0.1:9200/haystack`
- `USE_OTP_VALIDATION=True` — OTP can be disabled in tests via settings override
- `RECAPTCHA_PUBLIC_KEY` / `RECAPTCHA_PRIVATE_KEY` — test keys in `.env.example`
- `OAUTH_*` — OAuth server config for Spinta integration
- `SPINTA_EXECUTABLE` / `SPINTA_PATH` — Spinta for structure data
