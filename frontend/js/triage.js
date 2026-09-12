/* === TRIAGE MODULE === */
const TriageModule = {
  paneId: 'jarvis-triage',

  async run() {
    const pane = document.getElementById(this.paneId);
    const container = pane.querySelector('.triage-results');
    if (!container) return;
    container.innerHTML = '<div class="jarvis-loading">Analyzing alerts</div>';

    try {
      const res = await API.post(CONFIG.JARVIS.TRIAGE, {
        county: Filters.getCounty(),
        severity: Filters.getSeverity()
      });
      this.render(container, res.triage || res);
    } catch (e) {
      this.renderMock(container);
    }
  },

  render(container, items) {
    if (!Array.isArray(items) || items.length === 0) {
      container.innerHTML = '<div class="jarvis-loading">No alerts to triage</div>';
      return;
    }
    container.innerHTML = items.map(t => `
      <div class="triage-card">
        <div class="triage-severity ${t.severity || 'medium'}"></div>
        <div class="triage-info">
          <div class="triage-type">${t.type || t.alert_type || 'Unknown'}</div>
          <div class="triage-location">${t.county || t.location || 'Kenya'}</div>
          <div class="triage-reason">${t.reason || t.triage_note || ''}</div>
        </div>
      </div>
    `).join('');
  },

  renderMock(container) {
    const mock = [
      { severity: 'critical', type: 'Multi-vehicle Collision', county: 'Nairobi', reason: 'Peak-hour highway incident with estimated 12+ casualties. Golden Hour critical — immediate trauma team dispatch recommended.' },
      { severity: 'critical', type: 'Building Collapse', county: 'Mombasa', reason: 'Reported structural failure in densely populated area. Search & rescue priority — potential trapped victims.' },
      { severity: 'high', type: 'Industrial Fire', county: 'Nakuru', reason: 'Chemical plant fire with toxic fume risk. Evacuation zone 500m recommended. HazMat team required.' },
      { severity: 'high', type: 'Flood Emergency', county: 'Kisumu', reason: 'Rising water levels threatening low-lying settlements. Pre-position rescue boats and emergency shelter.' },
      { severity: 'medium', type: 'Road Accident', county: 'Kiambu', reason: 'Single-vehicle rollover, minor injuries reported. Standard ambulance dispatch sufficient.' },
      { severity: 'low', type: 'Power Outage', county: 'Eldoret', reason: 'Localized grid failure. Monitor for secondary incidents (traffic signals, medical equipment). No immediate response needed.' },
    ];
    this.render(container, mock);
  }
};