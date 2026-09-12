/* === ALERT FEED RENDERER === */
const Feed = {
  container: null,
  countBadge: null,

  init() {
    this.container = document.querySelector('.feed-list');
    this.countBadge = document.querySelector('.feed-count');
    this.render();

    Filters.onChange(() => this.render());
  },

  render() {
    if (!this.container) return;
    const county = Filters.getCounty();
    const severity = Filters.getSeverity();
    const alerts = AlertData.getFiltered(county, severity);
    
    if (this.countBadge) this.countBadge.textContent = alerts.length;
    
    if (alerts.length === 0) {
      this.container.innerHTML = '<div class="feed-empty">No alerts match current filters</div>';
      return;
    }

    this.container.innerHTML = alerts.map(a => {
      const timeAgo = this.timeAgo(new Date(a.time));
      return `
        <div class="alert-item" data-id="${a.id}" onclick="Feed.openAlert('${a.id}')">
          <div class="alert-severity-bar ${a.severity}"></div>
          <div class="alert-body">
            <div class="alert-type">
              ${a.type}
              <span class="alert-sev-tag ${a.severity}">${a.severity}</span>
            </div>
            <div class="alert-location">${a.location}, ${a.county}</div>
            <div class="alert-time">${timeAgo} · ${a.status}</div>
          </div>
        </div>
      `;
    }).join('');
  },

  openAlert(id) {
    const alert = AlertData.getById(id);
    if (!alert) return;
    const overlay = document.getElementById('alert-modal-overlay');
    if (!overlay) return;
    this._populateModal(alert);
    Modal.open('alert-modal-overlay');
  },

  _populateModal(a) {
    const overlay = document.getElementById('alert-modal-overlay');
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
          <div class="modal-meta-value">${this.timeAgo(new Date(a.time))} ago</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Casualties</div>
          <div class="modal-meta-value">${a.casualties || 'Unconfirmed'}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-label">Status</div>
          <div class="modal-meta-value">${a.status}</div>
        </div>
      </div>
      <div class="modal-description">${a.description}</div>
      <div class="modal-section-title">JARVIS Intelligence Brief</div>
      <div id="modal-brief-area">
        ${Auth.isLoggedIn() ? '<button class="modal-action-btn primary" onclick="JarvisTabs.loadBriefForAlert(\''+a.id+'\')">Generate Brief</button>' : '<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-dim);">Admin login required for JARVIS brief</span>'}
      </div>
    `;
  },

  flashNew(alertId) {
    const item = this.container.querySelector(`[data-id="${alertId}"]`);
    if (item) item.classList.add('flash');
  },

  timeAgo(date) {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return 'Just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours/24)}d ago`;
  }
};