"""
TED (Tenders Electronic Daily) API connector
Fetches architecture & masterplanning tenders from the EU Official Journal.
Used by the weekly tender intelligence cron.

CPV codes:
  71220000 - Architectural design services
  71240000 - Architectural, engineering and planning services
  71400000 - Urban planning and landscape architectural services
  71410000 - Urban planning services
  71420000 - Landscape architectural services
  71200000 - Architectural and related services

Usage:
  python ted_search.py [days_back]   (default: 8)
"""
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

TED_API = "https://api.ted.europa.eu/v3/notices/search"

# Architecture-related CPV codes
CPV_CODES = "71200000 71220000 71240000 71400000 71410000 71420000"

# Only contract notices (not award notices)
NOTICE_TYPES = "cn-standard cn-social cn-desg pin-cfc-social"

# Fields to retrieve
FIELDS = [
    "ND", "PD", "TI", "CY", "DD", "DT", "TV", "TV_CUR", "AU",
    "notice-type", "publication-number", "description-proc",
    "place-of-performance"
]

# Skip if title contains these (pure engineering/MEP)
SKIP_KEYWORDS = [
    "sewer", "sewage", "drainage", "wastewater", "water supply",
    "electrical installation", "HVAC", "heating system", "plumbing",
    "road surface", "pavement", "asphalt", "pipeline",
    "reningsverk",  # Swedish: water treatment plant
    "pumpwerk", "pumpstation",  # German: pumping station
    "Kl\u00e4ranlage",  # German: sewage treatment
    "_ELT", " ELT",  # German electrical engineering contracts
    "TGA", "Technische Ausr\u00fcstung",  # German: technical building services/MEP
    "Tragwerksplanung",  # German: structural engineering only
]


def notice_url(publication_number):
    return f"https://ted.europa.eu/en/notice/-/detail/{publication_number}"


def extract_title(ti_field):
    """Extract best available title from multilingual TI field."""
    if not ti_field:
        return ""
    if isinstance(ti_field, str):
        return _strip_ted_prefix(ti_field)
    if isinstance(ti_field, dict):
        # Language preference order
        for lang in ("eng", "gle", "fra", "deu", "pol", "ces", "nld", "swe", "est", "lav"):
            if lang in ti_field:
                t = ti_field[lang]
                t = t[0] if isinstance(t, list) else t
                return _strip_ted_prefix(t)
        # Fall back to first value
        for val in ti_field.values():
            t = val[0] if isinstance(val, list) else val
            return _strip_ted_prefix(t)
    return str(ti_field)


def _strip_ted_prefix(title):
    """TED prepends 'Country \u2013 Service type \u2013 Title', strip the prefix."""
    title = title.strip()
    # Strip narrow no-break spaces
    title = title.replace("\u202f", " ")
    # Split on em dash separator TED uses
    if " \u2013 " in title:
        parts = [p.strip() for p in title.split(" \u2013 ")]
        if len(parts) >= 3:
            return parts[-1]
        return parts[-1]
    return title


def extract_authority(au_field):
    if not au_field:
        return ""
    if isinstance(au_field, dict):
        for vals in au_field.values():
            if isinstance(vals, list) and vals:
                return vals[0]
            return str(vals)
    return str(au_field)


def extract_value(tv, cur):
    if not tv:
        return None
    val = tv[0] if isinstance(tv, list) else tv
    currency = ""
    if cur:
        currency = (cur[0] if isinstance(cur, list) else cur).upper()
    try:
        return f"{float(val):,.0f} {currency}".strip()
    except Exception:
        return str(val)


def extract_deadline(dd, dt):
    """Return the most useful deadline date."""
    for field in (dt, dd):
        if field:
            d = field[0] if isinstance(field, list) else field
            try:
                # Parse ISO datetime
                dt_obj = datetime.fromisoformat(d.split("+")[0].split("Z")[0])
                return dt_obj.strftime("%d %b %Y")
            except Exception:
                return str(d)[:10]
    return None


def extract_country(cy):
    if not cy:
        return ""
    c = cy[0] if isinstance(cy, list) else cy
    return c.upper() if isinstance(c, str) else str(c)


def should_skip(title):
    tl = title.lower()
    return any(kw.lower() in tl for kw in SKIP_KEYWORDS)


def search_ted(days_back=8):
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

    query = (
        f"classification-cpv IN ({CPV_CODES}) "
        f"AND publication-date >= {since} "
        f"AND notice-type IN ({NOTICE_TYPES})"
    )

    payload = json.dumps({
        "query": query,
        "fields": FIELDS,
        "scope": "ACTIVE",
    }).encode()

    req = urllib.request.Request(
        TED_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return [], f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return [], str(e)

    if "message" in data:
        return [], data["message"]

    results = []
    for notice in data.get("notices", []):
        pub_num = notice.get("publication-number", "")
        title = extract_title(notice.get("TI"))

        if not title or should_skip(title):
            continue

        # Clean up title — strip country/service prefix that TED prepends
        if " \u2013 " in title:
            parts = title.split(" \u2013 ")
            title = parts[-1].strip()
        elif title.count(" - ") >= 2:
            parts = title.split(" - ", 2)
            title = parts[-1].strip()

        results.append({
            "title": title,
            "authority": extract_authority(notice.get("AU")),
            "country": extract_country(notice.get("CY")),
            "deadline": extract_deadline(notice.get("DD"), notice.get("DT")),
            "value": extract_value(notice.get("TV"), notice.get("TV_CUR")),
            "pub_date": (notice.get("PD") or "")[:10],
            "notice_type": notice.get("notice-type", ""),
            "url": notice_url(pub_num) if pub_num else "",
        })

    return results, None


def format_for_discord(results):
    if not results:
        return "_No new architecture tenders on TED this week._"

    lines = []
    for r in results:
        line = f"**{r['title']}**"
        if r["authority"]:
            line += f"\n  Client: {r['authority']}"
        if r["country"]:
            line += f" ({r['country']})"
        if r["deadline"]:
            line += f" | Deadline: **{r['deadline']}**"
        if r["value"]:
            line += f" | Est. value: {r['value']}"
        if r["url"]:
            line += f"\n  {r['url']}"
        lines.append(line)

    return "\n\n".join(lines)


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    results, err = search_ted(days)
    if err:
        print(f"Error: {err}")
    else:
        print(f"Found {len(results)} notices\n")
        print(format_for_discord(results))
