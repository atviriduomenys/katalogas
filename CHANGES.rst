Changes
#######

v 1.25.0 (current)
==================

https://github.com/atviriduomenys/katalogas/issues/2791

- Show the "Tvarkyti IS metaduomenis" button, and open the IS metadata wizard, for every role that
  the wizard already allows: the resource coordinator, the resource manager and the superuser.
  Until now the button asked for two conditions that no single role met. The resource manager
  passed the wizard check but failed ``can_update_organization``, because updating a
  ``Representative`` is a coordinator right, so the button was never rendered for them. The
  resource coordinator and the superuser passed ``can_update_organization`` but failed the wizard
  check, which asked for the ``resource_manager`` role alone, so they were shown the "Redaguoti
  organizaciją" button instead. Nobody saw the wizard.
- The ACL of the wizard forms already granted ``CREATE_WIZARD``, ``UPDATE_WIZARD`` and
  ``DELETE_WIZARD`` to both resource roles, and ``has_perm`` already granted everything to a
  superuser, so this change opens the wizard shell to the users its forms already accepted.
- Replace ``is_organization_resource_manager`` with ``can_manage_is_metadata``, and rename the
  template flag ``is_information_system_administrator`` to ``can_manage_is_metadata``.
- The organization page now shows both buttons where both apply: a resource coordinator gets
  "Tvarkyti IS metaduomenis" and "Redaguoti organizaciją".
- Send a logged out visitor of a wizard URL to the login page again. Every wizard view overrode
  ``handle_no_permission`` unconditionally, and ``LoginRequiredMixin`` routes an anonymous request
  through that same method, so the login flow was replaced by a redirect to the organization page.
  An anonymous request now falls back to ``super().handle_no_permission()``, which keeps the
  ``next`` parameter, and an authenticated but unauthorized one still lands on the organization
  page. This matches ``OrganizationUpdateView``.
- Gather the access rules of the four wizard views into ``WizardAccessMixin``. Each of them
  carried its own copy of ``has_permission`` and ``handle_no_permission``, which is why the same
  anonymous redirect bug sat in all four. The method resolution order does not change.
- A staff account that is not a superuser stays outside the wizard shell. The team weighed
  ``is_staff``, the global manager, and settled on ``is_superuser``, which the two
  administrators who need the wizard both hold. That leaves the shell narrower than the forms it
  opens: ``determine_user_role`` maps ``is_staff`` to ``Role.GLOBAL_MANAGER``, every wizard ACL
  rule lists that role, and ``has_perm`` grants staff everything, so such a user reaches the
  forms through a direct URL but sees no button. The docstring of ``can_manage_is_metadata``
  records the decision.
- Keep the "Redaguoti organizaciją" button away from the two resource roles, so that the
  organization form is offered in one place rather than two: the wizard already opens it from
  its root node. The resource coordinator keeps the right itself and still edits the
  organization there. A new ``can_edit_organization_details`` decides the button, and hides it
  only when every role the user holds on that organization is a resource one, so a user who
  also holds an open data role there keeps what that role gave them. The open data roles keep
  exactly the access they had, a superuser keeps both buttons, and no ACL rule moves.
- Stop the wizard asking for the organization form on behalf of a user who may not edit the
  organization. The pane loaded ``organization-change`` on open, and the root node of the tree
  asked for it again on click, but ``Action.UPDATE`` on an organization belongs to the
  coordinators alone. A resource manager therefore got a redirect, which HTMX swapped into the
  pane as a whole organization page. The wizard now sends that request only for a user who holds
  the right, and shows a short note in its place for everyone else. That note keys off the
  organization node, because ``x-init`` selects that node as soon as Alpine starts, and it lives
  outside ``#wizard-main-pane``, because an HTMX swap replaces everything inside that element and
  would carry the note away with the first child form. The pane itself hides while the
  organization node is the selected one, and the root row still calls ``select(...)``, so a
  resource manager can leave a child form and come back to the organization state. The bug
  predates this change, but until now no resource manager had a button to reach it.



