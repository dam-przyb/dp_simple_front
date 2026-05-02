# App & UI — How It Works

A reference document summarising the current working state of the app: architecture, data flow, Alpine.js patterns, and known quirks. Updated after the filter visibility fix (commit `8662978`).

---

## Architecture Overview

- **Django 6** renders full data server-side on every page load — no database, data comes from JSON files in `data/`
- **Alpine.js 3 (CDN)** handles all client-side filtering, show/hide, and interactivity
- **Tailwind CSS (CDN)** for styling — dark slate theme
- No AJAX or API calls: all data is embedded in the HTML at render time

---

## Data Flow: Server → Client

Django embeds data directly into the Alpine component argument using the `tojson` template filter:

```html
<!-- report.html -->
<div x-data="reportFilter({{ teams|tojson }})">

<!-- review.html -->
<div x-data="reviewFilter({{ review_picks|tojson }})">
```

The JSON is rendered inline as a JS argument. Django's auto-escaping converts `"` → `&quot;` in the HTML attribute; the browser decodes it before Alpine evaluates the expression. This means **the arrays are fully populated at the moment the Alpine data object is created**, before any `x-show` is ever evaluated.

### Why inline — not `json_script`?

The previous approach used Django's `json_script` filter to embed data in a `<script type="application/json">` tag, then read it in `init()`:

```js
// OLD — causes flicker
init() {
  const el = document.getElementById('report-teams-data');
  this.allTeams = JSON.parse(el.textContent);
  this.activeTeams = [...this.allTeams];
}
```

`init()` is async relative to Alpine's first render pass. `activeTeams` started as `[]`, so all `x-show` expressions evaluated to `false` and hid every element before `init()` could correct the state — producing the "content flashes then disappears" bug.

The fix: pass data as a constructor argument so the data object is already complete when Alpine first processes `x-show`.

---

## Alpine Components

### `reportFilter(initialTeams)`

**File:** `viewer/static/viewer/app.js`

**State:**

| Property | Purpose |
|----------|---------|
| `allTeams[]` | All team names (from server) |
| `pendingTeams[]` | Teams checked in the filter UI (not yet applied) |
| `pendingSides[]` | Sides checked (`'long'`, `'short'`) |
| `pendingQuery` | Text in the search box |
| `activeTeams[]` | Teams actually used by `x-show` |
| `activeSides[]` | Sides actually used by `x-show` |
| `activeQuery` | Query actually used by `x-show` |

**Key pattern — pending / active split:**
Filter controls update `pending*` state. "Apply filters" button copies `pending*` → `active*`. Visible cards are determined by `active*` only. This prevents partial filter states from flashing on screen while the user is still making selections.

**Methods:** `apply()`, `reset()`, `togglePendingTeam()`, `togglePendingSide()`, `isPickVisible()`, `hasVisiblePick()`

---

### `reviewFilter(initialPicks)`

**File:** `viewer/static/viewer/app.js`

Same pending/active pattern as `reportFilter`, plus:

| Extra state | Purpose |
|-------------|---------|
| `pendingShowValid` / `activeShowValid` | Toggle valid picks |
| `pendingShowInvalid` / `activeShowInvalid` | Toggle invalid picks |
| `pendingScoreSort` / `activeScoreSort` | `null` / `'asc'` / `'desc'` |

`allTeams` is derived from `initialPicks` (deduplicated, order preserved) inside the function — not passed separately.

**Methods:** `apply()`, `reset()`, `togglePendingTeam()`, `togglePendingSide()`, `setPendingSort()`, `filteredPicks(team)`

`filteredPicks(team)` is used in `x-for` loops on the Review page to render pick cards via Alpine templates.

---

## Alpine Reactivity Constraint

**Alpine 3 does not track `Set` mutations reactively.**

Using `new Set()` for filter state means Alpine never detects changes → `x-show` never updates. All filter collections must be **plain arrays** using:

- `.includes()` instead of `.has()`
- `.push()` instead of `.add()`
- `.splice(index, 1)` instead of `.delete()`

---

## Template Structure

### `report.html`

- One section per team, `x-show="activeTeams.includes('{{ report.team }}')"` — sections hidden if team deselected
- Each pick card: `x-show="isPickVisible(team, side, ticker, name)"`
- Collapsible team sections (toggled via local `teamOpen` state)
- Filter bar: checkboxes bound to `pendingTeams`/`pendingSides`, text input to `pendingQuery`
- "Apply filters" button → `apply()`; "Reset" button shown when `hasActiveFilter`

### `review.html`

- One section per team, `x-show="activeTeams.includes('{{ team_block.team }}')"` 
- Pick cards rendered via `<template x-for="pick in filteredPicks('{{ team_block.team }}')" :key="pick.ticker">`
- Each card has `:id="'ticker-' + pick.ticker.toLowerCase()"` for hash-scroll from Judgement page
- Sort buttons: `setPendingSort('asc')` / `setPendingSort('desc')`

---

## Views

| View | Key data passed to template |
|------|-----------------------------|
| `report()` | `reports` (full report data), `teams` (list of team names) |
| `review()` | `review` (raw JSON), `review_picks` (flat list: `{team, ticker, name, side, note, valid, reasoning}`) |
| `judgement()` | `judgement` (raw JSON) |

`review_picks` is built in `views.py` by flattening the nested JSON structure so Alpine can filter and sort it without needing to understand the original shape.

---

## Template Tags (`viewer/templatetags/viewer_extras.py`)

| Tag | Purpose |
|-----|---------|
| `tojson` | `json.dumps(value)` — safe inline JSON serialisation for Alpine arguments |
| `picksmeta` | Returns `[{side, ticker, name}]` list from a team's picks — used by `hasVisiblePick()` |

---

## Phase Summary

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Report page filters (team, side, text search) + collapsible sections | ✅ Done |
| 2 | Review page filters (team, side, valid/invalid, score sort, text search) | ✅ Done |
| 3 | Judgement → Review deep links (hash scroll + flash highlight) | ✅ Done |
| — | Fix: `Set` → arrays (Alpine reactivity) | ✅ Done |
| — | Fix: pass data inline (eliminate init() flicker) | ✅ Done |

---

## VPS Deployment Notes

- SSH: `ssh -t -p 11044 frog@frog02.mikr.us`
- App root: `/srv/tradeviewer`
- Service: `sudo rc-service tradeviewer restart` — always prints an error but service recovers; verify with `curl http://127.0.0.1:8000/` (expect `302`)
- Static files must be collected after any JS/CSS change: `python manage.py collectstatic --noinput --settings=config.settings.prod`
- Standard deploy sequence:
  ```bash
  cd /srv/tradeviewer
  git pull
  source venv/bin/activate
  python manage.py collectstatic --noinput --settings=config.settings.prod
  sudo rc-service tradeviewer restart
  ```
