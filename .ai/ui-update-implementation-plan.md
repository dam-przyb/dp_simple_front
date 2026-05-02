# UI Update Implementation Plan

This is the corrected plan, incorporating lessons learned from the failed first attempt (see `ui-fail.md`). Follow these instructions precisely — deviations were the cause of all previous failures.

---

## Scope decisions (already agreed with developer)

| Question | Decision |
|----------|----------|
| Multi-team filter logic | OR — show picks from any ticked team |
| Report default state | Teams collapsed, click to expand |
| Judgement → Review link | Navigate to Review page, scroll + highlight matching ticker |
| Filter persistence | Reset on navigation (no localStorage) |
| Ticker text filter | Matches ticker symbol AND company name |
| Filter apply mode | "Apply filters" button — not live on every checkbox change |

---

## Critical constraints — read before writing any code

### 1. Alpine 3 does not track `Set` mutations
Never use `new Set()` for filter state. Use plain arrays:
- `.includes()` instead of `.has()`
- `.push()` instead of `.add()`
- `.splice(index, 1)` instead of `.delete()`

### 2. Do NOT use `json_script` + `init()` to pass data to Alpine
`init()` runs asynchronously after Alpine's first render pass. If `activeTeams = []` at creation time, every `x-show` evaluates to `false` immediately and content disappears.

**Correct pattern — pass data as a function argument:**
```html
<div x-data="myFilter({{ data|tojson }})">
```
The function receives the data synchronously, so all arrays are populated before any `x-show` evaluates.

### 3. Every template using `tojson` must `{% load viewer_extras %}` at the top
Forgetting this causes a `TemplateSyntaxError` → HTTP 500 on that page.

### 4. `tojson` filter output is safe in `x-data` attributes
Django auto-escaping converts `"` → `&quot;` inside HTML attributes. The browser decodes `&quot;` → `"` before Alpine evaluates the expression. The result is correct JSON. Do not use `|safe` — let Django escape it normally.

---

## Architecture

All filtering is **client-side Alpine.js**. Django renders the full dataset into the HTML on each page load; Alpine shows/hides elements reactively. No extra API calls.

**Pending / active state pattern** (required for Apply button):
- Filter controls (checkboxes, text input, sort buttons) update `pending*` state only
- "Apply filters" button copies `pending*` → `active*`
- All `x-show` / `x-for` expressions read `active*` state only
- This prevents partial filter states from affecting visible content while the user is still selecting

---

## Files to create / modify

### New file: `viewer/templatetags/__init__.py`
Empty file. Required to make the directory a Python package.

### New file: `viewer/templatetags/viewer_extras.py`
```python
import json
from django import template

register = template.Library()

@register.filter
def tojson(value):
    """Serialize value to JSON string for safe inline use in Alpine x-data attributes."""
    return json.dumps(value)

@register.filter
def picksmeta(picks):
    """Return [{side, ticker, name}] from a team's picks list."""
    return [{'side': p.get('side', ''), 'ticker': p.get('ticker', ''), 'name': p.get('name', '')} for p in picks]
```

---

## Phase 1 — Report page filters

### `views.py` — `report()` view
Add `teams` to context: a deduplicated list of team names in the order they appear in the data.

```python
teams = list(dict.fromkeys(r['team'] for r in reports))
context = {'reports': reports, 'teams': teams}
```

### `report.html`
1. Add `{% load viewer_extras %}` at the **very top** (after `{% extends %}`)
2. Replace the outer wrapper div with:
   ```html
   <div x-data="reportFilter({{ teams|tojson }})">
   ```
   No `x-init`. No `json_script` tag. The argument is the data.

3. **Filter bar** (checkboxes and text input bind to `pending*`):
   ```html
   <!-- Team checkbox -->
   <input type="checkbox"
          :checked="pendingTeams.includes('TeamName')"
          @change="togglePendingTeam('TeamName')">

   <!-- Side checkbox -->
   <input type="checkbox"
          :checked="pendingSides.includes('long')"
          @change="togglePendingSide('long')">

   <!-- Text search -->
   <input type="text" x-model="pendingQuery">

   <!-- Apply button -->
   <button @click="apply()">Apply filters</button>

   <!-- Reset button (visible only when filter is active) -->
   <button x-show="hasActiveFilter" @click="reset()">Reset</button>
   ```

4. **Team sections** — hide if team not in `activeTeams`:
   ```html
   <div x-show="activeTeams.includes('{{ report.team }}')">
   ```

5. **Pick cards** — use `isPickVisible()`:
   ```html
   <div x-show="isPickVisible('{{ report.team }}', '{{ pick.side }}', '{{ pick.ticker }}', {{ pick.name|tojson }})">
   ```

