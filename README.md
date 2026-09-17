# AU 2026 Portal

Landing portal for Autodesk University 2026: https://tandem-engineering-group.github.io/Vegas_Autodesk/

- `index.html` — the portal: sessions by theme, keynotes, announcement coverage, Autodesk's class code, downloads, trip.
- `au2026/` — searchable catalog page, data (CSV/JSON), shortlist, material harvester. See [`au2026/README.md`](au2026/README.md).
- `itinerary/` — the password-protected team itinerary (below).

## Team itinerary (`itinerary/`)

Password-protected team itinerary for Autodesk University 2026 in Las Vegas, Sept 14-16, 2026:
flights, the Fontainebleau hotel, Stadium Swim at Circa, the AU conference day at the Venetian
Convention & Expo Center, a pinned schematic map with Google Maps links, confirmations, tickets,
driver contact and open items.

Live site: https://tandem-engineering-group.github.io/Vegas_Autodesk/

## How the password protection works

The repo is public, so the page itself is stored encrypted. `itinerary/index.html` is a small unlock screen
plus an AES-256-GCM ciphertext of the full itinerary. The key is derived in the browser from the
team password with PBKDF2-SHA256 (600,000 rounds) using the Web Crypto API; decryption happens
on the device and nothing readable is stored on GitHub. Ask Richard Letts for the password.

## Updating the content

The plaintext page is not kept in this repo. To publish a change, edit the plaintext copy, re-encrypt
it with the same password (Node's built-in `crypto` is enough: PBKDF2-SHA256 -> AES-256-GCM, tag
appended to the ciphertext), drop the new `{salt, iv, ct}` JSON into the `#payload` script tag in
`itinerary/index.html`, and push.

## Deploy

`.github/workflows/pages.yml` publishes `index.html`, `au2026/` and `itinerary/` to GitHub Pages on every push to the default branch. Pages must be
enabled once in **Settings -> Pages -> Source: GitHub Actions**; after that every push redeploys.
