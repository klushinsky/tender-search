"""
TED (Tenders Electronic Daily) API connector.

Fetches architecture and masterplanning tenders from the EU Official Journal
and prints them as a Discord-ready digest (or JSON). Used by Part 1 of the
weekly tender scan (prompts/01-europe-middle-east-australia.md).

CPV codes searched:
  71200000  Architectural and related services
  71220000  Architectural design services
  71240000  Architectural, engineering and planning services
  71400000  Urban planning and landscape architectural services
  71410000  Urban planning services
  71420000  Landscape architectural services

Usage:
  python scripts/ted_search.py [days_back] [min_value_eur] [--json] [--all] [--limit=N]

  days_back       Look back this many days by publication date (default 8)
  min_value_eur   Drop notices whose stated value is below this, in EUR
                  (default 0 = no filter). Notices with no stated value,
                  or a currency we cannot convert, are always kept.
  --json          Print JSON instead of the Discord digest.
  --all           Print every open notice, not just the top matches.
  --limit=N       How many top matches to print (default 40).

Output is ranked by a keyword relevance score (see POSITIVE_STEMS and
NEGATIVE_STEMS) because a normal week returns ~600 notices, most of them
engineering, supervision or infrastructure. Notices whose deadline has
already passed are dropped.

Examples:
  python scripts/ted_search.py 8 250000
  python scripts/ted_search.py 14 0 --json

No dependencies beyond the Python 3.8+ standard library. No API key needed.
"""
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

TED_API = "https://api.ted.europa.eu/v3/notices/search"

CPV_CODES = "71200000 71220000 71240000 71400000 71410000 71420000"

# Contract notices and design contests only (no award notices).
NOTICE_TYPES = "cn-standard cn-social cn-desg pin-cfc-social"

NOTICE_TYPE_LABELS = {
    "cn-standard": "Contract notice",
    "cn-social": "Contract notice (light regime)",
    "cn-desg": "Design contest",
    "pin-cfc-social": "Call for competition (PIN)",
}

FIELDS = [
    "ND", "PD", "TI", "CY", "DD", "DT", "TV", "TV_CUR", "AU",
    "notice-type", "publication-number", "description-proc",
    "place-of-performance",
]

PAGE_SIZE = 250   # API maximum per page
MAX_PAGES = 20    # safety cap: 5,000 notices is far more than a week produces

DEADLINE_WARNING_DAYS = 21

# Approximate EUR conversion, used only for the min_value threshold.
# Rough rates are fine here; refresh occasionally.
EUR_PER_UNIT = {
    "EUR": 1.0,
    "PLN": 1 / 4.25,
    "CZK": 1 / 25.0,
    "HUF": 1 / 400.0,
    "RON": 1 / 5.0,
    "BGN": 1 / 1.95583,
    "SEK": 1 / 11.0,
    "DKK": 1 / 7.46,
    "NOK": 1 / 11.5,
    "ISK": 1 / 145.0,
    "CHF": 1 / 0.94,
    "GBP": 1 / 0.86,
}

# Skip if the title contains any of these (pure engineering / MEP work).
SKIP_KEYWORDS = [
    "sewer", "sewage", "drainage", "wastewater", "water supply",
    "electrical installation", "HVAC", "heating system", "plumbing",
    "road surface", "pavement", "asphalt", "pipeline",
    "reningsverk",                    # Swedish: water treatment plant
    "pumpwerk", "pumpstation",        # German: pumping station
    "Kläranlage",                # German: sewage treatment
    "_ELT", " ELT",                   # German electrical engineering contracts
    "TGA", "Technische Ausrüstung",  # German: building services / MEP
    "Tragwerksplanung",               # German: structural engineering only
]

TITLE_LANGS = ("eng", "pol", "deu", "fra", "nld", "ces", "swe", "est", "lav", "gle")

DEFAULT_LIMIT = 40  # notices printed by default; --all prints every match

# --------------------------------------------------------------------------
# Relevance ranking. A week on TED returns ~600 notices for these CPV codes,
# most of them engineering, supervision or infrastructure. Titles are scored
# with multilingual keyword stems so the digest leads with architecture,
# urban design and competitions. Stems are matched on lowercase,
# accent-stripped titles. Stems shorter than 5 characters, or starting with
# "^", only match at the start of a word; longer stems match anywhere
# (German compounds such as "Grundschule").
# --------------------------------------------------------------------------

