Changes
#######

v 1.18.0 (current)
==================

Improvements:

https://github.com/atviriduomenys/katalogas/issues/2484

- Optimize DSA manifest import database performance.
    - Added database indices on `Metadata` and `Comment` models to speed up lookups during import.
    - Introduced in-memory caches for frequently accessed objects (users, dataset statuses, metadata) to reduce repeated database queries within a single import run.
    - Refactored structure import service to batch-fetch related objects and avoid N+1 query patterns.

https://github.com/atviriduomenys/katalogas/issues/2338

- Test-prove `boolean` type enums work as expected.

https://github.com/atviriduomenys/katalogas/issues/2519

- Smart contract notifications:
    - Send an email to the data owner organization when a smart contract agreement is submitted.

https://github.com/atviriduomenys/katalogas/issues/2337

- Implement `number` type enums.

https://github.com/atviriduomenys/katalogas/issues/2461

-  Implement dataset name check in manifest read

https://github.com/atviriduomenys/katalogas/issues/2522

- Added formatting for HTML tags to be rendered correctly and we would not have laying HTML tags in description text fields.

https://github.com/atviriduomenys/katalogas/issues/2524

- HTML formatting and breadcrumb adjustments.


Bug fixes:

<No Ticket>

- Fixing invalid template tags.

<No Ticket>
- Fixed duplicate comment creation on request detail page.

<No Ticket>
- Add djangocms-file, djangocms-picture, and djangocms-link plugins.


v 1.17.1 (2026-03-30)
==================

https://github.com/atviriduomenys/katalogas/issues/1828
- Publisher and creator changes.

v 1.17.0 (2026-03-27)
==================

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2324

- Several issues related to enum item handling:
    - When creating an enum item via the UI, the metadata version is now correctly set.
    - Importing a manifest that contains non-string enum items without prepare values will now add an error indicating that a prepare column is required.
    - Importing a manifest with string enum items and no prepare values will now automatically use the source column as the prepare value.
    - Creating enum items via the UI will now return an error if a value already exists in the enum.
    - Creating and importing enums will now check enum item value types.
    - Enum manifest export will export enum level column correctly.
    - Boolean type enum items can now be created/changed via UI.
    - Enum item uniqueness is checked for source+prepare values instead of prepare only. This allows creating enums with same prepare but different source values

Improvements:

https://github.com/atviriduomenys/katalogas/issues/2447

- DataService and Agent related improvements:
    - Disable deletion for `Agent` and `AgentEnvironemnt`.
    - Add validation so each `Agent` can have only one `AgentEnvironment` per `environment`.
    - Update DataService `endpoint_url`, `endpoint_description`, `endpoint_type`, `endpoint_description_type` fields validation to work with `Agent` selection.
    - Add dynamic `endpoint_url` and `endpoint_description` display for DataService details page.
    - Introduce `Dataset.conforms_to` field.
    - Fix help text for DataService form fields.


https://github.com/atviriduomenys/katalogas/issues/2329

- Ensure that it is possible to set referenced properties for `ref` type properties on property create/edit form.
    - Re-use already introduced widget for the field.
    - Adjust the DOM to show/hide/clear field on different selections.
    - Change the logic for the Create/Update view of property to create PropertyList objects.

https://github.com/atviriduomenys/katalogas/issues/2255

- Add organization representative access via org chain.
    - Added `get_effective_user_role_via_organization` on Dataset — resolves a user's effective role via the org representative chain, taking the most restrictive role between the org and user assignments.
    - Extended `has_perm` and `filter_datasets_for_user` to include datasets accessible through the organization representative chain.
    - Prevented `open_data_representative` users from creating or updating structure objects with visibility below Package.

https://github.com/atviriduomenys/katalogas/issues/2335

- Access level display adjustments; If value exists, display the initial provided value, otherwise, default to average.


v 1.16.0 (2026-03-16)
==================

https://github.com/atviriduomenys/katalogas/issues/2321

- Refactor `Agent` by introducing `AgentEnvironment` model.
- Move relation from `Agent.service` to `Dataset.agent`.


https://github.com/atviriduomenys/katalogas/issues/2435

