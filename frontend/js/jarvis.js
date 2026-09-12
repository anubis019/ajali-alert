/* === JARVIS PANEL CONTROLLER === */
const JarvisPanel = {
  lockedOverlay: null,

  init() {
    this.lockedOverlay = document.getElementById('jarvis-locked');
    Auth.onChange((loggedIn) => {
      this.updateLock(loggedIn);
    });
    this.updateLock(Auth.isLoggedIn());
  },

  updateLock(loggedIn) {
    if (!this.lockedOverlay) return;
    this.lockedOverlay.style.display = loggedIn ? 'none' : 'flex';
    const statusEl = document.querySelector('.jarvis-status');
    if (statusEl) {
      statusEl.className = loggedIn ? 'jarvis-status online' : 'jarvis-status';
      statusEl.innerHTML = loggedIn
        ? '<span class="status-dot"></span> ONLINE'
        : '<span class="status-dot"></span> LOCKED';
    }
  },

  openLogin() {
    Modal.open('login-overlay');
  }
};

/* === JARVIS TABS === */
const JarvisTabs = {
  activeTab: 'triage',

  init() {
    document.querySelectorAll('.jarvis-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTo(tab.dataset.tab));
    });
    this.switchTo('triage');
  },

  switchTo(tabId) {
    this.activeTab = tabId;
    document.querySelectorAll('.jarvis-tab').forEach(t =>
      t.classList.toggle('active', t.dataset.tab === tabId)
    );
    document.querySelectorAll('.jarvis-tab-pane').forEach(p =>
      p.classList.toggle('active', p.id === `jarvis-${tabId}`)
    );
  },

  async loadBriefForAlert(alertId) {
    const area = document.getElementById('modal-brief-area');
    if (!area) return;
    area.className = 'modal-brief-loading';
    area.textContent = 'Generating brief';
    try {
      const result = await BriefModule.run(alertId);
      area.className = 'modal-brief-result';
      area.textContent = result;
    } catch (e) {
      area.className = 'modal-brief-result';
      area.textContent = 'Brief unavailable — ' + e.message;
    }
  }
};