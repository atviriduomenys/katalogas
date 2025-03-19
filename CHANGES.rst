Changes
#######

2025-03-19
=======
https://github.com/atviriduomenys/katalogas/pull/1501
Squash migrations, link to commit, sql script, run python

Squash migrations (delete all and recreate)
Preserve only those RunPython which are creating initial data
Remove redundant compat app
Added DB migration SQL file which is required to be executed on DB of an already existing environments
After this change database dumps will be incorrect and need migration SQL script to be executed after they are applied.