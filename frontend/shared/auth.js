(function () {
  "use strict";

  const FRONTEND_BASE = window.FRONTEND_BASE || "/frontend";

  class Auth {
    static getToken() {
      return localStorage.getItem("auth_token");
    }

    static getUser() {
      try {
        const userStr = localStorage.getItem("auth_user");
        return userStr ? JSON.parse(userStr) : null;
      } catch {
        return null;
      }
    }

    static getAuth() {
      const token = this.getToken();
      const user = this.getUser();
      if (!token || !user) return null;

      const authTime = parseInt(localStorage.getItem("auth_time") || "0", 10);
      const hoursSinceLogin = (Date.now() - authTime) / (1000 * 60 * 60);
      if (hoursSinceLogin > 24) {
        this.clear();
        return null;
      }
      return { token, user };
    }

    static store(authResponse) {
      localStorage.setItem("auth_token", authResponse.access_token);
      localStorage.setItem("auth_user", JSON.stringify(authResponse.user));
      localStorage.setItem("auth_time", Date.now().toString());
      if (window.medicalAPI) {
        window.medicalAPI.setToken(authResponse.access_token);
      }
    }

    static clear() {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_time");
      if (window.medicalAPI) {
        window.medicalAPI.clearToken();
      }
    }

    static logout() {
      this.clear();
      window.location.href = `${FRONTEND_BASE}/index.html`;
    }

    static redirectToDashboard(role) {
      switch (role) {
        case "doctor":
          window.location.href = `${FRONTEND_BASE}/modules/doctor/dashboard.html`;
          break;
        case "patient":
          window.location.href = `${FRONTEND_BASE}/modules/patient/dashboard.html`;
          break;
        default:
          window.location.href = `${FRONTEND_BASE}/index.html`;
      }
    }

    static requireAuth(requiredRole) {
      const auth = this.getAuth();
      if (!auth) {
        window.location.href = `${FRONTEND_BASE}/index.html`;
        return null;
      }
      if (requiredRole && auth.user.role !== requiredRole) {
        this.redirectToDashboard(auth.user.role);
        return null;
      }
      return auth;
    }
  }

  window.Auth = Auth;
})();
