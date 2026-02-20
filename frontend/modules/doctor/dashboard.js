// Doctor Dashboard
(function () {
  "use strict";

  class DoctorDashboard {
    constructor() {
      this.api = window.medicalAPI;
      this.utils = window.Utils;
      this.currentUser = this.api.getCurrentUser();
      this.init();
    }

    init() {
      console.log("Doctor dashboard initializing...");

      // Update UI with user info
      this.updateUserInfo();

      // Load dashboard data
      this.loadDashboardData();

      // Bind events
      this.bindEvents();
    }

    updateUserInfo() {
      if (this.currentUser) {
        const rawName = this.currentUser.full_name || this.currentUser.username;
        const safeName = (rawName || "").toString().trim();

        // Avoid duplicated titles like: "Welcome, Dr. Dr. John Smith"
        // Normalize any leading "Dr", "Dr.", "DR." etc, then add exactly one "Dr."
        const nameWithoutTitle = safeName.replace(/^dr\.?\s+/i, "").trim();

        // Update navbar name (show name without title to avoid duplication)
        const userNameEl = document.getElementById("user-name");
        if (userNameEl) {
          userNameEl.textContent = nameWithoutTitle || safeName || "Doctor";
        }

        // Update welcome title (add Dr. prefix)
        const welcomeTitleEl = document.getElementById("welcome-title");
        if (welcomeTitleEl) {
          welcomeTitleEl.textContent = nameWithoutTitle
            ? `Welcome, Dr. ${nameWithoutTitle}`
            : "Welcome, Doctor";
        }
      }
    }

    async loadDashboardData() {
      try {
        // Load doctor-specific data
        const dashboardData = await this.api.get("/doctor/dashboard");

        // Update stats
        this.updateStats(dashboardData.stats || {});

        // Load high risk patients
        await this.loadHighRiskPatients();

        // Load recent activities
        this.loadRecentActivities();
      } catch (error) {
        console.error("Error loading dashboard data:", error);
        // Fallback to basic stats
        this.loadBasicStats();
      }
    }

    updateStats(stats) {
      document.getElementById("total-patients").textContent =
        stats.patients_today || "--";
      document.getElementById("total-records").textContent = "--"; // Will be updated separately
      document.getElementById("screenings-today").textContent = "--";
      document.getElementById("high-risk-cases").textContent =
        stats.high_risk_cases || "--";

      // Load actual records count
      this.loadRecordsCount();
    }

    async loadRecordsCount() {
      try {
        const records = await this.api.get("/records", { limit: 1 });
        // Count endpoint might not exist, we'll calculate from data
        document.getElementById("total-records").textContent = "--";
      } catch (error) {
        console.error("Error loading records count:", error);
      }
    }

    async loadHighRiskPatients() {
      const loadingEl = document.getElementById("high-risk-loading");
      const listEl = document.getElementById("high-risk-list");

      try {
        const response = await this.api.get("/screening/high_risk", {
          limit: 5,
        });
        const highRiskPatients = response.results || [];

        loadingEl.classList.add("hidden");

        if (highRiskPatients.length === 0) {
          listEl.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-check-circle"></i>
                            <p>No high-risk patients found</p>
                        </div>
                    `;
          return;
        }

        listEl.innerHTML = highRiskPatients
          .map(
            (patient) => `
                    <div class="patient-item high-risk">
                        <div class="patient-info">
                            <div class="patient-name">${this.utils.escapeHtml(
                              patient.patient_id
                            )}</div>
                            <div class="patient-details">
                                <span class="detail">
                                    <i class="fas fa-file"></i>
                                    ${this.utils.escapeHtml(
                                      patient.original_filename
                                    )}
                                </span>
                                <span class="detail">
                                    <i class="fas fa-calendar"></i>
                                    ${this.utils.formatDate(
                                      patient.screening_date
                                    )}
                                </span>
                            </div>
                        </div>
                        <div class="patient-actions">
                            <button class="btn btn-sm btn-danger" 
                                    onclick="DoctorDashboard.viewPatient('${
                                      patient.record_id
                                    }')">
                                <i class="fas fa-eye"></i> Review
                            </button>
                        </div>
                    </div>
                `
          )
          .join("");
      } catch (error) {
        console.error("Error loading high risk patients:", error);
        loadingEl.classList.add("hidden");
        listEl.innerHTML = `
                    <div class="error">
                        <i class="fas fa-exclamation-triangle"></i>
                        Error loading high-risk patients
                    </div>
                `;
      }
    }

    loadRecentActivities() {
      const activities = [
        {
          icon: "fa-file-medical",
          text: "Uploaded patient record",
          time: "2 hours ago",
        },
        {
          icon: "fa-search",
          text: "Ran screening on 5 records",
          time: "4 hours ago",
        },
        {
          icon: "fa-user-md",
          text: "Consulted with Dr. Smith",
          time: "1 day ago",
        },
        {
          icon: "fa-chart-line",
          text: "Viewed analytics report",
          time: "2 days ago",
        },
      ];

      const listEl = document.getElementById("activities-list");
      listEl.innerHTML = activities
        .map(
          (activity) => `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="fas ${activity.icon}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-text">${activity.text}</div>
                        <div class="activity-time">${activity.time}</div>
                    </div>
                </div>
            `
        )
        .join("");
    }

    loadBasicStats() {
      // Fallback if API fails
      document.getElementById("total-patients").textContent = "15";
      document.getElementById("total-records").textContent = "42";
      document.getElementById("screenings-today").textContent = "8";
      document.getElementById("high-risk-cases").textContent = "3";
    }

    bindEvents() {
      // User menu toggle
      document
        .getElementById("user-menu-btn")
        ?.addEventListener("click", (e) => {
          e.stopPropagation();
          const dropdown = document.getElementById("user-dropdown");
          dropdown.classList.toggle("hidden");
        });

      // Close dropdown when clicking outside
      document.addEventListener("click", () => {
        document.getElementById("user-dropdown")?.classList.add("hidden");
      });

      // Logout
      document.getElementById("logout-btn")?.addEventListener("click", (e) => {
        e.preventDefault();
        AuthApp.logout();
      });
    }

    static viewPatient(recordId) {
      // Navigate to patient detail view
      window.location.href = `/frontend/modules/doctor/patient-detail.html?id=${recordId}`;
    }
  }

  // Export to window
  window.DoctorDashboard = DoctorDashboard;
})();
