# AU 2026 — session catalog, shortlist, and material harvester

Everything about Autodesk University 2026 (Las Vegas, Sept 15–17, 2026) that could be
collected from public sources, in one place. Live page:
**https://tandem-engineering-group.github.io/Vegas_Autodesk/au2026/**

| What | Where | Notes |
|---|---|---|
| Searchable catalog page | `index.html` | 708 learning sessions, filter by day and theme, search title/speaker/abstract. Every title links to the official session page. |
| Full catalog, machine-readable | `data/au2026_catalog.json` | 750 rows: code, title, type, abstract, speakers, times, room, topics, level, URL |
| Full catalog, spreadsheet | `data/AU2026_catalog_750_sessions.csv` | same data, one row per session |
| Shortlist by day | `shortlist.md` | 453 sessions title-matched to Forma/data, AI/MCP, Civil 3D/AutoCAD, Revit/BIM, delivery/digital twins |
| Harvester | `harvest/` | Python + Playwright tool that signs in as you (visible browser) and downloads each session's handouts, decks and recordings to your PC. See `harvest/README.md`. Status AMBER: untested against the live site. |

## Keynotes (public, no sign-in)
- Day 1, Sept 15 — "Building AI for the Real World", Andrew Anagnost with Clara Shih: https://www.youtube.com/watch?v=dC-DqjnZonk
- Day 2, Sept 16 — AI in practice keynote: https://www.youtube.com/watch?v=mC1DyJTaDjI
- All AU streams: https://www.youtube.com/user/AutodeskUniversity/streams

## Announcement coverage
- AEC Magazine — Anagnost pitches "project intelligence" across Autodesk: https://aecmag.com/ai/anagnost-pitches-project-intelligence-across-autodesk
- AEC Magazine — Autodesk pushes Forma upstream and connects Civil 3D: https://aecmag.com/civil-engineering/autodesk-pushes-forma-upstream-and-connects-civil-3d
- ENR — Autodesk connects Civil 3D to Forma, creates unified coordinate system: https://www.enr.com/articles/63666-autodesk-connects-civil3d-to-forma-creates-unified-coordinate-system
- Architosh — AU2026: Autodesk expands Forma and leverages AI: https://architosh.com/2026/09/au2026-autodesk-expands-forma-and-leverages-ai/
- Autodesk News — AI and project intelligence at AU: https://adsknews.autodesk.com/en/news/autodesk-design-make-vision-au-2026/
- Autodesk News — Forma and AI for connected AEC workflows: https://adsknews.autodesk.com/en/news/autodesk-forma-ai-aec-connected-workflows-2026
- Engineering.com — Fusion news and more from AU 2026: https://www.engineering.com/fusion-news-and-more-from-au-2026/

## Code Autodesk published for AU 2026 classes
- Agent Skills for Autodesk Platform Services (MIT), incl. an MCP-server generator: https://github.com/autodesk-platform-services/skills
  — install with `npx skills add autodesk-platform-services/skills --global`
- Platform Leadership Forum MCP workshop, beginner: https://github.com/autodesk-platform-services/au2026-mcp-workshop-beginner
- Platform Leadership Forum MCP workshop, advanced: https://github.com/autodesk-platform-services/au2026-mcp-workshop-advanced
  — both carry step-by-step tutorials in `docs/`.

## Where the catalog came from
Autodesk's own hosts could not be reached from the environment that built this folder, so the
catalog is a snapshot of the public RainFocus search API that the AU "Digital" tab uses, as
published in https://github.com/Yushi219/AU-Schedule-Notebook (`data/catalog.js`, plus the
`scripts/fetch-catalog.mjs` that produced it). A second, older snapshot with 517 in-person rows
lives at https://github.com/chuongmep/wth-au-2026. The same notebook repo also holds an
attendee's rough live transcripts for 14 AI/MCP sessions under `notes/<CODE>.json`.

Titles, abstracts and speaker listings are Autodesk's and the speakers'. This folder redistributes
the public listing only; handouts, decks and recordings are not here and require an Autodesk
sign-in, which is what `harvest/` is for.