v 1.24.0 (2026-08-21)
==================

https://github.com/atviriduomenys/katalogas/issues/2785

- Bump `spinta` version `1.0.0` -> `1.1.0`.
- Bump cryptography from 48.0.1 to 50.0.0 (CVE-2026-69247).
- Bump sqlparse from 0.5.5 to 0.6.0.
- Bump aiohttp from 3.14.1 to 3.14.3.
- Bump the npm package fast-uri from 3.1.4 to 3.1.5.
- Bump the npm package nanoid from 3.3.16 to 3.3.18.
- Drop eight orphan packages from ``poetry.lock``: ``gprof2dot``, ``jsonschema``,
  ``jsonschema-specifications``, ``jsonsir``, ``pyinstrument``, ``pytest-profiling``, ``snakeviz``
  and ``tornado``.

The open Django alerts stay open. The fix for them is Django 5.2, and the team plans that upgrade
as a separate task: https://github.com/atviriduomenys/katalogas/issues/1826

https://github.com/atviriduomenys/katalogas/issues/2762

- Bump gunicorn 20.1.0 -> 23.0.0: setuptools 83 removed pkg_resources

https://github.com/atviriduomenys/katalogas/issues/2771

- Hide the deprecated "API specifikacijos formatas" (``endpoint_description_type``) field from
  service forms, detail pages, and administration while preserving existing database values and
  API output.

https://github.com/atviriduomenys/katalogas/issues/2722

- Make the "API specifikacija" (``dcat:endpointDescription``) field optional in the data service
  form. DCAT-AP and DCAT-AP-LT mark this property as recommended, not mandatory, so the form no
  longer demands an agent or an API specification. The mandatory ``dcat:endpointURL`` rule stays.

https://github.com/atviriduomenys/katalogas/issues/2723

- Accept links that point to an internal host. Django's ``URLValidator`` demands a public DNS
  name, so it refused ``http://ext-db:8888/orawsv/...``. A new ``validate_absolute_uri``
  validator asks only for an ``http``, ``https``, ``ftp`` or ``ftps`` scheme and a host, so a
  host name without a dot, a port and an IP address are all permitted. Free text, a missing
  scheme and ``javascript:`` stay refused, so the RDF ``rdf:resource`` output stays well formed.
- Apply the new validator to every link field a user fills in: ``access_url`` and
  ``download_url`` on a distribution, ``endpoint_url``, ``endpoint_description``,
  ``landing_page``, ``information_system_assessment_url`` and ``rights_relation`` on a data
  resource, and the link list fields (documentation, legal basis, service quality, qualified
  relation). This covers the old forms and the new DCAT forms.
- Raise ``endpoint_description`` from 200 to 512 characters, the same limit as ``endpoint_url``.
- The required fields do not change. DCAT-AP marks ``dcat:accessURL`` and ``dcat:endpointURL``
  as mandatory.
- A link with no scheme is now refused. Before this change ``forms.URLField`` silently made
  ``www.example.com`` into ``http://www.example.com``. Give the full link.

https://github.com/atviriduomenys/katalogas/issues/2746

- Render the dataset list without a query for each row. The view now batches the likes, the hits, the
  group titles and the data service formats once for each page. A list of 20 datasets that serve a
  data service made 172 queries and now makes 20.
- Stop the dataset list and the landing page writing to the database. The ``get_hit_count`` tag
  created a row for every dataset that nobody had opened yet, so a GET inserted rows on every render.
- Read the titles of the tags facet in one query. The sidebar shows up to 50 tags, and the list made
  one query for each of them.
- Read the areas of management of the organization list in one query.
- Read the icon of the dataset list in one query for each page. ``get_icon`` asked the database for
  the root of every category of every row, so a page of 20 datasets made up to 26 category queries.
  The query count of the list is now flat: 51 -> 28 queries for a page of the production catalogue.
- Read the distributions of a dataset once in ``distinct_formats``. The project datasets page and the
  landing page read them and every format twice.
