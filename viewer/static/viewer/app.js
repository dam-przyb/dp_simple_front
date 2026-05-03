// app.js — client-side logic for Damian's Trade Ideas viewer

/**
 * Read the CSRF token that Django sets in a cookie.
 * We need to send this header with every POST request so Django knows
 * the request came from our own page and not a third-party site.
 */
function getCsrfToken() {
  const match = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='));
  return match ? match.split('=')[1] : '';
}

/**
 * Alpine.js component for the file upload page.
 * Used via x-data="uploader()" in upload.html.
 */
function uploader() {
  return {
    dragging: false,
    uploading: false,
    files: [],      // array of { name, file, status, error, type }
    doneCount: 0,

    get allDone() {
      return this.files.length > 0 &&
             this.files.every(f => f.status === 'ok' || f.status === 'error');
    },

    onDrop(event) {
      this.dragging = false;
      const dropped = Array.from(event.dataTransfer.files)
        .filter(f => f.name.toLowerCase().endsWith('.json'));
      this.addFiles(dropped);
    },

    onFileSelect(event) {
      const selected = Array.from(event.target.files);
      this.addFiles(selected);
      // Reset the input so the same file can be re-selected if needed
      event.target.value = '';
    },

    addFiles(fileList) {
      for (const f of fileList) {
        // Skip duplicates already in the list
        if (!this.files.find(existing => existing.name === f.name)) {
          this.files.push({ name: f.name, file: f, status: 'pending', error: null, type: null });
        }
      }
    },

    reset() {
      this.files = [];
      this.doneCount = 0;
    },

    async doUpload() {
      if (this.uploading) return;
      this.uploading = true;
      this.doneCount = 0;

      // Mark all as uploading
      for (const item of this.files) {
        item.status = 'uploading';
      }

      const formData = new FormData();
      for (const item of this.files) {
        formData.append('files', item.file);
      }

      try {
        const response = await fetch('/upload/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        for (const result of data.results) {
          const item = this.files.find(f => f.name === result.filename);
          if (item) {
            item.status = result.ok ? 'ok' : 'error';
            item.error  = result.error ?? null;
            item.type   = result.type  ?? null;
            if (result.ok) this.doneCount++;
          }
        }
      } catch (err) {
        for (const item of this.files) {
          if (item.status === 'uploading') {
            item.status = 'error';
            item.error  = 'Network error — could not reach the server';
          }
        }
      }

      this.uploading = false;
    },
  };
}

function cleaner() {
  return {
    busy: false,
    result: null,   // { ok, deleted, type, error }

    async doClean(type) {
      const msg = `Delete all ${type} files? This cannot be undone.`;
      if (!window.confirm(msg)) return;

      this.busy = true;
      this.result = null;

      try {
        const body = new URLSearchParams({ type });
        const response = await fetch('/upload/clean/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body,
        });
        const data = await response.json();
        this.result = data;
      } catch (err) {
        this.result = { ok: false, type, error: 'Network error — could not reach the server' };
      }

      this.busy = false;
    },
  };
}

function reportFilter(initialTeams) {
  const teams = Array.isArray(initialTeams) ? initialTeams.filter(Boolean) : [];

  return {
    allTeams: [...teams],
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
      const idx = this.pendingTeams.indexOf(team);
      if (idx >= 0) this.pendingTeams.splice(idx, 1);
      else this.pendingTeams.push(team);
    },

    togglePendingSide(side) {
      const idx = this.pendingSides.indexOf(side);
      if (idx >= 0) this.pendingSides.splice(idx, 1);
      else this.pendingSides.push(side);
    },

    isPickVisible(team, side, ticker, name) {
      if (!this.activeTeams.includes(team)) return false;
      if (!this.activeSides.includes(side)) return false;

      const query = this.activeQuery.trim().toLowerCase();
      if (!query) return true;

      const tickerText = (ticker || '').toString().toLowerCase();
      const nameText = (name || '').toString().toLowerCase();
      return tickerText.includes(query) || nameText.includes(query);
    },

    hasVisiblePick(team, picks) {
      if (!Array.isArray(picks)) return true;
      return picks.some(pick => this.isPickVisible(team, pick.side, pick.ticker, pick.name));
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

function reviewFilter(initialPicks) {
  const allPicks = Array.isArray(initialPicks) ? initialPicks : [];
  const allTeams = [];
  const teamLabels = {};

  for (const pick of allPicks) {
    if (!pick.team) continue;
    if (!allTeams.includes(pick.team)) {
      allTeams.push(pick.team);
    }
    if (!teamLabels[pick.team]) {
      teamLabels[pick.team] = pick.team_label || pick.team;
    }
  }

  return {
    allPicks,
    allTeams,
    teamLabels,
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
      this.$nextTick(() => {
        const rawHash = window.location.hash;
        if (!rawHash) return;

        const targetId = decodeURIComponent(rawHash.slice(1));
        let target = document.getElementById(targetId);

        // Backward compatibility for older ticker-only links.
        if (!target && rawHash.startsWith('#ticker-')) {
          const tickerSuffix = `-${rawHash.slice('#ticker-'.length).toLowerCase()}`;
          target = Array.from(document.querySelectorAll('[id^="pick-"]'))
            .find(el => el.id.toLowerCase().endsWith(tickerSuffix));
        }

        if (!target) return;

        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.style.backgroundColor = '#451a03';
        target.style.boxShadow = '0 0 0 1px rgba(245, 158, 11, 0.45)';

        setTimeout(() => {
          target.style.backgroundColor = '';
          target.style.boxShadow = '';
        }, 1800);
      });
    },

    labelForTeam(team) {
      return this.teamLabels[team] || team;
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
      let picks = this.allPicks.filter(pick => {
        if (pick.team !== team) return false;
        if (!this.activeSides.includes((pick.side || '').toLowerCase())) return false;
        if (pick.valid && !this.activeShowValid) return false;
        if (!pick.valid && !this.activeShowInvalid) return false;

        const query = this.activeQuery.trim().toLowerCase();
        if (!query) return true;

        const tickerText = (pick.ticker || '').toString().toLowerCase();
        const nameText = (pick.name || '').toString().toLowerCase();
        return tickerText.includes(query) || nameText.includes(query);
      });

      if (this.activeScoreSort === 'desc') {
        picks = picks.slice().sort((a, b) => (Number(b.note) || 0) - (Number(a.note) || 0));
      }
      if (this.activeScoreSort === 'asc') {
        picks = picks.slice().sort((a, b) => (Number(a.note) || 0) - (Number(b.note) || 0));
      }
      return picks;
    },

    togglePendingTeam(team) {
      const idx = this.pendingTeams.indexOf(team);
      if (idx >= 0) this.pendingTeams.splice(idx, 1);
      else this.pendingTeams.push(team);
    },

    togglePendingSide(side) {
      const idx = this.pendingSides.indexOf(side);
      if (idx >= 0) this.pendingSides.splice(idx, 1);
      else this.pendingSides.push(side);
    },

    setPendingSort(direction) {
      this.pendingScoreSort = this.pendingScoreSort === direction ? null : direction;
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
