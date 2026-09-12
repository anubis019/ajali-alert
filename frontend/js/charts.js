/* === CHART RENDERER === */
const Charts = {
  instances: {},

  init() {
    this.renderAll();
  },

  renderAll() {
    this.renderSeverityDonut();
    this.renderCountyBar();
    this.renderTimeline();
    this.renderCategoryBar();
  },

  renderSeverityDonut() {
    const canvas = document.getElementById('chart-severity');
    if (!canvas || typeof Chart === 'undefined') return;
    if (this.instances.severity) this.instances.severity.destroy();
    const stats = AlertData.getStats().bySeverity;
    this.instances.severity = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: stats.map(s => s.name.charAt(0).toUpperCase() + s.name.slice(1)),
        datasets: [{
          data: stats.map(s => s.count),
          backgroundColor: ['rgba(214,74,74,0.8)','rgba(224,159,62,0.8)','rgba(74,143,214,0.8)','rgba(61,184,160,0.8)'],
          borderColor: ['rgba(214,74,74,1)','rgba(224,159,62,1)','rgba(74,143,214,1)','rgba(61,184,160,1)'],
          borderWidth: 1,
          hoverOffset: 6,
        }]
      },
      options: {
        cutout: '68%',
        responsive: true,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#a0a3ab', font: { family: 'DM Mono', size: 10 }, padding: 12, usePointStyle: true, pointStyleWidth: 8 } }
        }
      }
    });
  },

  renderCountyBar() {
    const canvas = document.getElementById('chart-county');
    if (!canvas || typeof Chart === 'undefined') return;
    if (this.instances.county) this.instances.county.destroy();
    const stats = AlertData.getStats().byCounty;
    this.instances.county = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: stats.map(c => c.name),
        datasets: [{
          data: stats.map(c => c.count),
          backgroundColor: stats.map(c => c.name === 'Nairobi' ? 'rgba(214,74,74,0.7)' : c.name === 'Mombasa' ? 'rgba(224,159,62,0.7)' : 'rgba(74,143,214,0.5)'),
          borderColor: stats.map(c => c.name === 'Nairobi' ? 'rgba(214,74,74,1)' : c.name === 'Mombasa' ? 'rgba(224,159,62,1)' : 'rgba(74,143,214,0.8)'),
          borderWidth: 1,
          borderRadius: 3,
          maxBarThickness: 28,
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } },
          y: { ticks: { color: '#a0a3ab', font: { family: 'DM Mono', size: 10 } }, grid: { display: false } }
        }
      }
    });
  },

  renderTimeline() {
    const canvas = document.getElementById('chart-timeline');
    if (!canvas || typeof Chart === 'undefined') return;
    if (this.instances.timeline) this.instances.timeline.destroy();
    const hours = ['6am','8am','10am','12pm','2pm','4pm','6pm','8pm','10pm','12am'];
    const data = [1,2,3,5,8,12,9,6,3,1];
    this.instances.timeline = new Chart(canvas, {
      type: 'line',
      data: {
        labels: hours,
        datasets: [{
          label: 'Alerts',
          data: data,
          borderColor: '#e09f3e',
          backgroundColor: 'rgba(224,159,62,0.08)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#e09f3e',
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } },
          y: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } }
        }
      }
    });
  },

  renderCategoryBar() {
    const canvas = document.getElementById('chart-category');
    if (!canvas || typeof Chart === 'undefined') return;
    if (this.instances.category) this.instances.category.destroy();
    const stats = AlertData.getStats().byType;
    const colors = ['rgba(214,74,74,0.7)','rgba(224,159,62,0.7)','rgba(74,143,214,0.7)','rgba(61,184,160,0.7)','rgba(139,108,193,0.7)','rgba(201,168,76,0.7)','rgba(214,74,74,0.5)','rgba(224,159,62,0.5)','rgba(74,143,214,0.5)','rgba(61,184,160,0.5)','rgba(139,108,193,0.5)','rgba(201,168,76,0.5)'];
    this.instances.category = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: stats.map(t => t.name.length > 14 ? t.name.slice(0,12) + '…' : t.name),
        datasets: [{
          data: stats.map(t => t.count),
          backgroundColor: stats.map((_, i) => colors[i % colors.length]),
          borderWidth: 0,
          borderRadius: 3,
          maxBarThickness: 24,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 8 }, maxRotation: 45 }, grid: { display: false } },
          y: { ticks: { color: '#5a5d65', font: { family: 'DM Mono', size: 9 } }, grid: { color: '#1e2028' } }
        }
      }
    });
  },

  update() {
    this.renderAll();
  }
};