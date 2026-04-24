# Damian's Trade Ideas

A private web app for visualising AI-generated trading JSON files — reports, peer reviews, and final judgements. Built with Django, styled with Tailwind CSS, deployed on a Mikrus Frog VPS.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + Django 6 |
| Frontend | Django templates + Tailwind CSS (CDN) + Alpine.js (CDN) |
| WSGI server | Gunicorn (2 workers) |
| Reverse proxy | Nginx |
| Hosting | Mikrus Frog VPS — Alpine Linux, 256 MB RAM |

No database. JSON files are stored on disk in `data/`.

---

## Local Development

### Prerequisites

- Python 3.11+
- Git

### Setup

```bash
git clone https://github.com/dam-przyb/dp_simple_front.git
cd dp_simple_front

python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DJANGO_SETTINGS_MODULE=config.settings.dev
```

Run the development server:

```bash
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000).

> The `data/` directory is gitignored. Drop your JSON files there manually or use the Upload page.

---

## JSON File Naming Conventions

The app detects file type from the filename — naming must follow these patterns:

| Type | Pattern | Example |
|------|---------|---------|
| Report | `*_report_*.json` | `202604181218_report_deepseek.json` |
| Review | `*_reviews.json` | `20260418_reviews.json` |
| Judgement | `*judgement*.json` | `20260424judgement.json` |

Multiple report files can coexist (one per AI team). Only one review and one judgement file are kept — uploading a new one replaces the old.

---

## Project Layout

```
config/
  settings/
    base.py       # shared settings
    dev.py        # local overrides (DEBUG=True)
    prod.py       # VPS overrides (reads from .env)
  urls.py
  wsgi.py
viewer/
  templates/viewer/
    base.html     # nav shell, hamburger menu
    report.html
    review.html
    judgement.html
    upload.html
  static/viewer/
    app.js        # Alpine.js uploader component
  views.py
  utils.py        # all JSON file I/O
  urls.py
data/             # JSON files (gitignored, not in repo)
.ai/              # project docs (PRD, tech stack, implementation plan)
```

---

## Deploying Updates to the VPS

After pushing changes to GitHub:

```bash
# 1. SSH into the server (see below)
# 2. Pull and restart Gunicorn
cd /srv/tradeviewer
git pull
rc-service tradeviewer restart
```

Static files only change if you modify `app.js` or add new static assets:

```bash
source venv/bin/activate
python manage.py collectstatic --noinput
rc-service nginx reload
```

---

## VPS Access

The app runs on a Mikrus Frog server. To connect via terminal:

```bash
ssh -p 11044 frog@frog02.mikr.us
```

Once logged in, switch to root for any admin tasks:

```bash
sudo su
```

Credentials are stored separately in `_frog_docs/access.txt` (not committed to the repo).

The live URL is: **https://frog02-21044.wykr.es**  
Basic Auth is required — credentials are in `_frog_docs/access.txt`.

---

## Service Management on the VPS

```bash
# Check service status
rc-service tradeviewer status
rc-service nginx status

# Restart services
rc-service tradeviewer restart
rc-service nginx reload

# View Gunicorn logs
tail -f /var/log/messages

# Check disk space
df -h

# Check memory
free -m

# Update system packages
apk update && apk upgrade
```

---

## Environment Variables (prod)

Set in `/srv/tradeviewer/.env` on the VPS — never committed to the repo.

| Variable | Description |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | Must be `config.settings.prod` |
| `SECRET_KEY` | Django secret key — keep private |
| `ALLOWED_HOSTS` | Comma-separated hostnames, e.g. `frog02-21044.wykr.es,localhost` |
