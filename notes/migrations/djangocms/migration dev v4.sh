#!/usr/bin/zsh

source notes/migrations/djangocms/utils.sh

###############################################
# Clean DEV environment
###############################################
# venv
clean_pyenv
poetry_install_all
# DB
clean_db
git checkout G1
python manage.py makemigrations
python manage.py migrate
create_superuser
##############################################
# Integration tests
#############################################
git cherry-pick 5ca3a297e95eff905010e1b3d1d10264508f2852
pip install playwright
playwright install chromium
python scripts/tests/create_organisation.py
##############################################
dump_db_GPX GP1dev
ls -altr dist/backup/20260519
# or restore DB from GP1dev1
restore_db_GPX GP1dev
##################################################
# Migrate to djangocms-text==0.9.2
pip install djangocms-text==0.9.2
sed -i 's/djangocms_text_ckeditor/djangocms_text/' vitrina/settings.py
python manage.py migrate
dump_db_GPX GP2dev
###############################################
# Migrate to djangocms-blog==2.0.9 (from 1.2.3)
###############################################
pip install django-meta==2.3.0
pip install djangocms-blog==2.0.0
python manage.py makemigrations --merge
python manage.py migrate
# Tvarka, veikia
pip install djangocms-blog==2.0.9
python manage.py makemigrations --merge
python manage.py migrate
# Tvarka, veikia. No problems
dump_db_GPX GP3dev
# or restore DB from GP1dev1
restore_db_GPX GP3dev
###############################################
pip install pipdeptree
pipdeptree > /tmp/pdt3
ck /tmp/pdt3
pip freeze > /tmp/requirements_GP3.txt
cat /tmp/requirements_GP3.txt | grep -E "link|meta|cms"
###############################################
# dar reikalingin djangocms-link==5.1.1 ir djangocms-text-ckeditor==5.1.7
###############################################
# čia pataisytas pyproject.toml ir pyproject.lock
# iki čia padaryta


###############################################
# Migrate to django-cms 4.1.11
###############################################
sed -i '/aldryn_apphooks_config/d' vitrina/settings.py
pip install django-cms==4.1.11
pip install djangocms-versioning==2.5.1
pip install djangocms-alias==2.0.5
pip install git+https://github.com/django-cms/djangocms-4-migration
# 
cat <<EOF >> vitrina/settings.py

INSTALLED_APPS += [
    "djangocms_4_migration",
    "djangocms_versioning",
    "djangocms_alias",
]
CMS_CONFIRM_VERSION4 = True
CMS_MIGRATION_USER_ID = 1
EOF

################################################# 
python manage.py cms4_migration
# run scripts to check and to remove duplicates
python manage.py makemigrations
python manage.py migrate
git checkout 8b1fa5f546a8049 vitrina/templatetags/navigation_tags.py vitrina/cms/templates/vitrina/cms/post_list.html
#################################################
# Migrate to djangocms-stories
#################################################
pip uninstall djangocms-blog

#|    /home/oa/.pyenv/versions/3.12.8/envs/kt312b/lib/python3.12/site-packages/djangocms_blog/migrations/0040_alter_authorentriesplugin_cmsplugin_ptr_and_more.py
#|    /home/oa/.pyenv/versions/3.12.8/envs/kt312b/lib/python3.12/site-packages/djangocms_blog/migrations/0042_merge_20260525_2030.py
#|    /home/oa/.pyenv/versions/3.12.8/envs/kt312b/lib/python3.12/site-packages/djangocms_blog/migrations/0043_merge_20260525_2034.py

pip install djangocms-stories
cat <<EOF >> vitrina/settings.py

INSTALLED_APPS += [
    "djangocms_stories",
]
EOF
git cherry-pick c707845e1e9d5db5f
git commit -m "migration to djangocms-stories 1"
git add .
git commit -m "migration plan v4"
git cherry-pick e26df61ee9c6fa129
git commit -a --message 'migration to djangocms-stories 2'
git cherry-pick -n 9ba5966b2946f674e
git checkout 50efa00491c011fbf vitrina/cms/templates/vitrina/cms/post_detail.html
python manage.py makemigrations --merge
python manage.py migrate djangocms_blog
python manage.py migrate djangocms_text
python manage.py migrate djangocms_stories

# ● Update(~/.pyenv/versions/kt312b/lib/python3.12/site-packages/djangocms_blog/migrations/0040_alter_authorentriesplugin_cmsplugin_ptr_and_more.py)
#  ⎿  Removed 7 lines
#      86                  auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
#      87              ),
#      88          ),
#      89 -        migrations.AlterField(                                                                                                                             
#      90 -            model_name="posttranslation",                                                                                                                  
#      91 -            name="id",                                                                                                                                     
#      92 -            field=models.BigAutoField(                                                                                                                     
#      93 -                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"                                                                    
#      94 -            ),                                                                                                                                             
#      95 -        ),                                                                                                                                                 
#      89      ]
sed -i '/djangocms_blog/d' vitrina/settings.py
echo 'DJANGOCMS_VERSIONING_USERNAME_FIELD = "email"' >> vitrina/settings.py
git commit -m "migration to djangocms-stories 3"
git add  .gitignore
git commit -m "gitignore __pycache__"
git add .
git commit -m "migration plan v4"
# sukurti failiukai:
# dist/history_2026-05-26_19-22.txt
# dist/requirements-2026-05-26_19-24.txt
pip install django-cms==5.0.0
python manage.py makemigrations --merge
python manage.py migrate
git checkout b123e9efe76f67ce vitrina/templatetags/navigation_tags.py
pip install django-cms\>5.0.0
python manage.py makemigrations 
python manage.py migrate

#

#|  Summary of the root cause and fix:
#|
#|  The 0037_alter_cmsplugin_id_... and 0038_alter_cmsplugin_id_... migrations were locally generated (2026-05-25) to convert CMS model IDs to BigAutoField and back. Both
#|  included an AlterField on treenode.id.
#|
#|  The problem: django-cms 5.0.7 already has an upstream migration pair (0037_merge_page_treenode → 0038_alter_page_site) that deletes the TreeNode model. When Django
#|  reconstructs migration state, it processes the merge branch first (forced by the 0039–0041 dependency chain), which deletes TreeNode. Then when it processes the
#|  BigAutoField branch's AlterField on treenode, the model no longer exists in the state → KeyError.
#|
#|  Fix: Removed the treenode AlterField entries from both local migrations in the installed CMS package. Since TreeNode gets deleted by the upstream migration, altering its
#|  id is pointless and was causing the state reconstruction to crash.
#|

#############################################
# djangocms-alias
#############################################
pip install djangocms-alias\>3.0.0
python manage.py makemigrations --merge
python manage.py makemigrations 
python manage.py migrate
# updated pyproject.toml and poetry.lock
dump_db_GPX GP4dev
ls -altr dist/backup/20260519
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ #
# iki čia padaryta                 #
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ #

