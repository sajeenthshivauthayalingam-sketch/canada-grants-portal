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


def text_or_none(tag):
    return tag.get_text(" ", strip=True) if tag else None


def parse_otf_program_page(html, url):
    soup = BeautifulSoup(html, "html.parser")

    # --- TITLE ---
    title = text_or_none(soup.find("h1")) or "Unknown Grant"

    # ---- DESCRIPTION ----
    desc_block = soup.select_one("section.general-section p")
    description = text_or_none(desc_block)

    # ---- ELIGIBILITY ----
    eligibility_section = soup.find("section", id="who-is-eligible-to-apply")
    eligibility = None
    if eligibility_section:
        paragraphs = eligibility_section.find_all("p")
        eligibility = "\n".join(p.get_text(strip=True) for p in paragraphs)

    # ---- FUNDING ----
    funding_min = None
    funding_max = None

    try:
        for wrapper in soup.select("div.grant_info__wrapper"):
            label_tag = wrapper.find("p", class_="grant_info__label")
            content = wrapper.find("div", class_="grant_info__content")
            if not label_tag or not content:
                continue

            label_text = label_tag.get_text(strip=True).lower()
            if "amount awarded" in label_text:
                for p in content.find_all("p"):
                    txt = p.get_text(strip=True).lower()

                    # parse minimum
                    if txt.startswith("minimum"):
                        if "$" in txt:
                            funding_min = float(
                                txt.split("$")[1].replace(",", "").strip()
                            )
                        else:
                            funding_min = None

                    # parse maximum
                    if txt.startswith("maximum"):
                        if "$" in txt:
                            funding_max = float(
                                txt.split("$")[1].replace(",", "").strip()
                            )
                        else:
                            funding_max = None
                break
    except Exception as e:
        print("Funding parse error:", e)

    # ---- DEADLINE ----
    deadline_date = None
    ongoing_flag = True

    try:
        for wrapper in soup.select("div.grant_info__wrapper"):
            label_tag = wrapper.find("p", class_="grant_info__label")
            content = wrapper.find("div", class_="grant_info__content")
            if not label_tag or not content:
                continue

            if "next deadline" in label_tag.get_text(strip=True).lower():
                raw = content.get_text(" ", strip=True)
                if raw and "tbd" not in raw.lower() and "ongoing" not in raw.lower():
                    try:
                        # remove ", at 5:00 p.m. ET"
                        cleaned = raw.split(" at ")[0]
                        deadline_date = datetime.strptime(cleaned, "%B %d, %Y").date()
                        ongoing_flag = False
                    except:
                        deadline_date = None
                break
    except Exception:
        pass

    return {
        "name": title,
        "description": description,
        "eligibility": eligibility,
        "funding_min": funding_min,
        "funding_max": funding_max,
        "deadline_date": deadline_date,
        "ongoing_flag": ongoing_flag,
        "source_url": url,
    }


def scrape_otf():
    print("Scraping Ontario Trillium Foundation (OTF)...")

    # Ensure organization exists
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

        if Grant.query.filter_by(external_id=url).first():
            continue

        try:
            html = fetch_html(url)
            data = parse_otf_program_page(html, url)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue

        # ✅ NEW: skip expired grants
        from datetime import date
        if data["deadline_date"] and data["deadline_date"] < date.today():
            print(f"Skipping expired grant: {data['name']} (deadline {data['deadline_date']})")
            continue

        # Create grant
        grant = Grant(
            name_en=data["name"],
            description_en=data["description"],
            eligibility_en=data["eligibility"],
            organization=org,
            category="Community",
            region_scope="Provincial",
            country="Canada",
            province="Ontario",
            team_scope="Regional",
            funding_min=data["funding_min"],
            funding_max=data["funding_max"],
            currency="CAD",
            deadline_date=data["deadline_date"],
            ongoing_flag=data["ongoing_flag"],
            language="EN",
            is_ngo_only=False,
            source_url=url,
            external_id=url,
        )

        db.session.add(grant)
        created += 1

    db.session.commit()
    print(f"OTF scraping done. Created {created} grants.")
