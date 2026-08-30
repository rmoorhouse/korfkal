#!/usr/bin/env python3
"""KorfKal - generate iCalendar (.ics) fixture feeds for a korfball club.

Usage:
    python3 generate_ics.py "LKA Fixtures 26-27 Draft v0.01.xlsx" [--club Bromley] [--outdir docs]

Produces, in --outdir:
    bromley.ics        every club fixture
    bromley-1.ics ...  one per team
    index.html         subscribe links for phones

Design notes
------------
* Event UIDs are deterministic (hash of club/teams/date), so re-running after a
  new draft updates existing events in subscribers' calendars rather than
  creating duplicates. Never change UID_NAMESPACE once published.
* Times are emitted in UTC. The season crosses a DST boundary, so local wall
  times are converted via the Europe/London zone rather than written naively.
* Away National League fixtures have no throw-off time in the source workbook;
  they become all-day events rather than being dropped.
"""

import argparse
import hashlib
import html
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import venues as venue_book

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl required:  pip install openpyxl")

UID_NAMESPACE = "korfkal-fixtures"
LOCAL = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")

NL_LEAGUE = "EKA"
NL_DURATION = 78          # 30 + 10 + 30 plus four 2-minute timeouts
LKA_DURATION = 68         # 50 + 10 half-time plus timeouts
NL_ARRIVAL = 30           # minutes before throw-off
LKA_ARRIVAL = 20

COL = dict(matchweek=3, date=4, league=5, home_club=7, home_team=8,
           away_club=9, away_team=10, venue=11, hall_start=12,
           hall_end=13, throw_off=14, notes=15)

# Fixtures under query, keyed by (date ISO, home team, away team).
QUERIES = {
    ("2027-02-14", "Bromley 1", "Birmingham City"):
        "QUERY: Bromley declared 14 February unavailable (Club Avail). Under review with the LKA.",
    ("2027-02-21", "Cambridge Tigers", "Bromley 1"):
        "QUERY: Bromley declared 21 February unavailable (Club Avail). Under review with the LKA.",
    ("2027-04-11", "Kingfisher", "Bromley 1"):
        "QUERY: Bromley declared 11 April unavailable (Club Avail). Under review with the LKA.",
    ("2027-02-07", "Bromley 5", "Croydon 4"):
        "QUERY: throw-off clashes with the previous game on the same court. Time likely to move.",
    ("2027-02-07", "Bromley 4", "Supernova 5"):
        "QUERY: very tight turnaround; time may move if 7 Feb is rescheduled.",
    ("2026-11-08", "Trojans 1", "Bromley 1"):
        "QUERY: only 17 minutes of free court before throw-off, below the 30-minute National League minimum.",
    ("2027-01-10", "Bec 1", "Bromley 1"):
        "QUERY: only 27 minutes of free court before throw-off, below the 30-minute National League minimum.",
}


def duration_for(league):
    return NL_DURATION if league == NL_LEAGUE else LKA_DURATION


def arrival_for(league):
    return NL_ARRIVAL if league == NL_LEAGUE else LKA_ARRIVAL


def load_fixtures(path, club):
    workbook = openpyxl.load_workbook(path, data_only=True)
    fixtures = []
    for row in workbook["Calendar"].iter_rows(min_row=2, values_only=True):
        if not (row[COL["date"]] and row[COL["home_team"]] and row[COL["away_team"]]):
            continue
        fixture = {k: row[i] for k, i in COL.items()}
        if club not in (str(fixture["home_club"]), str(fixture["away_club"])):
            continue
        fixtures.append(fixture)
    return sorted(fixtures, key=lambda f: (f["date"], f["throw_off"] or datetime.min.time()))


def teams_of(fixture, club):
    """Which of the club's teams are involved (usually one)."""
    return [t for t in (fixture["home_team"], fixture["away_team"])
            if str(t).startswith(club)]


def uid_for(fixture):
    key = f"{UID_NAMESPACE}|{fixture['date']:%Y-%m-%d}|{fixture['home_team']}|{fixture['away_team']}"
    return hashlib.sha1(key.encode()).hexdigest() + "@korfkal"


def fold(line):
    """iCalendar lines must not exceed 75 octets; continuation lines start with a space."""
    out, current = [], line
    while len(current.encode()) > 73:
        cut = 73
        while len(current[:cut].encode()) > 73:
            cut -= 1
        out.append(current[:cut])
        current = " " + current[cut:]
    out.append(current)
    return out


def esc(text):
    return (str(text).replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))


def as_utc(date, time):
    return datetime.combine(date, time, tzinfo=LOCAL).astimezone(UTC)


