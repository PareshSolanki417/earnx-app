// ==========================================================================
// EarnX Admin API Client
// ==========================================================================

const AdminAPI = {
  baseUrl: '/api',

  getToken() {
    return localStorage.getItem('earnx_admin_token');
  },

  setToken(token) {
    localStorage.setItem('earnx_admin_token', token);
  },

  clearToken() {
    localStorage.removeItem('earnx_admin_token');
  },

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };

    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        // Unauthorized admin: clear token and display login screen
        AdminAPI.clearToken();
        AdminApp.showLogin();
      }
      throw new Error(data.detail || 'API request failed');
    }

    return data;
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }
};
