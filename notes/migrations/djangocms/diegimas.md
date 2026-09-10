# django-cms 5 migravimas: žingsnis po žingsnio

> Instrukcija tam, kas atlieka migravimą aplinkoje (TEST arba PROD).
> **Prasukta nuo pradžios iki galo 2026-08-11** ant anonimizuotos prod kopijos: visos komandos
> `exit 0`, portalas pakilo, smoke testas švarus.
> Techninis pagrindimas, kodėl taip — [receptas.md](receptas.md). Katalogo aprašas — [README.md](README.md).
> Susiję: DAS-428 · #1824 · PR #2646
>
> Rašyta 2026-08-11. Lentelė „Ką tas commit'as keičia", vėliavos vardas ir 5 žingsnis atnaujinti pagal
> #2646 būklę 2026-09; kita — kaip repeticijoje.

**Rollback'o nėra.** Versioning migracijos atgal nesisuka. Vienintelis kelias atgal — atkurti bazę
iš backup'o. Todėl 2 žingsnis (patikrintas backup'as) nėra formalumas.

**Kodėl reikia dviejų žingsnių, o ne vieno diegimo:** bazė iš cms 3.11 į 5.0 tiesiai nemigruoja, ji
privalo pereiti per 4.1. Portalui per 4.1 eiti nereikia — 4.1 aplinka naudojama tik kaip įrankis
bazei ir svetaine niekada netampa.

---

## Ko reikia turėti prieš pradedant

Dviejų Docker image'ų ir aplinkos `.env` su teisingu `DATABASE_URL`.

django-cms versija yra **image'o viduje** — kartu su Python'u, bibliotekomis ir katalogo kodu.
Veikiančiame konteineryje jos pakeisti negalima, reikia build'inti naują image'ą. Dėl to jų ir dvi.

### Iš kur tagai

**Leidimo tagas** (cms 5.0) — įprastas `vX.Y.Z`, kurį uždeda Release manager, kaip ir kiekvienam
leidimui. Nieko naujo.

