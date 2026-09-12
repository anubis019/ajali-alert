/* === API LAYER === */

class ApiClient {
  constructor() {
    this.baseUrl = CONFIG.API_BASE;
  }

  get headers() {
    const h = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem(CONFIG.TOKEN_KEY);
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  }

  async request(method, path, body = null, isForm = false) {
    const url = `${this.baseUrl}${path}`;
    const opts = {
      method,
      headers: { ...this.headers },
    };
    if (body && isForm) {
      delete opts.headers['Content-Type'];
      opts.body = new URLSearchParams(body);
    } else if (body) {
      opts.body = JSON.stringify(body);
    }
    try {
      const res = await fetch(url, opts);
      if (res.status === 401) {
        Auth.logout();
        Toast.show('Session expired — please log in again', 'warning');
        throw new Error('Unauthorized');
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }
      return res.json();
    } catch (e) {
      if (e.name === 'TypeError' && e.message.includes('fetch')) {
        throw new Error('Network error — API unreachable');
      }
      throw e;
    }
  }

  post(path, body) { return this.request('POST', path, body); }
  get(path) { return this.request('GET', path); }
  postForm(path, body) { return this.request('POST', path, body, true); }
}

const API = new ApiClient();