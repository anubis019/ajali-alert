/* === MODAL MANAGER === */
const Modal = {
  currentOverlay: null,

  open(overlayId) {
    const overlay = document.getElementById(overlayId);
    if (!overlay) return;
    this.currentOverlay = overlay;
    overlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });
  },

  close() {
    if (this.currentOverlay) {
      this.currentOverlay.classList.remove('visible');
      this.currentOverlay = null;
      document.body.style.overflow = '';
    }
  },

  showAlert(alertData) {
    const overlay = document.getElementById('alert-modal-overlay');
    if (!overlay) return;
    this._populateAlert(alertData);
    this.open('alert-modal-overlay');
  },

  _populateAlert(a) {
    const modal = overlay.querySelector('.modal');
    const header = modal.querySelector('.modal-header');
    header.className = `modal-header severity-${a.severity}`;
    modal.querySelector('.modal-title').textContent = `${a.type} — ${a.county}`;
    
    const body = modal.querySelector('.modal-body');
    body.innerHTML = `
      <div class="modal-meta-grid">
        <div class="modal-meta-item">
          <div class="modal-meta-label">Alert ID</div>
          <div class="modal-meta-value">${a.id}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Severity</div>
          <div class="modal-meta-value" style="color:var(--severity-${a.severity})">${a.severity.toUpperCase()}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Location</div>
          <div class="modal-meta-value">${a.location}, ${a.county}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Reported</div>
          <div class="modal-meta-value">${a.time}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Casualties</div>
          <div class="modal-meta-value">${a.casualties || 'Unconfirmed'}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Status</div>
          <div class="modal-meta-value">${a.status || 'Active'}</div>
        </div>
      </div>
      <div class="modal-description">${a.description || 'Details being verified by responders on the ground.'}</div>
      <div class="modal-section-title">JARVIS Intelligence Brief</div>
      <div id="modal-brief-area" class="modal-brief-loading">Generating brief</div>
      <div class="modal-actions">
        <button class="modal-action-btn primary" onclick="JarvisTabs.loadBriefForAlert('${a.id}')">Get Brief</button>
        <button class="modal-action-btn secondary" onclick="Modal.close()">Close</button>
      </div>
    `;
  }
};