**Migracijos įrankio tagas** — naujas dalykas, sukuriamas **vieną kartą** (#1824). Tai commit'as su 4.1
priklausomybėmis, pažymėtas atskiru vardu, pvz. `cms4-migration-tool`. Į `vX.Y.Z` schemą jis
nepatenka, nes tai ne leidimas.

**Kas jį sukuria:** programuotojas, rengiantis migraciją, **vieną kartą**. 2026-09 jo dar nėra —
`cms4-migration-tool` tagas nesukurtas.

**Ką tas commit'as keičia.** Tai ne atskiras projektas, o tas pats katalogas su kitomis priklausomybėmis
ir minimaliais pakeitimais, kad Django pakiltų ir migracijos pravažiuotų. Navigacijos ir plugin'ų kodo
liesti **nereikia**, nes svetainė iš šio image'o nekeliama.

Pirminėje versijoje tai buvo devyni failai, ~73 eilutės. Didžioji dalis jau yra #2646 ir į įrankį ateina
kartu su leidimo commit'u: stories importai `vitrina/cms/urls.py` ir `views.py`, naujienlaiškio
filtravimas `vitrina/messages/signals.py`, `User.version` → `model_version` su migracija `0007`, Post
admin'o perkėlimas į `vitrina/cms/admin.py`, blog shim'as (`DJANGOCMS_BLOG_MIGRATION`),
`CMS_CONFIRM_VERSION4`, `DJANGOCMS_VERSIONING_USERNAME_FIELD`, `django-taggit-autosuggest` ir
`aldryn-apphooks-config`. Įrankio commit'ui lieka:

| Failas | Kas |
|---|---|
| `pyproject.toml`, `poetry.lock` | django-cms `>=4.1,<5`, **djangocms-alias `<3`**, `djangocms-4-migration` iš git prikaltu commit'u (žr. [receptą](receptas.md)) |
| `docker/Dockerfile` | pridėti `git` į apt sąrašą — be jo poetry neparsiųs git priklausomybės |
| `vitrina/settings.py` | `djangocms_4_migration` į `INSTALLED_APPS`; `CMS_MIGRATION_USER_ID` |

> ⚠️ **Dar nepatikrinta.** Django bet kuriai `manage.py` komandai įkelia visas programas — ir `admin.py`,
> ir `apps.py`. #2646 kodas rašytas cms 5, tad ar jis įsikels po cms 4.1, parodys tik pirmas image'o
> build'as. Tai pirmas repeticijos klausimas; jei ne, įrankio commit'as turės daugiau pakeitimų.

**Kaip sukuriamas.** Tagas nepriklauso nuo šakos, tad šakos laikyti nereikia — ji ištrinama, o tagas
commit'ą išlaiko:

```sh
git checkout -b tmp-cms4-tool <leidimo commit'as>
# ... devynių failų pakeitimai ...
git commit -am "django-cms 4.1 migration tool"
git tag cms4-migration-tool
git push origin cms4-migration-tool        # stumiamas TIK tagas, ne šaka
git branch -D tmp-cms4-tool
```

Į `devel` šis commit'as **nepatenka** — jame 4.1 priklausomybės, o `devel` eina į 5.0.

Naudojamas tik migravimo metu; kai visos aplinkos pereis į cms 5, tagą galima ištrinti.

### Build'inimas

Abu build'inami ta pačia komanda, tik iš skirtingų kodo būsenų:

```sh
# A. Migracijos įrankis (django-cms 4.1)
git checkout cms4-migration-tool
docker build -f docker/Dockerfile -t katalogas-cms4-migration:$(date +%F) .

# B. Leidimas (django-cms 5.0)
git checkout v1.X.0                   # leidimo tagas
docker build -f docker/Dockerfile -t katalogas-cms5:$(date +%F) .
```

> ⚠️ **Nenaudok `docker compose build`.** Jis image'ą visada tag'ina vardu `vitrina-app:latest`
> (taip nurodyta `docker-compose.yml`), o tas vardas yra **bendras visam Docker host'ui**. Aplinka,
> kuri tuo vardu remiasi, po build'o pradės kilti su nauju kodu — net jei jos niekas nediegė.
> Repeticijoje būtent taip ir nutiko: build'as nulaužė veikiantį cms 3 portalą, nes jis pakilo su
> cms 5 kodu ant cms 3 bazės. `docker tag` po build'o nuo to neapsaugo — `vitrina-app:latest` vis
> tiek lieka rodyti į paskutinį build'ą.
>
> `docker build -t <vardas>` to vardo neliečia.

Kiekvienas build'as trunka ~4 min ir reikalauja prieigos prie **PyPI** ir prie **GitHub**
(`djangocms-4-migration` PyPI neturi gyvos versijos, imamas iš git). Uždaroje aplinkoje image'us
reikia subuild'inti ten, kur prieiga yra, ir perkelti.

Pasitikrink, kad image'ai tikrai skirtingi:

```sh
docker run --rm katalogas-cms4-migration:<data> python -c "import cms; print(cms.__version__)"   # 4.1.x
docker run --rm katalogas-cms5:<data>            python -c "import cms; print(cms.__version__)"   # 5.0.x
```

### Kaip paleidžiamos komandos

> ⚠️ **Nepaleisk per `docker run --env-file .env`.** Aplinkos `.env` turi `REDIS_URL`,
> `SEARCH_URL` ir `DATABASE_URL`, rodančius į `127.0.0.1`. Atskirame konteineryje `127.0.0.1` yra
> jis pats, ne aplinkos servisai, todėl komandos krenta su `ConnectionError`. Repeticijoje taip
> krito visos šešios. Compose tuos adresus perrašo servisų vardais (`redis`, `postgres`) per
> `environment:` bloką — o `docker run` to nedaro.

Paprasčiausias būdas nekartoti tų adresų ranka — paleisti per tą pačią compose konfigūraciją,
tik pakeitus image'ą. Šalia aplinkos `docker-compose.yml` pasidėk:

```yaml
# docker-compose.migration.yml
services:
  vitrina:
    image: katalogas-cms4-migration:<data>
    volumes: !reset []          # BUTINA, zr. zemiau
```

> ⚠️ **`volumes: !reset []` nepamiršk.** `docker-compose.yml` turi `- ".:/app"`, t. y. host'o
> katalogas užklojamas ant image'o kodo. Be šios eilutės konteineris paims 4.1 bibliotekas, bet
> **kodą — aplinkos**, tad migracijos suksis su cms 3 kodu ir kris (`No module named
> 'djangocms_blog.admin'`). Repeticijoje taip ir nutiko. Su `!reset []` kodas ateina iš image'o,
> kaip ir turi.

> ⚠️ **Šį override naudok tik su `run --rm`.** `docker compose ... up` su juo iškeltų portalą iš 4.1
> image'o: po 3 žingsnio `entrypoint.sh` rastų būseną `complete` ir paleistų svetainę ant cms 4.1 su
> cms 5 kodu. Apsauga to nesustabdo — ji saugo bazę, ne portalą.

ir komandas leisk taip. `docker-compose.yml` servisui nurodo `command: ./entrypoint.sh`, o `run` su savo
komanda jį pakeičia, tad `entrypoint.sh` nesisuks; `--entrypoint ""` — draudimas, jei kas nors compose'e
jį perkeltų į `entrypoint:`:

```sh
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.migration.yml"
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=1 --entrypoint "" vitrina \
  python manage.py migration_preparation
```

Taip visi adresai, tinklas ir kintamieji ateina iš tos pačios vietos, iš kurios juos gauna portalas.

> **Serviso vardai priklauso nuo aplinkos.** Čia rašoma `vitrina` ir `postgres`, kaip
> `docker-compose.yml`. Review aplinkose (`docker-compose.template.yml`) jie vadinasi `katalogas-<šaka>`
> ir `katalogas-<šaka>-database`, `docker-compose.dev.yml` Postgres — `katalogas-database`. Pakeisk juos
> ir override'e, ir komandose.

Postgres, Elasticsearch ir Redis turi suktis viso proceso metu. Portalas — ne.

Reikia dar: vietos backup'ui ir laiko jį atkurti, jei prireiktų.

---

## 0. Patikra prieš pradedant (nieko nekeičia)

Ar bazei apskritai reikia 4.1 žingsnio:

```sql
select count(*) from (select node_id from cms_page group by node_id having count(*) > 1) t;
```

- **> 0** — draft/public poros yra, 4.1 žingsnis **būtinas**. Prod kopijoje buvo `29`.
- **0** — porų nėra; sustok ir pasitikslink, ar bazė tikrai cms 3 būsenos.

Užsirašyk pradinius skaičius — jų prireiks tikrinant:

```sql
select count(*) from cms_page;                      -- pvz. 59
select count(*) from cms_treenode;                  -- pvz. 30
select count(*) from djangocms_blog_post;           -- pvz. 47
```

---

## 1. Turinio įšaldymas ir portalo sustabdymas

1. Įspėk turinio redaktorių, kad nuo šio momento turinio nekeistų.
2. **Sustabdyk portalą.** Jei jis rašys į bazę migracijos metu, rezultatas nenuspėjamas.

---

## 2. Backup'as

`pg_dump` turi būti ne senesnis už serverį. Nuo PostgreSQL 18 atnaujinimo (#2794) host'o klientas
dažnai senesnis ir tiesiog atsisako dirbti, tad leisk tą, kuris ateina su serveriu:

```sh
# Postgres sukasi compose'e (serviso vardas priklauso nuo aplinkos, žr. aukščiau)
docker compose exec -T <postgres-servisas> sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > pries-cms5-$(date +%F-%H%M).dump
# kitaip — serverio versijos klientas iš image'o
docker run --rm --network host postgres:18 pg_dump -Fc -d "$DATABASE_URL" > pries-cms5-$(date +%F-%H%M).dump
```

**Patikrink, kad jis atsikuria** — atkurk į laikiną bazę ir įsitikink, kad lentelių kiekis sutampa.
Neatkurtas backup'as nėra backup'as. `pg_restore` — tas pats: serverio versijos.

---

## 2b. Sekų suvienodinimas

Prieš migruojant suvienodink `SERIAL` sekas su realiais duomenimis:

```sql
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS seq, t.relname AS tbl, a.attname AS col
    FROM pg_class c
    JOIN pg_depend d ON d.objid = c.oid AND d.deptype = 'a'
    JOIN pg_class t ON t.oid = d.refobjid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
    WHERE c.relkind = 'S'
  LOOP
    EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1))', r.seq, r.col, r.tbl);
  END LOOP;
END $$;
```

**Kodėl.** Tai **saugiklis, ne būtina pataisa**. Švariame kelyje (atkurta iš prod dump'o) sekos
būna tvarkingos ir šis žingsnis nieko nekeičia — repeticijoje `max` ir seka jau sutapo.

Bet jei bazė atkuriama iš **tarpinio** backup'o, sekos gali atsilikti, ir tada migracijos krenta su
`duplicate key value violates unique constraint "django_migrations_pkey"`, paskui
`django_content_type_pkey`. Taip nutiko bandant. Žingsnis idempotentiškas ir trunka sekundę, tad
pigiau jį atlikti visada, negu aiškintis vidury diegimo.

Pasitikrink, kad suvienodinta:

```sql
select max(id), (select last_value from django_migrations_id_seq) from django_migrations;
-- abu skaiciai turi sutapti
```

---

## 3. Migracija į 4.1 (migracijos image)

Šešios komandos ta pačia tvarka, prieš tą pačią bazę. Pirmos dvi — su įjungtu blog shim'u, likusios
be jo: po duomenų perkėlimo blog lentelės jau numestos, ir valymas į jas kreiptųsi.

```sh
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.migration.yml"
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=1 --entrypoint "" vitrina python manage.py migration_preparation
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=1 --entrypoint "" vitrina python manage.py migrate
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=0 --entrypoint "" vitrina python manage.py migrate_alias_plugins
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=0 --entrypoint "" vitrina python manage.py migrate_static_placeholders
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=0 --entrypoint "" vitrina python manage.py migration_cleanup
$COMPOSE run --rm -e DJANGOCMS_BLOG_MIGRATION=0 --entrypoint "" vitrina python manage.py remove_unlinked_placeholders
```

Kiekviena turi baigtis **exit 0**. Trukmė kartu — apie **2 min** (repeticijoje 116 s).

> **Jei kuri nors krenta — STOP.** Netaisyk vietoje ir nebandyk paleisti kitos. Bazė yra tarpinėje
> būsenoje: `cms.0031` jau išmetusi `publisher_is_draft`, tad nei pirmyn, nei atgal. Atkurk iš
> backup'o ir grįžk pas programuotoją su logu.

**Tvarka svarbi.** `migration_preparation` privalo eiti pirma. Paleidus bet kokį kitą `migrate`
anksčiau, kartu pritaikomos `cms.0028`–`0033`, o `0031` sunaikina draft/public informaciją dar
prieš tai, kai ji išsaugoma.

Antroji komanda — **paprastas** `migrate`, ne `migrate djangocms_stories`. Stories `0002` nuo blog
migracijų nepriklauso: ji tik vykdymo metu tikrina, ar `djangocms_blog.0051` jau pritaikyta, ir kitaip
meta `RuntimeError`. Migruojant visą grafą Django lapus planuoja surūšiuotai, tad `djangocms_blog`
suspėja prieš `djangocms_stories`. Susiaurinus komandą iki vienos programos, ta tvarka nebegarantuota.

---

## 4. Patikra po 4.1

```sql
select count(*) from (select node_id from cms_page group by node_id having count(*) > 1) t;
```

**Privalo būti `0`.** Jei ne — nejudėk toliau, `cms.0037` kris.

```sql
select count(*) from cms_page;                          -- turi sumažėti maždaug per pusę (59 -> 30)
select count(*) from cms_treenode;                      -- nepakitęs (30)
select count(*) from djangocms_stories_post;            -- tiek, kiek buvo blog postų (47)
select state, count(*) from djangocms_versioning_version group by state;
```

Versijų būsenose turi būti ir `published`, ir `draft` (pvz. 94 / 16). Jei `published` nėra — turinys
po diegimo dings iš svetainės; **stok ir atkurk iš backup'o**.

Blog lentelių nebeturi likti:

```sql
select count(*) from information_schema.tables where table_name like 'djangocms_blog%';  -- 0
```

---

## 5. cms 5.0 diegimas (image A)

Diegiama **įprastai**. `entrypoint.sh` per `scripts/migrate_djangocms.sh` pirmiausia patikrina bazės
būseną: po 3 žingsnio ji `complete`, tad paleidžiamas įprastas `migrate`, kuris pritaiko
`cms.0037`–`0041`. Dabar tai saugu, nes vienam mazgui liko vienas puslapis.

Trukmė: migracijos ir portalo pakilimas kartu — apie **3,5 min** (repeticijoje 212 s;
`entrypoint.sh` dar prasuka webpack build'ą, `collectstatic` ir `rebuild_search`).

> Jei 5.0 image'as vis dėlto pasileistų ant bazės, 3 žingsnio nebaigusios, jis nemigruos:
> `migrate_djangocms.sh` randa `cms_title` (`legacy_pages`) arba neperkeltas blog lenteles
> (`pending`), sustoja, ir konteineris nepakyla. Pats leidimas duomenų neperkelia. Tai apsauga, ne
> kelias — grįžk prie 3 žingsnio.

---

## 6. Patikra po 5.0

```sql
select count(*) from cms_page;                    -- toks pat kaip po 4 žingsnio (30)
select count(*) from cms_pagecontent;             -- pvz. 63
select count(*) from djangocms_stories_post;      -- nepakitęs (47)
```

`cms_treenode` po `cms.0037` nebenaudojama — `Page` pats tampa medžio mazgu.

---

## 7. Smoke testas

- Titulinis puslapis atsidaro
- Naujienų sąrašas (`/blog/`) rodo naujienas su datomis
- Bent du puslapiai su **šoniniu meniu** — meniu rodo teisingą medį
- Bent vienas puslapis iš navigacijos viršutinio meniu su išskleidžiamu sąrašu
- Admin atsidaro

Jei kas nors iš to lūžta, o migracijos praėjo — tai kodo, ne duomenų problema. Bazės atkurti nebūtina;
taisoma nauju leidimu.

---

## 8. Turinio patikra

Turinio redaktorius peržiūri, ar turinys nepasikeitė. Ką tikrinti pirmiausia:

- Puslapiai, kurie turi šoninį meniu
- Naujienos: ar visos vietoje, su datomis ir autoriais
- Ar niekur nerodomi nepublikuoti puslapiai

**Prod kopijoje vienintelis realus turinio pokytis buvo:** puslapis, turėjęs tuščią `en` vertimą (be
pavadinimo ir slug'o), po migracijos gavo adresą `more/regulation/regulations` ir pavadinimą
„Legislation". Migracijos paketas tai daro sąmoningai — pataiso seną defektą, bet **URL pasikeičia**.
Verta patikrinti, ar nėra daugiau tokių puslapių, ir ar nauji adresai priimtini.

---

## Jei reikia atsukti

Vienintelis būdas:

1. Sustabdyti portalą
2. Atkurti bazę iš 2 žingsnio backup'o
3. Sudiegti ankstesnį (cms 3.11) leidimą

Viskas, kas suvesta po įšaldymo pradžios, prarandama — todėl įšaldymas ir yra būtinas.
