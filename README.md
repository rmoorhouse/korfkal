# KorfKal

Subscribable calendar feeds for korfball fixtures. Turns a league fixture
spreadsheet into `.ics` calendars that players subscribe to once and never have
to re-import.

Currently publishing **Bromley Korfball Club, 2026-27**.

**Subscribe:** https://rmoorhouse.github.io/korfkal/

Pick your team, tap **Add to phone** (iPhone) or **Add to Google** (Android).

| Calendar | Fixtures |
|---|---|
| `bromley.ics` | All teams (64) |
| `bromley-1.ics` | Bromley 1 — National League (16) |
| `bromley-2.ics` | Bromley 2 — LKA 1 (16) |
| `bromley-3.ics` | Bromley 3 — LKA 2 (14) |
| `bromley-4.ics` | Bromley 4 — LKA 3S (10) |
| `bromley-5.ics` | Bromley 5 — LKA 3S (10) |

## What's in an event

Title is `Home team v Away team (League)`, location is the venue, and the
description carries the league, matchweek, whether it's home or away, the
throw-off time, an **arrive-by** time, and — for home games — the hall booking
window.

Events run from throw-off to the expected final whistle: 78 minutes for National
League (30 + 10 + 30 plus timeouts), 68 for other games (50 + 10 half-time plus
timeouts).

## Draft status

These are generated from a **draft** fixture list and will change.

- Fixtures under query are marked **tentative** and carry a note explaining why.
- Away National League games appear as **all-day events** until throw-off times
  are confirmed.

## Regenerating

```
python3 generate_ics.py "<fixtures>.xlsx" \
    --base-url https://rmoorhouse.github.io/korfkal
```

Requires `openpyxl`. Writes into `docs/`, which GitHub Pages serves.

Event UIDs are derived from the teams and date, so regenerating updates existing
events in subscribers' calendars rather than duplicating them. **Do not change
`UID_NAMESPACE` in the script** once published.

The source fixture workbook is deliberately not committed — it contains other
clubs' hall availability and contact preferences.

## Known limitation

Google refreshes subscribed calendars on its own schedule, typically every
8–24 hours. Same-day fixture changes will not reach subscribers promptly. Apple
Calendar refreshes more often and can be set per-calendar.

## Not seeing it on your phone?

Newly added calendars are hidden by default in the Google Calendar app. Open the
app, then ☰ → Settings, and tick the calendar to make it visible.
