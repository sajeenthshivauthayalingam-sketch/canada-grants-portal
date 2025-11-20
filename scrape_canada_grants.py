# scrape_canada_grants.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from db import get_connection, init_db, insert_organization, insert_scholarship


BASE_URL = "https://www.canada.ca"
GCOS_LANDING_URL = "https://www.canada.ca/en/employment-social-development/services/funding/gcos.html"


def fetch_html(url):
    """Fetch HTML content with basic error handling."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_gcos_landing(html):
    """
    Parse the GCOS landing page and extract links to funding programs.
    You will likely need to tweak CSS selectors after inspecting the page.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Example: find funding program links inside main content
    main = soup.find("main")
    if not main:
        main = soup

    program_links = []

    # This is a generic selector; adjust after inspecting the HTML:
    for a in main.select("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        # crude filter: links that look like funding programs
        if href and "funding" in href and text:
            full_url = urljoin(BASE_URL, href)
            program_links.append(
                {
                    "name": text,
                    "url": full_url,
                }
            )

    # Deduplicate by URL
    unique = {}
    for p in program_links:
        unique[p["url"]] = p
    return list(unique.values())


def parse_program_page(html, url):
    """
    Parse an individual funding program page.
    This will vary by page; we use fallbacks and keep it simple.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("h1")
    name = title_tag.get_text(strip=True) if title_tag else f"Funding Program ({url})"

    # Description: first paragraph or summary block
    desc = ""
    summary_div = soup.find(class_="mwsgeneric-base-html")
    if summary_div:
        p = summary_div.find("p")
        if p:
            desc = p.get_text(strip=True)
    if not desc:
        p = soup.find("p")
        if p:
            desc = p.get_text(strip=True)

    # We don't have structured amount/deadline here; you can refine later
    scholarship = {
        "name": name,
        "description": desc,
        "category": None,
        "region_scope": "National",
        "country": "Canada",
        "province_state": None,
        "funding_min": None,
        "funding_max": None,
        "currency": "CAD",
        "deadline_date": None,  # most gov pages are ongoing/intake-based
        "ongoing_flag": True,
        "language": "EN",
        "team_scope": "National",
        "source_url": url,
        "external_id": url,  # using URL as external_id for now
    }
    return scholarship


def main():
    print("Initializing database...")
    init_db()

    print(f"Fetching GCOS landing page: {GCOS_LANDING_URL}")
    html = fetch_html(GCOS_LANDING_URL)
    programs = parse_gcos_landing(html)

    print(f"Found {len(programs)} potential funding program links")

    with get_connection() as conn:
        # We'll treat "Government of Canada" / ESDC as the organization for now
        org_id = insert_organization(conn, "Government of Canada - ESDC", country="Canada")

        for p in programs:
            try:
                print(f"Fetching program page: {p['url']}")
                program_html = fetch_html(p["url"])
                scholarship_data = parse_program_page(program_html, p["url"])
                scholarship_data["organization_id"] = org_id

                insert_scholarship(conn, scholarship_data)
            except Exception as e:
                print(f"Error processing {p['url']}: {e}")

    print("Done. Data written to grants.db")


if __name__ == "__main__":
    main()