- Cache the navigation menu for each language. A change to a page clears the cache after the
  transaction commits. The cache lasts 60 seconds, because a page move sends no signal.
- Fix the dataset list pushing its cards past the right edge of the page.

https://github.com/atviriduomenys/katalogas/issues/1825

- Remove Elasticsearch and ``django-haystack``. Use PostgreSQL for search.
- Add the ``vitrina.search`` app.
- Replace the ``rebuild_index`` deploy step with ``rebuild_search``.
- Replace the nightly ``update_index`` job in ``cronjobs/crontab`` with ``rebuild_search``. Install
  the new crontab on the server together with this release.
- Drop the ``SEARCH_URL`` and ``ELASTIC_FACET_SIZE`` settings, and the Elasticsearch service from
  the compose files and from the test workflow.
- Sort the request list by the title of the request.
- End every list order with the primary key, so a page cannot repeat or drop a row.
- Match a search word anywhere in the text, not only at the start of a word. A search now finds
  more datasets than before.


v 1.23.0 (2026-08-03)
==================

https://github.com/atviriduomenys/katalogas/issues/2755

- Update ``cryptography`` to 48.0.1. The wheels before this version bundle a vulnerable OpenSSL
  (GHSA-537c-gmf6-5ccf).
- Update ``setuptools`` to 83.0.0 (GHSA-h35f-9h28-mq5c).
- Update ``weasyprint`` to 69.0. Version 68.1 and earlier build CSS from an unescaped ``background``
  attribute (GHSA-jhhc-3hcp-qhm5). The application never turns on ``presentational_hints``, so the
  defect was not reachable.
- Update ``pytest`` to 9 and ``pytest-cov`` to 7 (GHSA-6w46-j5rx-g56g).
- Update the webpack build dependencies to clear 11 npm alerts: ``fast-uri``, ``immutable``,
  ``@babel/core``, ``@babel/plugin-transform-modules-systemjs``, ``postcss``, ``picomatch``,
  ``serialize-javascript`` and ``terser-webpack-plugin``. All of them are build-time only.
- Remove 9 unused Python dependencies: ``c3pyo``, ``django-braces``, ``django-chartjs``,
  ``django-formtools``, ``asciidoc``, ``pgpy``, ``docx``, ``python-docx`` and ``resource``.
  The ``resource`` package installs no module at all. The ``docx`` package is abandoned and
  collides with ``python-docx`` on the ``docx`` module name. ``django-formtools`` stays in the
  lock file because ``django-cms`` needs it. With their own dependencies, this drops 16 packages.
- Move ``freezegun`` and ``requests-mock`` to the dev group. The tests are their only user.

https://github.com/atviriduomenys/katalogas/issues/2753

- Filter ``dcat:servesDataset`` links in the EDP DCAT-AP export (`/edp/dcat-ap.rdf` and
  `/edp/dcat-ap-restricted.rdf`). A data service listed the URL of every related dataset, also of
  non-public and deleted ones, which the European Data Portal turned into empty catalogue records.
  A service now links only to datasets that the export publishes.

https://github.com/atviriduomenys/dvms/issues/515

- Replace unsanitized ``mark_safe`` with ``format_html`` in admin display methods and form labels
  (classifiers, datasets, orgs, resources, statistics, users).
- Rewrite version metadata labels in ``Dataset.get_metadata_objects_for_version`` to use ``format_html``
  instead of manually escaped f-strings.
- Sanitize user HTML in comments before rendering.
- Validate URL scheme in links to prevent ``javascript:`` XSS.
- Fix unquoted ``href`` attributes.
- Sanitize learning material description instead of rendering it raw.
- Escape ``<``, ``>`` and ``&`` in JSON-LD output so a dataset title cannot break out of the
  ``<script>`` block on the dataset detail page.
- Render chart data with ``json_script`` instead of ``|safe`` on statistics, jurisdiction,
  publication and user charts, so organisation and jurisdiction names cannot break out of the
  ``<script>`` block.
