from . import bp
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from ..extensions import db
from ..models import Grant, GrantStatus, Region


def _apply_filters(query):
    """
    Apply multi-filter search logic based on query params.
    Supports:
      region_id, province, ngo_only, min_amount, max_amount,
      category, language, team_scope, individual_type, deadline_before
    """
    region_id = request.args.get("region_id", type=int)
    province = request.args.get("province", type=str)
    ngo_only = request.args.get("ngo_only", type=str)  # "true" or ""
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)
    category = request.args.get("category", type=str)
    language = request.args.get("language", type=str)
    team_scope = request.args.get("team_scope", type=str)
    individual_type = request.args.get("individual_type", type=str)
    deadline_before = request.args.get("deadline_before", type=str)

    if region_id:
        # join to GrantStatus to ensure at least one status row for that region
        query = query.join(GrantStatus, GrantStatus.grant_id == Grant.id).filter(
            GrantStatus.region_id == region_id
        )

    if province:
        query = query.filter(Grant.province == province)

    if ngo_only == "true":
        query = query.filter(Grant.is_ngo_only.is_(True))

    if min_amount is not None:
        query = query.filter(Grant.funding_max >= min_amount)

    if max_amount is not None:
        query = query.filter(Grant.funding_min <= max_amount)

    if category:
        query = query.filter(Grant.category == category)

    if language:
        query = query.filter(Grant.language == language)

    if team_scope:
        query = query.filter(Grant.team_scope == team_scope)

    if individual_type:
        query = query.filter(Grant.individual_type == individual_type)

    if deadline_before:
        try:
            year, month, day = map(int, deadline_before.split("-"))
            cutoff = date(year, month, day)
            query = query.filter(
                Grant.deadline_date.isnot(None),
                Grant.deadline_date <= cutoff,
            )
        except ValueError:
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
