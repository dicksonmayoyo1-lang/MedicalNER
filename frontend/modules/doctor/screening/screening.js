// Medical Screening Module

class MedicalScreening {
  constructor() {
    this.apiBase = "http://localhost:8000";
    this.currentResults = [];
    this.screeningRules = null;
    this.riskThreshold = 60;

    this.init();
  }

  async init() {
    // Load screening rules (using your endpoint)
    await this.loadScreeningRules();

    // Load initial data
    await this.loadDashboardStats();

    // Bind events
    this.bindEvents();

    // Check if we should auto-run screening
    if (localStorage.getItem("autoScreen") === "true") {
      this.runScreening();
    }
  }

  bindEvents() {
    // Risk threshold slider
    const thresholdSlider = document.getElementById("riskThreshold");
    if (thresholdSlider) {
      thresholdSlider.addEventListener("input", (e) => {
        this.riskThreshold = e.target.value;
        document.getElementById(
          "threshold-value"
        ).textContent = `${this.riskThreshold}%`;
        localStorage.setItem("riskThreshold", this.riskThreshold);
      });

      // Load saved threshold
      const savedThreshold = localStorage.getItem("riskThreshold");
      if (savedThreshold) {
        thresholdSlider.value = savedThreshold;
        this.riskThreshold = savedThreshold;
        document.getElementById(
          "threshold-value"
        ).textContent = `${savedThreshold}%`;
      }
    }

    // Auto screening toggle
    const autoScreenToggle = document.getElementById("autoScreen");
    if (autoScreenToggle) {
      autoScreenToggle.addEventListener("change", (e) => {
        localStorage.setItem("autoScreen", e.target.checked);
      });

      // Load saved setting
      const savedAutoScreen = localStorage.getItem("autoScreen");
      if (savedAutoScreen !== null) {
        autoScreenToggle.checked = savedAutoScreen === "true";
      }
    }

    // Run batch screening
    const runBtn = document.getElementById("runBatchScreening");
    if (runBtn) {
      runBtn.addEventListener("click", () => this.runScreening());
    }

    // View rules button
    const viewRulesBtn = document.getElementById("viewScreeningRules");
    if (viewRulesBtn) {
      viewRulesBtn.addEventListener("click", () => this.showRulesModal());
    }

    // Start screening from empty state
    const startBtn = document.getElementById("startScreening");
    if (startBtn) {
      startBtn.addEventListener("click", () => this.runScreening());
    }

    // Export results
    const exportBtn = document.getElementById("exportResults");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => this.exportResults());
    }

    // Filter controls
    const riskFilter = document.getElementById("riskFilter");
    if (riskFilter) {
      riskFilter.addEventListener("change", () => this.filterResults());
    }

    const dateFilter = document.getElementById("dateFilter");
    if (dateFilter) {
      dateFilter.addEventListener("change", () => this.filterResults());
    }

    // Modal close
    const modalClose = document.querySelector(".modal-close");
    if (modalClose) {
      modalClose.addEventListener("click", () => this.hideRulesModal());
    }

    // Close modal on background click
    const modal = document.getElementById("rulesModal");
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          this.hideRulesModal();
        }
      });
    }
  }

  async loadScreeningRules() {
    try {
      // Use your actual endpoint
      const response = await fetch(`${this.apiBase}/screening/rules`);
      if (response.ok) {
        this.screeningRules = await response.json();
        console.log("Loaded screening rules:", this.screeningRules);
      } else {
        console.error("Failed to load screening rules:", response.status);
        // Create fallback rules
        this.screeningRules = {
          risk_levels: {
            HIGH: { score: 70, color: "#fd7e14", label: "High Risk" },
            MEDIUM: { score: 40, color: "#ffc107", label: "Moderate Risk" },
            LOW: { score: 0, color: "#28a745", label: "Low Risk" },
          },
        };
      }
    } catch (error) {
      console.error("Failed to load screening rules:", error);
      this.showError("Could not load screening rules");
      // Create fallback rules
      this.screeningRules = {
        risk_levels: {
          HIGH: { score: 70, color: "#fd7e14", label: "High Risk" },
          MEDIUM: { score: 40, color: "#ffc107", label: "Moderate Risk" },
          LOW: { score: 0, color: "#28a745", label: "Low Risk" },
        },
      };
    }
  }

  async loadDashboardStats() {
    try {
      // Get total records count
      const response = await fetch(`${this.apiBase}/records/stats`);
      if (response.ok) {
        const stats = await response.json();

        // Get recent records for screening stats
        const screeningResponse = await fetch(
          `${this.apiBase}/records?limit=100`
        );
        if (screeningResponse.ok) {
          const records = await screeningResponse.json();

          // Run quick screening to get risk distribution
          const riskCounts = {
            HIGH: 0,
            MEDIUM: 0,
            LOW: 0,
          };

          // Sample a few records for quick screening
          const sampleRecords = records.slice(0, 20); // Check first 20
          for (const record of sampleRecords) {
            try {
              const screeningResult = await this.screenRecord(record);
              const riskLevel = screeningResult?.risk_level || "LOW";
              riskCounts[riskLevel] = (riskCounts[riskLevel] || 0) + 1;
            } catch (e) {
              console.error("Error screening record:", e);
            }
          }

          // Update dashboard
          document.getElementById("high-risk-count").textContent =
            riskCounts.HIGH || 0;
          document.getElementById("total-screened").textContent =
            sampleRecords.length;
          document.getElementById("normal-risk-count").textContent =
            riskCounts.LOW + riskCounts.MEDIUM || 0;
        }
      }
    } catch (error) {
      console.error("Failed to load dashboard stats:", error);
    }
  }

  async runScreening() {
    const resultsContainer = document.getElementById("screeningResults");
    if (!resultsContainer) return;

    // Show loading state
    resultsContainer.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Running medical screening analysis...</p>
            </div>
        `;

    try {
      // Use your actual screening endpoint
      const response = await fetch(`${this.apiBase}/screening/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          run_all: true,
          limit: 50,
        }),
      });

      if (!response.ok) {
        throw new Error(`Screening API error: ${response.status}`);
      }

      const screeningData = await response.json();

      if (screeningData.error) {
        throw new Error(screeningData.error);
      }

      // Store results
      this.currentResults = screeningData.results || [];

      // Update dashboard
      await this.loadDashboardStats();

      // Display results
      this.displayResults();
    } catch (error) {
      console.error("Screening failed:", error);

      // Fallback to individual record screening
      await this.runFallbackScreening();
    }
  }

  async runFallbackScreening() {
    const resultsContainer = document.getElementById("screeningResults");

    try {
      // Get recent records
      const response = await fetch(`${this.apiBase}/records?limit=30`);
      if (!response.ok) {
        throw new Error("Failed to fetch records");
      }

      const records = await response.json();
      this.currentResults = [];

      // Process each record with your single record endpoint
      for (const record of records) {
        try {
          const screeningResult = await this.screenSingleRecord(record.id);
          if (screeningResult) {
            this.currentResults.push(screeningResult);
          }
        } catch (e) {
          console.error(`Failed to screen record ${record.id}:`, e);
        }
      }

      // Update dashboard
      await this.loadDashboardStats();

      // Display results
      this.displayResults();
    } catch (error) {
      console.error("Fallback screening failed:", error);
      resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i>
                    <strong>Screening Failed:</strong> ${error.message}
                </div>
            `;
    }
  }

  async screenSingleRecord(recordId) {
    try {
      // Use your single record screening endpoint
      const response = await fetch(
        `${this.apiBase}/screening/analyze_record/${recordId}`,
        {
          method: "POST",
        }
      );

      if (response.ok) {
        return await response.json();
      } else {
        // Fallback: use analyze endpoint
        const analyzeResponse = await fetch(
          `${this.apiBase}/screening/analyze`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              record_id: recordId,
            }),
          }
        );

        if (analyzeResponse.ok) {
          const data = await analyzeResponse.json();
          return data.results?.[0] || null;
        }
      }
      return null;
    } catch (error) {
      console.error(`Failed to screen record ${recordId}:`, error);
      return null;
    }
  }

  // Remove the old screenRecord and performLocalScreening methods
  // and replace with your backend-based screening

  displayResults() {
    const resultsContainer = document.getElementById("screeningResults");
    if (!resultsContainer || this.currentResults.length === 0) {
      resultsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h3>No Screening Results</h3>
                    <p>Run a screening analysis to see results here.</p>
                    <button class="btn btn-primary" id="startScreening">
                        <i class="fas fa-play"></i> Start Screening
                    </button>
                </div>
            `;

      // Rebind the button
      const startBtn = document.getElementById("startScreening");
      if (startBtn) {
        startBtn.addEventListener("click", () => this.runScreening());
      }
      return;
    }

    // Filter results
    const filteredResults = this.filterResults();

    // Generate HTML
    let html = `
            <div class="results-summary">
                <p>Showing ${filteredResults.length} of ${this.currentResults.length} screened records</p>
            </div>
        `;

    filteredResults.forEach((result) => {
      const riskLevel = result?.risk_level?.toLowerCase() || "low";

      html += `
                <div class="patient-card ${riskLevel}">
                    <div class="patient-header">
                        <div class="patient-info">
                            <h4>${
                              result.original_filename || "Patient Record"
                            }</h4>
                            <div class="patient-id">ID: ${
                              result.patient_id || result.record_id
                            }</div>
                        </div>
                        <div class="patient-meta">
                            <span><i class="far fa-calendar"></i> ${new Date(
                              result.upload_timestamp || result.screening_date
                            ).toLocaleDateString()}</span>
                            <span><i class="fas fa-file-medical"></i> ${
                              result.disease_count || 0
                            } diseases</span>
                            <span><i class="fas fa-flask"></i> ${
                              result.lab_count || 0
                            } labs</span>
                        </div>
                        <span class="risk-badge risk-${riskLevel}">${
        result.risk_level || "LOW"
      }</span>
                    </div>
                    
                    <div class="risk-summary">
                        <div class="risk-factor">
                            <i class="fas fa-heartbeat"></i>
                            <span>${
                              result.triggered_rules?.length || 0
                            } Rules Triggered</span>
                        </div>
                        
                        ${
                          result.diseases_found?.length
                            ? `
                            <div class="risk-factor">
                                <i class="fas fa-disease"></i>
                                <span>${result.diseases_found.length} Diseases</span>
                            </div>
                        `
                            : ""
                        }
                        
                        ${
                          result.labs_found?.length
                            ? `
                            <div class="risk-factor">
                                <i class="fas fa-flask"></i>
                                <span>${result.labs_found.length} Lab Tests</span>
                            </div>
                        `
                            : ""
                        }
                    </div>
                    
                    ${
                      result.recommendations?.length
                        ? `
                        <div class="alert alert-${
                          riskLevel === "high" ? "warning" : "info"
                        }">
                            <i class="fas fa-bell"></i>
                            ${
                              result.recommendations[0] ||
                              "No specific recommendations"
                            }
                        </div>
                    `
                        : ""
                    }
                    
                    ${
                      result.triggered_rules?.length
                        ? `
                        <div class="alert alert-info">
                            <i class="fas fa-exclamation-circle"></i>
                            <strong>Triggered Rules:</strong> ${result.triggered_rules
                              .map((r) => r.rule_name)
                              .join(", ")}
                        </div>
                    `
                        : ""
                    }
                    
                    <div class="patient-actions">
                        <button class="btn btn-sm btn-outline" onclick="window.location.href='/frontend/modules/doctor/patients/manage.html?patient=${
                          result.patient_id || ""
                        }'">
                            <i class="fas fa-eye"></i> View Details
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="screening.viewPatientScreening('${
                          result.record_id || result.patient_id
                        }')">
                            <i class="fas fa-chart-line"></i> Full Report
                        </button>
                    </div>
                </div>
            `;
    });

    resultsContainer.innerHTML = html;
  }

  filterResults() {
    const riskFilter = document.getElementById("riskFilter")?.value || "all";
    const dateFilter = document.getElementById("dateFilter")?.value || "all";

    return this.currentResults.filter((result) => {
      // Risk filter
      const riskLevel = result?.risk_level?.toLowerCase() || "low";
      let riskMatch = true;

      switch (riskFilter) {
        case "critical":
          riskMatch = riskLevel === "critical";
          break;
        case "high":
          riskMatch = riskLevel === "critical" || riskLevel === "high";
          break;
        case "moderate":
          riskMatch = ["critical", "high", "moderate"].includes(riskLevel);
          break;
        case "low":
          riskMatch = ["critical", "high", "moderate", "low"].includes(
            riskLevel
          );
          break;
        default:
          riskMatch = true;
      }

      if (!riskMatch) return false;

      // Date filter
      const recordDate = new Date(
        result.upload_timestamp || result.screening_date
      );
      const now = new Date();

      switch (dateFilter) {
        case "today":
          return recordDate.toDateString() === now.toDateString();
        case "week":
          const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
          return recordDate >= weekAgo;
        case "month":
          const monthAgo = new Date(now - 30 * 24 * 60 * 60 * 1000);
          return recordDate >= monthAgo;
        default:
          return true;
      }
    });
  }

  showRulesModal() {
    const modal = document.getElementById("rulesModal");
    const rulesContent = document.getElementById("rulesContent");

    if (!modal || !rulesContent) return;

    // Generate rules display
    let html = "";

    if (this.screeningRules) {
      // Risk Levels
      if (this.screeningRules.risk_levels) {
        html += `
                    <div class="rule-category">
                        <h4>Risk Level Definitions</h4>
                        ${Object.entries(this.screeningRules.risk_levels)
                          .map(
                            ([level, data]) => `
                            <div class="rule-item">
                                <div class="rule-header">
                                    <span class="rule-name">${level}</span>
                                    <span class="risk-badge risk-${level.toLowerCase()}">${level}</span>
                                </div>
                                <div class="rule-desc">
                                    Score ≥ ${
                                      data.score || 0
                                    }, Color: <span style="color: ${
                              data.color || "#000"
                            }">${data.color || "#000"}</span>
                                </div>
                            </div>
                        `
                          )
                          .join("")}
                    </div>
                `;
      }

      // If we have screening rules array
      if (Array.isArray(this.screeningRules)) {
        html += `
                    <div class="rule-category">
                        <h4>Screening Rules</h4>
                        ${this.screeningRules
                          .map(
                            (rule) => `
                            <div class="rule-item ${rule.risk_level.toLowerCase()}">
                                <div class="rule-header">
                                    <span class="rule-name">${rule.name}</span>
                                    <span class="risk-badge risk-${rule.risk_level.toLowerCase()}">${
                              rule.risk_level
                            }</span>
                                </div>
                                <div class="rule-desc">
                                    ${rule.description}
                                </div>
                                <div class="rule-thresholds">
                                    <div><strong>Conditions:</strong></div>
                                    ${
                                      rule.conditions
                                        ?.map(
                                          (cond) => `
                                        <div class="threshold-item">
                                            <span class="threshold-label">${
                                              cond.type
                                            }:</span>
                                            <span class="threshold-value">${
                                              cond.value
                                            } ${cond.operator || ""}</span>
                                        </div>
                                    `
                                        )
                                        .join("") || ""
                                    }
                                </div>
                                <div class="rule-recommendation">
                                    <strong>Recommendation:</strong> ${
                                      rule.recommendation
                                    }
                                </div>
                            </div>
                        `
                          )
                          .join("")}
                    </div>
                `;
      }
    } else {
      html = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    Could not load screening rules. Please check your backend connection.
                </div>
            `;
    }

    rulesContent.innerHTML = html;
    modal.classList.add("active");
  }

  hideRulesModal() {
    const modal = document.getElementById("rulesModal");
    if (modal) {
      modal.classList.remove("active");
    }
  }

  async viewPatientScreening(patientId) {
    // Redirect to stats page with patient focus
    window.location.href = `/frontend/modules/doctor/patients/manage.html?patient=${patientId}&tab=screening`;
  }

  async exportResults() {
    if (this.currentResults.length === 0) {
      this.showError("No results to export");
      return;
    }

    try {
      // Create CSV content
      let csv =
        "Patient ID,Risk Level,File Name,Screening Date,Diseases Found,Lab Tests,Recommendations\n";

      this.currentResults.forEach((result) => {
        csv += `"${result.patient_id || result.record_id}",`;
        csv += `"${result.risk_level || "LOW"}",`;
        csv += `"${result.original_filename || "Unknown"}",`;
        csv += `"${new Date(
          result.screening_date || result.upload_timestamp
        ).toISOString()}",`;
        csv += `"${(result.diseases_found || []).join("; ")}",`;
        csv += `"${(result.labs_found || []).join("; ")}",`;
        csv += `"${(result.recommendations || []).join("; ")}"\n`;
      });

      // Create download link
      const blob = new Blob([csv], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medical_screening_${
        new Date().toISOString().split("T")[0]
      }.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
      this.showError("Failed to export results");
    }
  }

  showError(message) {
    // Create temporary error message
    const errorDiv = document.createElement("div");
    errorDiv.className = "alert alert-danger";
    errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            ${message}
        `;
    errorDiv.style.position = "fixed";
    errorDiv.style.top = "20px";
    errorDiv.style.right = "20px";
    errorDiv.style.zIndex = "1000";

    document.body.appendChild(errorDiv);

    setTimeout(() => {
      document.body.removeChild(errorDiv);
    }, 5000);
  }
}

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
  window.screening = new MedicalScreening();
});
