from . import bp
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from ..extensions import db
from ..models import Grant, GrantStatus, Region
from sqlalchemy import func

def _apply_filters(query):
    """
    Apply multi-filter search logic based on query params.
    - Empty / 'Any' values are ignored
    - Province supports 'ON' or 'Ontario' etc. (case-insensitive, partial)
    - 'Grant type = both' is treated as 'any'
    """
    args = request.args

    # ---- Normalize inputs ----
    region_id = args.get("region_id", default=None, type=int)

    province_raw = (args.get("province") or "").strip()
    province = province_raw or None

    ngo_only = args.get("ngo_only")  # "true" or None
    min_amount = args.get("min_amount", type=float)
    max_amount = args.get("max_amount", type=float)

    category = (args.get("category") or "").strip() or None

    language = (args.get("language") or "").strip() or None
    if language == "":
        language = None

    team_scope = (args.get("team_scope") or "").strip() or None

    individual_type = (args.get("individual_type") or "").strip() or None
    # Treat "both" as "any" so we don't accidentally filter out everything
    if individual_type == "both":
        individual_type = None

    deadline_before_raw = (args.get("deadline_before") or "").strip() or None

    # ---- Apply filters only when values are meaningful ----

    if region_id:
        # Only show grants that have a status row for that region
        query = query.join(GrantStatus, GrantStatus.grant_id == Grant.id).filter(
            GrantStatus.region_id == region_id
        )

    if province:
        # Map common province abbreviations to full names
        prov_map = {
            "ON": "Ontario",
            "BC": "British Columbia",
            "AB": "Alberta",
            "QC": "Quebec",
            "MB": "Manitoba",
            "SK": "Saskatchewan",
            "NS": "Nova Scotia",
            "NB": "New Brunswick",
            "PE": "Prince Edward Island",
            "NL": "Newfoundland and Labrador",
        }
        abbrev = province.upper()
        full = prov_map.get(abbrev)

        if full:
            # Exact match on full name, case-insensitive
            query = query.filter(func.lower(Grant.province) == full.lower())
        else:
            # Fallback: partial match (typing "Ont" will match "Ontario")
            like_pattern = f"%{province.lower()}%"
            query = query.filter(func.lower(Grant.province).like(like_pattern))

    if ngo_only == "true":
        query = query.filter(Grant.is_ngo_only.is_(True))

    if min_amount is not None:
        # Only apply to grants where funding_max is set
        query = query.filter(
            Grant.funding_max.isnot(None),
            Grant.funding_max >= min_amount,
        )

    if max_amount is not None:
        query = query.filter(
            Grant.funding_min.isnot(None),
            Grant.funding_min <= max_amount,
        )

    if category:
        query = query.filter(Grant.category == category)

    if language:
        query = query.filter(Grant.language == language)

    if team_scope:
        query = query.filter(Grant.team_scope == team_scope)

    if individual_type:
        query = query.filter(Grant.individual_type == individual_type)

    if deadline_before_raw:
        try:
            year, month, day = map(int, deadline_before_raw.split("-"))
            cutoff = date(year, month, day)
            query = query.filter(
                Grant.deadline_date.isnot(None),
                Grant.deadline_date <= cutoff,
            )
        except ValueError:
            # Ignore bad date input
            pass

    return query

@bp.route("/")
def index():
    # Base query
    query = Grant.query

    # Apply filters
    query = _apply_filters(query)

    # Sort by deadline (nulls last)
    grants = query.order_by(Grant.deadline_date.is_(None), Grant.deadline_date.asc()).all()

    regions = Region.query.filter_by(is_active=True).all()

    current_date = date.today()

    return render_template(
        "grants/list.html",
        grants=grants,
        regions=regions,
        current_date=current_date,
        filters=request.args,
    )


@bp.route("/grant/<int:grant_id>", methods=["GET", "POST"])
def grant_detail(grant_id):
    grant = Grant.query.get_or_404(grant_id)
    regions = Region.query.filter_by(is_active=True).all()

    # Region-specific status handling
    selected_region_id = request.args.get("region_id", type=int)
    region = None
    status_record = None

    if selected_region_id:
        region = Region.query.get(selected_region_id)
        if region:
            status_record = GrantStatus.query.filter_by(
                grant_id=grant.id, region_id=region.id
            ).first()

    if request.method == "POST":
        region_id = request.form.get("region_id", type=int)
        status = request.form.get("status")
        notes = request.form.get("notes")

        if not region_id:
            flash(_("Please select a region before updating status."), "warning")
            return redirect(
                url_for("grants.grant_detail", grant_id=grant.id, region_id=selected_region_id)
            )

        region = Region.query.get_or_404(region_id)

        status_record = GrantStatus.query.filter_by(
            grant_id=grant.id, region_id=region.id
        ).first()

        if not status_record:
            status_record = GrantStatus(
                grant_id=grant.id,
                region_id=region.id,
            )
            db.session.add(status_record)

        status_record.status = status
        status_record.notes = notes
        db.session.commit()
        flash(_("Status updated successfully."), "success")

        return redirect(
            url_for("grants.grant_detail", grant_id=grant.id, region_id=region.id)
        )

    # If no region selected, just show generic view
    return render_template(
        "grants/detail.html",
        grant=grant,
        regions=regions,
        selected_region=region,
        status_record=status_record,
    )
