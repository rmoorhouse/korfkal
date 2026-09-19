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
        "full_name": "Langley Park School for Boys",
        "address": "South Eden Park Road, Beckenham",
        "postcode": "BR3 3BP",
        "lat": 51.3889901,
        "lng": -0.0190759,
        "host": "Bromley",
        "notes": "Bromley home venue. Address and coordinates from the club's Heja history (304 uses). Hall opens 12:50 in draft v0.03.",
    },

    # ------------------------------------------------------------------
    # Venues Bromley visit
    # ------------------------------------------------------------------
    "Sacred Heart": {
        "full_name": "Sacred Heart Catholic Secondary School",
        "address": "Camberwell New Road, London",
        "postcode": "SE5 9JN",
        "lat": 51.47541029,
        "lng": -0.09727099,
        "host": "Supernova",
        "notes": "Busiest venue in the league. Address and coordinates from Heja.",
    },
    "Royal Russell": {
        "full_name": "Royal Russell School",
        "address": "Coombe Lane, Croydon",
        "postcode": "CR9 5BX",
        "host": "Croydon",
        "notes": "Address confirmed from the club's Heja location history (used 26 times).",
    },
    "Excelsior": {
        "full_name": "The Excelsior Academy",
        "address": "Shacklewell Lane, London",
        "postcode": "E8 2HE",
        "host": "Highbury",
        "notes": "Resolves the 'Highbury (TBC)' placeholder used up to v0.01. Address confirmed from the club's Heja location history (used 6 times).",
    },
    "Highbury (TBC)": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "Highbury",
        "notes": "Superseded by Excelsior in v0.03. Kept so older drafts "
                 "still resolve; safe to delete once v0.01 is no longer used.",
    },
    "Trinity": {
        "full_name": "Trinity School",
        "address": "Shirley Park, Croydon",
        "postcode": "CR9 7AT",
        "lat": 51.3752161,
        "lng": -0.0600856,
        "host": "Bec, Trojans",
        "notes": "Shared by Bec and Trojans. Address and coordinates from Heja; a minority of records give Addiscombe Rd CR0 5EB, so confirm if a player reports trouble finding it.",
    },
    "Epsom": {
        "full_name": "Epsom College",
        "address": "Epsom, Surrey",
        "postcode": "KT17 4JQ",
        "host": "Nomads",
        "notes": "Address confirmed from the club's Heja location history (used 19 times).",
    },
    "St Pauls Way": {
        "full_name": None,
        "address": None,
        "postcode": None,
        "host": "East London",
        "notes": "",
    },
    "Harris Invictus": {
        "full_name": "Harris Invictus Academy Croydon",
        "address": "88 London Road, Croydon",
        "postcode": "CR0 2TB",
        "host": "Bec",
        "notes": "Address confirmed from the club's Heja location history (used 5 times).",
    },
    "Queen Elizabeth Girls' School": {
        "full_name": "Queen Elizabeth's Girls' School",
        "address": "High Street, Barnet",
        "postcode": "EN5 5RR",
        "host": "Harrow",
        "notes": "Address confirmed from the club's Heja location history (used 1 times). Single use - lower confidence.",
    },

    # ------------------------------------------------------------------
    # No Bromley fixtures - only needed if other clubs are published
    # ------------------------------------------------------------------
    "Ernest Bevin": {
        "full_name": "Ernest Bevin Academy",
        "address": "Beechcroft Road, Wandsworth, London",
        "postcode": "SW17 7DF",
        "host": "Bec",
        "notes": "No Bromley fixtures. Address confirmed from the club's Heja location history (used 18 times).",
    },
    "Glyn School": {
        "full_name": "Glyn School",
        "address": "The Kingsway, Epsom, Surrey",
        "postcode": "KT17 1NB",
        "host": "Nomads",
        "notes": "Address confirmed from the club's Heja location history (used 1 times). Single use - lower confidence.",
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


def coords(venue):
    """(lat, lng) when known, else None. Coordinates beat address text."""
    entry = lookup(venue)
    if entry and entry.get("lat") is not None and entry.get("lng") is not None:
        return entry["lat"], entry["lng"]
    return None


def maps_url(venue):
    """A Google Maps URL, or None when the venue is unconfirmed.

    Prefers coordinates: they are unambiguous, whereas an address string is
    re-geocoded by Maps and can drift to a similarly named place.
    """
    entry = lookup(venue)
    if not entry or not entry.get("address"):
        return None
    from urllib.parse import quote_plus
    pt = coords(venue)
    if pt:
        return f"https://www.google.com/maps/search/?api=1&query={pt[0]},{pt[1]}"
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
        return maps_url(venue)
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
