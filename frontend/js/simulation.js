/* === LIVE SIMULATION === */
const Simulation = {
  interval: null,
  alertTypes: ['Road Accident','Matatu Rollover','Building Fire','Flood Warning','Gas Leak','Traffic Pile-up','Power Line Down','Market Stampede'],
  counties: CONFIG.COUNTIES,
  locations: {
    Nairobi: ['CBD','Thika Rd','Mombasa Rd','Westlands','Eastleigh','Kasarani'],
    Mombasa: ['Digo Rd','Nyali','Likoni','Old Town','Port'],
    Kisumu: ['CBD','Pier','Mamboleo','Oginga Odinga'],
    Nakuru: ['Town','Lanet','Eldoret Hwy','Bahati'],
    Kiambu: ['Ruiru','Thika','Juja','Limuru'],
    Eldoret: ['Town','Kapsabet Rd','Uasin Gishu'],
  },

  start() {
    this.interval = setInterval(() => this.tick(), CONFIG.REFRESH_INTERVAL);
  },

  stop() {
    if (this.interval) clearInterval(this.interval);
  },

  tick() {
    // Random chance to generate new alert
    if (Math.random() < 0.35) {
      const county = this.counties[Math.floor(Math.random() * this.counties.length)];
      const locs = this.locations[county] || ['Town Center'];
      const type = this.alertTypes[Math.floor(Math.random() * this.alertTypes.length)];
      const severity = CONFIG.SEVERITY_LEVELS[Math.floor(Math.random() * CONFIG.SEVERITY_LEVELS.length)];
      const alert = AlertData.addAlert({
        type,
        county,
        location: locs[Math.floor(Math.random() * locs.length)],
        severity,
        casualties: severity === 'critical' ? Math.floor(Math.random()*10+2) : Math.floor(Math.random()*3),
        description: `${type} reported in ${county}. Emergency services alerted.`,
        status: 'Active',
      });
      Feed.render();
      Feed.flashNew(alert.id);
      Metrics.update();
      Charts.update();
      Toast.show(`New ${severity} alert: ${type} in ${county}`, severity === 'critical' ? 'error' : 'warning', 'AJALI');
    }
  }
};