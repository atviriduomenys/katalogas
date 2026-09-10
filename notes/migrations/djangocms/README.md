# django-cms 3.10 → 5.0 migracija

Viskas, kas susiję su vienkartiniu django-cms atnaujinimu, vienoje vietoje. Į šį katalogą rodo ir
`scripts/migrate_djangocms.sh`: kai leidimo konteineris atsisako migruoti bazę, dar neperėjusią
cms 3 → 4 konversijos, jis siunčia čia.

Susiję: #1824 (užduotis) · PR #2646 (atnaujinimas) · PR #2795 (išvalymas po migracijos).

## Kas čia yra

| Failas | Kam | Kas |
|---|---|---|
| [`receptas.md`](receptas.md) | programuotojui | Kodėl migracija trijų etapų, kokios priklausomybės kiekvienam etapui, kas pakeista kode |
| [`diegimas.md`](diegimas.md) | diegiančiam | Žingsnis po žingsnio TEST/PROD aplinkoje: backup'as, 4.1 įrankis, 5.0 leidimas, patikros |
| [`cms_ab_manifest.py`](cms_ab_manifest.py), [`cms_ab_diff.py`](cms_ab_diff.py) | abiem | Priėmimo patikra: tos pačios formos manifestas iš bazės prieš ir po, ir jų palyginimas |
| `migration dev v4.sh`, `utils.sh` | istorijai | Pirmojo bandymo darbo žurnalas. **Ne skriptas** — žr. žemiau |

## Eiga

1. Perskaityk `receptas.md` — kodėl eiliškumas toks griežtas ir kodėl atsukti negalima.
2. Sukurk 4.1 migracijos įrankio image'ą (`diegimas.md`, „Ko reikia turėti prieš pradedant"). Jo dar
   nėra: `cms4-migration-tool` tagas nesukurtas.
3. Repeticija ant anonimizuotos prod kopijos pagal `diegimas.md`, su A/B manifestais prieš ir po.
   Priėmimo kriterijus ne „pakilo", o „migracija iš prod formos bazės praėjo ir turinys išliko".
4. Tik tada TEST, paskui PROD — ta pačia instrukcija.
5. Kai visos aplinkos pereis, #2795 išima vienkartinę mechaniką.

## A/B patikra

Manifestas paleidžiamas aplinkos konteineryje, bet pats failas ten neturi būti: Python jį skaito iš
standartinės įvesties, o `vitrina` importuojama iš konteinerio darbinio katalogo (`/app`).

    docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-a.json
    # ... migracija ...
    docker compose exec -T vitrina python - < notes/migrations/djangocms/cms_ab_manifest.py > manifest-b.json
    python3 notes/migrations/djangocms/cms_ab_diff.py manifest-a.json manifest-b.json

Taip tą patį failą galima paleisti ir prieš seną (`devel`, cms 3) kodą, kuriame jo nėra. Palyginimas grąžina
`exit 1`, jei pažeistas bent vienas blokuojantis kriterijus — dingęs puslapis, publikuotas → juodraštis,
pasikeitęs URL, dingęs redirect'as ar naujiena.

## Bazinė būsena dev aplinkoje

Tuščios bazės variantas, į kurį rodo `scripts/ui/README.md`: žinomas nedidelis turinys, kurį po migracijos
lengva patikrinti akimis.

    git checkout devel                 # senas cms 3 kodas; su #2784 jame yra ir scripts/ui/
    poetry install
    poetry run python manage.py migrate
    poetry run python manage.py createsuperuser        # skriptams reikia būtent superuser'io
    poetry run playwright install chromium
    poetry run python scripts/ui/create_organization.py   # ir kiti iš „Any portal" stulpelio
    pg_dump -Fc ... > baseline.dump

Portalas turi veikti, o prisijungimo duomenys ir vienkartinių kodų išjungimas aprašyti
`scripts/ui/README.md`. Blog → stories dalies taip nepatikrinsi: naujienų skriptai reikalauja jau
atnaujinto admin'o, tad senų įrašų tuščioje bazėje nebus. Tam reikia prod kopijos.

## Darbo žurnalas (`migration dev v4.sh`)

Pirmojo bandymo užrašai: kaip dev aplinka buvo vedama per visus etapus, su iškrova po kiekvieno.
Vertingas kaip žemėlapis, bet **nevykdomas**:

- `git checkout G1` ir septyni `cherry-pick` rodo į commit'us, kurių nėra nei GitHub'e, nei jokioje šakoje —
  jie egzistavo tik autoriaus kompiuteryje;
- turi alternatyvas ir žymas „iki čia padaryta", keičia `settings.py` per `sed`;
- `utils.sh` funkcija `clean_db` daro `DROP SCHEMA public CASCADE` vietinei dev bazei.

Atkartojamas to paties kelio variantas yra `receptas.md` + `diegimas.md`. Žurnalą išima #2795.