6. **Collapsible team sections** — use a scoped `x-data`:
   ```html
   <div x-data="{ teamOpen: false }">
     <button @click="teamOpen = !teamOpen">{{ report.team }}</button>
     <div x-show="teamOpen">...picks...</div>
   </div>
   ```

### `app.js` — `reportFilter(initialTeams)` function
```js
function reportFilter(initialTeams) {
  const teams = Array.isArray(initialTeams) ? initialTeams : [];
  return {
    allTeams: teams,
    pendingTeams: [...teams],
    pendingSides: ['long', 'short'],
    pendingQuery: '',
    activeTeams: [...teams],
    activeSides: ['long', 'short'],
    activeQuery: '',

    apply() {
      this.activeTeams = [...this.pendingTeams];
      this.activeSides = [...this.pendingSides];
      this.activeQuery = this.pendingQuery;
    },

    get hasActiveFilter() {
      return this.activeQuery.trim() !== '' ||
             this.activeSides.length < 2 ||
             this.activeTeams.length < this.allTeams.length;
    },

    togglePendingTeam(team) {
      const i = this.pendingTeams.indexOf(team);
      if (i >= 0) this.pendingTeams.splice(i, 1);
      else this.pendingTeams.push(team);
    },

    togglePendingSide(side) {
      const i = this.pendingSides.indexOf(side);
      if (i >= 0) this.pendingSides.splice(i, 1);
      else this.pendingSides.push(side);
    },

    isPickVisible(team, side, ticker, name) {
      if (!this.activeTeams.includes(team)) return false;
      if (!this.activeSides.includes(side)) return false;
      const q = this.activeQuery.trim().toLowerCase();
      if (q && !ticker.toLowerCase().includes(q) && !name.toLowerCase().includes(q)) return false;
      return true;
    },

    hasVisiblePick(team, picks) {
      if (!Array.isArray(picks)) return true;
      return picks.some(p => this.isPickVisible(team, p.side, p.ticker, p.name));
    },

    reset() {
      this.pendingTeams = [...this.allTeams];
      this.pendingSides = ['long', 'short'];
      this.pendingQuery = '';
      this.activeTeams = [...this.allTeams];
      this.activeSides = ['long', 'short'];
      this.activeQuery = '';
    },
  };
}
```

---

## Phase 2 — Review page filters

### `views.py` — `review()` view
Build `review_picks` — a flat list that Alpine can filter without understanding the nested JSON structure:

```python
review_picks = []
for team_block in review.get('teams', []):
    for pick in team_block.get('picks', []):
        review_picks.append({
            'team': team_block['team'],
            'ticker': pick['ticker'],
            'name': pick.get('name', ''),
            'side': pick.get('side', ''),
            'note': pick.get('note', 0),
            'valid': pick.get('valid', False),
            'reasoning': pick.get('reasoning', ''),
        })
context = {'review': review, 'review_picks': review_picks}
```

### `review.html`
1. Add `{% load viewer_extras %}` at the **very top** (after `{% extends %}`) — **this was missing in the failed attempt and caused the 500 error**
2. Replace outer wrapper:
   ```html
   <div x-data="reviewFilter({{ review_picks|tojson }})">
   ```
   No `x-init`. No `json_script` tag.

3. Filter bar — same pending/active pattern as Report. Extra controls:
   ```html
   <!-- Valid/Invalid toggles -->
   <input type="checkbox" x-model="pendingShowValid"> Valid
   <input type="checkbox" x-model="pendingShowInvalid"> Invalid

   <!-- Score sort buttons -->
   <button @click="setPendingSort('desc')" :class="pendingScoreSort === 'desc' ? 'active' : ''">Score ↓</button>
   <button @click="setPendingSort('asc')"  :class="pendingScoreSort === 'asc'  ? 'active' : ''">Score ↑</button>
   ```

4. **Team sections**:
   ```html
   <div x-show="activeTeams.includes('{{ team_block.team }}')">
   ```

5. **Pick cards via `x-for`** (Alpine renders from the flat `allPicks` array):
   ```html
   <template x-for="pick in filteredPicks('{{ team_block.team }}')" :key="pick.ticker">
     <div :id="'ticker-' + pick.ticker.toLowerCase()">
       <!-- bind pick.ticker, pick.name, pick.side, pick.note, pick.valid, pick.reasoning -->
     </div>
   </template>
   ```

