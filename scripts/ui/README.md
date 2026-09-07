# UI scripts

Recorded browser sessions that drive the portal through Chromium. They live in `scripts/ui/`
rather than under a directory called `tests`. They create content
(pages, stories, organisations, datasets, pending member invitations) so the admin can be
looked at with real data in it.

**These are not tests.** They assert nothing, and they run headed and slowed down so a person can
watch. The automated suite is `tests/`, run with pytest. `VITRINA_UI_HEADLESS=1` turns the browser
off when the point is only to get content into the database.

## What they are for

Two jobs, worth keeping apart.

**Something to look at.** An upgrade is judged by eye: pages still render, articles keep their
text and their images, the menu is still in order. That needs content in the database first, and
retyping it by hand every time a database is rebuilt is how a check quietly stops being done.

**Reaching what pytest cannot.** The django-cms admin is iframe- and JavaScript-driven: the rich
text editor, the versioning toolbar and the publish actions are out of reach for the HTTP client
the pytest suite uses, so there is no way to exercise them without a real browser.

Neither job is the migration itself. These scripts migrate nothing and verify nothing on their
own - they only put content in front of a person who can tell whether it looks right.

## Where they fit in the django-cms upgrade

**Before, to build the baseline.** A clean database on the pre-upgrade code, seeded, then dumped
as the point to return to: clean the database, check out the old code, migrate, create the
superuser, run `create_organization.py`, dump. Every later attempt restores that dump rather than
starting over. The upgrade branch writes this out step by step in `notes/migrations/djangocms` -
those notes reach devel with the django-cms 5 work, not with this branch, so do not go looking
for them here yet.

**After, to see what survived.** The same portal on the new code, gone through by hand, with the
story scripts adding fresh content to show that versioning, the editor and publishing work.

Only some of them work on both sides:

| Any portal | Needs the upgraded portal |
| --- | --- |
| `create_organization.py`, `create_dataset.py`, `create_dataset_with_plan.py`, `add_users_to_org.py`, `update_profile.py` | `create_stories.py`, `create_blog_posts.py`, `add_blog_post.py`, `stories_images.py` |

The right-hand column clicks "Publikuoti Article dabar", which is djangocms-versioning, and fills
`#id_1-abstract_editor`, which is djangocms-text. On django-cms 3.11 with djangocms-blog neither
exists.

**So a database seeded this way cannot test the blog-to-stories half of the upgrade.** There are
no old blog posts in it for that migration to move. Testing that needs an anonymised production
copy, which also brings the real page tree and the path collisions that come with it. Seeded
content still earns its place next to one: with three articles and one organisation you can see
at a glance what went missing, which 59 articles and 5000 datasets will not tell you.

## What runs when

Each script runs on its own, and none of them clean up after themselves.

On either portal, in this order. Only the first stands alone: everything from step 3 on
navigates to Org1, so `create_organization.py` has to have run before them.

1. `update_profile.py` - gives the logged-in account a first and last name.
2. `create_organization.py` - Org1, Org2, Org3. The names are unique in the database, so read
   `VITRINA_UI_ORG_START` below before running it twice.
3. `add_users_to_org.py` - two members for Org1. Invitations, not accounts: the portal only
   emails a registration link, and the user appears when somebody follows it.
4. `create_dataset.py` - one dataset under Org1.
5. `create_dataset_with_plan.py` - a second dataset, then plan entries with deadlines.

On the upgraded portal, in this order, because each leans on the one before:

6. `create_stories.py` - Blog 1 to Blog 3.
7. `create_blog_posts.py` - Blog 4, plus the filer folder `Skaiciai` holding the six local images.
8. `add_blog_post.py` - Blog 5, with one of those images.
9. `stories_images.py` - puts images on Blog 2 and Blog 3.

Steps 8 and 9 need the folder from step 7; step 9 needs the stories from step 6.

## Running one

Playwright is deliberately not a project dependency - only these scripts want it, and they
are run by hand a few times a year. Install it separately, browser included: the pip package
brings the driver, the second command fetches Chromium.

```bash
pip install playwright
playwright install chromium
```

Each script then runs on its own:

```bash
python scripts/ui/create_organization.py
```

## What a script expects

- The portal running on `http://localhost:8000`, or `VITRINA_UI_URL` pointing elsewhere.
- The django-cms Site named `localhost`, or `VITRINA_UI_SITE` naming it. `stories_images.py`
  reaches the stories through the admin's site link, and a deployment names that after itself.
- An account with rights to reach the admin, passed in the environment:

  ```bash
  export VITRINA_UI_EMAIL=...
  export VITRINA_UI_PASSWORD=...
  ```

  The scripts stop with an explanation if either is missing, rather than typing an empty
  password into the form and failing on some later selector.
- One-time codes turned off. `USE_OTP_VALIDATION` defaults to `True`, and every Playwright run
  is a new browser, so the portal treats it as an unrecognised device and asks for a code sent by
  email. The login helper does not answer that challenge - start the portal with
  `USE_OTP_VALIDATION=False` for these scripts.
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
- `create_organization.py` names its organizations Org1, Org2, Org3, and those names are unique in
  the database. Running it twice over the same database collides, so set `VITRINA_UI_ORG_START`
  past the highest number already there.

Scripts that stop mid-way usually mean the admin markup moved. Re-record with
`playwright codegen http://localhost:8000` rather than patching the selectors by hand.

## `content_frame` is a property

`page.locator("iframe").content_frame.get_by_role(...)` is correct and is what
`playwright codegen` emits. Review tooling keeps reporting it as a method that has to be called;
it is not:

```python
>>> inspect.getattr_static(Locator, "content_frame")   # playwright 1.62
<property object>
>>> inspect.signature(...fget).return_annotation
'FrameLocator'
```

Its own docstring says "Returns a `FrameLocator` object pointing to the same `iframe` as this
locator", and `FrameLocator` carries `get_by_text`, `get_by_role` and `locator`.
`page.frame_locator("iframe")` reaches the same place and is equally fine - it is an alternative,
not a fix.
