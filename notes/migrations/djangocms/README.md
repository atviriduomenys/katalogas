# django-cms 3.11 → 5.0 migracija

Baigta. Vienkartinė mechanika — būsenos patikra paleidžiant konteinerį, blog → stories suderinamumo
programa, migracijų veidrodis — išimta #2795.

Liko viena nuolatinė apsauga: `migrate` atsisako dirbti su baze, kurioje dar yra `cms_title` — t. y. su
cms 3 schema. Taip nutiktų atkūrus backup'ą iš prieš atnaujinimą aplinkoje, kuri jau sukasi ant cms 5
(`vitrina/cms/apps.py`, `_refuse_cms3_schema`).

Receptas, diegimo instrukcija, A/B patikros įrankiai ir pirmojo bandymo darbo žurnalas liko git
istorijoje (PR #2646). Surasti:

    git log -- notes/migrations/djangocms/diegimas.md