- Render the UML diagram mermaid source with ``json_script``.
- Add tests for JSON-LD escaping, learning material sanitization and metadata label escaping.

<No ticket>
- Remove unused files: stale SQL dumps in ``resources/`` (``adp-dev.sql``, ``adp-dev-fresh.sql``, ``adp-pg.sql``, ``migrations_squash.sql``) and ``uml.drawio.svg``.
- Remove unused ``BASE_DB_PATH`` setting (only referenced the removed ``adp-pg.sql``).
- Clean up README.rst
- Fix webpack bundle output path to ``vitrina/static`` (was writing to an unserved root ``static/``).

<No ticket>
Adjustments to the DCAT forms (through the wizard);
- New DCAT form button and access forbidden, depending on the role;
- Adjustments to DCAT displays (separation of read-only fields, hidden elements, adjustments, etc.);
- Bug fixes;


https://github.com/atviriduomenys/katalogas/issues/2716

- Separate data freshness from metadata freshness for dataset distributions.

https://github.com/atviriduomenys/katalogas/issues/2719

- Fix data download in the structure "Duomenys" view producing a broken Spinta request. RQL query
  fragments (``select(...)``, ``sort(...)``, filters) are value-less params, not ``key=value`` pairs;
  the download path serialized them with a trailing ``=``, which Spinta's RQL parser rejected with
  ``UnexpectedToken``. Both the ``downloadData()`` template helper and ``_build_spinta_download_url``
  now preserve the RQL query verbatim.

https://github.com/atviriduomenys/katalogas/issues/2267

- Fix dataset distribution CSV preview: auto-detect the delimiter and render data rows correctly (empty cells no longer break the preview).
- Add a fullscreen toggle to the distribution preview modal.
- Preview reads only the requested number of rows (``rows`` query parameter) instead of the whole file, avoiding memory issues on large distributions.

https://github.com/atviriduomenys/katalogas/issues/2585

- Fix HTTP 500 error when registering or logging in via VIISP.
- Return a graceful VIISP API error page instead of a 500 when the VIISP signing keys are missing, the login ticket is absent, or the VIISP SOAP call fails (including proxy connection/timeout errors).
- Reject VIISP login when the supplied personal code does not match the linked account instead of logging the user in.
- Scope the linked-account lookup to the VIISP provider and guard a missing stored personal code, so a user with a non-VIISP social account (e.g. Google) or a legacy VIISP account no longer triggers a 500.
- Only persist ``is_viisp_login`` / company code after authentication succeeds, so a rejected login no longer leaves those fields updated.
- Guard the account-merge token decryption against tampered or malformed tokens, and serialise the confirmation token as a keyed structure so account merges decode correctly when a company code is present.
- Compare emails case-insensitively during the token login flow, and log VIISP SOAP failures.

<No Ticket>

- Add a Content Security Policy via ``django-csp``. Directives with no breakage trade-off for this site are locked
  down (``default-src 'self'``, ``object-src 'none'``, ``base-uri 'self'``, ``frame-ancestors 'self'``,
  ``form-action 'self'``), while ``script-src`` still allows ``'unsafe-inline'``/``'unsafe-eval'`` and
  ``style-src`` still allows ``'unsafe-inline'`` because the templates rely on inline scripts, event handlers and styles.
  Tightening those is deferred to a later nonce/refactor pass. Also switch the Leaflet OpenStreetMap tile URLs from ``http://`` to
  ``https://`` (they were mixed content on an HTTPS page).

https://github.com/atviriduomenys/katalogas/issues/2632

- Prefix log records with the authenticated user's ID (``user ID: <id>``), falling back to ``anonymous`` for unauthenticated requests and background tasks.
- Add a request-scoped logging context (``vitrina.log_context``) and ``LogContextMiddleware`` so additional details can be surfaced in logs later.
DVMS-514

- Fix insufficient file upload validation (CWE-434): block ``.xhtml`` (``application/xhtml+xml``) uploads,
  which previously bypassed the HTML deny rule and allowed stored XSS / phishing pages to be served from the media URL.

