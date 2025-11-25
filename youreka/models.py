from datetime import datetime, date
from .extensions import db


class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_fr = db.Column(db.String(100))
    province = db.Column(db.String(50))
    city = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)

    statuses = db.relationship("GrantStatus", back_populates="region")

    def __repr__(self):
        return f"<Region {self.name_en}>"


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))  # e.g., "Government", "Foundation"
    ngo_only = db.Column(db.Boolean, default=False)
    website_url = db.Column(db.String(255))
    country = db.Column(db.String(50), default="Canada")
    province = db.Column(db.String(50))

    grants = db.relationship("Grant", back_populates="organization")

    def __repr__(self):
        return f"<Org {self.name}>"


class Grant(db.Model):
    __tablename__ = "grants"

    id = db.Column(db.Integer, primary_key=True)

    # Bilingual name and description
    name_en = db.Column(db.String(255), nullable=False)
    name_fr = db.Column(db.String(255))
    description_en = db.Column(db.Text)
    description_fr = db.Column(db.Text)

    eligibility_en = db.Column(db.Text)
    eligibility_fr = db.Column(db.Text)

    # Relationships
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    organization = db.relationship("Organization", back_populates="grants")

    # Classification
    category = db.Column(db.String(100))  # e.g., "Education", "Youth"
    province = db.Column(db.String(50))
    region_scope = db.Column(db.String(50))  # e.g., "National", "Provincial"
    country = db.Column(db.String(50), default="Canada")
    team_scope = db.Column(db.String(50))    # "National", "Regional"
    individual_type = db.Column(db.String(20))  # "individual", "organization", "both"

    # Funding
    funding_min = db.Column(db.Float)
    funding_max = db.Column(db.Float)
    currency = db.Column(db.String(10), default="CAD")

    # Deadline
    deadline_date = db.Column(db.Date, nullable=True)
    ongoing_flag = db.Column(db.Boolean, default=False)

    # Language
    language = db.Column(db.String(20), default="EN")  # "EN", "FR", "Bilingual"
    is_ngo_only = db.Column(db.Boolean, default=False)

    # Links
    source_url = db.Column(db.String(255))
    external_id = db.Column(db.String(255), unique=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    statuses = db.relationship("GrantStatus", back_populates="grant")

    def days_until_deadline(self):
        if not self.deadline_date:
            return None
        return (self.deadline_date - date.today()).days

    def __repr__(self):
        return f"<Grant {self.name_en}>"


class GrantStatus(db.Model):
    """
    Region-specific status for each grant.
    Allows each region to track its own status, notes, and budgets.
    """
    __tablename__ = "grant_statuses"

    id = db.Column(db.Integer, primary_key=True)
    grant_id = db.Column(db.Integer, db.ForeignKey("grants.id"), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)

    status = db.Column(
        db.String(20),
        default="Not Started",
    )  # Not Started, In Progress, Submitted, Rejected, Awarded
    notes = db.Column(db.Text)

    budget_allocated = db.Column(db.Float)
    amount_applied = db.Column(db.Float)
    amount_awarded = db.Column(db.Float)

    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    grant = db.relationship("Grant", back_populates="statuses")
    region = db.relationship("Region", back_populates="statuses")

    def __repr__(self):
        return f"<GrantStatus grant={self.grant_id} region={self.region_id} status={self.status}>"
