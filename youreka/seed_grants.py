import csv
import os
from datetime import datetime
from .extensions import db
from .models import Grant, Organization


def seed_grants_if_empty():
    if Grant.query.count() > 0:
        return

    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "grants.csv"))
    if not os.path.exists(csv_path):
        print(f"⚠️ grants.csv not found at {csv_path}. Skipping grant seed.")
        return

    org = Organization.query.filter_by(name="Imported Grants").first()
    if not org:
        org = Organization(
            name="Imported Grants",
            type="Unknown",
            ngo_only=False,
            country="Canada",
        )
        db.session.add(org)
        db.session.commit()

    def to_float(val):
        val = (val or "").strip()
        return float(val) if val else None

    def to_bool(val):
        val = (val or "").strip()
        if val == "":
            return False
        if val.lower() in ("true", "t", "yes", "y"):
            return True
        if val.lower() in ("false", "f", "no", "n"):
            return False
        try:
            return bool(int(val))
        except Exception:
            return False

    created = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # prevent autoflush from firing during query checks
        with db.session.no_autoflush:
            for row in reader:
                source_url = (row.get("source_url") or "").strip()
                if not source_url:
                    continue

                # De-dupe: prefer external_id if present, else source_url
                external_id = (row.get("external_id") or "").strip() or source_url
                if Grant.query.filter_by(external_id=external_id).first():
                    continue

                deadline = None
                deadline_raw = (row.get("deadline_date") or "").strip()
                if deadline_raw:
                    try:
                        deadline = datetime.strptime(deadline_raw.split(" ")[0], "%Y-%m-%d").date()
                    except Exception:
                        deadline = None

                g = Grant(
                    organization_id=org.id,  # ✅ IMPORTANT: don’t trust CSV org IDs
                    name_en=(row.get("name_en") or row.get("name") or "").strip() or "Untitled",
                    name_fr=(row.get("name_fr") or "").strip() or None,
                    description_en=(row.get("description_en") or row.get("description") or "").strip() or None,
                    description_fr=(row.get("description_fr") or "").strip() or None,
                    eligibility_en=(row.get("eligibility_en") or "").strip() or None,
                    eligibility_fr=(row.get("eligibility_fr") or "").strip() or None,
                    category=(row.get("category") or "").strip() or None,
                    region_scope=(row.get("region_scope") or "").strip() or None,
                    country=(row.get("country") or "Canada").strip(),
                    province=(row.get("province_state") or row.get("province") or "").strip() or None,
                    funding_min=to_float(row.get("funding_min")),
                    funding_max=to_float(row.get("funding_max")),
                    currency=(row.get("currency") or "CAD").strip(),
                    deadline_date=deadline,
                    ongoing_flag=to_bool(row.get("ongoing_flag")),
                    language=(row.get("language") or "EN").strip(),
                    team_scope=(row.get("team_scope") or "").strip() or None,
                    individual_type=(row.get("individual_type") or "").strip() or None,
                    is_ngo_only=to_bool(row.get("is_ngo_only")),
                    source_url=source_url,
                    external_id=external_id,
                )

                db.session.add(g)
                created += 1

    db.session.commit()
    print(f"✅ Seeded {created} grants from grants.csv")
