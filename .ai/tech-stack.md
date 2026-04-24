# Tech Stack — Damian's Trade Ideas Viewer

## Overview

A lightweight Django web app deployed directly on Alpine Linux (no Docker). The stack is chosen to run comfortably within the Mikrus Frog VPS constraints: 256 MB RAM, 3 GB disk, unprivileged LXC container.

---

## Backend

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | Python 3.11+ | Available on Alpine via `apk`; matches AI tooling ecosystem |
| Framework | Django 5.x | Built-in template engine, URL routing, file upload handling — no extras needed |
| WSGI server | Gunicorn | Lightweight production-grade server; replaces Django's dev server in production |
| JSON handling | Python built-in `json` module | No third-party library needed |
| Storage | Filesystem (`data/` directory) | No database required; files replaced on upload |

### Why Django over Flask/FastAPI?
Django's template engine, form handling, and static file management cover everything needed without additional libraries. Flask would require assembling more pieces. FastAPI is API-oriented and would pair awkwardly with server-rendered HTML.

### No database
All persistent state is a handful of JSON files on disk. Django's ORM is not used. `DATABASES` in settings will be set to an empty dict or SQLite kept only if Django internals require it.

---

## Frontend

| Layer | Choice | Reason |
|-------|--------|--------|
| Templating | Django templates | Server-rendered HTML; no build step; works without JS |
| CSS framework | Tailwind CSS (CDN) | Utility-first; clean cards and typography without a PostCSS build pipeline |
| Interactivity | Alpine.js (CDN) | Lightweight (15 KB); handles tabs, collapsibles, drag-and-drop without a framework |
| Icons | Heroicons (inline SVG) | Free, clean, no extra dependency |

### Why Tailwind via CDN?
Avoids Node.js toolchain on the VPS. The CDN build is slightly larger than a purged build but negligible for a personal tool.

### Why Alpine.js?
Handles all needed interactivity (tab switching between report teams, collapsible sections, drag-and-drop upload zone feedback) with minimal code. No build step. Pairs naturally with Django templates via `x-data` / `x-show` directives.

---

## Infrastructure

| Layer | Choice | Reason |
|-------|--------|--------|
| OS | Alpine Linux (pre-installed on Frog) | Minimal RAM footprint; `apk` package manager |
| Reverse proxy | Nginx | Serves static files directly; proxies `/` to Gunicorn; handles Basic Auth |
| Process management | OpenRC (Alpine's init system) | Keeps Gunicorn running as a service; restarts on crash |
| Access control | Nginx HTTP Basic Auth (`.htpasswd`) | Simplest private-tool protection; no Django auth layer needed |
| HTTPS | Mikrus `wykr.es` subdomain proxy | Automatic HTTPS termination handled upstream — app serves plain HTTP on internal port |

### Deployment URL pattern
```
https://frog02-PORT.wykr.es
```
`PORT` is one of the three TCP ports allocated by Mikrus for VPS `f21044`. Confirmed after first SSH login.

### No Docker
The Frog VPS runs as an unprivileged LXC container. Docker requires kernel features (namespaces, cgroups v2, `overlay` filesystem) that are unavailable or restricted in this environment. The stack is installed natively on Alpine instead.

---

## Project Layout

```
project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── viewer/                  # Main Django app
│   ├── templates/
│   │   └── viewer/
│   │       ├── base.html
│   │       ├── report.html
│   │       ├── review.html
│   │       └── judgement.html
│   ├── static/
│   │   └── viewer/
│   │       └── app.js
│   ├── views.py
│   ├── urls.py
│   └── utils.py             # JSON loading, filename parsing
├── data/                    # Stored JSON files (gitignored)
│   ├── *_report_*.json
│   ├── *_reviews.json
│   └── *judgement.json
├── manage.py
├── requirements.txt
├── gunicorn.conf.py
└── .env                     # SECRET_KEY, DEBUG, ALLOWED_HOSTS (gitignored)
```

---

## Settings Split

| File | Purpose |
|------|---------|
| `base.py` | Shared config: installed apps, templates, static files, `DATA_DIR` path |
| `dev.py` | `DEBUG=True`, `ALLOWED_HOSTS=['localhost']`, data dir points to local `data/` |
| `prod.py` | `DEBUG=False`, `ALLOWED_HOSTS=['frog02-PORT.wykr.es']`, reads `SECRET_KEY` from env |

Selected via `DJANGO_SETTINGS_MODULE` environment variable.

---

## Key Dependencies (`requirements.txt`)

```
django>=5.0,<6.0
gunicorn>=21.0
```

That is the entire production dependency list.

---

## Local Development

- Run Django's built-in dev server (`python manage.py runserver`)
- No Nginx needed locally
- Use `dev.py` settings
- `data/` directory populated with sample JSON files from the repo

---

## RAM Budget (Frog VPS — 256 MB)

| Process | Estimated RAM |
|---------|--------------|
| Alpine OS baseline | ~30 MB |
| Nginx | ~5 MB |
| Gunicorn (2 workers) | ~80–100 MB |
| Headroom | ~120 MB |

Two Gunicorn workers is the right default for a single-user personal tool on 256 MB. Adjust to 1 worker if memory pressure appears.