- Change recipient for reply comment.

https://github.com/atviriduomenys/katalogas/issues/2438

Security: Fix open Dependabot vulnerability alerts across pip and npm dependencies:

- Bump Django from 4.2.26 to 4.2.28 (CVE-2026-1207 SQL injection, and 5 other CVEs).
- Bump django-allauth from 0.51.0 to 65.14.3 (CVE-2025-65430 inactive user token bypass, CVE-2025-65431 mutable identifier auth).
- Bump cryptography from 44.0.0 to 46.0.5 (SECT curves subgroup attack).
- Bump weasyprint from 62.0 to 68.1 (SSRF protection bypass).
- Bump pillow to 12.1.1 (out-of-bounds write on PSD images).
- Bump authlib from 1.6.0 to 1.6.8 (account takeover via login CSRF).
- Bump sqlparse to 0.5.5 (DoS via tuple list formatting).
- Bump aiohttp to 3.13.3 (cookie parser vulnerability, and 6 other CVEs).
- Bump pyasn1 to 0.6.2 (DoS via malformed RELATIVE-OID).
- Bump urllib3 to 2.6.3 (decompression bomb bypass on redirects).
- Bump python-multipart to 0.0.22 (arbitrary file write via path traversal).
- Bump setuptools from 75.7.0 to 78.1.1 (path traversal).
- Bump django-filer from 3.2.3 to 3.4.4 (unrestricted dangerous file upload).
- Bump brotli to 1.2.0 (DoS via malicious decompression).
- Bump djangorestframework to 3.16.1 (XSS).
- Bump django-select2 to 8.4.8 (secret cache key leakage).
- Bump Django from 4.2.28 to 4.2.29 (uncontrolled resource consumption, race condition).
- Bump immutable from 5.1.4 to 5.1.5 (prototype pollution).
- Replace node-sass with Dart Sass to fix transitive npm vulnerabilities (minimatch, tar).
- Bump webpack to 5.105.3 (SSRF via HTTP redirects).
- Remove lodash (prototype pollution).
- Add `allauth.account.middleware.AccountMiddleware` required by new django-allauth.
- Add `oauthlib` as explicit dependency (previously transitive via old django-allauth).
- Add dependency review CI workflow for PR vulnerability scanning.
- Override `serialize-javascript` version to ^7.0.3
- Fix GitHub CodeQL code scanning alerts:

  - Add explicit `permissions: contents: read` to `run_tests.yml` workflow.
  - Fix stack trace exposure in Spinta API responses (`structure/services.py`).
  - Fix stack trace exposure in API serializer validation (`api/serializers.py`).
  - Fix URL redirection from user input in `ModelDataView`.
  - Fix DOM XSS in `model_data.html` by using `URL` API for safe navigation.
  - Add SRI integrity hashes to CDN-loaded CodeMirror resources.
  - Remove dead commented-out code with insecure CDN references.

https://github.com/atviriduomenys/katalogas/issues/2363

- Introduce DatasetAccessMixin to centralize dataset access control logic
previously scattered across viewsets.
- `is_open_data_representative` – checks whether the current user or
organization role has open data access
- `_filter_queryset_by_access` – filters datasets based on access rights
appropriate to the user or role
- `_check_dataset_access` – raises `PermissionDenied` for inaccessible datasets
- Changed Dataset access_right default value to PUBLIC from CONFIDENTIAL

https://github.com/atviriduomenys/katalogas/issues/2349

- Fix issues with Base row not being linked correctly, if model is imported with one manifest and referenced with base with another.

https://github.com/atviriduomenys/katalogas/issues/2434

- Added metadata field for dataset when creating through post request

https://github.com/atviriduomenys/katalogas/issues/2334

- Propagate visibility upward from property to model
- Added _update_model_visibility_from_property which ensures a model's visibility is automatically elevated when one of its properties has higher visibility.
- Added _update_parent_visibility_from_enum which propagates visibility upward through the full chain — from enum to its parent property, and from property to the model — applying the same rule at each level.

https://github.com/atviriduomenys/katalogas/issues/2336

- Set all manifest fields on the imported Comment objects

