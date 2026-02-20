// Patient Dashboard
(function () {
  "use strict";

  class PatientDashboard {
    constructor() {
      this.api = window.medicalAPI;
      this.utils = window.Utils;
      this.currentUser = this.api.getCurrentUser();
      this.init();
    }

    init() {
      console.log("Patient dashboard initializing...");

      // Update UI with user info
      this.updateUserInfo();

      // Load patient data
      this.loadPatientData();

      // Bind events
      this.bindEvents();
    }

    updateUserInfo() {
      if (this.currentUser) {
        document.getElementById("user-name").textContent =
          this.currentUser.full_name || this.currentUser.username;
        document.getElementById("welcome-title").textContent = `Welcome, ${
          this.currentUser.full_name || this.currentUser.username
        }`;
      }
    }

    async loadPatientData() {
      try {
        // Load patient-specific data
        const dashboardData = await this.api.get("/patient/dashboard");

        // Update health summary
        this.updateHealthSummary(dashboardData);

        // Load recent records
        await this.loadRecentRecords();
      } catch (error) {
        console.error("Error loading patient data:", error);
        // Fallback
        this.loadBasicInfo();
      }
    }

    updateHealthSummary(data) {
      // These would come from backend in real implementation
      document.getElementById("total-my-records").textContent =
        data.recent_records || "0";
      document.getElementById("last-upload").textContent = "Today";
      document.getElementById("next-appointment").textContent =
        data.upcoming_appointments?.[0]?.date || "None";
    }

    async loadRecentRecords() {
      const loadingEl = document.getElementById("records-loading");
      const listEl = document.getElementById("recent-records");

      try {
        // Get records for this patient
        const records = await this.api.get("/records", { limit: 5 });

        loadingEl.classList.add("hidden");

        if (!records || records.length === 0) {
          listEl.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-file-medical"></i>
                            <p>No medical records yet</p>
                            <button class="btn btn-primary" onclick="window.location.href='/frontend/modules/patient/upload-record.html'">
                                Upload Your First Record
                            </button>
                        </div>
                    `;
          return;
        }

        listEl.innerHTML = records
          .map(
            (record) => `
                    <div class="record-item">
                        <div class="record-icon">
                            <i class="fas fa-file-pdf"></i>
                        </div>
                        <div class="record-info">
                            <div class="record-name">${this.utils.escapeHtml(
                              record.original_filename
                            )}</div>
                            <div class="record-meta">
                                <span class="meta-item">
                                    <i class="fas fa-calendar"></i>
                                    ${this.utils.formatDate(
                                      record.upload_timestamp
                                    )}
                                </span>
                                <span class="meta-item">
                                    <i class="fas fa-disease"></i>
                                    ${record.diseases_count || 0} conditions
                                </span>
                            </div>
                        </div>
                        <div class="record-actions">
                            <button class="btn btn-sm btn-primary" 
                                    onclick="PatientDashboard.viewRecord('${
                                      record.id
                                    }')">
                                <i class="fas fa-eye"></i> View
                            </button>
                        </div>
                    </div>
                `
          )
          .join("");

        // Update counts
        document.getElementById("total-my-records").textContent =
          records.length;
        if (records.length > 0) {
          const latest = records[0];
          document.getElementById("last-upload").textContent =
            this.utils.formatDate(latest.upload_timestamp);
        }
      } catch (error) {
        console.error("Error loading records:", error);
        loadingEl.classList.add("hidden");
        listEl.innerHTML = `
                    <div class="error">
                        <i class="fas fa-exclamation-triangle"></i>
                        Error loading your records
                    </div>
                `;
      }
    }

    loadBasicInfo() {
      // Fallback information
      document.getElementById("total-my-records").textContent = "0";
      document.getElementById("last-upload").textContent = "Never";
      document.getElementById("next-appointment").textContent = "None";
      document.getElementById("last-screening").textContent = "Never";
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

    static viewRecord(recordId) {
      // Navigate to records page and auto-open the modal for that record
      window.location.href = `/frontend/modules/patient/records/view.html?record_id=${encodeURIComponent(
        recordId
      )}`;
    }
  }

  // Export to window
  window.PatientDashboard = PatientDashboard;
})();
