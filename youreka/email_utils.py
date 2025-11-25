from datetime import date, timedelta
from flask import current_app
from .extensions import db
from .models import Grant, GrantStatus, Region


def get_upcoming_deadlines(days_ahead=7):
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    return (
        Grant.query.filter(
            Grant.deadline_date.isnot(None),
            Grant.deadline_date >= today,
            Grant.deadline_date <= cutoff,
        )
        .order_by(Grant.deadline_date.asc())
        .all()
    )


def send_deadline_reminders():
    """
    Stub: In production you would integrate with an email provider (SMTP, SendGrid, etc.).
    For now, this function just logs which grants would get reminders.
    """
    days_ahead = current_app.config.get("REMINDER_DAYS", 7)
    upcoming = get_upcoming_deadlines(days_ahead=days_ahead)

    if not upcoming:
        print("No upcoming deadlines in the next", days_ahead, "days.")
        return

    print("Upcoming grant deadlines (for reminder emails):")
    for grant in upcoming:
        print(
            f"- {grant.name_en} (deadline: {grant.deadline_date}, source: {grant.source_url})"
        )
    print("Stub: integrate with email service here.")


# This helper can be wired into a cron job by running:
#   flask send-reminders
# See __init__.py where the CLI command is registered.
