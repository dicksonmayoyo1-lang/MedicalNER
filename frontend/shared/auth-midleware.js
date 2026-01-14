// Auth Middleware for protected pages
(function () {
  "use strict";

  class AuthMiddleware {
    static checkAuth(requiredRole = null) {
      const auth = this.getCurrentAuth();

      if (!auth) {
        // Not logged in, redirect to login
        window.location.href = "/frontend/auth/login.html";
        return null;
      }

      if (requiredRole && auth.user.role !== requiredRole) {
        // Wrong role, redirect to appropriate dashboard
        this.redirectToRoleDashboard(auth.user.role);
        return null;
      }

      return auth;
    }

    static getCurrentAuth() {
      try {
        const token = localStorage.getItem("auth_token");
        const userStr = localStorage.getItem("auth_user");

        if (!token || !userStr) {
          return null;
        }

        const user = JSON.parse(userStr);

        // Check token expiration (simplified)
        const authTime = parseInt(localStorage.getItem("auth_time") || "0");
        const hoursSinceLogin = (Date.now() - authTime) / (1000 * 60 * 60);

        if (hoursSinceLogin > 24) {
          // Expired after 24 hours
          this.clearAuth();
          return null;
        }

        return { token, user };
      } catch (error) {
        console.error("Auth middleware error:", error);
        this.clearAuth();
        return null;
      }
    }

    static redirectToRoleDashboard(role) {
      switch (role) {
        case "doctor":
          window.location.href = "/frontend/modules/doctor/dashboard.html";
          break;
        case "patient":
          window.location.href = "/frontend/modules/patient/dashboard.html";
          break;
        case "admin":
          window.location.href = "/frontend/modules/admin/dashboard.html";
          break;
        default:
          window.location.href = "/frontend/index.html";
      }
    }

    static clearAuth() {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_time");

      if (window.medicalAPI) {
        window.medicalAPI.clearToken();
      }
    }

    static requireRole(role) {
      return function () {
        return AuthMiddleware.checkAuth(role);
      };
    }

    static isAuthenticated() {
      return !!this.getCurrentAuth();
    }

    static getCurrentUser() {
      const auth = this.getCurrentAuth();
      return auth ? auth.user : null;
    }

    static getToken() {
      const auth = this.getCurrentAuth();
      return auth ? auth.token : null;
    }
  }

  // Export to window
  window.AuthMiddleware = AuthMiddleware;
})();