POSITIVE_STEMS = [
    # architecture
    "architect", "architekt", "arquitect", "architett", "arhitekt", "arkitekt", "arkkiteht", "epitesz",
    # urban design, masterplanning, landscape, public realm, heritage
    "masterplan", "master plan", "plan directeur", "rahmenplan", "stadtebau", "urbanis", "urbanist",
    "urban design", "stedenbouw", "zagospodarowan", "bauleitplan", "bebauungsplan", "amenagement",
    "quartier", "freiraum", "freianlag", "landschaft", "landscape", "paysag", "public realm",
    "espace public", "espaces publics", "spazio pubblico", "espacio publico", "renouvellement urbain",
    "npnru", "revitali", "rewitaliz", "patrimon", "heritage", "denkmal", "plein", "platz", "planning",
    # competitions
    "wettbewerb", "concours", "konkurs", "competition", "concorso", "concurso", "soutez", "prijsvraag",
    "tavling", "kilpailu",
    # architectural design services by their local names
    "objektplanung", "generalplan", "maitrise d'oeuvre", "maitre d'oeuvre", "moe", "auteur de projet",
    "ontwerp", "design team", "koncepc", "proyecto basico", "progettazione", "hochbau", "innenarchitekt",
    "inredning", "tervez", "neubau",
    # building types
    "schul", "school", "ecole", "college", "lycee", "szkol", "escuela", "colegio", "scuola", "gymnasium",
    "kita", "kindergarten", "przedszkol", "creche", "campus", "universit", "hochschule", "bildung",
    "^educat", "edukac", "dydaktyczn", "oktatas", "hospital", "hopital", "klinik", "szpital", "ospedale",
    "krankenhaus", "healthcare", "zorgcentrum", "pflege", "ehpad", "museum", "musee", "muzeum", "museo",
    "bibliothe", "bibliotek", "mediatheque", "library", "theater", "theatre", "teatr", "kultur", "^cultu",
    "logement", "wohnbau", "wohnquartier", "wohnung", "housing", "woning", "woonwijk", "mieszkan",
    "vivienda", "rathaus", "mairie", "hotel de ville", "town hall", "verwaltungsgebaude", "siedzib",
    "stadion", "stadium", "arena", "sporthalle", "sportow", "widowisk", "gymnase", "piscine", "schwimm",
    "mixed-use", "mixed use", "headquarter", "sede", "salle polyvalente", "feuerwehr", "polizei", "polic",
    "justiz",
]

NEGATIVE_STEMS = [
    # site supervision, contract engineer, project or claims management, checking
    "nadzor", "inspektor", "uberwachung", "bauoberleitung", "uzraudz", "supervision", "supervisi",
    "dozor", "tds", "inzynier", "projektsteuerung", "bauherrenvertretung", "projectmanag",
    "projektmanag", "project manager", "nachtrag", "verifica",
    # transport, utilities, energy
    "railway", "kolejow", "dzelzcel", "^trate", "signal", "senaliz", "gazociag", "gaz-system",
    "pipeline", "road", "drog", "kelio", "carretera", "autobahn", "bridge", "brucke", "tunnel", "kanal",
    "sewer", "wastewater", "abwasser", "^water", "oczyszczal", "depuraz", "fibra optica", "fibre",
    "fiber", "vaarweg", "hafen", "odnawialn", "fotowolt", "photovolt", "kv", "substation",
    # MEP and other engineering-only scopes
    "elektr", "electric", "sahko", "energieausweis", "energy audit", "audyt energ", "vermessung",
    "geodez", "geodet", "survey", "topograf", "tiefbau", "ingenieurbau", "verkehrsanlage", "fernmelde",
    "geotech", "brandschutz", "tragwerk", "tga", "hls", "hvac",
    # not design work
    "impression", "printing", "mantenimiento", "maintenance", "conservacion", "reinigung", "cleaning",
]


# Letters that Unicode does not decompose into base letter + accent.
_FOLD_EXTRA = str.maketrans({
    "’": "'", "‘": "'", "œ": "oe", "Œ": "oe", "ł": "l", "Ł": "l",
    "ø": "o", "Ø": "o", "đ": "d", "Đ": "d", "ß": "ss", "æ": "ae",
    "Æ": "ae", "ı": "i",
})


def _fold(text):
    """Lowercase and strip accents so 'Maîtrise d’œuvre' matches "maitrise d'oeuvre" and 'szkoły' matches "szkol"."""
    text = unicodedata.normalize("NFKD", text.translate(_FOLD_EXTRA))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _compile_stems(stems):
    compiled = []
    for stem in stems:
        word_start = stem.startswith("^")
        stem = _fold(stem.lstrip("^"))
        pattern = re.escape(stem)
        if word_start or len(stem) < 5:
            pattern = r"\b" + pattern
        compiled.append((stem, re.compile(pattern)))
    return compiled


_POSITIVE = _compile_stems(POSITIVE_STEMS)
_NEGATIVE = _compile_stems(NEGATIVE_STEMS)


