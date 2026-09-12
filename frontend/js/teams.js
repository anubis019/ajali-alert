/* === RESPONSE TEAMS RENDERER === */
const Teams = {
  init() {
    this.render();
  },

  render() {
    const grid = document.querySelector('.teams-grid');
    if (!grid) return;
    const teams = AlertData.getTeams();
    grid.innerHTML = teams.map(t => {
      const statusClass = t.status === 'available' ? 'available' : t.status === 'busy' ? 'busy' : 'offline';
      return `
        <div class="response-card team-${statusClass}">
          <div class="team-name">${t.name}</div>
          <div class="team-location">📍 ${t.county}</div>
          <div class="team-status-badge ${statusClass}">
            <span class="team-status-dot ${statusClass}"></span>
            ${t.status}
          </div>
          <div class="team-meta">
            ${t.type} · ${t.members} members<br>
            ${t.phone}
          </div>
          <div class="team-capacity-bar">
            <div class="team-capacity-fill ${statusClass}" style="width:${t.capacity}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }
};