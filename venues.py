"""Venue addresses for korfball fixtures.

Fill in `address` for each venue. Once a venue has an address:

* the `.ics` LOCATION field carries the full address, so Apple and Google
  geocode it correctly and their native "Directions" button works;
* the web fixture pages show a maps link.

A venue with `address=None` publishes as a bare name with no link. That is the
safe default — a wrong address sends someone to the wrong place on a Sunday
morning, which is worse than no address at all. Do not guess: confirm with the
host club or the LKA.

`postcode` is optional but strongly recommended; it is what makes UK geocoding
reliable. `lat`/`lng` are optional and only worth adding if a venue geocodes
badly even with a full address.

Every entry below was taken from the fixture list, not from any club's contact
details, and only names that already appear publicly in fixtures belong here.
"""

VENUES = {
    # ------------------------------------------------------------------
    # Bromley's home venue - all 33 Bromley home fixtures
    # ------------------------------------------------------------------
    "Langley Park": {
        "full_name": "Langley Park School for Boys",   # CONFIRM
        "address": None,        # e.g. "Hawksbrook Lane, Beckenham"
        "postcode": None,       # e.g. "BR3 3BE"
        "host": "Bromley",
        "notes": "Bromley home venue. Hall available from 13:00.",
    },

    # ------------------------------------------------------------------
    # Venues Bromley visit
    # ------------------------------------------------------------------
    "Sacred Heart": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Supernova",
        "notes": "Busiest venue in the league (49 fixtures).",
    },
    "Royal Russell": {
        "full_name": "Royal Russell School",           # CONFIRM
        "address": None,
        "postcode": None,
        "host": "Croydon",
        "notes": "",
    },
    "Highbury (TBC)": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Highbury",
        "notes": "Venue not confirmed in the draft - do NOT add an address "
                 "until the TBC is resolved.",
    },
    "Trinity": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Bec, Trojans",
        "notes": "Shared by two clubs - confirm it is one hall, not two "
                 "venues with the same name.",
    },
    "Epsom": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Nomads",
        "notes": "",
    },
    "St Pauls Way": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "East London",
        "notes": "",
    },
    "Harris Invictus": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Bec",
        "notes": "",
    },
    "Queen Elizabeth Girls' School": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Harrow",
        "notes": "",
    },

    # ------------------------------------------------------------------
    # No Bromley fixtures - only needed if other clubs are published
    # ------------------------------------------------------------------
    "Ernest Bevin": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Bec",
        "notes": "No Bromley fixtures.",
    },
    "Glyn School": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Nomads",
        "notes": "No Bromley fixtures.",
    },
}


def lookup(venue):
    """Return the entry for a venue name, or None.

    'Away - <club>' placeholders have no venue recorded in the fixture list,
    so they never resolve.
    """
    if not venue or str(venue).startswith("Away"):
        return None
    return VENUES.get(str(venue))


def full_location(venue):
    """The string to put in an .ics LOCATION field.

    Falls back to the bare venue name when there is no confirmed address.
    """
    entry = lookup(venue)
    if not entry or not entry.get("address"):
        return str(venue)
    parts = [entry.get("full_name") or str(venue),
             entry["address"],
             entry.get("postcode")]
    return ", ".join(p for p in parts if p)


def maps_url(venue):
    """A Google Maps search URL, or None when the address is unconfirmed."""
    entry = lookup(venue)
    if not entry or not entry.get("address"):
        return None
    from urllib.parse import quote_plus
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(full_location(venue))


def search_url(venue, area="London"):
    """A Google Maps *search* URL, usable even when the address is unconfirmed.

    Safe on a web page in a way a bare address is not in a calendar file: the
    person sees candidate results and judges, rather than being routed silently
    to a wrong place. Uses the confirmed address when there is one.
    """
    if not venue or str(venue).startswith("Away"):
        return None
    from urllib.parse import quote_plus
    entry = lookup(venue)
    if entry and entry.get("address"):
        query = full_location(venue)
    else:
        # Bias an unconfirmed name towards the right region, and towards a
        # sports venue rather than a place of the same name.
        name = (entry or {}).get("full_name") or str(venue)
        query = f"{name} sports hall {area}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def is_confirmed(venue):
    """True when we hold a real address, not just a searchable name."""
    entry = lookup(venue)
    return bool(entry and entry.get("address"))


def unresolved(venues_seen):
    """Venue names in use that have no confirmed address, for run-end reporting."""
    return sorted({str(v) for v in venues_seen
                   if not str(v).startswith("Away") and not maps_url(v)})
