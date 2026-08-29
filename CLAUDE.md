# KorfKal — working notes

Generates subscribable `.ics` fixture feeds from a London Korfball Association
fixture spreadsheet. Published via GitHub Pages at
https://rmoorhouse.github.io/korfkal/ for Bromley Korfball Club.

## Repository conventions

**This repo is public.** Nothing internal, employer-related, or personal goes in
it. Before committing, check the tree for internal hostnames and identifiers.

**Use a repo-local git identity.** The machine's global git config uses a work
email address. This repo sets its own:

```
git config user.name "rmoorhouse"
git config user.email "rmoorhouse@users.noreply.github.com"
```

**Two `gh` hosts are configured.** Always prefix GitHub.com calls with
`GH_HOST=github.com`, or commands may hit the wrong host.

**Never change `UID_NAMESPACE` in `generate_ics.py`.** Event UIDs are hashed
from the namespace, teams and date. Subscribers' calendars match on UID, so a
changed namespace duplicates every event for everyone. This is the single most
damaging mistake available in this codebase.

**The source workbook is not committed** and is gitignored. It contains other
clubs' hall availability and contact preferences. Analysis outputs that quote
that data are kept in the parent directory, outside this repo, deliberately.

Source workbook currently lives at
`~/Downloads/LKA Fixtures 26-27 Draft v0.01.xlsx`.

## Domain rules

These came from the club and are **not** stated anywhere in the spreadsheet.
They drive event durations and every scheduling check.

| Rule | Value |
|---|---|
| National League match | 30 + 10 half-time + 30 = 70 min |
| Other league match | 50 play + 10 half-time = 60 min |
| Timeouts | 2 per team, up to 2 min each — so **+8 min worst case** |
| Worst-case occupancy | NL 78 min, other 68 min — what the generator uses |
| NL warm-up minimum | **30 min of free court** before throw-off (strict reading, confirmed by the club) |
| Courts at Langley Park | **One.** Games are strictly sequential. |
| Hall charging | **Hourly blocks** — an 8-minute overrun costs a full hour |
| Langley Park availability | From **13:00**, despite Club Avail recording "13:20 to TBC" |

Non-NL warm-up has no stated minimum; the generator assumes 20 min for the
arrive-by time.

## Spreadsheet quirks

- The **Calendar** tab is authoritative; other tabs are derived or working notes.
- Away National League fixtures have **no throw-off time and no hall booking** —
  those come from the EKA. They become all-day events.
- **Club Avail** is free text, not structured. The unavailable-date parser in
  `check_fixtures.py` reads prose and is best-effort.
- Non-London clubs only appear in fixtures against London clubs, so a naive
  round-robin check reports huge numbers of false "missing" fixtures. Only check
  London teams as the subject.
- Only **Bec, Bromley, Nomads and Trojans** have National League teams. The
  guidelines' hard rule about 2nd teams sharing a venue applies to those four
  only — not to Highbury, Supernova, East London or Croydon, whose 1st teams
  play LKA 1. (Supernova 1 also plays Promo; unclear whether the rule extends
  to Promo clubs.)

## Design

Tokens are lifted from bromleykorfball.com (WordPress block theme, no published
design system):

- Orange `#F78F1E` — links, buttons, rules
- Ink `#0F1518` — text, hover state
- Figtree, weights 400/600/800

The club crest is **not** used: their server 403s direct image requests, and
copying the asset into a public repo would be republishing it without asking.
The header is a Figtree wordmark instead.

## Known limitations

- Google refreshes subscribed calendars roughly every **8–24 hours**. Same-day
  fixture changes will not reach subscribers promptly. Fixing this properly
  means the Google Calendar API rather than a hosted feed.
- No GitHub Action yet to regenerate on commit. The github.com token lacked the
  `workflow` scope; `gh auth refresh -h github.com -s workflow` would enable it.

## Draft status

Built from **v0.01**. Seven fixtures are marked `STATUS:TENTATIVE` with an
explanatory note, listed in `QUERIES` in `generate_ics.py`. When a new draft
lands, update that dict — stale queries are worse than none.

Outstanding issues raised with the LKA (detail kept outside this repo):

- Bromley 1 is missing two National League fixtures; eight are missing across
  the four London NL clubs, plus one duplicated fixture.
- Three Bromley fixtures fall on dates the club declared unavailable, including
  14 Feb 2027 at home.
- 7 Feb 2027 cannot be played as drawn — four games do not fit the booking and
  the last two overlap.
