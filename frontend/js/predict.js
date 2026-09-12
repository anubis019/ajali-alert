/* === PREDICT MODULE === */
const PredictModule = {
  paneId: 'jarvis-predict',

  async run() {
    const pane = document.getElementById(this.paneId);
    const chartContainer = pane.querySelector('.predict-chart');
    const riskContainer = pane.querySelector('.predict-risk');
    if (!chartContainer && !riskContainer) return;

    try {
      const res = await API.get(CONFIG.JARVIS.PREDICT);
      this.renderRisk(riskContainer, res.risks || res);
      this.renderChart(chartContainer, res.timeline || res);
    } catch (e) {
      this.renderMockRisk(riskContainer);
      this.renderMockChart(chartContainer);
    }
  },

  renderRisk(container, risks) {
    if (!container || !Array.isArray(risks)) return;
    container.innerHTML = risks.map(r => {
      const level = r.level || r.risk || 'moderate';
      return `
        <div class="predict-risk-item">
          <div class="risk-county">${r.county || r.name || '—'}</div>
          <div class="risk-level ${level}">${level.toUpperCase()}</div>
        </div>
      `;
    }).join('');
  },

  renderChart(container, timeline) {
    if (!container) return;
    const canvas = container.querySelector('canvas') || document.getElementById('predict-canvas');
    if (canvas && typeof Chart !== 'undefined' && timeline) {
      new Chart(canvas, {
        type: 'line',
        data: timeline.data || timeline,
        options: { responsive: true, plugins: { legend: { labels: { color: '#a0a3ab', font: { family: 'DM Mono', size: 10 } } } }, scales: { x: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#2a2d35' } }, y: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#2a2d35' } } } }
      });
    }
  },

  renderMockRisk(container) {
    const risks = [
      { county: 'Nairobi', level: 'high' },
      { county: 'Mombasa', level: 'elevated' },
      { county: 'Kisumu', level: 'moderate' },
      { county: 'Nakuru', level: 'elevated' },
      { county: 'Kiambu', level: 'moderate' },
      { county: 'Eldoret', level: 'moderate' },
    ];
    this.renderRisk(container, risks);
  },

  renderMockChart(container) {
    if (!container) return;
    const canvas = container.querySelector('canvas') || document.getElementById('predict-canvas');
    if (!canvas || typeof Chart === 'undefined') return;
    const labels = ['6am','8am','10am','12pm','2pm','4pm','6pm','8pm','10pm'];
    const nairobi = [2,3,5,8,12,15,11,7,4];
    const mombasa = [1,2,3,4,5,6,5,3,2];
    const kisumu = [0,1,2,2,3,3,2,1,1];
    new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Nairobi', data: nairobi, borderColor: '#d64a4a', backgroundColor: 'rgba(214,74,74,0.1)', tension: 0.4, fill: true },
          { label: 'Mombasa', data: mombasa, borderColor: '#e09f3e', backgroundColor: 'rgba(224,159,62,0.05)', tension: 0.4, fill: true },
          { label: 'Kisumu', data: kisumu, borderColor: '#4a8fd6', backgroundColor: 'rgba(74,143,214,0.05)', tension: 0.4, fill: true },
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#a0a3ab', font: { family: 'DM Mono', size: 10 } } } },
        scales: {
          x: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } },
          y: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } }
        }
      }
    });
  }
};