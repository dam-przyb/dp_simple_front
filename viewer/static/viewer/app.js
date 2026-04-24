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