https://github.com/atviriduomenys/katalogas/issues/2713

- Deployment banner messages are now edited with a rich-text (CKEditor) editor, so a link can be placed behind a word instead of showing the raw URL.
- Add a "publish" flag to deployment messages: mark which single message is shown on the portal without deleting the older ones, so a message can be kept as a template.
- Add a deployment message type (informational, warning, critical); each is shown with its own colour, icon and left-border accent.

https://github.com/atviriduomenys/katalogas/issues/2736

- ``Dataset.is_public`` now defaults to ``False``, so the "Duomenų išteklius viešinamas" checkbox is
  unchecked in all resource creation forms.
- Access rights default to "CONFIDENTIAL" instead of "PUBLIC" when creating a dataset or a data
  service.


v 1.22.0 (2026-06-30)
==================

https://github.com/atviriduomenys/katalogas/pull/2707

- Fix EDP DCAT-AP harvesting (`/edp/dcat-ap.rdf` and `/edp/dcat-ap-restricted.rdf`) exposing datasets that should not be published.

https://github.com/atviriduomenys/katalogas/pull/2650

- Add single-page DCAT wizard for creating datasets and dataset distributions, accessible from the Organisation detail page; supports non-public resources and exposes additional DCAT-AP fields not available in the standard dataset creation flow.
- Wizard displays the full dataset parent-child structure (Information System → Service → Dataset → Distribution) in a sidebar tree; datasets created via the wizard remain fully compatible with existing dataset views and editing flows.
- Adds new `DCATResourceSubclass.IS_PUBLIC_SERVICE` type. It's only possible to create it via wizard forms
- Adds new `Contact` creation: creating contacts not related to user or organization. Form is only accessible with wizard permissions
- Add new classifier models with corresponding migrations:
    - `classifiers.Rule`
    - `classifiers.ServiceQualityPage`
    - `classifiers.ProvenanceStatement`
    - `classifiers.Activity`
    - `classifiers.FormFieldText`
    - `classifiers.SpatialCoverage`
    - `datasets.DatasetQualifiedRelation`
    - `datasets.QualityAnnotationBody`
    - `datasets.QualityAnnotation`
    - `datasets.MeasurementTitle`
    - `datasets.MeasurementTitleItem`
    - `datasets.Measurement`
    - `datasets.QualityMeasurement`
    - `resources.MediaType`
- Add new fields to exising models (relations to new models + non-relation fields) needed to save DCAT related data.
- Model `classifiers.FormFieldText` allows changing label and/or help text for any wizard form field. With small development same model can be used with any other form if needed.
- Add `wizard.js` webpack entry point driving the wizard UI interactions.
- Move webpack css building step to run before before collectstatic. Previously it copied older css files.


https://github.com/atviriduomenys/katalogas/issues/2660

- Fix a bug where comment notification emails were still sent to users who had been removed from an organization's
  representatives or whose accounts were deactivated.
- Remove a representative's auto-created subscription when they are deleted.

<No Ticket>

- Update ``django-allauth`` to 65.18.x. The new version reverses ``account_login`` (unguarded) while rendering the
  email-confirmation page; since this project uses VIISP with a custom login view and never registered that URL name,
  this broke ``test_email_confirmation_after_sign_up`` with ``NoReverseMatch``. Register an ``account_login`` URL alias
  that redirects to the existing ``login`` view (preserving the ``?next=`` parameter) to restore compatibility.

https://github.com/atviriduomenys/katalogas/issues/1585

- The dataset list download counter (tooltip "Atsisiuntimų skaičius") now counts actual downloads from the portal instead of external get.data.gov.lt API request statistics.
- Fix statistics charts collapsing to one dataset per period; dataset-count bars and time charts now show real counts.
- Fix the status chart double-counting datasets with coinciding comment times.
- Count datasets without a status comment in the status chart, at their published date.
- Include datasets outside the visible time window in dataset-count bar totals.
- Show all values in sidebar filters and statistics charts instead of only the top 50; make the facet size configurable via ``ELASTIC_FACET_SIZE``.
- Collect ``DatasetStats`` daily via a Celery task instead of a manual script.

