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

## Source of truth

**Heja is now the source**, not the LKA workbook:

```
node ~/heja-cli/heja.mjs export --window all --ics -o /tmp/heja-src.ics
python3 generate_ics.py /tmp/heja-src.ics --from 2026-09-01 \
    --base-url https://rmoorhouse.github.io/korfkal
```

Heja is a superset once reconciled against the LKA draft: it carries
pre-season and friendly fixtures the workbook never contains, plus real venue
addresses. The workbook remains the authority for *league* fixtures, so the
order is: LKA draft → `heja reconcile` → Heja → KorfKal.

The generator still reads the workbook directly (pass the `.xlsx` instead) —
useful for diffing a new draft before pushing it into Heja. Current copy:
`~/KorfKal/LKA Fixtures 26-27 Draft v0.03.xlsx` (filename says v0.03, the
sheet's own header says v0.06).

`--from` matters with Heja input: an export spans years of history.

Only events titled "A v B" naming a real `<Club> <number>` team are taken, so
training, trials and socials stay off the public site. Team matching is exact:
a loose prefix test let historical titles like "Bromley 3 friendly" and
"Bromley1" become their own bogus per-team calendars.

## Do not import KorfKal descriptions into Heja

KorfKal writes a block into each event's `.ics` description:

```
League: LKA 2
Matchweek: 1
Away
Throw-off: 13:10
Arrive by: 12:50
Hall booked: 13:20-17:55
```

That is for **calendar subscribers**, who have no other way to see the league,
the arrive-by time or the hall window. It must not end up in Heja.

Heja already shows all of it as structured fields — start time, meet time,
home/away, opponent, location — and renders them itself. Importing the text
copies it into Heja's free-text "Additional info", where it is duplicated on
arrival and then **frozen**: it does not move when the fixture is retimed or
rescheduled. 62 fixtures carried a block from an August import that by
September contradicted the event it sat on, telling players a throw-off time
an hour out from the one directly above it.

So: `heja import` / `bulk` from a KorfKal file should not carry the
description. Anything genuinely Heja's — "£5 per player, card readers on
site" — lives in that field and must be preserved; filter on the block's
`League:` opening rather than clearing wholesale.

Same trap, different field: `heja update --start` used to leave the end and
meet times behind, because both are stored as absolute timestamps. Fixed in
heja-cli f09740d, which shifts them with the start unless `--absolute-times`
is passed. Anything that mirrors a time into a second place will drift.

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

Built from **LKA draft v0.03** (via Heja). Nine fixtures carry
`STATUS:TENTATIVE` with a note, listed in `QUERIES` in `generate_ics.py`. When
a new draft lands, update that dict — stale queries are worse than none.

Outstanding with the LKA (detail kept outside this repo):

- **Seven fixtures fall on dates Bromley declared unavailable** (1 Nov, 24 Jan,
  14 Feb ×2, 21 Feb, 4 Apr, 11 Apr). All involve the 1st or 2nd team; v0.03
  keeps 3s/4s/5s clear on every one, so the LKA appears to have read the
  "especially for 3s and 4s" caveat literally. The one to push hardest is
  **24 Jan**: a home fixture, the only game that day, on a declared no-go date.
- **Kingfisher v Trojans 1 is scheduled twice**, both away.
- Two National League warm-ups fall below the 30-minute minimum: 8 Nov at
  Trojans (17 min) and 10 Jan at Bec (27 min).
- Bromley hosts LKA 3 play-offs at Langley Park on **14 March** — a hall
  booking not in the club's own fixture list.

Resolved since v0.01: the 7 February court clash, the "Highbury (TBC)" venue
(now Excelsior), and most booking overruns.

**Not a defect:** Bromley 1 appears to be missing two EKA fixtures (home v
Bristol Thunder, away at Nomads 1). They exist — as pre-season games on 20 and
27 September, before the LKA season opens. The league calendar simply does not
carry them. Do not raise these.