https://github.com/atviriduomenys/katalogas/issues/2467

- Comments for `Base` manifest rows are now imported & displayed correctly in Catalog & after export.

v 1.15.0 (2026-02-27)
==================

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2353

- Do not strip `/` prefix from `property.ref` during import/export.


https://github.com/atviriduomenys/katalogas/issues/2339

- Adjust export logic for the `resource` column of manifest:
    - More explicit filtering on distributions;
    - Removing short-circuit which caused some resources to not be exported;
    - Adjusting the logic for `_to_relative_model_name`;
    - Additional improvements on `_dataset_resources_to_tabular` to avoid early exports for some rows (which caused missing some data)

https://github.com/atviriduomenys/katalogas/issues/2429

- Comment button fix for reply/edit/delete buttons to work.

https://github.com/atviriduomenys/katalogas/issues/2257

- Index query optimization to fix N+1 problem.

v 1.14.1 (2026-02-23)
==================

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2397

- Fix url for `Dataset` landing page.

v 1.14.0 (2026-02-17)
==================

Improvements:

https://github.com/atviriduomenys/katalogas/issues/1906

- Export Dataset structure for a specific version.

https://github.com/atviriduomenys/spinta/issues/1656

- Add endpoints for Agreement and Client synchronization

https://github.com/atviriduomenys/katalogas/issues/2276

- Export dependent models in Dataset structure.

https://github.com/atviriduomenys/katalogas/issues/2378

- Adding a connection-check endpoint.

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2296

- Fixed menu-items in Organization and Dataset views.

https://github.com/atviriduomenys/katalogas/issues/2326

- Encode TAB spaces for RDF exports.

https://github.com/atviriduomenys/katalogas/issues/2340

- Card content alignment fixes in home page.

https://github.com/atviriduomenys/katalogas/issues/2332

- Use correct url for AJAX requests in `model_data.html`.
- Clean `SPINTA_*` variables in `settings.py`.

https://github.com/atviriduomenys/katalogas/issues/2382

- Fix incorrect email for error pages.
- Github check fix for redis and elasticsearch
- `NoneType` object has no attribute `is_draft` fix.

v 1.13.0 (2026-01-26)
==================

Improvements:

https://github.com/atviriduomenys/katalogas/issues/705

- Add delete button for `Structure` in dataset.
- Do not display `None` body comments.

https://github.com/atviriduomenys/katalogas/pull/2275

- A number of changes regarding UAPI.

https://github.com/atviriduomenys/katalogas/pull/2149

- Structure tab navigation rewritten to accept version_id.
- Implemented rules on how DSA data is versioned and saved.
- Implemented a version picker that allows the user to view Metadata for different versions.

https://github.com/atviriduomenys/katalogas/pull/2192

- Changed the publication logic, so that each version is a snapshot.
- Implemented validations so that invalid versions can not be published.

https://github.com/atviriduomenys/katalogas/pull/2233

- Changed the logic on how DatasetDistributions are displayed and saved.
- Implemented versions for DatasetDistributions.

https://github.com/atviriduomenys/katalogas/pull/2285

- Disabled the ability to create, edit, import and delete structure objects when the version is not a draft.

https://github.com/atviriduomenys/katalogas/pull/2313

- Disabled the Publish Version button.

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2284

- Fix child-resources url in resources tab

https://github.com/atviriduomenys/spinta/issues/1656

- Implement pagination for UAPI

https://github.com/atviriduomenys/spinta/issues/1647

- Add API for Version model conforming to UAPI
- Add API for Agent model conforming to UAPI

https://github.com/atviriduomenys/katalogas/issues/2031

- Refactor `Task` views and restrict access.
- Filter elastic to show correct assigned datasets.
- Allow comments only for public datasets.
- Fix landing page counts.
- Refactor `CreateMemberView.form_valid` function into service.

v 1.12.1 (2026-01-19)
==================

Bug fixes:

https://github.com/atviriduomenys/spinta/issues/1630

- Fix import logic when resource params were imported as dataset params.

v 1.12.0 (2026-01-15)
==================

Improvements

https://github.com/atviriduomenys/katalogas/issues/2070

