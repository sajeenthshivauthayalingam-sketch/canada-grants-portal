# Youreka Grant Portal

Internal web app for Youreka Canada to track grants and scholarships by region, status, and deadline.  
Built with **Flask** and **SQLite**, with basic scraping + bilingual support scaffolding.

---

## 1. Requirements

- Python 3.10+  
- pip (Python package manager)  
- Git (optional, if you’re cloning from GitHub)

---

## 2. Getting Started

### 2.1. Clone the repo (or download)

```bash
git clone https://github.com/<your-username>/canada-grants-portal.git
cd canada-grants-portal
````

Or just download the ZIP and extract it, then `cd` into the folder.

---

### 2.2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the start of your terminal prompt.

---

### 2.3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Initialize the Database

The app uses SQLite (`grants.db` in the project root).

The first time you run the app, it will:

* Create all tables (Grants, Organizations, Regions, GrantStatus)
* Seed default regions (National, Vancouver, Montreal, Calgary, Edmonton, Kingston, Toronto, Windsor, French Expansion)

Just start the app once:

```bash
python app.py
```

You should see Flask start up. You can stop it with `Ctrl + C` if you want.

---

## 4. (Optional) Import Example Grants via Scraper

There is a simple scraping command that pulls some basic funding program data from a Government of Canada page and inserts them as sample grants.

Run:

```bash
flask --app app scrape-grants
```

You should see log output like:

```text
Running scraping task for Canada funding programs...
Found X candidate program links
Scraping complete. Created Y new grants.
```

---

## 5. Run the Web App

To start the server:

```bash
flask --app app run
```

or:

```bash
python app.py
```

By default, the app will be available at:

> [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 6. How people maintain it later
Update code:
Anyone with repo access edits locally → `git commit && git push`.
Render auto-detects the push and redeploys.

Update DB schema:
If you add new columns, just deploy – `db.create_all()` will create new tables, and for new columns you can either run simple ALTER statements or later add Alembic, but for this project simple tables are usually fine.

Scrape data in the cloud:
You already have the `scrape-grants` CLI. On Render:

Go to the web service → Shell (or Jobs) and run:

```bash
flask --app app scrape-grants
```