https://github.com/atviriduomenys/katalogas/issues/2643

- Fix a bug where two different datasets in the same organization could have the same name.

https://github.com/atviriduomenys/katalogas/issues/2671

- Add a "Teminiai duomenų ištekliai" (thematic data resources) section to the landing page, below the main categories.
- Add a ``thematic`` flag to ``Category`` so flagged categories render in the new section instead of the main categories block.
- Add a "Sveikatos duomenys" tile linking to the external health data portal; it opens in a new tab and is marked with an external-link icon.

https://github.com/atviriduomenys/katalogas/issues/2629

- Fix property-level enum `ref` export: structure export now always outputs an empty `ref` for enums declared at the property dimension.
- Fix property-level enum creation via form: `Enum` objects created through the UI no longer inherit the property name as `enum.name`.
- Add import validation: importing a CSV manifest with a non-empty `ref` on a property-level enum row now produces a structure error comment and silently sets the `ref` to an empty string.

https://github.com/atviriduomenys/katalogas/issues/2624

- Remove auto-stripping of quotes from string enum values in the form's initial data
- Remove auto-wrapping of unquoted string values in clean_value()
- Remove synchronous type checking (TypeCheckerError) from clean_value()
- Fix edge case in CSV import: when prepare is empty and source is also empty, no longer produces "" as a valid quoted value

https://github.com/atviriduomenys/katalogas/issues/2566

- Route per-user permission filtering and the manager-dataset list filter through Elasticsearch ``terms`` queries (via a custom Haystack backend) so large primary-key sets no longer expand into Lucene boolean OR clauses. Fixes intermittent ``too_many_clauses`` 400s on ``/datasets/manager`` and any authenticated dataset list whose user has many representations.


https://github.com/atviriduomenys/katalogas/issues/2588

- Significantly speed up the statistics pages (dataset status, organization, category, jurisdiction, publication and year/quarter) by removing per-time-bucket N+1 queries; aggregations are now computed once and reused.
- Add database indexes on ``dataset_statistic.dataset_id`` and ``model_download_statistic.model``.
- Raise the Haystack Elasticsearch iterator batch size (env-configurable via ``HAYSTACK_ITERATOR_LOAD_PER_QUERY``) to cut Elasticsearch round-trips when loading statistics pages.

https://github.com/atviriduomenys/katalogas/issues/2652

- Adjust HTML form to display the edit/delete buttons for enum values even if the `enum.prepare` is not set.

https://github.com/atviriduomenys/katalogas/issues/2642

- Fix dataset description rendering: a URL in the description is no longer linkified twice.
- Truncate long description links via CSS (``text-overflow: ellipsis``) instead, keeping the full URL in ``href``.

<No Ticket>

- Fix the comment reply button doing nothing: ``comments.js`` was included twice on the dataset and request detail pages, binding the reply-toggle handler twice so its non-idempotent ``classList.toggle`` cancelled itself out. The ``{% comments %}`` component now provides the script exactly once.
- Remove the dead jQuery ``.show-reply-form`` handler from the comments component.

v 1.21.0 (2026-05-18)
==================

https://github.com/atviriduomenys/katalogas/issues/2563

- Add UML class-diagram generation and viewing for dataset structures, rendered with Mermaid.
- Add `UMLDiagram` model that persists the generated mermaid source, generation status (`OUTDATED`, `PENDING`, `UP_TO_DATE`, `FAILED`) and the error message for failed generations.
- Generate diagrams asynchronously via a new `update_uml_diagram` Celery task; on failure, persist the exception message to `UMLDiagram.error_message` so it can be surfaced in the UI.
- Auto-invalidate diagrams via `post_save` / `post_delete` signals on structure-related models, bumping a version counter so the next view request triggers regeneration.
- Add `DatasetStructureUMLView` with embedded and `?expanded` fullscreen variants.
- Add `.mmd` (server-side) and `.svg` (client-side from the rendered SVG) download options.