- Update `HistoryView` to list history rows per `Revision`
- Display list of modified related objects next to each history row.
- Add `Agreement`, `AgreementFile`, `UseCaseClient` and `UseCaseClientScope` model changes to be included in `Project` history tab.

- https://github.com/atviriduomenys/katalogas/issues/2155

Corrected some texts

https://github.com/atviriduomenys/katalogas/issues/2172

Security: Update katalogas to automatically record all data changes made through UI, django-admin or celery tasks:

- Update katalogas to use django-reversion middleware to wrap each request in revision context.
- Update celery default task to wrap each task execution with revision context
- Automatically add custom JSON context to revision comment to be able to calculate origin of a change that was made.

https://github.com/atviriduomenys/katalogas/issues/2168

Refactored representative role model to split coordinator and manager roles into:

- OPEN_DATA_COORDINATOR, OPEN_DATA_MANAGER, RESOURCE_COORDINATOR, RESOURCE_MANAGER
- Enforced validation rules preventing Open Data representatives from creating non_public and confidential resources
- Creating and updating Information systems
- Ensured backward compatibility by updating all role checks and queryset filters referencing legacy roles
- Added logic to not let OPEN_DATA_COORDINATORS add/update/delete RESOURCE_MANAGERS and RESOURCE_COORDINATORS

https://github.com/atviriduomenys/spinta/issues/1647

- Adding an API permission to check if Agent is enabled (in Catalog) before performing any requests coming from the Agent (spinta/other(custom) implementations).
- Adjusting Sync-done API endpoint to return errors in UDTS format.
- Minimal cleanup for tests & mixins.

https://github.com/atviriduomenys/katalogas/issues/2227

- Fix landing page cards height

https://github.com/atviriduomenys/katalogas/issues/2244

- Display maturity level for all Dataset cards.

<No ticket>

- Add custom error pages for 400, 403, 404, 500.
- Fix django translations file.

<No ticket>

- Update `has_perm` to allow update organization for super users.

<No ticket>

- Bump `spinta` version to latest 0.2dev13.

v 1.11.3 (2026-01-05)
==================

- Revert `CustomSignalProcessor`.

v 1.11.2 (2025-12-18)
==================

- Add missing 0012 migration for `vitrina_smart_contracts`.
- Remove `vitrina_datasets` 0037 migration.

v 1.11.1 (2025-12-18)
==================

- Add reverse function for 0037 migration in `vitrina_datasets`.

v 1.11 (2025-12-16)
==================

Bug fixes:

<No ticket>

- Make a `Representative.can_make_agreements` boolean field non-nullable.

v 1.10 (2025-12-11)
==================

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2196

- Return the mock for translation calling, vertimas.vu.lt is up and running, tests are breaking again, because the mock
  was removed.

<No ticket>

- Adjust button spacing for dataset form.
- Forbid deleting contacts assigned to agreements (protected attributes, throw a nicer error to the user).
- Replace incorrect translation.

https://github.com/atviriduomenys/katalogas/issues/1925

- Remove `save()` from `Representative` model.
- Update elasticsearch indices from `Representative` and `DataDistribution` model.
Improvements:

https://github.com/atviriduomenys/katalogas/issues/2040

- Part 1-2: Organization-based detail & list agreement pages (previously only available under Projects).
- Part 3: Refactor agreements to be easily extendable to other pages.
- Part 4: Add separate agreement-negotiation views that are organization-based (reachable from organization tabs).
- Part 5: Leftovers. Adding the PDF replace in ADOC's script.

https://github.com/atviriduomenys/katalogas/issues/2075

- OrganizationUpdateForm disables the name field when updating an existing organization to prevent edits.
- OrganizationBaseForm now includes a clean method that automatically generates a dataset prefix based on the organization’s name and kind, and saves it to the database.
- Uniqueness is enforced across WhitelistedCodeNames and the generated organization names.
- Introduced WhitelistedCodeName, linked to Organization.
- Added support in the Organization admin form to manage an array of WhitelistedCodeNames.
- Made migrations to Organization and Dataset models, to generate organization name prefixes.

v 1.9 (2025-12-04)
==================

