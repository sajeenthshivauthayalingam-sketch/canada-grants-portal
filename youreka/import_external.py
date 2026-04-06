"""
Fetch external grant data from the Hellodarwin page-data JSON feed
and upsert them into the DB.  Runs automatically at app startup.
"""
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .extensions import db
from .models import Grant, Organization

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (canada-grants-portal/1.0)",
}

LISTING_BASE = "https://hellodarwin.com/page-data/business-aid/grants-and-funding"
DETAIL_BASE = "https://hellodarwin.com/page-data"

# How many listing pages to fetch (0 = all)
MAX_PAGES = 0
# How many detail pages to fetch per run (0 = skip detail enrichment)
MAX_DETAILS = 200
# Pause between HTTP requests (seconds)
REQUEST_DELAY = 0.25


# ── helpers ─────────────────────────────────────────────────

def _fetch_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _listing_url(page):
    if page == 1:
        return f"{LISTING_BASE}/page-data.json"
    return f"{LISTING_BASE}/{page}/page-data.json"


def _detail_url(full_handle):
    return f"{DETAIL_BASE}/{full_handle}/page-data.json"


def _html_to_text(value):
    if not value:
        return None
    return BeautifulSoup(value, "html.parser").get_text("\n", strip=True)


def _parse_date(raw):
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _join_list(val):
    """Turn a list/None into a comma-separated string."""
    if not val:
        return None
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v)
    return str(val)


# ── listing fetch ───────────────────────────────────────────

def _fetch_all_listings():
    """Fetch all listing pages and return (summaries_list, handles_set)."""
    first = _fetch_json(_listing_url(1))
    node = first["result"]["data"]["allGrantPageLinks"]["nodes"][0]
    page_total = node["pageTotal"]

    if MAX_PAGES:
        page_total = min(page_total, MAX_PAGES)

    all_summaries = []
    handles = set()

    for page in range(1, page_total + 1):
        if page == 1:
            data = node
        else:
            try:
                raw = _fetch_json(_listing_url(page))
                data = raw["result"]["data"]["allGrantPageLinks"]["nodes"][0]
            except Exception as exc:
                print(f"⚠️  Listing page {page} failed: {exc}")
                continue

        for g in data.get("grants", []):
            all_summaries.append(g)
            handle = (g.get("grantPageLink") or {}).get("fullHandle")
            if handle:
                handles.add(handle)

        if page > 1:
            time.sleep(REQUEST_DELAY)

    return all_summaries, handles


# ── detail fetch ────────────────────────────────────────────

def _fetch_detail(full_handle):
    raw = _fetch_json(_detail_url(full_handle))
    return raw["result"]["data"]["allSingleGrantPageLinks"]["nodes"][0]["grant"]


# ── upsert logic ────────────────────────────────────────────

def _get_or_create_org(provider_names):
    """Return an Organization for the first listed provider, or a default."""
    if not provider_names:
        name = "Hellodarwin"
    elif isinstance(provider_names, list):
        name = provider_names[0] if provider_names else "Hellodarwin"
    else:
        name = str(provider_names)

    name = name[:200]
    org = Organization.query.filter_by(name=name).first()
    if not org:
        org = Organization(name=name, type="Government", ngo_only=False, country="Canada")
        db.session.add(org)
        db.session.flush()
    return org


def _upsert_from_summary(g):
    """Create or skip a Grant from a listing-level summary object."""
    grant_id = g.get("grant_id") or g.get("id")
    handle = (g.get("grantPageLink") or {}).get("fullHandle")
    ext_id = f"hd-{grant_id}" if grant_id else f"hd-{handle}"

    if Grant.query.filter_by(external_id=ext_id).first():
        return None  # already exists

    title = g.get("grant_title") or "Unnamed Grant"
    org = _get_or_create_org(g.get("grant_providers"))

    provinces = g.get("grant_provinces") or []
    province_str = ", ".join(provinces) if provinces else None

    source_url = f"https://hellodarwin.com/{handle}" if handle else None

    grant = Grant(
        name_en=title[:255],
        description_en=g.get("grant_description_short"),
        organization=org,
        province=province_str,
        country=g.get("country") or "Canada",
        funding_min=_safe_float(g.get("funding_min_amount")),
        funding_max=_safe_float(g.get("funding_max_amount")),
        percentage_funding=_safe_float(g.get("percentage_funding")),
        application_status=g.get("application_status"),
        financing_types=_join_list(g.get("grant_financing_type")),
        services=_join_list(g.get("grant_service")),
        logo_url=g.get("grant_logo"),
        hd_handle=handle,
        source_url=source_url,
        external_id=ext_id[:255],
        source_type="external",
    )
    db.session.add(grant)
    return grant


def _enrich_with_detail(grant, detail):
    """Merge rich detail fields onto an existing Grant row."""
    grant.long_description = _html_to_text(detail.get("grant_description_long"))
    grant.eligibility_en = _html_to_text(detail.get("eligibility_criteria"))
    grant.who_can_apply = _html_to_text(detail.get("who_can_apply"))
    grant.who_cannot_apply = _html_to_text(detail.get("who_cannot_apply"))
    grant.eligible_expenses = _html_to_text(detail.get("eligible_expenses"))
    grant.selection_criteria = _html_to_text(detail.get("selection_criteria"))
    grant.steps_how_to_apply = _html_to_text(detail.get("steps_how_to_apply"))
    grant.documents_needed = _html_to_text(detail.get("documents_needed"))
    grant.additional_information = _html_to_text(detail.get("additional_information"))
    grant.application_email = (detail.get("application_email_address") or "")[:255] or None
    grant.application_phone = (detail.get("application_phone_number") or "")[:100] or None

    deadline = _parse_date(detail.get("grant_deadline"))
    if deadline:
        grant.deadline_date = deadline


# ── public entry point ──────────────────────────────────────

def fetch_and_import_external_grants():
    """Main entry point — fetch from Hellodarwin and insert new grants."""
    # Skip if we already have external grants (don't re-fetch every restart)
    existing = Grant.query.filter_by(source_type="external").count()
    if existing > 0:
        print(f"ℹ️  {existing} external grants already loaded — skipping fetch.")
        return 0

    print("⏳ Fetching grants from Hellodarwin…")
    summaries, handles = _fetch_all_listings()
    print(f"   Fetched {len(summaries)} summaries across {len(handles)} unique handles.")

    created = 0
    new_grants_by_handle = {}

    for g in summaries:
        grant = _upsert_from_summary(g)
        if grant:
            created += 1
            handle = (g.get("grantPageLink") or {}).get("fullHandle")
            if handle:
                new_grants_by_handle[handle] = grant

    db.session.flush()

    # Optionally enrich the first N grants with detail data
    if MAX_DETAILS and new_grants_by_handle:
        detail_handles = list(new_grants_by_handle.keys())[:MAX_DETAILS]
        enriched = 0
        for handle in detail_handles:
            try:
                detail = _fetch_detail(handle)
                _enrich_with_detail(new_grants_by_handle[handle], detail)
                enriched += 1
            except Exception as exc:
                print(f"⚠️  Detail fetch failed for {handle}: {exc}")
            time.sleep(REQUEST_DELAY)
        print(f"   Enriched {enriched}/{len(detail_handles)} grants with detail data.")

    db.session.commit()
    print(f"✅ Imported {created} external grants from Hellodarwin "
          f"({len(summaries)} fetched, {len(summaries) - created} duplicates skipped).")
    return created
