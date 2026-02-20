// Updated API client with auth support
class MedicalAPI {
  constructor(baseURL = "http://localhost:8000") {
    this.baseURL = baseURL;
    this.token = localStorage.getItem("auth_token") || null;
  }

  setToken(token) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`);
    Object.keys(params).forEach((key) =>
      url.searchParams.append(key, params[key])
    );

    const headers = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      // Handle auth errors
      if (response.status === 401) {
        this.handleAuthError();
      }
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    return response.json();
  }

  async post(endpoint, data = {}) {
    const headers = {
      "Content-Type": "application/json",
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      // Handle auth errors
      if (response.status === 401) {
        this.handleAuthError();
      }
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    return response.json();
  }

  async put(endpoint, data = {}) {
    const headers = {
      "Content-Type": "application/json",
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.handleAuthError();
      }
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    return response.json();
  }

  async delete(endpoint) {
    const headers = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.handleAuthError();
      }
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    // 204 No Content is common for deletes
    if (response.status === 204) return null;
    return response.json();
  }

  handleAuthError() {
    // Clear invalid token
    this.clearToken();
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");

    // Redirect to login if not already there
    if (!window.location.pathname.includes("auth/")) {
      window.location.href = "/frontend/auth/login.html";
    }
  }

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.token;
  }

  // Get current user from localStorage
  getCurrentUser() {
    try {
      const userStr = localStorage.getItem("auth_user");
      return userStr ? JSON.parse(userStr) : null;
    } catch (e) {
      return null;
    }
  }
}

// Export singleton instance
window.medicalAPI = new MedicalAPI();