https://github.com/atviriduomenys/katalogas/issues/2124

- Adds new "internal media" directory for non public uploaded files. It works same way as Django media files, but uses `INTERNAL_MEDIA_ROOT` and `INTERNAL_MEDIA_URL` settings.
- Adds new endpoint for downloading uploaded smart contract files. In production, file is returned via `X-Accel-Redirect` header
- Additional Nginx configuration is needed:
    ```
    location /internal-static {
        internal;
        alias /internal-static;
    }
    ```

Security improvements:

- Added HTTP Strict Transport Security (HSTS) with 1-year max-age;
- Enabled HSTS preload and includeSubDomains;
- Strengthened cookie security (Secure, HttpOnly, SameSite=Lax);
- Implemented Referrer-Policy: strict-origin-when-cross-origin;
- Added Subresource Integrity (SRI) hashes to external scripts;
- Migrated jQuery from HTTP to HTTPS CDN;
- Enhanced Content Security Policy (CSP) directives.

https://github.com/atviriduomenys/dvms/issues/293

Security: Upgrade cryptography library to address CVE vulnerabilities:

- Updated cryptography from 38.0.4 to 44.0.3 (fixes CVE-2023-49083, CVE-2024-26130);
- Updated signxml from 3.0.0 to 4.2.0;
- Updated lxml from 4.9.4 to 6.0.2;
- Migrated VIISP authentication signatures from SHA1 to SHA256;
- Updated test fixtures for new signature algorithm.

v 1.8 (2025-11-28)
==================

https://github.com/atviriduomenys/dvms/issues/336

- new OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH setting for .well-known/jwks.json (and env variable) which if specified will automatically jwks from specified endpoint and store it inside of a cache.
- add support for multiple public keys picked dynamically for each access token by kid value. If not found, then by
  algorithm (`alg` & `kty`).
- these features unlock using auth servers with public key rotation, like gravitee.

https://github.com/atviriduomenys/katalogas/issues/2123

- Update partner registration permissions: validate that user is in active VIISP session.
- Update fake VIISP login to work with new partner registration.

https://github.com/atviriduomenys/dvms/issues/346

- Add password validation for fake VIISP login.

https://github.com/atviriduomenys/katalogas/pull/2115

- Publish version form now shows and lets the user select all fields that are created.

https://github.com/atviriduomenys/katalogas/issues/2067

- Part 2.4: Adjust queryset to allow selecting contacts without an assigned user as well.
- Part 3: Add forms for `submit`, `approve`, change the `form` status form. Separate the forms to be independant for each status.
- Part 4: Add forms for `initiate` and `sign` statuses. Adjust the logic for each one. Make them easily extendable.
- Part 5: Adjust selectable contact queryset for agreements.

https://github.com/atviriduomenys/katalogas/issues/2076

- New Flags for Government Organization Representatives
- open_data_representative

  - Cannot view non-public datasets.
  - Cannot create Information System Resources.
- information_system_representative

  - Can create and update information systems within their organization.
  - Can view non-public datasets.
- Permissions for Structure Models, Properties, and Enums

  - open_data_representative

    - Access limited to Public and Package-level structure items.
  - information_system_representative

    - Access limited to Public, Package, and Protected-level structure items.
- Indexes and managers have been updated to reflect the new roles and their respective permissions.

https://github.com/atviriduomenys/katalogas/issues/2147

- Order by title in `DatasetResourceForm` dropdowns of `Organization`.

https://github.com/atviriduomenys/katalogas/issues/921

- Fix breadcrumbs and title for dataset detail view.
- Add custom title field for `Request` from comments.
- Add link to `Request` in comments.
- Delete comment functionality for comment author or superuser.
- Edit comment functionality for comment author or superuser.
- Remove automated status update comments.

https://github.com/atviriduomenys/katalogas/pull/2145

- Refactored `vertimas.vu.lt` translation function.
- Added `try/except` for automatic translation with a timeout.

v 1.7 (2025-11-20)
==================
New features:

https://github.com/atviriduomenys/katalogas/issues/2067
- Part 1: Move field `other_assignee_legislations` from `Agreement` to `Project`.
- Part 2: Add assigner & assignee representatives that are displayed on the contract file.
- Part 2.1: Remove organizations as juridical entities from the list of possible entities to represent organizations in agreements.
- Part 2.2: Add new field `template` and new statuses for `Agreement`. Adding a few adjustments for field displays & formatting.
- Part 2.3: Move permissions to dedicated `permisions.py` file.

https://github.com/atviriduomenys/katalogas/issues/1955
- Improved contact form by adding new contact, position, removed dataset field.

Bugfixes:

<no ticket>
- Fix form layout, do not add a field that should be removed from the form itself on specific conditions.
- Fixed a malformed Django template variable by removing an accidental trailing `%` and properly closing the `{{ ... }}` tag.

https://github.com/atviriduomenys/katalogas/issues/2094
- Fix an issue where if `vertimas.vu.lt` is down, tests are failing on the pipelines and during local development, by introducing mocks for direct external API calls.

https://github.com/atviriduomenys/katalogas/issues/2092
- Added Version_type column and handling to Version table. It follows SemVer principles.
- Added a few more columns which will be needed for further versioning changes.

v 1.6 (2025-11-06)
==================

New features:

https://github.com/atviriduomenys/katalogas/pull/2050
- Made the status field of structure versionable.
- Added automatic handling of status values and hid them from the user.

https://github.com/atviriduomenys/katalogas/issues/1976
Add authorization server and API gateway server fields to Agent model.

https://github.com/atviriduomenys/katalogas/pull/2034
- Removed `print` statements;
- Added a Ruff rule for warning about said `print` statements;
- Removing an `api_key` logging/printing to avoid sensitive information leaks.

https://github.com/atviriduomenys/katalogas/issues/2011
- Installed celery as dependency in poetry;
- Added seperate docker container for celery;
- Added celery task to run `spinta check` command and save the manifest status to `ManifestValidationEntry`

https://github.com/atviriduomenys/katalogas/issues/2028
- Added a fake VIISP login feature to simulate authentication via VIISP.
- The login functionality is available only in test mode and will be hidden in production.

v 1.5 (2025-10-27)
==================

https://github.com/atviriduomenys/katalogas/issues/2032
Add IN_PROGRESS status to Request.

https://github.com/atviriduomenys/dvms/issues/303
Clients tab synchronization with authorization server. Client creation now actually provides the access.

v 1.4 (2025-10-23)
==================

https://github.com/atviriduomenys/katalogas/issues/1934
Translate `Requests`.

Security improvements:
- Added HTTP Strict Transport Security (HSTS) with 1-year max-age;
- Enabled HSTS preload and includeSubDomains;
- Strengthened cookie security (Secure, HttpOnly, SameSite=Lax);
- Implemented Referrer-Policy: strict-origin-when-cross-origin;
- Added Subresource Integrity (SRI) hashes to external scripts;
- Migrated jQuery from HTTP to HTTPS CDN;
- Enhanced Content Security Policy (CSP) directives.

https://github.com/atviriduomenys/katalogas/issues/1948
Add optional `organization` field to `Project` model.
Add `organization_card.html` component to display organization info where needed.
Add `OrganizationProjectsView` to show `Organization`s projects.
Refactor organization views to use `OrganizationBaseViewMixin` for shared properties
Refine project view permission checks to match updated logic

https://github.com/atviriduomenys/katalogas/pull/1989
Fixed persistent XSS vulnerability in comments by implementing HTML sanitization with bleach library.
Added comprehensive security test suite covering XSS attack vectors.

https://github.com/atviriduomenys/katalogas/issues/1929
Removed content editing language tab from forms.
Replaced old format scopes with the prefix of `spinta_` with UDTS format scopes.

https://github.com/atviriduomenys/katalogas/issues/1875
Add checkbox "Can edit data" to organization and dataset representative form

https://github.com/atviriduomenys/katalogas/issues/1836
Changed ACL list for Dataset read/update access, introduced `PermittedDatasetManager`

https://github.com/atviriduomenys/katalogas/issues/1967
Add `_version/` endpoint to see project version.

