import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from ..extensions import db
from ..models import Grant, Organization

BASE_URL = "https://otf.ca"

HEADERS = {"User-Agent": "Mozilla/5.0"}

OTF_PROGRAMS = {
    "Seed Grant": "/our-grants/community-investments-grants/seed-grant",
    "Grow Grant": "/our-grants/community-investments-grants/grow-grant",
    "Capital Grant": "/our-grants/community-investments-grants/capital-grant",
    "Resilient Communities Fund": "/our-grants/other-grant-programs/resilient-communities-fund",
    "Community Building Fund – Capital Stream":
        "/our-grants/community-building-fund/community-building-fund-capital-stream",
    "Community Building Fund – Operating Stream":
        "/our-grants/community-building-fund/community-building-fund-operating-stream",
    "Youth Innovations Test Grant": 
        "/our-grants/youth-opportunities-fund/youth-innovations-test-grant",
    "Youth Innovations Scale Grant":
        "/our-grants/youth-opportunities-fund/youth-innovations-scale-grant",
    "Family Innovations Test Grant":
        "/our-grants/youth-opportunities-fund/family-innovations-test-grant",
    "Family Innovations Scale Grant":
        "/our-grants/youth-opportunities-fund/family-innovations-scale-grant",
}

def fetch_html(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

def parse_otf_program_page(html):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("h1")
    title = title.get_text(strip=True) if title else "OTF Grant"

    desc_tag = soup.find("p")
    description = desc_tag.get_text(strip=True) if desc_tag else ""

    deadline = None
    for tag in soup.find_all(["strong", "b"]):
        t = tag.get_text(strip=True).lower()
        if "deadline" in t:
            parent = tag.find_parent()
            if parent:
                deadline = parent.get_text(strip=True)
            break

    return {
        "name": title,
        "description": description,
        "deadline": deadline,
    }

def scrape_otf():
    print("Scraping Ontario Trillium Foundation (OTF)...")

    org = Organization.query.filter_by(name="Ontario Trillium Foundation").first()
    if not org:
        org = Organization(
            name="Ontario Trillium Foundation",
            type="Government",
            country="Canada",
            province="Ontario",
            ngo_only=False,
        )
        db.session.add(org)
        db.session.commit()

    created = 0

    for program_name, relative_url in OTF_PROGRAMS.items():
        url = urljoin(BASE_URL, relative_url)

        # Skip duplicates
        if Grant.query.filter_by(external_id=url).first():
            continue

        try:
            html = fetch_html(url)
            data = parse_otf_program_page(html)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue

        # ---- DATE FIX ----
        raw_deadline = data["deadline"]
        deadline_date = None
        if raw_deadline:
            try:
                deadline_date = datetime.strptime(raw_deadline, "%B %d, %Y").date()
            except:
                deadline_date = None
        # -------------------

        grant = Grant(
            name_en=data["name"],
            description_en=data["description"],
            organization=org,
            category="Community",
            region_scope="Provincial",
            country="Canada",
            province="Ontario",
            funding_min=None,
            funding_max=None,
            currency="CAD",
            deadline_date=deadline_date,    # MUST be date or None
            ongoing_flag=(deadline_date is None),
            language="EN",
            team_scope="Regional",
            is_ngo_only=False,
            source_url=url,
            external_id=url,
        )

        db.session.add(grant)
        created += 1

    db.session.commit()
    print(f"OTF scraping done. Created {created} grants.")
