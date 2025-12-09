import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from youreka.models import Grant, Organization, db

BASE = "https://www.ontario.ca"
URL = "https://www.ontario.ca/page/available-funding-opportunities-ontario-government"

EDU_KEYWORDS = [
    "education", "school", "student", "youth", "learning",
    "training", "skills", "innovation", "research", "technology"
]


def fetch_html(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return res.text


def scrape_program_page(link):
    """Scrape the program's DEDICATED page for real info."""
    html = fetch_html(link)
    soup = BeautifulSoup(html, "html.parser")

    # Description is usually the first paragraph after h1
    description = ""
    eligibility = ""
    funding = ""
    deadline = ""

    # Capture description under "About the program"
    about_header = soup.find("h2", string=lambda x: x and "About" in x)
    if about_header:
        for el in about_header.find_all_next(["p", "ul"], limit=8):
            description += el.get_text(" ", strip=True) + "\n"

    # Eligibility
    elig_header = soup.find("h2", string=lambda x: x and "Eligibility" in x)
    if elig_header:
        for el in elig_header.find_all_next(["p", "ul"], limit=10):
            eligibility += el.get_text(" ", strip=True) + "\n"

    # Deadlines
    deadline_header = soup.find("h2", string=lambda x: x and "Deadline" in x)
    if deadline_header:
        d = deadline_header.find_next("p")
        if d:
            deadline = d.get_text(strip=True)

    return description.strip(), eligibility.strip(), deadline.strip()


def scrape_ontario():
    print("Scraping Ontario — WITH SUBPAGE DETAILS...")

    # Ensure organization exists
    org = Organization.query.filter_by(name="Ontario Government").first()
    if not org:
        org = Organization(
            name="Ontario Government",
            type="Government",
            country="Canada",
            province="Ontario"
        )
        db.session.add(org)
        db.session.commit()

    html = fetch_html(URL)
    soup = BeautifulSoup(html, "html.parser")

    created = 0

    for h2 in soup.find_all("h2"):
        title = h2.get_text(strip=True)

        # Skip filler sections
        if "Overview" in title or "On this page" in title:
            continue

        # Keyword filter
        if not any(k in title.lower() for k in EDU_KEYWORDS):
            continue

        # Find the clickable link for the program
        link_tag = h2.find_next("a")
        if not link_tag:
            continue

        relative_link = link_tag.get("href")
        full_link = urljoin(BASE, relative_link)

        external_id = f"ontario-{title}"

        # Skip duplicates
        if Grant.query.filter_by(external_id=external_id).first():
            continue

        # Scrape subpage (REAL info)
        description, eligibility, deadline = scrape_program_page(full_link)

        grant = Grant(
            name_en=title,
            description_en=description or "No description available.",
            eligibility_en=eligibility or "Eligibility criteria not specified.",
            category="Education/Technology",
            organization=org,
            language="EN",
            region_scope="Provincial",
            province="Ontario",
            source_url=full_link,
            external_id=external_id,
        )

        # Parse deadline date if possible
        try:
            if deadline:
                grant.deadline_date = datetime.strptime(
                    deadline.split(" at ")[0], "%B %d, %Y"
                ).date()
        except:
            pass

        db.session.add(grant)
        created += 1

    db.session.commit()
    print(f"Ontario scraping finished. Created {created} grants.")
