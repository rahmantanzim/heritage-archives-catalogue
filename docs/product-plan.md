# Heritage Archives Catalogue: Product Plan

_Status: planned. Last updated November 2026._

This plan describes where the catalogue goes next: from a data pipeline and search API to a public catalogue website with an admin panel for archive staff.

## 1. Goal

- **For researchers:** anyone, anywhere, can find an item in the archive in seconds, in Bengali or English.
- **For the archive staff:** they can keep the catalogue up to date themselves, without a developer.

## 2. Who uses it

| User | What they need |
|---|---|
| Researchers and students | Search, browse by category, see full item details, share or cite an item |
| Archive staff (editors) | Upload new catalogue files, fix a single record, check problems the pipeline found |
| Owner (admin) | Everything editors can do, plus manage staff accounts |

## 3. Import flow: review before publish

Nothing goes public straight from an upload:

**Upload → pipeline → preview → staff approve → publish**

- **Preview** shows what will change before it changes, for example "120 new records, 8 changed, 3 problems to check".
- **Each upload is saved as a batch** (one import, with its date and who did it). A bad upload can be rolled back in one step.
- **Staff can edit a single record** in the admin panel, without re-uploading a whole file.

Over time, the database becomes the catalogue's **source of truth**. Word and Excel files become only a way to add records in bulk.

## 4. How the data is shown

The site follows the pattern used by library and museum catalogues: **search first, then results as a clean list**, not one giant table.

- **Home page:** one large search box, plus category tiles with item counts (Periodicals, Books, Posters, Leaflets, Theses, Biographies, District books).
- **Results list:** one compact row per item: title (Bengali and English when both exist), category, year, catalogue number.
- **Item page:** every item has its own permanent URL, so it can be shared, cited and found by search engines. Includes a "Cite this item" button.
- **Master list:** the results page with no search typed: all items, with filters.
- **Category pages:** the same results page with the category filter already set, for example `/catalogue/periodicals`.
- **Optional table view:** a dense, sortable table for staff and power users.
- **Shareable searches:** the search and filters live in the URL.
- **Design:** clean and uncluttered, one accent colour, a good Bengali font (Noto Sans Bengali or Hind Siliguri), mobile-first.

## 5. Filters

A filter is added only if the data supports it. Each option shows a count, for example "Periodicals (4,210)", and the counts update as filters change (**faceted search**).

- Category (source catalogue)
- Language (Bengali, English, both)
- Year or date range
- Subject (from the archive's subject index)
- Place or district, where recorded
- Later: has a digital copy

## 6. Search, in measured stages

| Stage | What it does | Notes |
|---|---|---|
| 1. Keyword search (done) | Finds words, tolerates small spelling differences | PostgreSQL trigram search (`pg_trgm`) |
| 2. Transliteration | Typing "Rabindranath" also finds রবীন্দ্রনাথ | Many researchers can't type Bengali |
| 3. Meaning-based search | Finds items about the same idea in different words | Embeddings stored in PostgreSQL with `pgvector` |
| 4. Hybrid ranking | Combines keyword and meaning scores | Keeps exact-name matches strong while adding meaning |
| 5. "Ask the archive" | A chat answer that always links to real items | Retrieval-augmented generation (RAG); never invents items |

**Measurement:** a set of 50 real test searches with the items that should rank first, run before and after each stage. A stage is kept only if results improve. This follows the same approach as the 200-cell conversion accuracy check.

**Cost:** embeddings are created once at import time, not on every search.

## 7. Architecture

- **Frontend:** Next.js, for the public site and the admin panel.
- **Backend:** the existing FastAPI service, extended with admin endpoints.
- **Database:** PostgreSQL with `pg_trgm` (in use) and `pgvector` (stage 3).
- **Pipeline:** the existing Python pipeline, run as a background job so large uploads don't block the admin panel. FastAPI background tasks first; Redis and Celery only if needed.
- **File storage:** uploaded files are kept so every batch can be traced to its original file.
- **Authentication:** owner and editor roles, using a proven authentication library.
- **Hosting:** Next.js on Vercel; API and database on a small managed server, with daily database backups.

## 8. Quality standards

- Bilingual interface (Bengali and English).
- Accessible: WCAG 2.1 AA (keyboard use, contrast, screen readers).
- Search-engine friendly: indexable item pages and a sitemap.
- Fast: search responses under half a second.
- Safe: backups, logged admin actions, no private data made public.
- Tested: automated tests in GitHub Actions for every change.

## 9. Roadmap

| Phase | What ships | When |
|---|---|---|
| 0. Foundation | Pipeline, database, search API, tests, Docker demo, measured accuracy | Done |
| 1. Public catalogue | Search, category pages, item pages, filters, deployed (read-only) | December 2026 |
| 2. Admin panel | Login, upload with preview and approval, single-record editing, import history | Early 2027 |
| 3. Smarter search | Transliteration, meaning-based and hybrid search, 50-query quality test | After phase 2 |
| 4. Full website | Move heritage-archives.org off WordPress, with redirects for old links | After phase 3 |
| 5. Digitization | Scans and OCR (turning scanned pages into searchable text), "Ask the archive" | Later |

Each phase ends with something live and usable.

## 10. Success measures

- Staff can add a new catalogue file without a developer.
- Researchers find what they need: how often a search leads to opening an item.
- The archive receives research requests from people who found items through the site.

## 11. Risks

- **Scope creep:** ship one phase at a time.
- **Messy new uploads:** the preview and review step catches problems before they go public.
- **One developer:** keep the stack small and documented so someone else could take over.
- **Hosting cost:** start on free or low-cost tiers; traffic is modest.
