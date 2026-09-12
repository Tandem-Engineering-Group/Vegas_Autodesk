# Vegas AU 2026 Trip

Team itinerary for Autodesk University 2026 in Las Vegas, Sept 14-16, 2026: flights, the
Fontainebleau hotel, Stadium Swim at Circa, the AU conference day at the Venetian Convention &
Expo Center, a pinned schematic map with Google Maps links, confirmations, and open items.

Live site: https://tandem-engineering-group.github.io/Vegas_Autodesk/

## How it's built

- `index.html` is the whole site: one self-contained page, no build step, Google Fonts only.
- `.github/workflows/pages.yml` publishes `index.html` to GitHub Pages on every push.
  If the first run fails on the "Configure Pages" step, enable Pages once in
  **Settings → Pages → Source: GitHub Actions** and re-run the workflow.

## What is deliberately not on the public page

Booking confirmation codes, the Stadium Swim QR entry ticket and the driver's phone number are
kept off this public copy. The full version is on the private team link that Richard shares.
