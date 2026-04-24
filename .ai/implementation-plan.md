# Implementation Plan — Damian's Trade Ideas Viewer

## How to Read This Plan

Each phase builds on the previous one. **Do not skip phases** — each one produces a working, testable state before adding more complexity. Phases 1–4 are local development. Phase 5 is deployment to the VPS.

Coding agents working on this project should:
- Complete one phase fully before starting the next
- Run the app and verify the acceptance criteria before moving on
- Never hardcode secrets, paths, or environment-specific values

---

## Phase 1 — Django Project Skeleton

**Goal:** A running Django app with correct structure, settings split, and a single placeholder page.

### Tasks
1. Create virtual environment and install dependencies
   ```
   python -m venv venv
   pip install django gunicorn
   pip freeze > requirements.txt
   ```
2. Scaffold Django project
   ```
   django-admin startproject config .
   python manage.py startapp viewer
   ```
3. Restructure settings into `config/settings/base.py`, `dev.py`, `prod.py`
4. Set `DJANGO_SETTINGS_MODULE=config.settings.dev` in a `.env` file
5. Register `viewer` in `INSTALLED_APPS` in `base.py`
6. Add `DATA_DIR = BASE_DIR / 'data'` to `base.py`
7. Create `config/urls.py` routing to `viewer/urls.py`
8. Create a single index view returning `200 OK` with plain text "OK"
9. Create `.gitignore` (Python/Django standard — exclude `.env`, `data/`, `__pycache__`, `db.sqlite3`)

### Acceptance Criteria
- `python manage.py runserver` starts without errors
- `http://localhost:8000/` returns a response
- No secrets in any committed file

---

## Phase 2 — Base Template & Navigation Shell

**Goal:** The full page chrome (top bar, sidebar, content area) rendered in HTML with Tailwind and Alpine.js. No real data yet — placeholder content only.

### Tasks
1. Create `viewer/templates/viewer/base.html` with:
   - Top horizontal bar: title "Damian's Trade Ideas"
   - Left vertical sidebar with three links: Report, Review, Judgement
   - Main content `<div>` block for child templates to fill
   - Tailwind CSS loaded via CDN
   - Alpine.js loaded via CDN
