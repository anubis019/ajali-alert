/* === BRIEF MODULE === */
const BriefModule = {
  paneId: 'jarvis-brief',

  async runForPane() {
    const pane = document.getElementById(this.paneId);
    const container = pane.querySelector('.brief-results');
    if (!container) return;
    container.innerHTML = '<div class="jarvis-loading">Generating brief</div>';

    const latestAlert = AlertData.getLatest();
    if (latestAlert) {
      try {
        const brief = await this.run(latestAlert.id);
        this.render(container, brief, latestAlert);
      } catch (e) {
        this.renderMock(container, latestAlert);
      }
    } else {
      this.renderMock(container, null);
    }
  },

  async run(alertId) {
    const res = await API.get(CONFIG.JARVIS.BRIEF + alertId);
    return res.brief || res.summary || res;
  },

  render(container, briefText, alert) {
    const a = alert || {};
    container.innerHTML = `
      <div class="brief-summary">${typeof briefText === 'string' ? briefText : JSON.stringify(briefText)}</div>
      <div class="brief-facts">
        <div class="brief-fact">
          <div class="brief-fact-label">Alert</div>
          <div class="brief-fact-value">${a.type || '—'}</div>
        </div>
        <div class="brief-fact">
          <div class="brief-fact-label">County</div>
          <div class="brief-fact-value">${a.county || '—'}</div>
        </div>
        <div class="brief-fact">
          <div class="brief-fact-label">Severity</div>
          <div class="brief-fact-value" style="color:var(--severity-${a.severity || 'medium'})">${(a.severity || 'medium').toUpperCase()}</div>
        </div>
        <div class="brief-fact">
          <div class="brief-fact-label">Golden Hour</div>
          <div class="brief-fact-value">${a.golden_hour_status || 'Active'}</div>
        </div>
      </div>
    `;
  },

  renderMock(container, alert) {
    const a = alert || { id: 'ALT-001', type: 'Multi-vehicle Collision', county: 'Nairobi', severity: 'critical' };
    const briefText = `CRITICAL ALERT: ${a.type} reported in ${a.county} County at ${new Date().toLocaleTimeString('en-KE')}. Initial reports indicate multiple casualties requiring immediate medical evacuation. Golden Hour protocol activated — trauma teams have a ${CONFIG.GOLDEN_HOUR_MINUTES}-minute window for optimal intervention. Recommended response: immediate dispatch of Nairobi Fire & Rescue for extrication, St John Ambulance for on-site triage, and Kenya Police Air Wing for medevac if casualty count exceeds 8. Road conditions on Thika Superhighway may delay ground units by 4–6 minutes. Staging area: Moi International Sports Centre parking.`;
    this.render(container, briefText, a);
  }
};