def build_event(fixture, club, stamp):
    home, away = fixture["home_team"], fixture["away_team"]
    is_home = str(fixture["home_club"]) == club
    venue = str(fixture["venue"] or "TBC")
    league = fixture["league"]

    lines = ["BEGIN:VEVENT",
             f"UID:{uid_for(fixture)}",
             f"DTSTAMP:{stamp:%Y%m%dT%H%M%SZ}",
             f"SUMMARY:{esc(f'{home} v {away}')} ({esc(league)})"]

    description = [f"League: {league}",
                   f"Matchweek: {fixture['matchweek']}",
                   "Home" if is_home else "Away"]

    if fixture["throw_off"]:
        start = as_utc(fixture["date"], fixture["throw_off"])
        end = start + timedelta(minutes=duration_for(league))
        arrive = (start - timedelta(minutes=arrival_for(league))).astimezone(LOCAL)
        lines += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}",
                  f"DTEND:{end:%Y%m%dT%H%M%SZ}"]
        description.append(f"Throw-off: {fixture['throw_off']:%H:%M}")
        description.append(f"Arrive by: {arrive:%H:%M}")
        if is_home and fixture["hall_start"] and fixture["hall_end"]:
            description.append(
                f"Hall booked: {fixture['hall_start']:%H:%M}-{fixture['hall_end']:%H:%M}")
    else:
        # No time set (away National League trips) - all-day event.
        lines += [f"DTSTART;VALUE=DATE:{fixture['date']:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{fixture['date'] + timedelta(days=1):%Y%m%d}"]
        description.append("Throw-off: TBC - time to be confirmed by the EKA")

    if fixture["notes"]:
        description.append(str(fixture["notes"]))

    query = QUERIES.get((f"{fixture['date']:%Y-%m-%d}", str(home), str(away)))
    if query:
        description.append("")
        description.append(query)
        lines.append("STATUS:TENTATIVE")

    lines += [f"LOCATION:{esc(venue_book.full_location(venue))}",
              f"DESCRIPTION:{esc(chr(10).join(description))}",
              "END:VEVENT"]
    return lines


def build_calendar(fixtures, club, name):
    stamp = datetime.now(tz=UTC)
    lines = ["BEGIN:VCALENDAR",
             "VERSION:2.0",
             "PRODID:-//KorfKal//Fixtures//EN",
             "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH",
             f"X-WR-CALNAME:{esc(name)}",
             "X-WR-TIMEZONE:Europe/London",
             f"X-WR-CALDESC:{esc(f'{name} - 2026-27 season. Draft fixtures, subject to change.')}"]
    for fixture in fixtures:
        lines += build_event(fixture, club, stamp)
    lines.append("END:VCALENDAR")

    folded = []
    for line in lines:
        folded.extend(fold(line))
    return "\r\n".join(folded) + "\r\n"


def slug(team):
    return re.sub(r"[^a-z0-9]+", "-", str(team).lower()).strip("-")


STYLE = """
 /* Design tokens taken from bromleykorfball.com */
 :root{--orange:#F78F1E;--ink:#0F1518;--muted:#5d666a;--line:#e4e7e8;--wash:#fdf6ee}
 *{box-sizing:border-box}
 body{font:16px/1.55 Figtree,system-ui,-apple-system,sans-serif;margin:0;
   padding:1.5rem;max-width:44rem;color:var(--ink)}
 header{border-bottom:4px solid var(--orange);padding-bottom:.9rem;margin-bottom:1.35rem}
 .brand{font-size:1.7rem;font-weight:800;letter-spacing:-.025em;margin:0;
   text-transform:uppercase}
 .brand a{color:inherit;text-decoration:none;font-weight:800}
 .brand span{color:var(--orange)}
 .tag{color:var(--muted);margin:.2rem 0 0;font-size:.95rem;font-weight:600}
 h2{font-size:1.05rem;font-weight:800;margin:0 0 .2rem}
 p.sub{color:var(--muted);margin:0 0 1.25rem;font-size:.95rem}
 a{color:var(--orange);font-weight:700}
 a:hover{color:var(--ink)}
 table{border-collapse:collapse;width:100%}
 td{padding:.8rem .4rem;border-top:1px solid var(--line);vertical-align:middle}
 .count{color:var(--muted);font-size:.85rem;font-weight:400}
 .btn{display:inline-block;padding:.44rem .8rem;margin:.15rem .15rem .15rem 0;
   background:var(--orange);color:#fff;text-decoration:none;border-radius:.3rem;
   font-size:.85rem;font-weight:700}
 .btn:hover{background:var(--ink);color:#fff}
 .btn.plain{background:#eef0f1;color:var(--ink)}
 .btn.plain:hover{background:var(--ink);color:#fff}
 .note,.warn{background:var(--wash);padding:.8rem 1rem;border-radius:.4rem;
   font-size:.9rem;border-left:4px solid var(--orange)}
 .warn{background:#fff4e5;border-left-color:#cf2e2e}
 footer{margin-top:2rem;padding-top:.9rem;border-top:1px solid var(--line);
   color:var(--muted);font-size:.82rem}
 /* fixture list */
 .fx{margin-top:.5rem}
 .fx td{padding:.7rem .4rem}
 .fx .when{white-space:nowrap;font-weight:700;width:6.4rem}
 .fx .when small{display:block;font-weight:400;color:var(--muted)}
 .fx .who{font-weight:600}
 .fx .where{color:var(--muted);font-size:.87rem;font-weight:400}
 .ha{display:inline-block;min-width:1.15rem;padding:.05rem .32rem;margin-right:.4rem;
   border-radius:.2rem;font-size:.72rem;font-weight:800;vertical-align:.08em}
 .ha.h{background:var(--orange);color:#fff}
 .ha.a{background:#eef0f1;color:var(--muted)}
 .fx .where a{font-weight:600}
 .fx .where a.unsure{border-bottom:1px dotted currentColor;text-decoration:none}
 .tent{color:#b3560c;font-size:.82rem;font-weight:600;display:block;margin-top:.2rem}
 .mth{font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;
   color:var(--muted);padding-top:1.1rem}
"""