2. Create stub templates `report.html`, `review.html`, `judgement.html` — each extends `base.html` and shows a placeholder heading
3. Add URL routes and views for `/report/`, `/review/`, `/judgement/`
4. Highlight the active sidebar link based on current URL (use Django's `request.resolver_match` or pass an `active_page` context variable)
5. Add basic static file config (`STATICFILES_DIRS`, `STATIC_URL`)

### Acceptance Criteria
- All three routes load without error
- Top bar and sidebar visible on all pages
- Active page is visually highlighted in the sidebar
- Layout does not break on a narrow browser window (basic horizontal scroll acceptable at this stage)

---

## Phase 3 — JSON Loading & Display (Read-Only)

**Goal:** Each page reads its JSON file(s) from disk and renders real data in styled cards.

### Tasks

#### 3a — Utility functions (`viewer/utils.py`)
1. `get_latest_reports(data_dir)` — returns a list of all `*_report_*.json` files, each parsed, with `team` name extracted from filename
2. `get_latest_review(data_dir)` — returns parsed content of the single `*_reviews.json` file (or `None` if absent)
3. `get_latest_judgement(data_dir)` — returns parsed content of the single `*judgement.json` file (or `None` if absent)
4. `detect_file_type(filename)` — returns `'report'`, `'review'`, `'judgement'`, or `None` based on filename pattern
5. All functions handle missing files gracefully (return `None` / empty list, never raise unhandled exceptions)

#### 3b — Report page
1. View calls `get_latest_reports()` and passes list to template
2. Template renders one section per team:
   - Team name as section heading
   - General market overview (collapsible via Alpine.js `x-show`)
   - One card per company pick:
     - Ticker + company name
     - LONG/SHORT badge (green/red)
     - Last close, target price, upside %
     - Technical summary, fundamental situation, detailed report
     - Sources as `<a>` links (open in new tab)
3. Show "No report uploaded yet" state if list is empty

#### 3c — Review page
1. View calls `get_latest_review()` and passes data to template
2. Template renders one section per team:
   - One card per pick: ticker, stock name, LONG/SHORT badge, score (colour-coded), validity badge, reasoning
3. Show "No review uploaded yet" state if `None`

#### 3d — Judgement page
1. View calls `get_latest_judgement()` and passes data to template
2. Template renders:
   - Selected Picks — one card per pick: ticker, direction badge, confidence (1–5), price → target → upside, session scope, reasoning
   - Excluded Candidates — compact list: ticker + reason
3. Show "No judgement uploaded yet" state if `None`

### Acceptance Criteria
- All three pages render real data from the sample files in `data/`
- Missing file states display gracefully
- Colour coding (green/red/amber) applied consistently
- No raw JSON visible anywhere on the page

---

## Phase 4 — File Upload

**Goal:** Owner can drag-and-drop (or click to select) multiple JSON files. The server detects file type, validates JSON, and saves to `data/`.

### Tasks

#### 4a — Upload UI
1. Add a drag-and-drop upload zone to `base.html` (visible on all pages, e.g. floating button or section in sidebar)
2. On drop or file-picker selection, display a list of selected filenames with pending status icons
3. Submit files via `fetch()` (AJAX POST) to `/upload/` — no full page reload
4. Display per-file result after response: success (green tick) or error (red X + message)
5. On success, reload the current page content (or full page reload — simpler and acceptable)

#### 4b — Upload view (`viewer/views.py`)
1. `POST /upload/` accepts `multipart/form-data` with one or more files
2. For each file:
   - Reject if not `.json` extension → return error for that file
   - Parse JSON → reject with error if invalid
   - Call `detect_file_type(filename)` → reject with error if pattern unrecognised
   - Save to `DATA_DIR` using the original filename
   - For review and judgement: overwrite any existing file of that type
   - For report: save with original filename (multiple coexist)
3. Return JSON response: `{ "results": [{ "filename": "...", "ok": true/false, "error": "..." }] }`
4. Protect the upload endpoint with Django's CSRF token (included automatically via `{% csrf_token %}` in the form or the `X-CSRFToken` header in fetch)

### Security Notes
- Validate file extension AND parse JSON before saving — never save raw unvalidated input
- Use `os.path.basename()` on uploaded filename to prevent path traversal attacks
- Only write to `DATA_DIR` — never allow arbitrary paths

### Acceptance Criteria
- Drag-and-drop of 5 reports + 1 review + 1 judgement in a single gesture works
- Each file gets individual success/error feedback
- Invalid JSON is rejected with a clear message
- Unrecognised filenames are rejected with a clear message
- After upload, the relevant page shows updated data

---

## Phase 5 — VPS Deployment

**Goal:** App running on Mikrus Frog, accessible via `https://frog02-PORT.wykr.es` with Basic Auth.

### Tasks

#### 5a — Prepare VPS
1. SSH into the server:
   ```bash
   ssh -p 11044 frog@frog02.mikr.us
   ```
2. Switch to root and update packages:
   ```bash
   sudo su
   apk update && apk upgrade
   ```
3. Install required system packages:
   ```bash
   apk add python3 py3-pip nginx apache2-utils git
   ```
4. Create app directory:
   ```bash
   mkdir -p /srv/tradeviewer
   ```

#### 5b — Deploy application code
1. Clone the repository (or `scp` the project folder) into `/srv/tradeviewer/`
2. Create and activate virtual environment:
   ```bash
   python3 -m venv /srv/tradeviewer/venv
   source /srv/tradeviewer/venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create `/srv/tradeviewer/.env` with production values:
   ```
   DJANGO_SETTINGS_MODULE=config.settings.prod
   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(50))">
   ```
4. Create `data/` directory and copy initial JSON files
5. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

#### 5c — Gunicorn service (OpenRC)
1. Create `/etc/init.d/tradeviewer` OpenRC service script that runs:
   ```bash
   /srv/tradeviewer/venv/bin/gunicorn \
     --workers 2 \
     --bind 127.0.0.1:8000 \
     config.wsgi:application
   ```
2. Enable and start the service:
   ```bash
   rc-update add tradeviewer default
   rc-service tradeviewer start
   ```

#### 5d — Nginx configuration
1. Create `/etc/nginx/http.d/tradeviewer.conf`:
   - Listen on the allocated Mikrus TCP port (e.g. `20044`)
   - Proxy all non-static requests to `127.0.0.1:8000`
   - Serve `staticfiles/` directory directly
   - Enable HTTP Basic Auth on all locations using `.htpasswd`
2. Create `.htpasswd` file:
   ```bash
   htpasswd -c /etc/nginx/.htpasswd damian
   ```
3. Test and reload Nginx:
   ```bash
   nginx -t && rc-service nginx reload
   ```

#### 5e — Verify
1. Visit `https://frog02-PORT.wykr.es` in a browser
2. Confirm Basic Auth prompt appears
3. Confirm all three pages load with sample data
4. Confirm file upload works end-to-end

---

## Phase 6 — Post-v1 Improvements (Backlog)

These are out of scope for the initial build but documented here for future iterations:

| Item | Notes |
|------|-------|
| Mobile sidebar (hamburger menu) | Alpine.js `x-show` toggle; CSS breakpoint for `lg:` |
| Dark mode toggle | Tailwind `dark:` variant; preference stored in `localStorage` via Alpine.js |
| Collapsible pick cards | Alpine.js `x-show` on card body |
| Search / filter | Client-side filtering of tickers using Alpine.js |
| HTTPS on custom domain | Point A record to Frog IPv6; use `certbot` for Let's Encrypt |

---

## Reference

| Document | Path |
|----------|------|
| Product Requirements | `.ai/prd.md` |
| Tech Stack | `.ai/tech-stack.md` |
| Sample data | `data/` |
| VPS access | `_frog_docs/access.txt` |
| VPS constraints | `_frog_docs/docs.txt` |
