# django-cms 3.11 → 5.0 migracija

Viskas, kas susiję su vienkartiniu django-cms atnaujinimu, vienoje vietoje. Į šį katalogą rodo ir
`scripts/migrate_djangocms.sh`: kai leidimo konteineris atsisako migruoti bazę, kurios 4.1 migracijos
įrankis dar nesutvarkė — cms 3 → 4 konversijos ar blog → stories perkėlimo — jis siunčia čia.

Susiję: #1824 (užduotis) · PR #2646 (atnaujinimas) · PR #2795 (išvalymas po migracijos).

Šaltinis — django-cms **3.11.11**: tiek rodo `devel` `poetry.lock`, nors `pyproject.toml` rašo `^3.10.1`.

## Kas čia yra

| Failas | Kam | Kas |
|---|---|---|
| [`receptas.md`](receptas.md) | programuotojui | Kodėl migracija trijų etapų, kokios priklausomybės kiekvienam etapui, kas pakeista kode |
| [`diegimas.md`](diegimas.md) | diegiančiam | Žingsnis po žingsnio TEST/PROD aplinkoje: backup'as, 4.1 įrankis, 5.0 leidimas, patikros |
| [`cms_ab_manifest.py`](cms_ab_manifest.py), [`cms_ab_diff.py`](cms_ab_diff.py) | abiem | Priėmimo patikra: tos pačios formos manifestas iš bazės prieš ir po, ir jų palyginimas |

## Eiga

1. Perskaityk `receptas.md` — kodėl eiliškumas toks griežtas ir kodėl atsukti negalima.
2. Subuild'ink 4.1 migracijos įrankio image'ą iš tago `cms4-migration-tool` (`diegimas.md`, „Ko reikia
   turėti prieš pradedant"). Tagas sukurtas 2026-09-21, nuo `devel` su sumerginta #2646.
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

Taip tą patį failą galima paleisti ir prieš seną (cms 3) kodą, kuriame jo nėra.

Repeticijai iš dump'o: prieš manifestą A atvesk bazę į paskutinio cms 3 leidimo būseną (`migrate` su cms 3
image'u) — dump'as gali būti senesnis už kodą, o prod diegimo metu bus būtent tokioje būsenoje. Palyginimas grąžina
`exit 1`, jei pažeistas bent vienas blokuojantis kriterijus — dingęs puslapis, publikuotas → juodraštis,
pasikeitęs URL, dingęs redirect'as ar naujiena.

## Repeticija 2026-09-21

Ant anonimizuotos prod kopijos (dump'as 2026-08-19), su tagu `cms4-migration-tool` ir devel `e97a36a4`:
visos šešios įrankio komandos praėjo (83 s), cms 5 `migrate` — taip pat (19 s, `cms.0037` be klaidų).
A/B: vienintelis blokuojantis skirtumas — žinomas „Legislation" atvejis (`diegimas.md`, 8 žingsnis).
Visi 53 publikuoti puslapiai abiem kalbomis ir 54 naujienos atsidaro, 5 nepublikuotos grąžina 404,
5 priedai liko prie savo naujienų, 5xx klaidų nebuvo.

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

## Nauja aplinka be duomenų

Tuščiai bazei 4.1 įrankio nereikia: `scripts/migrate_djangocms.sh` ją atpažįsta kaip `fresh` ir tiesiog
paleidžia migracijas. Puslapių medį, kokį turi produkcija, ir naujienų (stories) konfigūraciją tada sukuria:

    poetry run python manage.py createsuperuser        # puslapiai publikuojami jo vardu
    poetry run python scripts/create_pages.py

Veikia tik su cms 5 kodu (#2646 ir vėliau). Puslapių, kurių slug jau yra, neliečia, tad paleisti pakartotinai
saugu — taip ir pabaigiamas nutrūkęs paleidimas.

## Pirmasis bandymas

Pirmojo bandymo darbo žurnalas (`migration dev v4.sh` ir `utils.sh`) iš katalogo išimtas: vykdyti jo nebuvo
galima — jis rėmėsi commit'ais, egzistavusiais tik autoriaus kompiuteryje, — tad jis tik painiojo. Tą patį
kelią atkartojamai aprašo `receptas.md` ir `diegimas.md`. Žurnalas liko git istorijoje:

    git log --full-history -- "notes/migrations/djangocms/migration dev v4.sh"
