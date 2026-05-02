# UI Failure Post-Mortem

What went wrong during the first UI implementation attempt, root causes, and what to watch for in future sessions.

---

## Bug 1 — All picks invisible after filters were added

### Symptom
After implementing filters on Report and Review pages, all pick cards were hidden. The page rendered correctly (filter bar visible, team sections visible) but zero picks appeared.

### Root cause
**Alpine 3 does not track `Set` object mutations reactively.**

The original implementation used:
```js
init() {
  this.selectedTeams = new Set(allTeams);  // Alpine cannot observe Set changes
}
```

When a checkbox was toggled, `.add()` or `.delete()` mutated the `Set` in place. Alpine's reactivity system never detected the change because it tracks object identity and array length — not internal `Set` state.

The side-effect: `x-show` expressions like `selectedTeams.has(team)` always returned the initial value and never updated when the filter changed.

### Fix
Replace every `Set` with a plain array:
```js
// Set.has()    → Array.includes()
// Set.add()    → Array.push()
// Set.delete() → Array.splice(indexOf, 1)
```

---

## Bug 2 — Content flickers then disappears on page load

### Symptom
On page load, content was briefly visible (for a fraction of a second), then everything disappeared. The "Apply filters" button was present but clicking it had no effect. Refreshing reproduced the same flicker.

### Root cause
**`init()` runs asynchronously — after Alpine's first render pass.**

The implementation used Django's `json_script` filter to embed data, then read it in `init()`:

```html
{{ teams|json_script:"report-teams-data" }}
<div x-data="reportFilter()" x-init="init()">
```

```js
function reportFilter() {
  return {
    activeTeams: [],   // ← empty at creation time
    ...
    init() {
      // This runs AFTER Alpine's first render
      const el = document.getElementById('report-teams-data');
      this.activeTeams = JSON.parse(el.textContent);  // too late
    }
  };
}
```

Timeline of what happened:
1. Alpine parses `x-data` → data object created with `activeTeams = []`
2. Alpine processes all `x-show="activeTeams.includes(...)"` → all return `false` → everything hidden
3. `init()` runs, populates `activeTeams` with real data
4. Alpine re-evaluates `x-show` → content should reappear… but it didn't reliably

The flicker was the brief moment between step 1 and step 2 where the DOM was still in its server-rendered state before Alpine took control.

### Fix
Pass data directly as a function argument so the data object is fully populated at creation time, before any `x-show` is ever evaluated:

```html
<div x-data="reportFilter({{ teams|tojson }})">
```

```js
function reportFilter(initialTeams) {
  const teams = Array.isArray(initialTeams) ? initialTeams : [];
  return {
    activeTeams: [...teams],  // ← populated synchronously
    ...
  };
}
```

No `x-init`, no `json_script`, no `init()` function for data loading.

---

## Bug 3 — HTTP 500 on Review page after second fix

### Symptom
After applying the inline-argument fix, the Review page returned HTTP 500. Report page was unaffected.

### Root cause
**`review.html` was missing `{% load viewer_extras %}` at the top.**

The `tojson` filter is defined in `viewer/templatetags/viewer_extras.py`. Django template tags must be explicitly loaded in each template that uses them. `report.html` had `{% load viewer_extras %}` correctly; `review.html` did not.

When Django tried to render `{{ review_picks|tojson }}` without the tag library loaded, it threw a `TemplateSyntaxError`, which resulted in a 500 response.

### Fix
Add at the top of every template that uses `tojson` or `picksmeta`:
```django
{% extends "viewer/base.html" %}
{% load viewer_extras %}   ← must be here
```

---

## Summary table

| Bug | Root cause | Fix |
|-----|-----------|-----|
| Picks always hidden | Alpine 3 cannot track `Set` mutations | Replace `Set` with plain arrays |
| Content flickers then disappears | `init()` runs after Alpine's first render; `activeTeams = []` at creation time | Pass data as function argument; remove `init()` data loading |
| Review page 500 error | `{% load viewer_extras %}` missing from `review.html` | Add `{% load viewer_extras %}` to every template using custom filters |

---

## Lessons for future agents

1. **Never use `new Set()` for Alpine reactive state.** Use arrays with `.includes()` / `.push()` / `.splice()`.

2. **Never use `json_script` + `init()` to pass server data to Alpine filter state.** Pass it inline as a function argument in `x-data`. The data object must be fully populated synchronously before Alpine processes any `x-show`.

3. **`{% load viewer_extras %}` is required in every template that uses `tojson` or `picksmeta`.** Check all templates, not just the one you're editing.

4. **Alpine `x-data` inline argument with Django auto-escaping is safe.** `json.dumps()` output inside an HTML attribute gets `"` → `&quot;` from Django's escaping, which browsers decode back to `"` before Alpine evaluates it. Do not add `|safe` — let Django escape normally.

5. **`init()` is still valid for side effects** (e.g. hash scroll, DOM manipulation) as long as it is not responsible for populating reactive filter state.