def relevance(title, notice_type=""):
    """Score a notice: +1 per positive stem (max 3), -2 per negative stem, +3 for a design contest."""
    folded = _fold(title)
    positive = [s for s, rx in _POSITIVE if rx.search(folded)]
    negative = [s for s, rx in _NEGATIVE if rx.search(folded)]
    score = min(len(positive), 3) - 2 * len(negative) + (3 if notice_type == "cn-desg" else 0)
    return score, positive, negative


# --------------------------------------------------------------------------
# Field helpers. TED returns most fields as a list, or as a dict keyed by
# three-letter language code whose values are lists.
# --------------------------------------------------------------------------

def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _strip_ted_prefix(title):
    """TED titles look like 'Country – Service type – Title'. Keep the title part only."""
    title = title.replace(" ", " ").strip()
    parts = title.split(" – ", 2)
    return parts[2].strip() if len(parts) == 3 else title


def extract_title(ti_field):
    if not ti_field:
        return ""
    if isinstance(ti_field, dict):
        for lang in TITLE_LANGS:
            if lang in ti_field:
                return _strip_ted_prefix(str(_first(ti_field[lang]) or ""))
        for val in ti_field.values():
            return _strip_ted_prefix(str(_first(val) or ""))
        return ""
    return _strip_ted_prefix(str(_first(ti_field) or ""))


def extract_authority(au_field):
    if not au_field:
        return ""
    if isinstance(au_field, dict):
        for vals in au_field.values():
            return str(_first(vals) or "")
        return ""
    return str(_first(au_field) or "")


def parse_date(value):
    """Return a date from TED values like '2026-10-20+02:00' or '2026-10-20T10:00:00Z'."""
    value = _first(value)
    if not value:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def extract_deadline(dt_field, dd_field, today=None):
    """Deadline from DT (tender receipt), else DD.

    Multi-lot notices carry several dates and some carry stale ones, so this
    returns the earliest date that is still upcoming. If every date has
    passed it returns the latest one, which the caller treats as expired.
    """
    today = today or date.today()
    for field in (dt_field, dd_field):
        values = field if isinstance(field, list) else [field]
        dates = [d for d in (parse_date(v) for v in values if v) if d]
        if dates:
            upcoming = [d for d in dates if d >= today]
            return min(upcoming) if upcoming else max(dates)
    return None


def extract_value(tv, cur):
    """Return (amount, currency) or (None, '')."""
    raw = _first(tv)
    if raw in (None, ""):
        return None, ""
    currency = str(_first(cur) or "").upper()
    try:
        return float(raw), currency
    except (TypeError, ValueError):
        return None, currency


def value_in_eur(amount, currency):
    if amount is None:
        return None
    rate = EUR_PER_UNIT.get(currency or "EUR")
    return amount * rate if rate else None