https://github.com/atviriduomenys/katalogas/issues/2485

- Strip leading newline from DCAT-AP RDF response
- Sanitize whitespace URIs in DCAT-AP RDF export

https://github.com/atviriduomenys/katalogas/issues/2260

- Fix SPINTA data_last_updated to use :changes/-1 and aggregate all dataset models

Bug fixes:

https://github.com/atviriduomenys/katalogas/issues/2620

 - Fixed an issue where base models were not exported as dependencies from another manifest, which also propagated to it not being displayed on UML diagrams.

https://github.com/atviriduomenys/katalogas/issues/2607

 - Fixed an issue where importing a structure with name errors deletes the draft version.

v 1.20.0 (2026-05-12)
==================

https://github.com/atviriduomenys/spinta/issues/1874

- Add an additional error message indicating, that the external reference is not found, during manifest import.

https://github.com/atviriduomenys/katalogas/issues/2589

- Sets Django Tagulous to use Django vendor Select2 css/js files to match Select2 versions
- Adds select2 css fixes to `base_form.html` so it can be used across all forms
- Removes any duplicated custom css related to Select2 from specific forms after global fixes were introduced

https://github.com/atviriduomenys/katalogas/issues/2595

- Overrides `python manage.py makemessages` command to automatically include `-l en -l lt --no-location` if not provided
- Overrides `python manage.py compilemessages` command to automatically include `-l en -l lt ` if not provided
- Change all Lithuanian translation of "Distribution" to single term - "Pateiktis" (in line with DCAT-AP-LT)

v 1.19.0 (2026-04-29)
==================

Improvements:

- Adds `dcat` app. It will be used for new Dataset CRUD that only changes non-public datasets.
- Adds variable `Agency.RISR_CODE = "risr"` and uses it throughout the code.
- Moves some code from `Dataset` form and view to separate methods so that it can be reused. It's mostly copy-paste code

Bug fixes:

https://github.com/atviriduomenys/dvms/issues/549
https://github.com/atviriduomenys/katalogas/issues/2558

- Added an access check, which makes sure that given roles are from MANAGER_ROLES, else skips the iteration.
- Removed `can_update_publishers` permission check from HTML forms and the corresponding view.
- Removed the early return that was blocking non-superusers from updating Organizations as Representatives.

v 1.18.0 (2026-04-15)
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

https://github.com/atviriduomenys/katalogas/issues/2530

- Remove Teritorija, Periodo pradžia, Periodo pabaiga columns from distribution table

https://github.com/atviriduomenys/katalogas/issues/2546

- Allow uploading ADOC files for `PartnerRegisterForm`.

https://github.com/atviriduomenys/katalogas/issues/2260

- Add `data_last_updated` field to `DatasetDistribution` model.
- Periodic Celery task for SPINTA distribution date updates.

Bug fixes:

<No Ticket>

- Fixing invalid template tags.

<No Ticket>
- Fixed duplicate comment creation on request detail page.

<No Ticket>
- Add djangocms-file, djangocms-picture, and djangocms-link plugins.

https://github.com/atviriduomenys/katalogas/issues/2538

- Fix RDF export validation errors:
    - Wrap ``dct:RightsStatement`` text content in ``rdfs:label`` element.
    - Guard ``dct:issued`` date fields against empty values.
    - Encode unwise URI characters (``{``, ``}``, ``\``, etc.) in RDF resource attributes.

https://github.com/atviriduomenys/katalogas/issues/2537

- Fix Spinta download URL in Data tab to use `/:format/<fmt>` endpoint instead of query parameter format.

https://github.com/atviriduomenys/katalogas/issues/2541

- Added `ConceptSchema` admin action that downloads SKOS `Concept` objects from `ConceptSchema.uri`,
  if uri is valid URI to EU Vocabulary Authority Tables.

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