### `app.js` — `reviewFilter(initialPicks)` function
```js
function reviewFilter(initialPicks) {
  const allPicks = Array.isArray(initialPicks) ? initialPicks : [];
  const _seen = new Set();
  const allTeams = allPicks.map(p => p.team).filter(t => _seen.has(t) ? false : _seen.add(t));
  return {
    allPicks,
    allTeams,
    pendingTeams: [...allTeams],
    pendingSides: ['long', 'short'],
    pendingShowValid: true,
    pendingShowInvalid: true,
    pendingScoreSort: null,
    pendingQuery: '',
    activeTeams: [...allTeams],
    activeSides: ['long', 'short'],
    activeShowValid: true,
    activeShowInvalid: true,
    activeScoreSort: null,
    activeQuery: '',

    init() {
      // Hash scroll for deep links from Judgement page
      this.$nextTick(() => {
        const hash = window.location.hash;
        if (!hash.startsWith('#ticker-')) return;
        const target = document.querySelector(hash);
        if (!target) return;
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.style.backgroundColor = '#451a03';
        requestAnimationFrame(() => {
          requestAnimationFrame(() => { target.style.backgroundColor = ''; });
        });
      });
    },

    apply() {
      this.activeTeams = [...this.pendingTeams];
      this.activeSides = [...this.pendingSides];
      this.activeShowValid = this.pendingShowValid;
      this.activeShowInvalid = this.pendingShowInvalid;
      this.activeScoreSort = this.pendingScoreSort;
      this.activeQuery = this.pendingQuery;
    },

    get hasActiveFilter() {
      return this.activeQuery.trim() !== '' ||
             this.activeSides.length < 2 ||
             this.activeTeams.length < this.allTeams.length ||
             !this.activeShowValid ||
             !this.activeShowInvalid ||
             this.activeScoreSort !== null;
    },

    filteredPicks(team) {
      let picks = this.allPicks.filter(p => {
        if (p.team !== team) return false;
        if (!this.activeSides.includes(p.side)) return false;
        if (p.valid && !this.activeShowValid) return false;
        if (!p.valid && !this.activeShowInvalid) return false;
        const q = this.activeQuery.trim().toLowerCase();
        if (q && !p.ticker.toLowerCase().includes(q) && !p.name.toLowerCase().includes(q)) return false;
        return true;
      });
      if (this.activeScoreSort === 'desc') picks = picks.slice().sort((a, b) => b.note - a.note);
      if (this.activeScoreSort === 'asc')  picks = picks.slice().sort((a, b) => a.note - b.note);
      return picks;
    },

    togglePendingTeam(team) {
      const i = this.pendingTeams.indexOf(team);
      if (i >= 0) this.pendingTeams.splice(i, 1);
      else this.pendingTeams.push(team);
    },

    togglePendingSide(side) {
      const i = this.pendingSides.indexOf(side);
      if (i >= 0) this.pendingSides.splice(i, 1);
      else this.pendingSides.push(side);
    },

    setPendingSort(dir) {
      this.pendingScoreSort = this.pendingScoreSort === dir ? null : dir;
    },

    reset() {
      this.pendingTeams = [...this.allTeams];
      this.pendingSides = ['long', 'short'];
      this.pendingShowValid = true;
      this.pendingShowInvalid = true;
      this.pendingScoreSort = null;
      this.pendingQuery = '';
      this.activeTeams = [...this.allTeams];
      this.activeSides = ['long', 'short'];
      this.activeShowValid = true;
      this.activeShowInvalid = true;
      this.activeScoreSort = null;
      this.activeQuery = '';
    },
  };
}
```

---

## Phase 3 — Judgement → Review deep links

### `judgement.html`
For each pick, add a link to the Review page anchored to that ticker:

```html
<a href="/review/#ticker-{{ pick.ticker|lower }}">→ See reviews for {{ pick.ticker }}</a>
```

### `review.html`
Each pick card's `id` is set via Alpine (since cards are rendered via `x-for`):
```html
:id="'ticker-' + pick.ticker.toLowerCase()"
```
Add a CSS transition class for the flash highlight:
```html
class="transition-colors duration-[2000ms]"
```
The scroll + flash logic is in `reviewFilter.init()` above (uses `$nextTick` so DOM is ready).

---

## Verification checklist

After implementing, verify each of these before deploying:

- [ ] `python manage.py check` reports no issues
- [ ] `/report/` loads without 500 — all picks visible by default
- [ ] Checking/unchecking team filter and clicking Apply hides/shows correct sections
- [ ] Side filter works; text search filters by ticker and name
- [ ] Reset button clears filters
- [ ] `/review/` loads without 500 — all picks visible by default
- [ ] Valid/Invalid toggles work
- [ ] Score sort works (asc and desc)
- [ ] `/judgement/` → clicking a review link navigates to `/review/` and scrolls to + flashes the correct card
- [ ] No flicker on page load (content does not flash-then-disappear)
