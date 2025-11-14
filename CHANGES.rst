Changes
#######

v 1.7 (unreleased)
==================

New features:

https://github.com/atviriduomenys/katalogas/issues/2067
- Part 1: Move field `other_assignee_legislations` from `Agreement` to `Project`.
- Part 2: Add assigner & assignee representatives that are displayed on the contract file.
- Part 2.1: Remove organizations as juridical entities from the list of possible entities to represent organizations in agreements.


Bugfixes:

<no ticket>
- Fix form layout, do not add a field that should be removed from the form itself on specific conditions.
- Fixed a malformed Django template variable by removing an accidental trailing `%` and properly closing the `{{ ... }}` tag.

https://github.com/atviriduomenys/katalogas/issues/2094
- Fix an issue where if `vertimas.vu.lt` is down, tests are failing on the pipelines and during local development, by introducing mocks for direct external API calls.


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
