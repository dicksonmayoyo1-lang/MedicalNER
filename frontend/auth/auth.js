// Authentication Module
(function () {
  "use strict";

  class AuthApp {
    constructor(pageType) {
      this.api = window.medicalAPI;
      this.utils = window.Utils;
      this.pageType = pageType; // 'login' or 'register'
      this.init();
    }

    init() {
      console.log(`Auth module initializing for ${this.pageType} page`);

      if (this.pageType === "login") {
        this.initLoginPage();
      } else if (this.pageType === "register") {
        this.initRegisterPage();
      }

      // Check if already logged in
      this.checkExistingSession();
    }

    initLoginPage() {
      const form = document.getElementById("login-form");
      if (!form) return;

      form.addEventListener("submit", (e) => this.handleLogin(e));

      // Forgot password
      document
        .getElementById("forgot-password")
        ?.addEventListener("click", (e) => {
          e.preventDefault();
          this.showMessage("success", "Password reset feature coming soon!");
        });
    }

    initRegisterPage() {
      const form = document.getElementById("register-form");
      if (!form) return;

      form.addEventListener("submit", (e) => this.handleRegister(e));

      // Role selector
      const roleOptions = document.querySelectorAll(".role-option");
      roleOptions.forEach((option) => {
        option.addEventListener("click", () => {
          roleOptions.forEach((opt) => opt.classList.remove("selected"));
          option.classList.add("selected");
          document.getElementById("role").value = option.dataset.role;
        });
      });

      // Set default role
      document
        .querySelector('.role-option[data-role="patient"]')
        ?.classList.add("selected");
    }

    async handleLogin(e) {
      e.preventDefault();
      this.clearErrors();

      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;

      // Validation
      let valid = true;
      if (!username) {
        this.showError("username-error", "Username is required");
        valid = false;
      }
      if (!password) {
        this.showError("password-error", "Password is required");
        valid = false;
      }
      if (!valid) return;

      // Disable button
      const btn = document.getElementById("login-btn");
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';

      try {
        const response = await this.api.post("/auth/login", {
          username,
          password,
        });

        // Store token and user info
        this.storeAuthData(response);

        this.showMessage("success", "Login successful! Redirecting...");

        // Redirect based on role
        setTimeout(() => {
          this.redirectToDashboard(response.user.role);
        }, 1500);
      } catch (error) {
        console.error("Login error:", error);
        this.showMessage("error", error.message || "Login failed");
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
      }
    }

    async handleRegister(e) {
      e.preventDefault();
      this.clearErrors();

      const formData = {
        full_name: document.getElementById("full_name").value.trim(),
        email: document.getElementById("email").value.trim(),
        username: document.getElementById("username").value.trim(),
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirm_password").value,
        role: document.getElementById("role").value,
      };

      // Validation
      let valid = this.validateRegistration(formData);
      if (!valid) return;

      // Disable button
      const btn = document.getElementById("register-btn");
      btn.disabled = true;
      btn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Creating account...';

      try {
        const response = await this.api.post("/auth/register", {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          role: formData.role,
          full_name: formData.full_name,
        });

        this.showMessage(
          "success",
          "Account created successfully! Logging in..."
        );

        // Auto login after registration
        setTimeout(async () => {
          try {
            const loginResponse = await this.api.post("/auth/login", {
              username: formData.username,
              password: formData.password,
            });

            this.storeAuthData(loginResponse);
            this.redirectToDashboard(loginResponse.user.role);
          } catch (loginError) {
            this.showMessage(
              "error",
              "Account created but auto-login failed. Please login manually."
            );
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-user-plus"></i> Create Account';
            // Redirect to login
            setTimeout(() => {
              window.location.href = "/frontend/auth/login.html";
            }, 2000);
          }
        }, 2000);
      } catch (error) {
        console.error("Registration error:", error);
        this.showMessage("error", error.message || "Registration failed");
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-user-plus"></i> Create Account';
      }
    }

    validateRegistration(formData) {
      let valid = true;

      // Email validation
      if (!formData.email) {
        this.showError("email-error", "Email is required");
        valid = false;
      } else if (!this.isValidEmail(formData.email)) {
        this.showError("email-error", "Invalid email format");
        valid = false;
      }

      // Username validation
      if (!formData.username) {
        this.showError("username-error", "Username is required");
        valid = false;
      } else if (formData.username.length < 3) {
        this.showError(
          "username-error",
          "Username must be at least 3 characters"
        );
        valid = false;
      }

      // Password validation
      if (!formData.password) {
        this.showError("password-error", "Password is required");
        valid = false;
      } else if (formData.password.length < 6) {
        this.showError(
          "password-error",
          "Password must be at least 6 characters"
        );
        valid = false;
      }

      // Confirm password
      if (formData.password !== formData.confirm_password) {
        this.showError("confirm-password-error", "Passwords do not match");
        valid = false;
      }

      return valid;
    }

    isValidEmail(email) {
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return re.test(email);
    }

    storeAuthData(authResponse) {
      localStorage.setItem("auth_token", authResponse.access_token);
      localStorage.setItem("auth_user", JSON.stringify(authResponse.user));
      localStorage.setItem("auth_time", Date.now().toString());

      // Update API client with token
      if (window.medicalAPI) {
        window.medicalAPI.setToken(authResponse.access_token);
      }
    }

    checkExistingSession() {
      const token = localStorage.getItem("auth_token");
      const userStr = localStorage.getItem("auth_user");

      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          // Check if token is expired (simplified check)
          const authTime = parseInt(localStorage.getItem("auth_time") || "0");
          const hoursSinceLogin = (Date.now() - authTime) / (1000 * 60 * 60);

          if (hoursSinceLogin < 24) {
            // Token valid for 24 hours
            // Update API client
            if (window.medicalAPI) {
              window.medicalAPI.setToken(token);
            }

            // If on auth page, redirect to dashboard<script src="/frontend/auth/auth.js"></script>
            if (this.pageType && window.location.pathname.includes("auth/")) {
              this.redirectToDashboard(user.role);
            }
          } else {
            // Token expired, clear storage
            this.clearAuthData();
          }
        } catch (e) {
          console.error("Error parsing stored user:", e);
          this.clearAuthData();
        }
      }
    }

    clearAuthData() {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_time");

      if (window.medicalAPI) {
        window.medicalAPI.clearToken();
      }
    }

    redirectToDashboard(role) {
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

    showError(elementId, message) {
      const element = document.getElementById(elementId);
      if (element) {
        element.textContent = message;
        element.classList.add("show");

        // Highlight input
        const inputId = elementId.replace("-error", "");
        const input = document.getElementById(inputId);
        if (input) {
          input.classList.add("error");
        }
      }
    }

    clearErrors() {
      // Clear all error messages
      document.querySelectorAll(".error-message").forEach((el) => {
        el.classList.remove("show");
        el.textContent = "";
      });

      // Remove error class from inputs
      document.querySelectorAll(".form-control.error").forEach((el) => {
        el.classList.remove("error");
      });

      // Clear messages
      this.hideMessage("error");
      this.hideMessage("success");
    }

    showMessage(type, message) {
      const element = document.getElementById(`${type}-message`);
      if (element) {
        element.textContent = message;
        element.classList.add("show");

        // Auto-hide after 5 seconds
        setTimeout(() => {
          this.hideMessage(type);
        }, 5000);
      }
    }

    hideMessage(type) {
      const element = document.getElementById(`${type}-message`);
      if (element) {
        element.classList.remove("show");
      }
    }

    // Static method for other modules to use
    static checkAuth() {
      const token = localStorage.getItem("auth_token");
      const userStr = localStorage.getItem("auth_user");

      if (!token || !userStr) {
        return null;
      }

      try {
        const user = JSON.parse(userStr);
        return { token, user };
      } catch (e) {
        return null;
      }
    }

    static logout() {
      // Clear local storage
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_time");

      // Clear API token
      if (window.medicalAPI) {
        window.medicalAPI.clearToken();
      }

      // Redirect to login
      window.location.href = "/frontend/auth/login.html";
    }
  }

  // Export to window
  window.AuthApp = AuthApp;
})();