https://github.com/atviriduomenys/katalogas/issues/1935
Add different staff groups for Organization, LearningMaterial, DjangoCms and Dataset.
Add Catalog model to admin.

https://github.com/atviriduomenys/katalogas/issues/720
Add cronjobs for periodic scripts.

https://github.com/atviriduomenys/katalogas/issues/1968
Add `receive_request_email` flag to User.
Change default status in `RequestCommentForm`.

https://github.com/atviriduomenys/katalogas/issues/1904
Export Dataset structure to OpenAPI

https://github.com/atviriduomenys/katalogas/issues/1941
Fix wrong `eli` value in model_structure on properties

v 1.3 (2025-09-30)
==================

https://github.com/atviriduomenys/katalogas/issues/1621
Data migrations to add the Public access rights to those datasets which currently have no access rights.

https://github.com/atviriduomenys/katalogas/issues/1916
Create or update organisation should not require icon.

https://github.com/atviriduomenys/katalogas/issues/1928
Add contact tab to Dataset list form.

https://github.com/atviriduomenys/spinta/issues/1488
Adjustments from the Catalog side for spinta changes:
- Create Metadata w/ the initial data service that is created during agent creation
- Assign subclass to the service
- Add an explicit message for Agent creation form, when the auth server is unavailable/unreachable
- Define better error messages for Agent creation form

https://github.com/atviriduomenys/spinta/issues/1488
Add additional changes required by sinchronization from the Agent side:
- New API endpoint for getting manifest structure (in csv).
- Add an additional query parameter `parent_id` for retrieving all child datasets of a single dataset.

v 1.2 (2025-09-10)
==================

New features:

https://github.com/atviriduomenys/katalogas/issues/1626
Learning material should have an option to upload a file.

https://github.com/atviriduomenys/katalogas/issues/1818
Introduced `DistributionStatus` into the distribution form
    - Created `DistributionStatus` `ConceptSchema` (migration)
    - Created new instances in `Concept` which connect to the created `ConceptSchema`.
    - Made a data correction, so that old distributions get this `Status` field.

https://github.com/atviriduomenys/katalogas/issues/1780
Changed ENUM values for access rights:
    - Added value confidential.
    - Changed translations by the specification.

https://github.com/atviriduomenys/dvms/issues/185
Introduce scripts to export users dump and to execute SQL queries; improved anonymization.

https://github.com/atviriduomenys/spinta/issues/1415
Some additional improvements for the synchronization:
    - Added new fields for Dataset API that conforms to the UAPI: `service` & `series`.
    - Added `parent_id` to the API to be able to add hierarchy via the API.
    - Fixed a bug where the translations were not setting properly.


https://github.com/atviriduomenys/katalogas/issues/1812
Upgrade Django 3.2 -> Django 4.2:
    - Changed `delete(..)` methods to `form_valid(..)` in all `DeleteView` views.
    - Changed some model `save(..)` methods to automatically update fields, if `update_fields` are used.
    - Few smaller fixes for deprecated features.
Fix `AgreementGeneratePdf` view errors by adding missing urls to context. Also reuse `base_form.html` instead of custom one.

https://github.com/atviriduomenys/katalogas/issues/1758
Add CI/CD for checking `ruff format`. Also run `ruff format` on codebase.

https://github.com/atviriduomenys/katalogas/issues/1725
Add `applicable_legislation` field to Dataset,
Add `applicable_legislation` field to Dataset Distribution.

https://github.com/atviriduomenys/katalogas/issues/1752
Add hierarchical breadcrumbs for datasets


https://github.com/atviriduomenys/katalogas/issues/1736
Add `documentation` field to Dataset

https://github.com/atviriduomenys/katalogas/issues/1751
Add enhancements to organization, dataset, model and property page titles.

https://github.com/atviriduomenys/katalogas/issues/1762
Adds configurable RISR identifier validation to the Agency model.

https://github.com/atviriduomenys/katalogas/issues/1860
Added a github template for registering a bug in UAT testing.

https://github.com/atviriduomenys/katalogas/issues/1784
Added field "Resource type" to the resource form.

