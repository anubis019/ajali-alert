/* === MOCK DATA (Kenya-focused) === */
const AlertData = {
  alerts: [],
  _idCounter: 1,

  init() {
    this.alerts = this.generateInitial();
  },

  generateInitial() {
    const types = ['Multi-vehicle Collision','Building Collapse','Industrial Fire','Flood Emergency','Road Accident','Power Outage','Landslide Warning','Market Fire','Gas Explosion','Bridge Failure','Matatu Rollover','Stadium Stampede'];
    const counties = CONFIG.COUNTIES;
    const locations = {
      Nairobi: ['Thika Superhighway','Uhuru Highway','Kenyatta Ave','Moi Ave','Industrial Area','Westlands','Eastleigh','Kibera'],
      Mombasa: ['Digo Road','Makadara Rd','Nyali Bridge','Likoni Ferry','Old Town','Port Area','Bamburi'],
      Kisumu: ['Jomo Kenyatta Hwy','Oginga Odinga St','Kisumu Pier','Mamboleo','Railways'],
      Nakuru: ['Eldoret-Nakuru Hwy','Kenol/Nakuru Rd','Bahati','Lanet','Industrial Area'],
      Kiambu: ['Kiambu Rd','Ruiru Bypass','Thika Rd Exit 14','Juja','Limuru Rd'],
      Eldoret: ['Eldoret-Nakuru Hwy','Uasin Gishu Rd','Kapsabet Rd','Town Center'],
    };
    const descs = {
      'Multi-vehicle Collision': 'Multiple vehicles involved in collision. Casualties reported. Emergency extrication may be required.',
      'Building Collapse': 'Structural failure reported. Potential trapped occupants. Search and rescue needed.',
      'Industrial Fire': 'Fire reported at industrial facility. Possible hazardous materials. Evacuation in progress.',
      'Flood Emergency': 'Rising water levels in low-lying areas. Residents being urged to move to higher ground.',
      'Road Accident': 'Single or multi-vehicle accident reported. Injuries confirmed. Ambulance dispatched.',
      'Power Outage': 'Major power outage affecting the area. Monitoring for secondary emergencies.',
      'Landslide Warning': 'Heavy rainfall increasing landslide risk in hilly terrain. Evacuation advisory issued.',
      'Market Fire': 'Fire reported at market area. Crowd management and fire suppression underway.',
      'Gas Explosion': 'Explosion reported at commercial premises. Multiple injuries. Gas supply shut off.',
      'Bridge Failure': 'Structural concern on bridge. Traffic being diverted. Engineering assessment en route.',
      'Matatu Rollover': 'Public service vehicle rollover. Multiple casualties. Ambulances requested.',
      'Stadium Stampede': 'Crowd crush reported at stadium event. Medical teams on standby.',
    };
    const severities = ['critical','high','medium','low'];
    const sevWeights = [0.12, 0.25, 0.38, 0.25];

    const result = [];
    for (let i = 0; i < 24; i++) {
      const county = counties[Math.floor(Math.random() * counties.length)];
      const locs = locations[county] || ['Town Center'];
      const type = types[Math.floor(Math.random() * types.length)];
      const r = Math.random();
      let sevIdx = 0;
      let cum = 0;
      for (let j = 0; j < sevWeights.length; j++) { cum += sevWeights[j]; if (r < cum) { sevIdx = j; break; } }
      const severity = severities[sevIdx];
      const minutesAgo = Math.floor(Math.random() * 120);
      const time = new Date(Date.now() - minutesAgo * 60000);
      result.push({
        id: `ALT-${String(this._idCounter++).padStart(3,'0')}`,
        type,
        county,
        location: locs[Math.floor(Math.random() * locs.length)],
        severity,
        time: time.toISOString(),
        casualties: severity === 'critical' ? Math.floor(Math.random()*20+3) : severity === 'high' ? Math.floor(Math.random()*8+1) : Math.floor(Math.random()*3),
        description: descs[type] || 'Emergency incident reported. Details being verified.',
        status: minutesAgo < 10 ? 'Active' : minutesAgo < 30 ? 'Responding' : 'Contained',
      });
    }
    return result.sort((a,b) => new Date(b.time) - new Date(a.time));
  },

  addAlert(alert) {
    alert.id = `ALT-${String(this._idCounter++).padStart(3,'0')}`;
    alert.time = new Date().toISOString();
    this.alerts.unshift(alert);
    return alert;
  },

  getFiltered(county = 'all', severity = 'all') {
    return this.alerts.filter(a => {
      if (county !== 'all' && a.county !== county) return false;
      if (severity !== 'all' && a.severity !== severity) return false;
      return true;
    });
  },

  getLatest() {
    return this.alerts.length > 0 ? this.alerts[0] : null;
  },

  getById(id) {
    return this.alerts.find(a => a.id === id) || null;
  },

  getStats() {
    const alerts = this.alerts;
    return {
      total: alerts.length,
      active: alerts.filter(a => a.status === 'Active').length,
      critical: alerts.filter(a => a.severity === 'critical').length,
      goldenHour: alerts.filter(a => {
        const mins = (Date.now() - new Date(a.time).getTime()) / 60000;
        return mins <= CONFIG.GOLDEN_HOUR_MINUTES && (a.severity === 'critical' || a.severity === 'high');
      }).length,
      byCounty: CONFIG.COUNTIES.map(c => ({ name: c, count: alerts.filter(a => a.county === c).length })),
      bySeverity: ['critical','high','medium','low'].map(s => ({ name: s, count: alerts.filter(a => a.severity === s).length })),
      byType: [...new Set(alerts.map(a => a.type))].map(t => ({ name: t, count: alerts.filter(a => a.type === t).length })),
    };
  },

  getTeams() {
    return [
      { name: 'Nairobi Fire & Rescue', county: 'Nairobi', status: 'available', capacity: 82, type: 'Fire / Extrication', phone: '+254-20-222181', members: 28 },
      { name: 'St John Ambulance', county: 'Nairobi', status: 'busy', capacity: 65, type: 'Medical / Trauma', phone: '+254-20-221100', members: 42 },
      { name: 'Kenya Red Cross', county: 'Nairobi', status: 'available', capacity: 90, type: 'Disaster Relief', phone: '+254-20-2719000', members: 60 },
      { name: 'Mombasa Coast Guard', county: 'Mombasa', status: 'available', capacity: 75, type: 'Marine / Coastal', phone: '+254-41-312000', members: 35 },
      { name: 'Nakuru County EMS', county: 'Nakuru', status: 'busy', capacity: 55, type: 'Medical / Rescue', phone: '+254-51-213000', members: 20 },
      { name: 'Kisumu Rescue Squad', county: 'Kisumu', status: 'available', capacity: 88, type: 'Water / General', phone: '+254-57-202000', members: 18 },
      { name: 'Kiambu Fire Service', county: 'Kiambu', status: 'available', capacity: 70, type: 'Fire / Rescue', phone: '+254-20-821000', members: 15 },
      { name: 'Eldoret Emergency Unit', county: 'Eldoret', status: 'offline', capacity: 30, type: 'Medical / Evac', phone: '+254-53-203000', members: 12 },
    ];
  }
};