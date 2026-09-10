"""A/B manifestų palyginimas (DAS-428) — tikrina plano 6 sk. priėmimo kriterijus.

    python3 notes/migrations/djangocms/cms_ab_diff.py manifest-a.json manifest-b.json

A = etalonas (devel kodas, be cms5 migracijos), B = bandomasis (sulieta #2646 + migracijos).
Grąžina exit code 1, jei pažeistas bent vienas kriterijus — tinka CI/skriptui.

Sąmoningai nelyginam visko su viskuo: `title` skirtumai patys savaime nėra gedimas
(migracija gali normalizuoti tarpus), o `published: true -> false` yra. Tad kriterijai
skirstomi į BLOKUOJANČIUS ir informacinius.
"""

import json
import sys


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _key(row):
    # Tapatybė — medžio kelias, ne URL. URL kelias tapatybei netinka: netransliuotas
    # puslapis duoda tuščią kelią ir susiduria su šakniniu (rasta prod duomenyse).
    return (row.get("tree_path"), row.get("language"))


def _post_key(row):
    return (row.get("slug"), row.get("language"))


def _index(rows, keyfunc):
    """Indeksuoja pagal raktą ir RĖKIA, jei raktas nevienareikšmis.

    Tylus perrašymas čia yra pavojingiausia klaida: praradę eilutę, palyginimą
    parodytume kaip „nukrito į draft" arba visai nepastebėtume dingusio puslapio.
    """
    index = {}
    for row in rows:
        key = keyfunc(row)
        if key in index:
            raise ValueError(
                f"Manifeste pasikartojantis raktas {key!r} — tapatybė nevienareikšmė, "
                f"palyginimo rezultatai būtų klaidingi. Taisyk manifesto generatorių."
            )
        index[key] = row
    return index


def compare(a, b):
    """Grąžina (blokuojantys, informaciniai) — abu sąrašai eilučių."""
    blocking = []
    info = []

    pages_a, pages_b = _index(a["pages"], _key), _index(b["pages"], _key)
    posts_a, posts_b = _index(a["posts"], _post_key), _index(b["posts"], _post_key)

    # --- puslapiai: ar visi vietoje, tie patys slug'ai, ta pati medžio struktūra
    for key in sorted(set(pages_a) - set(pages_b)):
        blocking.append(f"DINGO puslapis: path={key[0]!r} lang={key[1]}")
    for key in sorted(set(pages_b) - set(pages_a)):
        info.append(f"naujas puslapis B pusėje: path={key[0]!r} lang={key[1]}")

    for key in sorted(set(pages_a) & set(pages_b)):
        ra, rb = pages_a[key], pages_b[key]

        # Kritiškiausias tikrinimas visame plane: publikuotas -> nepublikuotas.
        if ra["published"] and not rb["published"]:
            blocking.append(
                f"NUKRITO Į DRAFT: path={key[0]!r} lang={key[1]} (A: published, B: ne)"
            )
        elif not ra["published"] and rb["published"]:
            blocking.append(
                f"NETIKĖTAI PUBLIKUOTAS: path={key[0]!r} lang={key[1]} (A: ne, B: published) "
                f"— nepublikuotas turinys išlįstų į svetainę"
            )

        if ra["slug"] != rb["slug"]:
            blocking.append(f"SLUG pasikeitė: path={key[0]!r} {ra['slug']!r} -> {rb['slug']!r}")
        if ra["path"] != rb["path"]:
            blocking.append(
                f"URL pasikeitė: tree={key[0]!r} lang={key[1]} {ra['path']!r} -> {rb['path']!r} "
                f"— senos nuorodos nustotų veikti"
            )
        if ra["parent_path"] != rb["parent_path"]:
            blocking.append(
                f"MEDIS pasikeitė: path={key[0]!r} tėvas {ra['parent_path']!r} -> {rb['parent_path']!r}"
            )
        if ra["in_navigation"] != rb["in_navigation"]:
            blocking.append(
                f"NAVIGACIJA pasikeitė: path={key[0]!r} "
                f"in_navigation {ra['in_navigation']} -> {rb['in_navigation']}"
            )

        if ra["plugins"] != rb["plugins"]:
            lost = {k: v for k, v in ra["plugins"].items() if rb["plugins"].get(k, 0) < v}
            if lost:
                blocking.append(f"DINGO plugin'ų: path={key[0]!r} {lost}")
            else:
                info.append(f"plugin'ų sudėtis skiriasi: path={key[0]!r} {ra['plugins']} -> {rb['plugins']}")

        if ra["title"] != rb["title"]:
            info.append(f"pavadinimas: path={key[0]!r} {ra['title']!r} -> {rb['title']!r}")

        # Dingęs redirect nėra kosmetika: puslapis, kuris permesdavo kitur, po migracijos
        # atiduoda tuščią lapą. Rasta būtent taip - crawl'as parodė 964 B atsakymus.
        if ra["redirect"] and not rb["redirect"]:
            blocking.append(
                f"DINGO REDIRECT: path={key[0]!r} lang={key[1]} {ra['redirect']!r} -> None "
                f"— puslapis nebepermeta, atiduoda tuščią lapą"
            )
        elif ra["redirect"] != rb["redirect"]:
            info.append(f"redirect: path={key[0]!r} {ra['redirect']!r} -> {rb['redirect']!r}")

    # --- naujienos: ar visos yra, su datomis ir autoriais
    for key in sorted(set(posts_a) - set(posts_b)):
        blocking.append(f"DINGO naujiena: slug={key[0]!r} lang={key[1]}")
    for key in sorted(set(posts_b) - set(posts_a)):
        info.append(f"nauja naujiena B pusėje: slug={key[0]!r} lang={key[1]}")

    for key in sorted(set(posts_a) & set(posts_b)):
        ra, rb = posts_a[key], posts_b[key]
        if ra["published"] and not rb["published"]:
            blocking.append(f"NAUJIENA nukrito į draft: slug={key[0]!r} lang={key[1]}")
        if ra["date_published"] != rb["date_published"]:
            blocking.append(
                f"NAUJIENOS data pasikeitė: slug={key[0]!r} "
                f"{ra['date_published']} -> {rb['date_published']}"
            )
        if ra["author"] != rb["author"]:
            blocking.append(
                f"NAUJIENOS autorius pasikeitė: slug={key[0]!r} {ra['author']!r} -> {rb['author']!r}"
            )

    return blocking, info


def main():
    if len(sys.argv) != 3:
        sys.exit("Naudojimas: cms_ab_diff.py manifest-a.json manifest-b.json")

    a, b = _load(sys.argv[1]), _load(sys.argv[2])
    blocking, info = compare(a, b)

    print(f"A stack: {a['stack']}  counts: {a['counts']}")
    print(f"B stack: {b['stack']}  counts: {b['counts']}")
    print()

    if blocking:
        print(f"=== BLOKUOJANTYS ({len(blocking)}) ===")
        for line in blocking:
            print(f"  ✗ {line}")
        print()
    if info:
        print(f"=== informaciniai ({len(info)}) ===")
        for line in info:
            print(f"  · {line}")
        print()

    if blocking:
        print("REZULTATAS: NEPRAĖJO — žr. blokuojančius punktus.")
        sys.exit(1)

    print("REZULTATAS: praėjo — struktūra, publikavimo būsenos, naujienos sutampa.")
    print("Lieka tai, ko skriptas nesprendžia: turinio prasmė (turinio redaktoriaus sign-off) ir URL crawl.")


if __name__ == "__main__":
    main()
