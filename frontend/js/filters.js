/* === FILTERS === */
const Filters = {
  _county: 'all',
  _severity: 'all',
  _onChange: [],

  init() {
    const countySelect = document.getElementById('county-filter');
    const pills = document.querySelectorAll('.severity-pill');
    
    if (countySelect) {
      CONFIG.COUNTIES.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c; opt.textContent = c;
        countySelect.appendChild(opt);
      });
      countySelect.addEventListener('change', (e) => {
        this._county = e.target.value;
        this._fire();
      });
    }

    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const sev = pill.dataset.severity;
        if (this._severity === sev) {
          this._severity = 'all';
          pill.className = 'severity-pill';
        } else {
          pills.forEach(p => p.className = 'severity-pill');
          this._severity = sev;
          pill.classList.add(`active-${sev}`);
        }
        this._fire();
      });
    });
  },

  getCounty() { return this._county; },
  getSeverity() { return this._severity; },

  onChange(fn) { this._onChange.push(fn); },

  _fire() {
    this._onChange.forEach(fn => fn(this._county, this._severity));
  }
};