https://github.com/atviriduomenys/katalogas/issues/1840
Tests runs are improved by removing --no-migrations command which allows to catch migrations conflicts.

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/1869
Fix files not saving in Resource create/update

https://github.com/atviriduomenys/katalogas/issues/1857
Fix can changes parent Resource from Resource edit form.

https://github.com/atviriduomenys/katalogas/issues/1602
Fixed newsletter subscription.

https://github.com/atviriduomenys/katalogas/issues/1511
Added new icons for categories.

https://github.com/atviriduomenys/katalogas/issues/1511
Added an endpoint to return protected datasets for EDP.

https://github.com/atviriduomenys/katalogas/issues/1658
Changes to

v 1.1 (2025-08-22)
==================

https://github.com/atviriduomenys/katalogas/issues/1742
Add `information_system_publisher` and `information_system_creator` fields to Dataset.

https://github.com/atviriduomenys/katalogas/issues/1679
Fixed a bug where `source.type` and `origin` columns were not allowed.
Now a DSA file that has `source.type` and `origin` can be uploaded.

https://github.com/atviriduomenys/katalogas/issues/1590
Improved logging and display of changes revisions.

https://github.com/atviriduomenys/katalogas/issues/1580
Fixed a bug where the dataset codename wasn't being generated if it was left empty.

Now, if the codename is left empty, it is being autogenerated from the name.

https://github.com/atviriduomenys/katalogas/issues/1810
Docker failo ir migracijų pakeitimai testavimo aplinkoms.

https://github.com/atviriduomenys/katalogas/issues/1802
Added a multi-insert widget option to forms.

https://github.com/atviriduomenys/katalogas/issues/1595
Added explanations for the form fields (based on DCAT).

https://github.com/atviriduomenys/katalogas/issues/1719
Adds new field "Identifier" to the informational system.

https://github.com/atviriduomenys/katalogas/issues/642
Moves `temporal_resolution` and `spatial_resolution` fields to `DatasetResourceForm` form.

https://github.com/atviriduomenys/katalogas/issues/1778
Adds `temporal_resolution` and `spatial_resolution` fields to `DatasetDistribution` model.

Adds `temporal_resolution` and `spatial_resolution` fields to `DatasetDistribution` form and
its page.


https://github.com/atviriduomenys/katalogas/issues/1747
Child dataset resources

Introduce Resource abstract model as concept of understanding among tech people and requirements.

Introduce new dataset relation structure based on MP_Node side by already existing DatasetRelations,
however they are tracking different relations and are NOT THE SAME THING.
This relation will store from new scratch (not migrating any old relations).

Child resource list tab with list dataset form

Parent resource selection inside of a Dataset form in case creating from root (my organization datasets)

Create child resource under parent child resources list

Fix url design from datasets/<org-id>/* to orgs/<org-id>/datasets/*


https://github.com/atviriduomenys/katalogas/issues/1756
Adds `Dataset.information_system_type` to dataset add/change/detail pages


https://github.com/atviriduomenys/katalogas/issues/1718
Adds `Dataset.information_system_importance` to dataset add/change/detail pages


https://github.com/atviriduomenys/katalogas/issues/1679
Adds origin, source.type values to headers list for importing DSA


https://github.com/atviriduomenys/katalogas/issues/1722
Adds label and help_text for `landing_page` field if resource subclass is `Information system`

Adds `foaf:homepage` in `dcat-ap.rdf` file if resource subclass is `Information system`


https://github.com/atviriduomenys/katalogas/issues/1726
Removes `period_start`, `period_end` fields from `DatasetDistributionForm`

Adds new datetime values `temporal_start` `temporal_end` into `DatasetResourceForm`

Makes a data migration, to get all dates from `DatasetDistribution`, and add them into `Dataset`



v 1.0 (2025-03-19)
==================
https://github.com/atviriduomenys/katalogas/issues/1500
Squash migrations, link to commit, sql script, run python

Squash migrations (delete all and recreate)
Preserve only those RunPython which are creating initial data
Remove redundant compat app
Added DB migration SQL file which is required to be executed on DB of an already existing environments
After this change database dumps will be incorrect and need migration SQL script to be executed after they are applied.
