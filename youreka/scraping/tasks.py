"""
Basic scraping skeleton for gov funding pages.
You can expand selectors for real data extraction.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from flask import current_app
from ..extensions import db
from ..models import Grant, Organization

BASE_URL = "https://www.canada.ca"
FUNDING_LIST_URL = "https://www.canada.ca/en/employment-social-development/services/funding.html"


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_funding_programs_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup

    program_links = []

    for a in main.select("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not href or not text:
            continue

        full_url = urljoin(BASE_URL, href)

        # Skip obvious non-program pages
        if any(
            skip in href
            for skip in ["gcos", "userguide", "register", "service-standards", "programs.html"]
        ):
            continue

        if "/employment-social-development/services/funding/" in href:
            program_links.append({"name": text, "url": full_url})

    uniq = {p["url"]: p for p in program_links}
    return list(uniq.values())


def parse_program_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup

    title_tag = soup.find("h1")
    name = title_tag.get_text(strip=True) if title_tag else url

    desc = ""
    p = main.find("p")
    if p:
        desc = p.get_text(strip=True)

    return {
        "name_en": name,
        "description_en": desc,
        "source_url": url,
    }


def run_scrape():
    """
    Scrape ESDC funding listing page and insert/update basic grants.
    This is a starting point you can refine with better selectors.
    """
    print("Running scraping task for Canada funding programs...")
    html = fetch_html(FUNDING_LIST_URL)
    programs = parse_funding_programs_page(html)
    print(f"Found {len(programs)} candidate program links")

    gov_org = Organization.query.filter_by(name="Government of Canada - ESDC").first()
    if not gov_org:
        gov_org = Organization(
            name="Government of Canada - ESDC",
            type="Government",
            country="Canada",
        )
        db.session.add(gov_org)
        db.session.commit()

    created = 0
    for p in programs:
        url = p["url"]
        existing = Grant.query.filter_by(external_id=url).first()
        if existing:
            continue

        try:
            program_html = fetch_html(url)
            data = parse_program_page(program_html, url)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue

        grant = Grant(
            name_en=data["name_en"],
            description_en=data["description_en"],
            organization=gov_org,
            category=None,
            region_scope="National",
            country="Canada",
            province=None,
            funding_min=None,
            funding_max=None,
            currency="CAD",
            deadline_date=None,
            ongoing_flag=True,
            language="EN",
            team_scope="National",
            is_ngo_only=False,
            source_url=url,
            external_id=url,
        )
        db.session.add(grant)
        created += 1

    db.session.commit()
    print(f"Scraping complete. Created {created} new grants.")
