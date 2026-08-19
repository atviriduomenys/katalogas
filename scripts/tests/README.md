# UI scripts

Recorded browser sessions that drive the portal through Chromium. They create content
(pages, stories, organisations, datasets, users) so the admin can be looked at with real
data in it.

**These are not tests.** They assert nothing, they run with `headless=False`, and several
run with `slow_mo` so a person can watch. The automated suite is `tests/`, run with pytest.

They exist because the django-cms admin is iframe- and JavaScript-driven: the rich text
editor, the versioning toolbar and the publish actions are out of reach for the HTTP client
the pytest suite uses, so there is no way to exercise them without a real browser.

## Running one

Playwright is deliberately not a project dependency - it is needed only for these scripts,
and adding it would drag a browser download into every `poetry install`. Install it
separately:

```bash
pip install playwright
playwright install chromium
```

Each script then runs on its own:

```bash
python scripts/tests/create_organisation.py
```

## What a script expects

- The portal running on `http://localhost:8000` (`BASE_URL` in `utils.py`).
- An account matching `CREDENTIALS` in `utils.py`, with rights to reach the admin.
- Lithuanian interface language - every element is looked up by its Lithuanian label
  (`get_by_role("link", name="Prisijungti")`), so another language makes the lookups miss.
- `add_blog_post.py` additionally expects a file named `03.png` in a filer folder called
  `skaičiai`.

Scripts that stop mid-way usually mean the admin markup moved. Re-record with
`playwright codegen http://localhost:8000` rather than patching the selectors by hand.
