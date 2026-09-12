/* === AUTH === */
const Auth = {
  _listeners: [],

  isLoggedIn() {
    return !!localStorage.getItem(CONFIG.TOKEN_KEY);
  },

  getUser() {
    try { return JSON.parse(localStorage.getItem(CONFIG.USER_KEY)); }
    catch { return null; }
  },

  getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
  },

  async login(username, password) {
    try {
      const res = await API.postForm(CONFIG.AUTH_ENDPOINT, {
        username, password
      });
      localStorage.setItem(CONFIG.TOKEN_KEY, res.access_token);
      localStorage.setItem(CONFIG.USER_KEY, JSON.stringify({
        username: res.username || username,
        role: res.role || 'admin'
      }));
      this._notify(true);
      return res;
    } catch (e) {
      throw e;
    }
  },

  logout() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
    this._notify(false);
  },

  onChange(fn) {
    this._listeners.push(fn);
  },

  _notify(loggedIn) {
    this._listeners.forEach(fn => fn(loggedIn, this.getUser()));
  }
};