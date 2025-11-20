# db.py
import sqlite3
from contextlib import contextmanager

DB_PATH = "grants.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()

        # Organizations table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                ngo_status INTEGER,
                country TEXT,
                province_state TEXT,
                website_url TEXT,
                language_primary TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )

        # Scholarships / grants table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scholarships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                region_scope TEXT,
                country TEXT,
                province_state TEXT,
                funding_min REAL,
                funding_max REAL,
                currency TEXT,
                deadline_date TEXT,
                ongoing_flag INTEGER,
                language TEXT,
                team_scope TEXT,
                source_url TEXT,
                external_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            );
            """
        )

        conn.commit()


def insert_organization(conn, org_name, country="Canada", province_state=None):
    """Insert organization if not exists, return its id."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM organizations WHERE name = ?",
        (org_name,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO organizations (name, country, province_state)
        VALUES (?, ?, ?)
        """,
        (org_name, country, province_state),
    )
    conn.commit()
    return cur.lastrowid


def insert_scholarship(conn, scholarship):
    """Insert a scholarship/grant row. `scholarship` is a dict."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scholarships (
            organization_id,
            name,
            description,
            category,
            region_scope,
            country,
            province_state,
            funding_min,
            funding_max,
            currency,
            deadline_date,
            ongoing_flag,
            language,
            team_scope,
            source_url,
            external_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            scholarship.get("organization_id"),
            scholarship.get("name"),
            scholarship.get("description"),
            scholarship.get("category"),
            scholarship.get("region_scope"),
            scholarship.get("country"),
            scholarship.get("province_state"),
            scholarship.get("funding_min"),
            scholarship.get("funding_max"),
            scholarship.get("currency"),
            scholarship.get("deadline_date"),
            1 if scholarship.get("ongoing_flag") else 0,
            scholarship.get("language"),
            scholarship.get("team_scope"),
            scholarship.get("source_url"),
            scholarship.get("external_id"),
        ),
    )
    conn.commit()
