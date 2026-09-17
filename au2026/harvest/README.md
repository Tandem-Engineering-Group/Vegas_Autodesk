# AU 2026 harvester (`au2026/harvest/`)

Pulls session **decks, handouts, datasets and recordings** from Autodesk University 2026
into a folder on your PC, writes a `manifest.csv`, and drops a one-page note per class
that can be filed by `/organize`.

**Status: AMBER.** The logic is tested (`python -m unittest discover -s au2026/harvest/tests`), but the
browser driver was written without access to any Autodesk host, so the first run against
the live site will probably need one round of selector tuning. It is built to fail soft:
one bad link never stops the run, and every class is checkpointed to the manifest.

## Why this runs on your PC and not in the cloud
The materials sit behind your Autodesk sign-in. The script opens a **visible** Chromium
window with a persistent profile; you sign in once, then it drives the browser. Your
password never touches the script. This is the host/remote pattern from the
remote-agents whitepaper: the desktop does the work, you can watch from your phone.

## Run (catalog mode — preferred)
`../data/au2026_catalog.json` is the full public AU 2026 catalog (750 sessions, with the
session-page URL for each). Catalog mode skips list-page scraping entirely and visits
every session URL directly, so the only thing that can need tuning is the download-link
detection on the session page.

```powershell
pip install -r au2026/harvest/requirements.txt
playwright install chromium

# smoke test: the three MCP/Claude sessions, decks only
python au2026/harvest/au_harvest.py --out "$env:USERPROFILE\Tandem\AU2026" `
    --from-catalog au2026/data/au2026_catalog.json --codes "AS2183,CS1316,BES4067" --skip-video

# full pull, notes straight into the org-brain inbox for /organize
python au2026/harvest/au_harvest.py --out "$env:USERPROFILE\Tandem\AU2026" `
    --from-catalog au2026/data/au2026_catalog.json --notes-dir "$env:USERPROFILE\Tandem\AU2026\_notes" --ytdlp
```
When the browser opens: sign in, then press Enter in the terminal. `--dates 2026-09-15`
limits to a day; logistics rows (meals, merch store, receptions) are skipped automatically.

## Run (discovery mode — fallback)
Omit `--from-catalog` and the tool scrapes whatever list page is on screen. Use this only
if the catalog file is stale. If it reports `found 0 class links`, copy the URL of the page
that lists the classes and re-run with `--start-url <that url>`.

`--start` options: `library` (post-event class library, where recordings land),
`catalog` (the RainFocus session catalog the Events app mirrors), `myschedule` (only
your saved sessions).

## What lands where
```
<out>/
  manifest.csv                      one row per material: class, kind, file, bytes, status
  <class-slug>/
    meta.json                       title, speakers, description, links, streams
    *.pdf *.pptx *.mp4 ...          the downloads
  _notes/au2026-<class-slug>.md     inbox-style note (or --notes-dir "$env:USERPROFILE\Tandem\AU2026\_notes")
```
Statuses: `saved`, `skipped` (already present), `failed` (see `note`), `stream`
(a player embed; pull with `--ytdlp` or by hand).

## Where the catalog came from
The Autodesk hosts were unreachable from the build environment. The catalog JSON was taken
from a public GitHub snapshot (github.com/Yushi219/AU-Schedule-Notebook, `data/catalog.js`)
of the RainFocus search API that the AU "Digital" tab uses (`attend.autodesk.com/api/search`,
no login). To refresh it on your PC, that repo's `scripts/fetch-catalog.mjs` +
`build-catalog.mjs` regenerate it; copy the result over `../data/au2026_catalog.json`.

## Timing
Autodesk publishes recordings to the class library over the weeks after the conference.
Re-run with the same `--out`; anything already saved is skipped, new material is added.

## Guardrails
- Read-only against Autodesk. Polite 1.5 s delay between classes.
- Personal-use download under your AU registration. Share internally via SharePoint,
  not by re-publishing.
- No credentials in the repo. The browser profile lives in `~/.au_harvest_profile`
  (outside the repo) and is never committed.
