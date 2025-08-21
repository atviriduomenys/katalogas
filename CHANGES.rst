Changes
#######
2025-08-20
=======
https://github.com/atviriduomenys/katalogas/pull/1801
Child dataset resources

Introduce Resource abstract model as concept of understanding among tech people and requirements.

Introduce new dataset relation structure based on MP_Node side by already existing DatasetRelations,
however they are tracking different relations and are NOT THE SAME THING.
This relation will store from new scratch (not migrating any old relations).

Child resource list tab with list dataset form

Parent resource selection inside of a Dataset form in case creating from root (my organization datasets)

Create child resource under parent child resources list

Fix url design from datasets/<org-id>/* to orgs/<org-id>/datasets/*


2025-08-20
==========
https://github.com/atviriduomenys/katalogas/pull/1796
Adds `Dataset.information_system_type` to dataset add/change/detail pages


2025-03-19
==========
https://github.com/atviriduomenys/katalogas/pull/1501
Squash migrations, link to commit, sql script, run python

Squash migrations (delete all and recreate)
Preserve only those RunPython which are creating initial data
Remove redundant compat app
Added DB migration SQL file which is required to be executed on DB of an already existing environments
After this change database dumps will be incorrect and need migration SQL script to be executed after they are applied.