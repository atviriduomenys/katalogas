# django-cms 3.10 → 5.0: patikrintas atnaujinimo receptas

> **Statusas:** patikrinta gyvai 2026-08-05 ant **anonimizuotos prod kopijos** (`adp-prod-2026-03-19`,
> 39 MB → 381 MB, 59 CMS puslapiai, 47 naujienos, 154 plugin'ai).
> **Susiję:** DAS-428 · #1824 · PR #2646 · [diegimas](diegimas.md) · [katalogo aprašas](README.md)
>
> Rašyta 2026-08-05, kai #2646 dar bandė šokti į 5.0 vienu žingsniu. Nuo tada #2646 šį skaidymą
> įgyvendina: 5.0 leidimo image'as ir atskiras 4.1 migracijos įrankis, o `scripts/migrate_djangocms.sh`
> atsisako migruoti bazę, kuri dar turi `cms_title`, t. y. nepraėjo 1 etapo. Vietos, aprašančios
> tuometinę #2646 būseną, pažymėtos; lentelių stulpelis „#2646" rodo, kas jau padaryta (2026-09).

## Esmė: atnaujinimas yra TRIJŲ etapų, ne vieno

Į 5.0 iš 3.10 vienu šuoliu nešokama. 2026-08 PR #2646 bandė būtent tai ir todėl lūžo ties
`cms.0037_merge_page_treenode` (`duplicate key ... cms_page_path_key` arba `AssertionError`).

**Kodėl.** CMS 3 kiekvienas puslapis egzistuoja dviem eilutėm (draft + public), bet abi dalijasi
**vienu** `cms_treenode`. `cms.0031_remove_fields` išmeta `publisher_is_draft`, o `cms.0037` tada
kopijuoja `node.path` į kiekvieną puslapį, kur `Page.path` yra `unique`. Prod duomenyse tai buvo
**30 mazgų, iš jų 29 su dviem puslapiais** — 29 garantuoti susidūrimai.

Struktūrinis skirtumas, kurį reikia turėti galvoje:

| | cms 4.1.11 | cms 5.0.x |
|---|---|---|
| `TreeNode` | `class TreeNode(MP_Node)`, `Page.node` → FK | **nebėra** |
| `Page` | `class Page(models.Model)` | `class Page(MP_Node)` |
| Migracijos | baigiasi ties `0036` | `0037_merge_page_treenode` |

Tad 4.1 etape `.node` kodas dar **privalo veikti**, o 5.0 — jau ne. Tuometinis #2646 sudėjo abiejų
etapų kodą į vieną šuolį; dabar 4.1 etapas vyksta atskirame įrankio image'e, kuris svetainės nekelia.

## Prieš pradedant

- **Rollback nėra.** `djangocms-4-migration` README: nepavykus migracijai atsukti negalima, tik
  atkurti iš backup'o. Prod'ui → turinio įšaldymo langas privalomas.
- Dirbama su **anonimizuota** prod kopija (`scripts/anonymize.py`), ne su test duomenimis:
  migracijos lūžta ant senienų, kurių test bazėje nėra.
- Kontrolinis `pg_dump` po kiekvieno etapo — kitaip klaida gale reiškia viską iš pradžių.

## 1 etapas: 3.10 → 4.1 (+ blog → stories)

### Priklausomybės

```toml
django-cms = ">=4.1,<5"
djangocms-versioning = "^2.5.1"
djangocms-alias = "<3"            # >=3 nesuderinamas su migracijos paketu
djangocms-stories = "^0.9.1"
djangocms-text = "^0.9.2"
django-filer = "^3.4.4"
django-meta = "~2.5.1"
dj-hitcount = "^2.0.0"
django-taggit-autosuggest = "*"   # buvo djangocms-blog tranzityvinė
aldryn-apphooks-config = "*"      # reikalinga blog shim modeliams
djangocms-4-migration = {git = "https://github.com/django-cms/djangocms-4-migration.git", rev = "1b2037c9521cf32111bcf36a6bdf5cb784bff233"}
```

#2646 iš jų jau turi `djangocms-versioning`, `djangocms-stories` (prikaltas `0.9.3`), `djangocms-text`,
`django-meta ~2.5.1`, `django-taggit-autosuggest` ir `aldryn-apphooks-config`. 4.1 įrankiui lieka
`django-cms >=4.1,<5`, `djangocms-alias <3` ir `djangocms-4-migration` iš git. Leidimas naudoja
`django-hitcount`, ne `dj-hitcount`.

`djangocms-blog` **išimamas** iš priklausomybių: `djangocms-stories` atsineša savo `djangocms_blog`
shim'ą su migracijomis iki `0052`. To reikia, nes stories `0002` turi kietą patikrą:

```python
required_migration = ("djangocms_blog", "0051_alter_blogconfig_type_and_more")
```

o `djangocms-blog 1.2.3` baigiasi ties `0039` — 12 migracijų atotrūkis.

### settings.py

`INSTALLED_APPS`: pašalinti `djangocms_text_ckeditor`, `aldryn_apphooks_config`, `djangocms_blog`;
pridėti `djangocms_text`, `djangocms_versioning`, `djangocms_alias`, `djangocms_stories` — #2646 tai
jau padarė, kartu su:

```python
# Shim'as įjungiamas tik migracijai.
if env.bool("DJANGOCMS_BLOG_MIGRATION", default=False):
    INSTALLED_APPS.insert(INSTALLED_APPS.index("djangocms_stories"), "djangocms_blog")

CMS_CONFIRM_VERSION4 = True
DJANGOCMS_VERSIONING_USERNAME_FIELD = "email"
STORIES_USE_PLACEHOLDER = False
```

Pirminėje šio recepto versijoje vėliava vadinosi `CMS_MIGRATION_BLOG_SHIM` ir įdėdavo dar
`aldryn_apphooks_config`. To nereikia: suderinamumo `djangocms_blog` migracijos importuoja jo laukus,
bet nuo jo migracijų nepriklauso, o pats paketas migracijų neturi — pakanka, kad jis įdiegtas.

4.1 įrankis dar prideda `djangocms_4_migration` į `INSTALLED_APPS` ir
`CMS_MIGRATION_USER_ID = env.int("CMS_MIGRATION_USER_ID", default=1)`.

`STORIES_USE_PLACEHOLDER = False` tęsia `devel` nustatymą `BLOG_USE_PLACEHOLDER = False`: straipsnių
tekstas lieka `post_text`. Prod kopijoje 59 straipsnių placeholder'iuose nėra nė vieno plugin'o, tad
perkelti nėra ko.

### Kodo pakeitimai (be jų nepasileidžia)

| Failas | Kas | #2646 |
|---|---|---|
| `vitrina/cms/urls.py`, `cms/views.py` | `djangocms_blog` → `djangocms_stories` | padaryta |
| `vitrina/messages/signals.py` | Naujienlaiškis turi imti tik publikuotas naujienas. Receptas siūlė `PostContent.admin_manager` **su `versions__state=PUBLISHED`** — vien `admin_manager` įtrauktų juodraščius | padaryta kitaip: `PostContent.objects`, versioning'ą suprantantis manager'is, pats grąžina tik publikuotą turinį |
| `vitrina/users/models.py` + migracija `0007` | `User.version` → `model_version`. Kertasi su `djangocms_versioning.Version.created_by` atgaliniu vardu (`fields.E303`). Laukas kode nenaudojamas | padaryta (jau ir `devel`) |
| `vitrina/users/admin.py` → `vitrina/cms/admin.py` | **Post admin'o perkėlimas.** `vitrina.users` turi būti PRIEŠ `cms` (`cms.models.permissionmodels` reikalauja registruoto `User`), bet Post admin'as turi krautis PO `djangocms_stories.admin`. `vitrina.cms` yra už stories → abi sąlygos tenkinamos. Kitaip — ciklinis importas per cms plugin discovery | padaryta |
| `vitrina/users/migrations/0003` | `djangocms_blog` → `djangocms_stories` app_label. Priklausomybė nuo `('djangocms_blog', '0001_initial')` **pašalinama, ne pernukreipiama**: pernukreipus į stories, esamose bazėse kiltų `InconsistentMigrationHistory` (0003 jau pritaikyta, o `djangocms_stories.0001` dar ne); palikus blog, po atnaujinimo — `NodeNotFoundError`, nes perkėlimo migracija ištrina visus `djangocms_blog` migracijų įrašus | padaryta |

### Vykdymas

`cms4_migration` viduje = `migration_preparation` → `migrate` → `migrate_alias_plugins` →
`migrate_static_placeholders` → `migration_cleanup` → `remove_unlinked_placeholders`.

Jį reikia **išskaidyti**, nes po duomenų perkėlimo shim'as turi dingti (kitaip valymas kreipiasi į
jau numestas blog plugin'ų lenteles):

```sh
DJANGOCMS_BLOG_MIGRATION=1 manage.py migration_preparation
DJANGOCMS_BLOG_MIGRATION=1 manage.py migrate                    # cms 3→4 IR blog→stories
DJANGOCMS_BLOG_MIGRATION=0 manage.py migrate_alias_plugins
DJANGOCMS_BLOG_MIGRATION=0 manage.py migrate_static_placeholders
DJANGOCMS_BLOG_MIGRATION=0 manage.py migration_cleanup
DJANGOCMS_BLOG_MIGRATION=0 manage.py remove_unlinked_placeholders
```

> **Tvarka svarbi.** `cms4_migration` privalo eiti **prieš** bet kokį `migrate`, liečiantį `cms`.
> Paleidus pvz. `migrate djangocms_blog` pirma, kartu pritaikomos `cms.0028–0033`, o `0031` išmeta
> `publisher_is_draft` — draft/public informacija dingsta dar prieš tai, kai `migration_preparation`
> spėja ją išsaugoti.

### Rezultatas po 1 etapo (patikrinta)

`cms_page` **59 → 30**; mazgų su >1 puslapiu **29 → 0**; `cms_pagecontent` 63;
`djangocms_versioning_version` 110 (**94 published, 16 draft**); `djangocms_stories_post` **47**;
blog lentelės numestos.

## 2 etapas: kontrolinis taškas

```sh
pg_dump -Fc > after-stage1.dump
```

## 3 etapas: 4.1 → 5.0

### Priklausomybės

```toml
django-cms = "^5.0.0"
djangocms-alias = "^3.0.0"
# djangocms-4-migration leidime nėra
```

`djangocms_4_migration` leidimo `INSTALLED_APPS` nėra. Shim'o sąlyga ir `aldryn-apphooks-config` lieka,
kol #2795 jų neišims: leidimo image'as irgi moka blog → stories etapą, jei bazei jo dar reikia.

### Kodo pakeitimai (CMS 5 API — `TreeNode` nebėra)

| Failas | Kas | #2646 |
|---|---|---|
| `vitrina/templatetags/navigation_tags.py` | `Page.objects.public()` → `PageContent` + `versions__state=PUBLISHED`; `page.children` | padaryta, testai `tests/cms/test_navigation*.py` |
| `vitrina/cms/cms_plugins.py` | `SideMenuPlugin`: 5 × `.node` → `get_child_pages()` / `get_parent_page()`, filtruojant pagal `PUBLISHED`. **59 instancijos prod'e** | padaryta, testai `tests/cms/test_side_menu_plugin.py` |
| `vitrina/cms/templates/pages/side_menu.html` | `.item` pašalinta | padaryta |
| `vitrina/templates/menu.html` | **vaikų kilpoje** `.item` pašalinta — tuometinis #2646 pataisė tik tėvinį puslapį, vaikai liko ir svetainė krisdavo 500 | padaryta |

### Vykdymas

```sh
manage.py migrate --skip-checks
```

Leidime tai daro `entrypoint.sh` per `scripts/migrate_djangocms.sh`: po 1 etapo bazės būsena `complete`,
tad paleidžiamas įprastas `migrate`. `cms.0037_merge_page_treenode` dabar praeina: vienam mazgui jau
lieka vienas puslapis.

## Patikra

Įrankiai: [`cms_ab_manifest.py`](cms_ab_manifest.py) (vienodos formos manifestas iš abiejų schemų) ir
[`cms_ab_diff.py`](cms_ab_diff.py). Manifestas skaitomas iš standartinės įvesties, tad konteineryje jo
failo nereikia — tas pats veikia ir su senu `devel` kodu:

```sh
# etalone (devel kodas, be migracijos)
docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-a.json
# po 3 etapo
docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-b.json
python3 notes/migrations/djangocms/cms_ab_diff.py manifest-a.json manifest-b.json
```

**Tapatybė — medžio kelias** (`node.path` → `page.path`), ne URL: netransliuotas puslapis duoda
tuščią URL ir susiduria su šakniniu (rasta prod duomenyse). Manifestas taip pat **sujungia**
published ir draft `PageContent` tam pačiam puslapiui+kalbai — kitaip palyginimas melagingai rodo
„nukrito į draft" (versionavime tai normalu: 9 tokie atvejai).

## Rezultatas (2026-08-05)

| | A (cms3 etalonas) | B (po 3 etapų) |
|---|---|---|
| Publikuotų puslapių | 52 | **52** ✓ |
| Naujienų | 47 | **47** ✓ |
| Publikuotų naujienų | 42 | **42** ✓ |
| URL crawl | — | **44/45 → 200**, 1 × 403 |

- 403 (`/more/sveikatos-duomenys/`) — **identiškas A pusėje**, ne regresija (teisėmis ribojamas).
- Redirect'ai išlikę (`/public/api/1/`, `https://old.data.gov.lt/public/api/1`).
- Vienintelis realus skirtumas: puslapis, cms3 turėjęs **tuščią `en` vertimą** (be slug'o, be
  pavadinimo, URL sutapdavo su šakniniu), po migracijos gavo `regulations` / „Legislation" /
  `more/regulation/regulations`. Migracijos paketas tai daro sąmoningai („ensure page urls are
  unique"), t. y. pataiso seną defektą — bet URL pasikeitė.

## Kas lieka

- ~~**Testų nėra** nei `SideMenuPlugin`, nei navigacijai~~ — **parašyti #2646**. Kodėl tai buvo svarbu: be
  jų #2646 CI buvo žalias su lūžtančiu kodu, o žalias CI ant tuščios bazės neįrodo nieko.
- ~~`scripts/anonymize.py` po migracijos lūš~~ — **pataisyta #2646.** Skriptas pats randa naujienų lenteles
  (`_story_content_tables`): `djangocms_blog_post_translation` prieš atnaujinimą,
  `djangocms_stories_postcontent` po jo, ir abi, jei atnaujinimas sustojo pusiaukelėje. Valo ir tekstą
  plugin'uose, jei kuri konfigūracija laikytų straipsnius placeholder'iuose. Pataisa keliauja **kartu su
  atnaujinimu**, ne po jo — kitaip pirmas dump'as po go-live liktų be veikiančio anonimizavimo.
- ~~`scripts/migrate_news.py` ir `scripts/migrate_pages.py` remiasi `djangocms_blog`~~ — sprendimas: juos
  ištrina #2795, istorija lieka git'e.

### ⚠️ `anonymize.py` — trys defektai, rasti taisant (2026-08-05)

Nesusiję su CMS atnaujinimu, bet rasti prie jo ir svarbesni už jį:

1. **`_anonymize_organization` dirbo su `djangocms_blog_post_translation`, ne su `organization`.**
   Kopijavimo klaida, atsiradusi commit'e `3536317d` („185: new tables in anonymization script").
   Reiškia, kad **organizacijų el. paštai, telefonai ir adresai nebuvo anonimizuojami**. Patikrinta
   prieš/po ant gauto dump'o: `519/525 → 525/525`. Likę 6 organizacijos gautame dump'e turėjo tikrus
   domenus — verta pranešti duomenų savininkui. Jų sąrašas čia sąmoningai neskelbiamas: repozitorija
   vieša. Pataisyta #2646.
2. **`_anonymize_adp_cms_page` dirbo su `news_item`** — `adp_cms_page` liko nedengtas, `news_item`
   anonimizuotas du kartus, o `dataset` kiekvienoje iškrovoje dar pridėdavo `news_item.description`
   stulpelį, kurio produkcijoje nėra. Pataisyta #2646 (2026-09; iki tol pataisa niekur nebuvo nukeliavusi).
3. **`faker` nedeklaruotas tiesiogiai** — jis ateina per `factory-boy` dev grupėje, tad skriptui reikia dev
   priklausomybių. Švarioje aplinkoje be jų skriptas lūžta `ModuleNotFoundError` pirmoje eilutėje.

- **Turinio sign-off** (turinio redaktorius) — skriptai patvirtina struktūrą, ne prasmę.
- Dump'as iš 2026-03-19: migracijai tinka, turinio patikrai — pasenęs.