FONT_LINKS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;800&display=swap"
      rel="stylesheet">"""


def build_team_page(club, label, fixtures, filename, base_url, team=None):
    """Human-readable fixture list for one calendar.

    `team` is the single team this page covers, or None for the club-wide page.
    Home/away must be judged against the team, not the club: in a Bromley 4 v
    Bromley 5 derby both sides share a club, so a club comparison calls it a
    home game for both.
    """
    url = f"{base_url.rstrip('/')}/{filename}" if base_url else filename
    webcal = re.sub(r"^https?://", "webcal://", url) if base_url else ""
    subscribe = ""
    if base_url:
        subscribe = (f'<a class="btn" href="{html.escape(webcal)}">Add to phone</a> '
                     f'<a class="btn" href="https://calendar.google.com/calendar/r?cid='
                     f'{html.escape(webcal)}">Add to Google</a>')

    rows, month = [], None
    for f in fixtures:
        if f["date"].strftime("%B %Y") != month:
            month = f["date"].strftime("%B %Y")
            rows.append(f'<tr><td class=mth colspan=2>{html.escape(month)}</td></tr>')

        if team:
            is_home = str(f["home_team"]) == str(team)
            who = str(f["away_team"] if is_home else f["home_team"])
        else:
            is_home = str(f["home_club"]) == club
            who = f'{f["home_team"]} v {f["away_team"]}'
        badge = ('<span class="ha h">H</span>' if is_home
                 else '<span class="ha a">A</span>')

        if f["throw_off"]:
            time = f"{f['throw_off']:%H:%M}"
        else:
            time = "TBC"

        venue = str(f["venue"] or "TBC")
        maps = venue_book.search_url(venue)
        if maps:
            # Unconfirmed venues link to a Maps search, not a pinned address:
            # the person sees candidates and judges. Marked so it is honest.
            hint = ("" if venue_book.is_confirmed(venue)
                    else ' class=unsure title="Address not confirmed - opens a map search"')
            venue_html = f'<a href="{html.escape(maps)}"{hint}>{html.escape(venue)}</a>'
        else:
            venue_html = html.escape(venue)
        query = QUERIES.get((f"{f['date']:%Y-%m-%d}", str(f["home_team"]), str(f["away_team"])))
        note = f'<span class=tent>Under query — {html.escape(query.split(": ", 1)[-1])}</span>' if query else ""

        rows.append(
            f'<tr><td class=when>{f["date"]:%a %d %b}<small>{time}</small></td>'
            f'<td><span class=who>{badge}{html.escape(who)}</span>'
            f'<div class=where>{venue_html} · {html.escape(str(f["league"]))}</div>'
            f'{note}</td></tr>')

    return f"""<!DOCTYPE html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(label)} fixtures 2026-27 — KorfKal</title>
{FONT_LINKS}
<style>{STYLE}</style>
<header>
  <p class=brand><a href="index.html">Korf<span>Kal</span></a></p>
  <p class=tag>{html.escape(label)} — 2026-27 fixtures</p>
