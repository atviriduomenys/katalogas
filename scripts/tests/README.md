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
python scripts/tests/create_organization.py
```

## What a script expects

- The portal running on `http://localhost:8000`, or `VITRINA_UI_URL` pointing elsewhere.
- An account with rights to reach the admin, passed in the environment:

  ```bash
  export VITRINA_UI_EMAIL=...
  export VITRINA_UI_PASSWORD=...
  ```

  The scripts stop with an explanation if either is missing, rather than typing an empty
  password into the form and failing on some later selector.
- Lithuanian interface language for the portal itself - its elements are looked up by their
  Lithuanian label (`get_by_role("link", name="Prisijungti")`), so another language makes those
  lookups miss.
- The django-cms toolbar is a different matter: it follows the session language, and these
  recordings were made in both, so some labels came out Lithuanian ("Naujas +") and some English
  ("Publish"). Those are matched either way now. A few are not - "+ properties..." for one - so a
  script stopping on a toolbar label is worth reading as a language mismatch before anything else.
- `create_blog_posts.py` uploads six local images (`00.jpg`, `01.jpg`, `02.jpg`, `03.png`,
  `04.png`, `05.png`). They are not in the repository - put them somewhere and point
  `VITRINA_UI_IMAGES` at that directory, or run the script from it. The script stops with the
  list of what it could not find.
- `add_blog_post.py` and `stories_images.py` expect those images to be uploaded already, in a
  filer folder called `Skaiciai` - the one `create_blog_posts.py` creates.
- `stories_images.py` also expects the stories named in its `STORY_TITLES` to exist.

Scripts that stop mid-way usually mean the admin markup moved. Re-record with
`playwright codegen http://localhost:8000` rather than patching the selectors by hand.