def should_skip(title):
    tl = title.lower()
    return any(kw.lower() in tl for kw in SKIP_KEYWORDS)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def _post(body):
    req = urllib.request.Request(
        TED_API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def fetch_notices(days_back):
    """Fetch every matching notice, page by page. Returns (notices, error)."""
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    query = (
        f"classification-cpv IN ({CPV_CODES}) "
        f"AND publication-date >= {since} "
        f"AND notice-type IN ({NOTICE_TYPES})"
    )

    notices = []
    for page in range(1, MAX_PAGES + 1):
        body = {
            "query": query,
            "fields": FIELDS,
            "scope": "ACTIVE",
            "limit": PAGE_SIZE,
            "page": page,
        }
        try:
            data = _post(body)
        except urllib.error.HTTPError as e:
            return notices, f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
        except Exception as e:  # network errors, bad JSON
            return notices, str(e)

        if "message" in data and "notices" not in data:
            return notices, str(data["message"])

        batch = data.get("notices", [])
        notices.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
    return notices, None


def search_ted(days_back=8, min_value_eur=0):
    """Returns (results, stats, error)."""
    raw, err = fetch_notices(days_back)
    stats = {"fetched": len(raw), "skipped_keyword": 0, "skipped_value": 0, "skipped_expired": 0}
    today = date.today()

    results = []
    seen = set()
    for notice in raw:
        pub_num = notice.get("publication-number", "")
        if pub_num in seen:
            continue
        seen.add(pub_num)

        title = extract_title(notice.get("TI"))
        if not title:
            continue
        if should_skip(title):
            stats["skipped_keyword"] += 1
            continue

        amount, currency = extract_value(notice.get("TV"), notice.get("TV_CUR"))
        eur = value_in_eur(amount, currency)
        if min_value_eur and eur is not None and eur < min_value_eur:
            stats["skipped_value"] += 1
            continue

        deadline = extract_deadline(notice.get("DT"), notice.get("DD"), today)
        if deadline and deadline < today:
            stats["skipped_expired"] += 1
            continue
        days_left = (deadline - today).days if deadline else None
        notice_type = _first(notice.get("notice-type")) or ""
        pub_date = parse_date(notice.get("PD"))
        score, matched, penalised = relevance(title, notice_type)

        results.append({
            "title": title,
            "authority": extract_authority(notice.get("AU")),
            "country": str(_first(notice.get("CY")) or "").upper(),
            "deadline": deadline.isoformat() if deadline else None,
            "days_left": days_left,
            "deadline_soon": days_left is not None and 0 <= days_left <= DEADLINE_WARNING_DAYS,
            "value": amount,
            "currency": currency,
            "value_eur": round(eur) if eur is not None else None,
            "pub_date": pub_date.isoformat() if pub_date else "",
            "notice_type": notice_type,
            "notice_type_label": NOTICE_TYPE_LABELS.get(notice_type, notice_type),
            "url": f"https://ted.europa.eu/en/notice/-/detail/{pub_num}" if pub_num else "",
            "relevance": score,
            "matched": matched,
            "penalised": penalised,
        })

    # The same tender often appears twice (a corrected re-publication, or one
    # notice per lot). Keep the most recently published copy.
    by_key = {}
    for r in results:
        key = (_fold(r["title"]), _fold(r["authority"]))
        if key not in by_key or _pub_order(r["url"]) > _pub_order(by_key[key]["url"]):
            by_key[key] = r
    stats["duplicates"] = len(results) - len(by_key)
    results = list(by_key.values())

    # Most relevant first; within a score, soonest deadline first.
    results.sort(key=lambda r: (-r["relevance"], r["deadline"] is None, r["deadline"] or ""))
    stats["kept"] = len(results)
    stats["relevant"] = sum(1 for r in results if r["relevance"] > 0)
    return results, stats, err


def _pub_order(url):
    """Sort key for TED publication numbers like '.../694082-2026' -> (2026, 694082)."""
    m = re.search(r"(\d+)-(\d{4})$", url or "")
    return (int(m.group(2)), int(m.group(1))) if m else (0, 0)


def select(results, limit=DEFAULT_LIMIT, show_all=False):
    """Notices to print: every one with --all, else the top `limit` with a positive score."""
    if show_all:
        return results
    return [r for r in results if r["relevance"] > 0][:limit]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def format_for_discord(results):
    if not results:
        return "_No new architecture tenders on TED this week._"

    blocks = []
    for r in results:
        line = f"**{r['title']}**"
        if r["notice_type_label"]:
            line += f" ({r['notice_type_label']})"
        meta = []
        client = r["authority"] + (f" ({r['country']})" if r["country"] else "")
        if client.strip():
            meta.append(f"Client: {client.strip()}")
        if r["deadline"]:
            d = datetime.strptime(r["deadline"], "%Y-%m-%d").strftime("%d %b %Y")
            flag = "⚠️ " if r["deadline_soon"] else ""
            meta.append(f"Deadline: {flag}**{d}**")
        if r["value"] is not None:
            meta.append(f"Est. value: {r['value']:,.0f} {r['currency']}".rstrip())
        if meta:
            line += "\n  " + " | ".join(meta)
        if r["url"]:
            line += f"\n  {r['url']}"
        blocks.append(line)
    return "\n\n".join(blocks)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = [a for a in argv if a.startswith("--")]
    as_json = "--json" in flags
    show_all = "--all" in flags
    limit = DEFAULT_LIMIT
    for f in flags:
        if f.startswith("--limit="):
            limit = int(f.split("=", 1)[1])
    days = int(args[0]) if len(args) > 0 else 8
    min_value = float(args[1]) if len(args) > 1 else 0

    results, stats, err = search_ted(days, min_value)
    shown = select(results, limit, show_all)
    stats["shown"] = len(shown)

    if as_json:
        print(json.dumps({"stats": stats, "error": err, "results": shown},
                         ensure_ascii=False, indent=2))
        return 1 if err and not results else 0

    if err:
        print(f"Error: {err}")
        if not results:
            return 1
        print("(partial results below)\n")

    print(
        f"Found {stats['kept']} open notices (fetched {stats['fetched']}; skipped "
        f"{stats['skipped_keyword']} as MEP/engineering, {stats['skipped_value']} below "
        f"{min_value:,.0f} EUR, {stats['skipped_expired']} past their deadline, "
        f"{stats['duplicates']} duplicates)."
    )
    if show_all:
        print(f"Showing all {len(shown)}, most relevant first.\n")
    else:
        print(
            f"{stats['relevant']} look like architecture or urban design work; showing the top "
            f"{len(shown)} by relevance. Run with --all to see everything.\n"
        )
    print(format_for_discord(shown))
    return 0


if __name__ == "__main__":
    # Windows consoles and pipes default to cp1252, which cannot print Polish
    # characters or emoji. Force UTF-8 so the script never crashes on output.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))
