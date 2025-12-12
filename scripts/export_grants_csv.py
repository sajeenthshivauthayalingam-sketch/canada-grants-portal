import os
import csv
import sys
from datetime import datetime

from youreka import create_app
from youreka.models import Grant

OUTPUT_PATH = os.path.join("data", "grants.csv")

def main():
    app = create_app("DevConfig")
    with app.app_context():
        grants = Grant.query.order_by(Grant.id.asc()).all()

        os.makedirs("data", exist_ok=True)

        fieldnames = [
            "id",
            "organization_id",
            "name_en",
            "name_fr",
            "description_en",
            "description_fr",
            "eligibility_en",
            "eligibility_fr",
            "category",
            "region_scope",
            "country",
            "province_state",
            "funding_min",
            "funding_max",
            "currency",
            "deadline_date",
            "ongoing_flag",
            "language",
            "team_scope",
            "individual_type",
            "is_ngo_only",
            "source_url",
            "external_id",
            "created_at",
            "updated_at",
        ]

        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for g in grants:
                writer.writerow({
                    "id": g.id,
                    "organization_id": g.organization_id,
                    "name_en": getattr(g, "name_en", None) or g.name_en if hasattr(g, "name_en") else (getattr(g, "name_en", "") or ""),
                    "name_fr": getattr(g, "name_fr", "") if hasattr(g, "name_fr") else "",
                    "description_en": getattr(g, "description_en", "") if hasattr(g, "description_en") else "",
                    "description_fr": getattr(g, "description_fr", "") if hasattr(g, "description_fr") else "",
                    "eligibility_en": getattr(g, "eligibility_en", "") if hasattr(g, "eligibility_en") else "",
                    "eligibility_fr": getattr(g, "eligibility_fr", "") if hasattr(g, "eligibility_fr") else "",
                    "category": g.category,
                    "region_scope": g.region_scope,
                    "country": g.country,
                    "province_state": getattr(g, "province", None) or getattr(g, "province_state", None),
                    "funding_min": g.funding_min,
                    "funding_max": g.funding_max,
                    "currency": g.currency,
                    "deadline_date": g.deadline_date.isoformat() if g.deadline_date else "",
                    "ongoing_flag": 1 if g.ongoing_flag else 0,
                    "language": g.language,
                    "team_scope": g.team_scope,
                    "individual_type": getattr(g, "individual_type", "") if hasattr(g, "individual_type") else "",
                    "is_ngo_only": 1 if getattr(g, "is_ngo_only", False) else 0,
                    "source_url": g.source_url,
                    "external_id": g.external_id,
                    "created_at": g.created_at.isoformat(sep=" ") if g.created_at else "",
                    "updated_at": g.updated_at.isoformat(sep=" ") if g.updated_at else "",
                })

        print(f"✅ Exported {len(grants)} grants to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
