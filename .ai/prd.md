# Product Requirements Document — Damian's Trade Ideas Viewer

## 1. Purpose

A private, personal web application for visualising AI-generated trading reports in a clean, human-readable format. The app is accessible from any device (desktop, tablet, phone) and is deployed on a Mikrus Frog VPS.

---

## 2. Problem Statement

AI agents generate JSON reports (report, review, judgement) that are difficult to read in raw form. The owner needs a fast, visually clear interface to review these documents from any device without manual formatting.

---

## 3. Goals

- Render three distinct JSON document types in a dedicated, well-structured layout
- Allow the owner to upload a new JSON file that replaces the current one (no history kept)
- Be accessible privately from any device via browser
- Be simple to maintain — no database, no heavy dependencies

### Non-Goals (v1)
- Multi-user access or sharing
- Historical comparison of reports
- Charts or data visualisations
- Search / filtering within documents
- Dark mode (post-v1)

---

## 4. Users

| User | Description |
|------|-------------|
| Owner (Damian) | Sole user. Accesses from desktop and mobile to review daily trade reports. |

---

## 5. Features

### 5.1 Navigation
- Persistent top horizontal bar with app title: **"Damian's Trade Ideas"**
- Left vertical sidebar with three navigation links:
  - Report
  - Review
  - Judgement
- Active page highlighted in the sidebar
- Sidebar collapses to a hamburger menu on mobile (post-v1, v1 can stack vertically)

### 5.2 Report Page
Renders all `*_report_*.json` files for the current date. Multiple files exist per date — one per AI team (e.g. `anthropic`, `deepseek`, `xai`). File naming convention: `YYYYMMDDHHSS_report_TEAM.json`.

- Date displayed in page header
- Team tabs or sections — one per uploaded report file, labelled by team name extracted from filename
- General market overview section per team (collapsible)
- Per-pick card (within each team section) containing:
  - Company name + ticker (prominent heading)
  - Side badge: **LONG** (green) / **SHORT** (red)
  - Price row: Last close → Target price → implied upside %
  - Technical summary
  - Fundamental situation
  - Detailed report text
  - Sources as clickable links

### 5.3 Review Page
Renders `*_reviews.json`. Key elements:

- Date in header
- Grouped by team (one section per team)
- Per-pick card containing:
  - Ticker + stock name
  - Side badge (LONG/SHORT)
  - Score (note) displayed as a prominent number with colour coding (≥8 green, 5–7 amber, <5 red)
  - Validity badge: **VALID** (green) / **INVALID** (red)
  - Reasoning text (full, readable paragraph)

### 5.4 Judgement Page
Renders `*_judgement.json`. Key elements:

- Judgement date in header
- Selected Picks section — one card per pick:
  - Ticker + direction badge
  - Confidence score (1–5 stars or coloured number)
  - Price at report → Target price → Upside %
  - Session scope badge (e.g. "5 sessions")
  - Reasoning text
- Excluded Candidates section — compact list:
  - Ticker + reason text

### 5.5 File Upload
- A single upload area (drag-and-drop zone + fallback file picker button), accessible from all pages
- Supports uploading **multiple files at once** — e.g. 5 report files + 1 review + 1 judgement in a single drop
- Accepts only `.json` files; other file types are rejected with a clear error message
- File type is detected automatically from the filename:
  - Filename contains `_report_` → stored as a report file
  - Filename contains `_reviews` → stored as the review file
  - Filename contains `judgement` → stored as the judgement file
  - Unrecognised pattern → rejected with a descriptive error
- For reports: each file is stored individually (multiple report files coexist, one per team)
- For review and judgement: the new file replaces the existing one (no history)
- Server validates JSON structure before saving; invalid JSON is rejected
- Per-file success / error feedback shown in the UI after upload
- No database — all files stored in a dedicated `data/` directory on the server

### 5.6 Access Control
- HTTP Basic Auth via Nginx — no Django login screen needed
- Credentials stored in an `.htpasswd` file on the server
- Single set of credentials for the owner

---

## 6. UX / Design Principles

- Clean, minimal aesthetic — no clutter
- Typography-first: reports are text-heavy, readability is the priority
- Tailwind CSS for styling
- Cards with subtle shadows and clear visual hierarchy
- Colour coding used consistently:
  - Green: LONG, valid, high score, positive
  - Red: SHORT, invalid, low score, negative
  - Amber: neutral / mid score
- Responsive layout: desktop-first in v1, mobile-friendly in v2

---

## 7. Technical Constraints

| Constraint | Detail |
|------------|--------|
| Server | Mikrus Frog VPS — Alpine Linux, 256 MB RAM, 3 GB disk, unprivileged LXC |
| No Docker | LXC constraints make Docker impractical; deploy directly on Alpine |
| No database | JSON files stored and replaced on disk |
| Outbound ports | Only 80, 443, and a few others allowed |
| Public URL | Free subdomain via `frog02-PORT.wykr.es` (HTTPS handled automatically) |
| HTTP only on VPS | App serves HTTP; HTTPS termination handled by Mikrus proxy |

---

## 8. Out of Scope for v1

- User accounts / multi-user
- Persistent storage of multiple report versions
- Charts or graphs
- Dark mode toggle
- Mobile-optimised sidebar (hamburger menu)
- Notifications or alerts

---

## 9. Success Criteria

- Owner can view all three document types in a readable format from a browser
- Owner can replace any document by uploading a new JSON file
- App is accessible via the Frog subdomain URL with basic auth protection
- App runs stably on the Frog VPS within the 256 MB RAM constraint
