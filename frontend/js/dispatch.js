/* === DISPATCH MODULE === */
const DispatchModule = {
  paneId: 'jarvis-dispatch',

  async run() {
    const pane = document.getElementById(this.paneId);
    const container = pane.querySelector('.dispatch-results');
    if (!container) return;
    container.innerHTML = '<div class="jarvis-loading">Computing dispatch</div>';

    try {
      const res = await API.post(CONFIG.JARVIS.DISPATCH, {
        county: Filters.getCounty(),
        severity: Filters.getSeverity()
      });
      this.render(container, res.suggestions || res);
    } catch (e) {
      this.renderMock(container);
    }
  },

  render(container, items) {
    if (!Array.isArray(items) || items.length === 0) {
      container.innerHTML = '<div class="jarvis-loading">No dispatch suggestions</div>';
      return;
    }
    container.innerHTML = items.map(d => {
      const etaClass = (d.eta_minutes || d.eta || 99) <= 8 ? 'fast' : ((d.eta_minutes || d.eta || 99) <= 15 ? 'moderate' : 'slow');
      return `
        <div class="dispatch-card">
          <div class="team-name">${d.team_name || d.team || 'Response Team'}</div>
          <div class="team-meta">${d.specialization || d.type || 'General Response'} · ${d.distance_km || d.distance || '?'} km away</div>
          <span class="team-eta ${etaClass}">ETA ${d.eta_minutes || d.eta || '—'} min</span>
        </div>
      `;
    }).join('');
  },

  renderMock(container) {
    const mock = [
      { team_name: 'Nairobi Fire & Rescue', specialization: 'Fire / Extrication', distance_km: 3, eta_minutes: 6 },
      { team_name: 'St John Ambulance', specialization: 'Medical / Trauma', distance_km: 5, eta_minutes: 9 },
      { team_name: 'Kenya Red Cross — Nairobi', specialization: 'Disaster Relief', distance_km: 7, eta_minutes: 14 },
      { team_name: 'Kenya Police Air Wing', specialization: 'Air Medevac', distance_km: 12, eta_minutes: 22 },
    ];
    this.render(container, mock);
  }
};