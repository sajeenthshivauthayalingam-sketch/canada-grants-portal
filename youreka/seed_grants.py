import csv
import os
from datetime import datetime
from .extensions import db
from .models import Grant, Organization


def seed_grants_if_empty():
    # Only seed if there are no grants
    if Grant.query.count() > 0:
        return

    # Path: repo_root/data/grants.csv
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "grants.csv")
    csv_path = os.path.abspath(csv_path)

    if not os.path.exists(csv_path):
        print(f"⚠️ grants.csv not found at {csv_path}. Skipping grant seed.")
        return

    # Ensure at least one organization exists (or create a default)
    org = Organization.query.first()
    if not org:
        org = Organization(
            name="Imported Grants",
            type="Unknown",
            ngo_only=False,
            country="Canada",
        )
        db.session.add(org)
        db.session.commit()

    created = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            source_url = (row.get("source_url") or "").strip()
            if not source_url:
                continue

            # de-dupe by source_url
            if Grant.query.filter_by(source_url=source_url).first():
                continue

            # parse deadline_date if present
            deadline = None
            deadline_raw = (row.get("deadline_date") or "").strip()
            if deadline_raw:
                try:
                    deadline = datetime.strptime(deadline_raw.split(" ")[0], "%Y-%m-%d").date()
                except Exception:
                    deadline = None

            def to_float(val):
                val = (val or "").strip()
                return float(val) if val else None

            def to_bool(val):
                val = (val or "").strip()
                if val == "":
                    return False
                # accepts "1"/"0", "true"/"false"
                if val.lower() in ("true", "t", "yes", "y"):
                    return True
                if val.lower() in ("false", "f", "no", "n"):
                    return False
                try:
                    return bool(int(val))
                except Exception:
                    return False

            g = Grant(
                organization_id=int(row.get("organization_id") or org.id),
                name_en=row.get("name_en") or row.get("name") or "",
                name_fr=row.get("name_fr") or "",
                description_en=row.get("description_en") or row.get("description") or "",
                description_fr=row.get("description_fr") or "",
                eligibility_en=row.get("eligibility_en") or "",
                eligibility_fr=row.get("eligibility_fr") or "",
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
                external_id=(row.get("external_id") or source_url).strip(),
            )

            db.session.add(g)
            created += 1

    db.session.commit()
    print(f"Seeded {created} grants from grants.csv")