</header>
<p class=sub>{len(fixtures)} fixtures. <a href="index.html">All teams</a></p>
{subscribe}
<table class=fx>{''.join(rows)}</table>
<p class=note><strong>Draft fixtures.</strong> Times and venues may change.
Fixtures marked <em>under query</em> are being checked with the LKA.
<strong>TBC</strong> means the throw-off time has not been confirmed yet.</p>
<footer>Generated by KorfKal ·
<a href="https://bromleykorfball.com/">bromleykorfball.com</a></footer>
</html>
"""


def build_index(club, entries, base_url):
    rows = []
    for filename, label, count, page in entries:
        url = f"{base_url.rstrip('/')}/{filename}" if base_url else filename
        webcal = re.sub(r"^https?://", "webcal://", url) if base_url else ""
        google = (f"https://calendar.google.com/calendar/r?cid={webcal}"
                  if base_url else "")
        buttons = f'<a class="btn" href="{html.escape(webcal)}">Add to phone</a>' if base_url else ""
        if google:
            buttons += f' <a class="btn" href="{html.escape(google)}">Add to Google</a>'
        if not base_url:
            # Without a published URL there is nothing to subscribe to, so fall
            # back to the raw file purely so the preview page is usable locally.
            buttons = f'<a class="btn plain" href="{html.escape(filename)}">{html.escape(filename)}</a>'
        buttons += f' <a class="btn plain" href="{html.escape(page)}">View fixtures</a>'
        rows.append(f"<tr><td><strong>{html.escape(label)}</strong><br>"
                    f"<span class=count>{count} fixtures</span></td>"
                    f"<td>{buttons}</td></tr>")

    warning = "" if base_url else (
        "<p class=warn>No --base-url was given, so subscribe links are missing. "
        "Re-run with the published address to enable them.</p>")

    return f"""<!DOCTYPE html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KorfKal — {html.escape(club)} fixtures 2026-27</title>
{FONT_LINKS}
<style>{STYLE}</style>
<header>
  <p class=brand>Korf<span>Kal</span></p>
  <p class=tag>{html.escape(club)} Korfball Club — 2026-27 season</p>
</header>
<h2>Subscribe to your team</h2>
<p class=sub>Subscribe once and your calendar updates automatically whenever the
fixtures change — there is nothing to re-download later.</p>
{warning}
<table>{''.join(rows)}</table>
<p class=note><strong>Draft fixtures.</strong> Based on LKA Fixtures 26-27 Draft v0.01.
Some fixtures are marked tentative and carry a note explaining what is under query.
Away National League games show as all-day events until the EKA confirms throw-off times.</p>
<p class=note><strong>Not seeing it on your phone?</strong> Newly added calendars are hidden
by default in the Google Calendar app. Open the app, then ☰ &rarr; Settings, and tick the
calendar to make it visible.</p>
<footer>Generated by KorfKal ·
<a href="https://bromleykorfball.com/">bromleykorfball.com</a></footer>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workbook")
    parser.add_argument("--club", default="Bromley")
    parser.add_argument("--outdir", default="docs")
    parser.add_argument("--base-url", default="",
                        help="published URL of the output dir, e.g. "
                             "https://user.github.io/bromley-fixtures")
    args = parser.parse_args()

    fixtures = load_fixtures(args.workbook, args.club)
    if not fixtures:
        sys.exit(f"No fixtures found for club {args.club!r}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    club_lower = args.club.lower()

    per_team = defaultdict(list)
    for fixture in fixtures:
        for team in teams_of(fixture, args.club):
            per_team[team].append(fixture)

    calendars = [(slug(args.club), f"{args.club} — all teams",
                  f"{args.club} Korfball — all teams", fixtures, None)]
    calendars += [(slug(team), str(team), f"{team} Korfball", per_team[team], team)
                  for team in sorted(per_team)]

    entries = []
    for stem, label, calname, items, team in calendars:
        filename, page = f"{stem}.ics", f"{stem}.html"
        (outdir / filename).write_text(
            build_calendar(items, args.club, calname), encoding="utf-8")
        (outdir / page).write_text(
            build_team_page(args.club, label, items, filename, args.base_url, team),
            encoding="utf-8")
        entries.append((filename, label, len(items), page))

    (outdir / "index.html").write_text(
        build_index(args.club, entries, args.base_url), encoding="utf-8")

    print(f"Wrote {len(entries)} calendars + pages to {outdir}/")
    for filename, label, count, page in entries:
        print(f"  {filename:<16} {page:<17} {label:<24} {count:>2} fixtures")
    missing = venue_book.unresolved(f["venue"] for f in fixtures)
    if missing:
        print(f"\n{len(missing)} venue(s) have no confirmed address, so publish as a "
              f"bare name with no map link. Add them in venues.py:")
        for name in missing:
            print(f"  - {name}")

    if not args.base_url:
        print("\nRe-run with --base-url once hosted, to generate working subscribe links.")


if __name__ == "__main__":
    main()
