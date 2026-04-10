from . import bp
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from ..extensions import db
from ..models import Grant, GrantStatus, Region, Earning
from sqlalchemy import func

PROVINCES = [
    ("AB", "Alberta"),
    ("BC", "British Columbia"),
    ("MB", "Manitoba"),
    ("NB", "New Brunswick"),
    ("NL", "Newfoundland and Labrador"),
    ("NS", "Nova Scotia"),
    ("NT", "Northwest Territories"),
    ("NU", "Nunavut"),
    ("ON", "Ontario"),
    ("PE", "Prince Edward Island"),
    ("QC", "Quebec"),
    ("SK", "Saskatchewan"),
    ("YT", "Yukon"),
]

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
        query = query.filter(func.lower(Grant.category) == category.lower())

    if language:
        query = query.filter(func.lower(Grant.language) == language.lower())

    if team_scope:
        query = query.filter(func.lower(Grant.team_scope) == team_scope.lower())

    if individual_type:
        query = query.filter(func.lower(Grant.individual_type) == individual_type.lower())

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
def landing():
    today = date.today()
    curated_count = Grant.query.filter(
        (Grant.source_type == "internal") | (Grant.source_type.is_(None))
    ).count()
    opendata_count = Grant.query.filter(Grant.source_type == "external").count()

    # Total earnings
    manual_total = db.session.query(
        func.coalesce(func.sum(Earning.amount), 0)
    ).scalar()
    awarded_total = db.session.query(
        func.coalesce(func.sum(GrantStatus.amount_awarded), 0)
    ).filter(GrantStatus.status == "Awarded").scalar()
    total_earned = (manual_total or 0) + (awarded_total or 0)

    return render_template(
        "landing.html",
        curated_count=curated_count,
        opendata_count=opendata_count,
        total_earned=total_earned,
        current_date=today,
    )


@bp.route("/grants")
def index():
    today = date.today()
    PER_PAGE = 12

    source = request.args.get("source", "curated")  # "curated" or "opendata"
    tab = request.args.get("tab", "active")          # "active" or "expired"
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    # Build base queries for counts (unfiltered by active/expired)
    internal_base = Grant.query.filter(
        (Grant.source_type == "internal") | (Grant.source_type.is_(None))
    )
    internal_base = _apply_filters(internal_base)

    external_base = Grant.query.filter(Grant.source_type == "external")
    external_base = _apply_filters(external_base)

    # Counts for tab badges
    internal_active_count = internal_base.filter(
        (Grant.deadline_date.is_(None)) | (Grant.deadline_date >= today)
    ).count()
    internal_expired_count = internal_base.filter(
        Grant.deadline_date.isnot(None), Grant.deadline_date < today
    ).count()
    external_active_count = external_base.filter(
        (Grant.deadline_date.is_(None)) | (Grant.deadline_date >= today)
    ).count()
    external_expired_count = external_base.filter(
        Grant.deadline_date.isnot(None), Grant.deadline_date < today
    ).count()

    # Pick the right query based on source + tab
    if source == "opendata":
        query = external_base
    else:
        query = internal_base

    if tab == "expired":
        query = query.filter(Grant.deadline_date.isnot(None), Grant.deadline_date < today)
    else:
        query = query.filter((Grant.deadline_date.is_(None)) | (Grant.deadline_date >= today))

    query = query.order_by(Grant.deadline_date.is_(None), Grant.deadline_date.asc())

    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    if page > total_pages:
        page = total_pages
    grants_page = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return render_template(
        "grants/list.html",
        grants_page=grants_page,
        source=source,
        tab=tab,
        page=page,
        total_pages=total_pages,
        total=total,
        internal_active_count=internal_active_count,
        internal_expired_count=internal_expired_count,
        external_active_count=external_active_count,
        external_expired_count=external_expired_count,
        internal_total=internal_active_count + internal_expired_count,
        external_total=external_active_count + external_expired_count,
        provinces=PROVINCES,
        current_date=today,
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


@bp.route("/earnings", methods=["GET", "POST"])
def earnings():
    if request.method == "POST":
        fiscal_year = (request.form.get("fiscal_year") or "").strip()
        amount = request.form.get("amount", type=float)
        source_label = (request.form.get("source_label") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if fiscal_year and amount is not None:
            earning = Earning(
                fiscal_year=fiscal_year,
                amount=amount,
                source_label=source_label or None,
                notes=notes or None,
            )
            db.session.add(earning)
            db.session.commit()
            flash(_("Earning entry added."), "success")
        return redirect(url_for("grants.earnings"))

    # Manual earnings grouped by fiscal year
    earnings_by_year = (
        db.session.query(
            Earning.fiscal_year,
            func.sum(Earning.amount).label("total"),
        )
        .group_by(Earning.fiscal_year)
        .order_by(Earning.fiscal_year.desc())
        .all()
    )

    # Awarded amounts from GrantStatus
    awarded_total = (
        db.session.query(func.coalesce(func.sum(GrantStatus.amount_awarded), 0))
        .filter(GrantStatus.status == "Awarded")
        .scalar()
    ) or 0

    manual_total = sum(row.total or 0 for row in earnings_by_year)
    grand_total = manual_total + awarded_total

    all_entries = Earning.query.order_by(
        Earning.fiscal_year.desc(), Earning.created_at.desc()
    ).all()

    return render_template(
        "grants/earnings.html",
        earnings_by_year=earnings_by_year,
        awarded_total=awarded_total,
        manual_total=manual_total,
        grand_total=grand_total,
        all_entries=all_entries,
        current_date=date.today(),
    )
