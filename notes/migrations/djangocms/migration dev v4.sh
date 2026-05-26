#!/usr/bin/zsh

source dist/utils.sh

###############################################
# Clean DEV environment
###############################################
# venv
clean_pyenv
install_library
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
python manage.py migrate djangocms_stories

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ #
# iki čia padaryta
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ #

#################################################
python manage.py migrate djangocms_alias
python manage.py migrate djangocms_versioning
python -m manage create_versions --userid 1
#################################################

