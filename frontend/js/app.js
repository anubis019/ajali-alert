/* === APP INIT === */
const Metrics = {
  update() {
    const stats = AlertData.getStats();
    const cards = document.querySelectorAll('.metric-card');
    if (cards[0]) cards[0].querySelector('.metric-value').textContent = stats.total;
    if (cards[1]) cards[1].querySelector('.metric-value').textContent = stats.critical;
    if (cards[2]) cards[2].querySelector('.metric-value').textContent = stats.active;
    if (cards[3]) cards[3].querySelector('.metric-value').textContent = stats.goldenHour;
  }
};

const App = {
  init() {
    Toast.init();
    AlertData.init();
    Filters.init();
    Feed.init();
    Teams.init();
    Metrics.update();
    Charts.init();
    JarvisPanel.init();
    JarvisTabs.init();
    ChatModule.init();
    this.bindAuth();
    this.bindJARVISButtons();
    Simulation.start();
    this.checkApiHealth();
    console.log('%c AJALI ALERT SYSTEM', 'background:#0a0b0d;color:#d64a4a;font-size:18px;font-family:monospace;padding:8px 16px;');
    console.log('%c Emergency Command Center — Kenya', 'color:#5a5d65;font-family:monospace;');
  },

  bindAuth() {
    // Admin button in header
    const adminBtn = document.getElementById('admin-btn');
    if (adminBtn) adminBtn.addEventListener('click', () => {
      if (Auth.isLoggedIn()) {
        Auth.logout();
        Toast.show('Logged out', 'info');
      } else {
        Modal.open('login-overlay');
      }
    });

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => {
      Auth.logout();
      Toast.show('Logged out', 'info');
    });

    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('login-username').value;
      const password = document.getElementById('login-password').value;
      const apiBase = document.getElementById('login-api-base').value;
      const errorEl = document.querySelector('.login-error');
      const btn = loginForm.querySelector('.login-btn');

      if (apiBase) {
        localStorage.setItem('ajali_api_base', apiBase);
        API.baseUrl = apiBase;
      }

      btn.disabled = true;
      btn.textContent = 'AUTHENTICATING...';
      try {
        await Auth.login(username, password);
        Modal.close();
        Toast.show(`Welcome, ${Auth.getUser()?.username || 'admin'}`, 'success');
      } catch (e) {
        if (errorEl) {
          errorEl.style.display = 'block';
          errorEl.textContent = e.message || 'Authentication failed';
        }
      } finally {
        btn.disabled = false;
        btn.textContent = 'AUTHENTICATE';
      }
    });

    // Login modal close
    const loginClose = document.querySelector('.login-close');
    if (loginClose) loginClose.addEventListener('click', () => Modal.close());

    // JARVIS locked login button
    const lockLoginBtn = document.querySelector('.lock-login-btn');
    if (lockLoginBtn) lockLoginBtn.addEventListener('click', () => Modal.open('login-overlay'));

    // Update header on auth change
    Auth.onChange((loggedIn, user) => {
      const adminBtn = document.getElementById('admin-btn');
      const logoutBtn = document.getElementById('logout-btn');
      if (adminBtn) {
        if (loggedIn) {
          adminBtn.classList.add('authenticated');
          adminBtn.innerHTML = `Admin <span class="auth-check">✓</span>`;
        } else {
          adminBtn.classList.remove('authenticated');
          adminBtn.innerHTML = 'Admin';
        }
      }
      if (logoutBtn) logoutBtn.style.display = loggedIn ? 'inline-block' : 'none';
    });

    // Set initial state
    if (Auth.isLoggedIn()) {
      Auth._notify(true);
    }
  },

  bindJARVISButtons() {
    const triageBtn = document.getElementById('jarvis-triage-btn');
    if (triageBtn) triageBtn.addEventListener('click', () => {
      if (!Auth.isLoggedIn()) { Modal.open('login-overlay'); return; }
      TriageModule.run();
    });

    const dispatchBtn = document.getElementById('jarvis-dispatch-btn');
    if (dispatchBtn) dispatchBtn.addEventListener('click', () => {
      if (!Auth.isLoggedIn()) { Modal.open('login-overlay'); return; }
      DispatchModule.run();
    });

    const briefBtn = document.getElementById('jarvis-brief-btn');
    if (briefBtn) briefBtn.addEventListener('click', () => {
      if (!Auth.isLoggedIn()) { Modal.open('login-overlay'); return; }
      BriefModule.runForPane();
    });

    const predictBtn = document.getElementById('jarvis-predict-btn');
    if (predictBtn) predictBtn.addEventListener('click', () => {
      if (!Auth.isLoggedIn()) { Modal.open('login-overlay'); return; }
      PredictModule.run();
    });
  },

  async checkApiHealth() {
    const dot = document.querySelector('.footer-api-dot');
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
      if (dot) dot.className = 'footer-api-dot';
    } catch {
      if (dot) dot.className = 'footer-api-dot offline';
    }
  }
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());