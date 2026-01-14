(function () {
  "use strict";

  // Chart instances
  let uploadChart = null;
  let diseasesChart = null;
  let labsChart = null;
  let diseaseTrendChart = null;

  // Initialize analytics dashboard
  async function initAnalytics() {
    try {
      // Load all analytics data
      await loadSummary();
      await loadTopEntities();
      await loadTrends();
      await loadOutbreakDetection(2.0);

      // Setup event listeners
      document
        .getElementById("analyze-outbreak")
        ?.addEventListener("click", () => {
          const threshold = parseFloat(
            document.getElementById("threshold-slider").value
          );
          loadOutbreakDetection(threshold);
        });

      document
        .getElementById("threshold-slider")
        ?.addEventListener("input", (e) => {
          document.getElementById(
            "threshold-value"
          ).textContent = `${e.target.value}x`;
        });
    } catch (error) {
      console.error("Error initializing analytics:", error);
      showError("Failed to load analytics data");
    }
  }

  // Load summary statistics
  async function loadSummary() {
    try {
      const response = await fetch("http://localhost:8000/analytics/summary");
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Update summary cards
      document.getElementById("total-records").textContent =
        data.total_records || 0;
      document.getElementById("total-diseases").textContent =
        data.total_diseases || 0;
      document.getElementById("total-labs").textContent = data.total_labs || 0;
      document.getElementById("avg-diseases").textContent =
        data.avg_diseases_per_record?.toFixed(1) || "0";
      document.getElementById("avg-labs").textContent =
        data.avg_labs_per_record?.toFixed(1) || "0";

      // Update date range
      if (data.date_range) {
        const start = data.date_range.start
          ? new Date(data.date_range.start).toLocaleDateString()
          : "N/A";
        const end = data.date_range.end
          ? new Date(data.date_range.end).toLocaleDateString()
          : "N/A";
        document.getElementById(
          "date-range-info"
        ).textContent = `Date range: ${start} to ${end}`;
      }
    } catch (error) {
      console.error("Error loading summary:", error);
      document.getElementById("date-range-info").textContent =
        "Error loading date range";
    }
  }

  // Load top diseases and labs
  async function loadTopEntities() {
    try {
      const response = await fetch(
        "http://localhost:8000/analytics/top_entities?limit=8"
      );
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Create diseases chart
      if (data.top_diseases && data.top_diseases.length > 0) {
        createDiseasesChart(data.top_diseases);
      }

      // Create labs chart
      if (data.top_labs && data.top_labs.length > 0) {
        createLabsChart(data.top_labs);
      }
    } catch (error) {
      console.error("Error loading top entities:", error);
      showError("Failed to load entity data");
    }
  }

  // Load trends data
  async function loadTrends() {
    try {
      const response = await fetch(
        "http://localhost:8000/analytics/trends?days=30"
      );
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Create upload trend chart
      if (data.upload_trend && data.upload_trend.length > 0) {
        createUploadChart(data.upload_trend);
      }

      // Create disease trend chart
      if (data.disease_trend && data.disease_trend.length > 0) {
        createDiseaseTrendChart(data.disease_trend);
      }
    } catch (error) {
      console.error("Error loading trends:", error);
      showError("Failed to load trend data");
    }
  }

  // Load outbreak detection
  async function loadOutbreakDetection(threshold) {
    const resultsDiv = document.getElementById("outbreak-results");
    resultsDiv.innerHTML =
      '<p class="loading">Analyzing disease patterns...</p>';

    try {
      const response = await fetch(
        `http://localhost:8000/analytics/outbreak_detection?threshold=${threshold}`
      );
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      if (!data.potential_outbreaks || data.potential_outbreaks.length === 0) {
        resultsDiv.innerHTML = `
                    <div class="no-data">
                        <p>✅ No significant outbreaks detected</p>
                        <p class="small">Analysis period: ${
                          data.analysis_period_days || 14
                        } days | Threshold: ${
          data.threshold || 2.0
        }x increase</p>
                    </div>
                `;
        return;
      }

      // Display outbreak alerts
      let html = `<div class="outbreak-info">
                <p class="small">Analysis period: ${data.analysis_period_days} days | Threshold: ${data.threshold}x increase</p>
            </div>`;

      data.potential_outbreaks.forEach((outbreak) => {
        const severityClass = outbreak.severity.toLowerCase();
        html += `
                    <div class="outbreak-alert ${severityClass}">
                        <h4>
                            <span class="severity">${outbreak.severity}</span>
                            ${outbreak.disease}
                        </h4>
                        <p><strong>Date:</strong> ${outbreak.date}</p>
                        <p><strong>Cases:</strong> ${outbreak.count} (Previous: ${outbreak.previous_count})</p>
                        <p><strong>Increase:</strong> ${outbreak.increase_ratio}x increase</p>
                    </div>
                `;
      });

      resultsDiv.innerHTML = html;
    } catch (error) {
      console.error("Error loading outbreak detection:", error);
      resultsDiv.innerHTML =
        '<p class="error">Error analyzing outbreak data</p>';
    }
  }

  // Chart creation functions
  function createUploadChart(trendData) {
    const ctx = document.getElementById("uploadChart").getContext("2d");

    if (uploadChart) {
      uploadChart.destroy();
    }

    const labels = trendData.map((point) => point.date);
    const data = trendData.map((point) => point.count);

    uploadChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Documents Uploaded",
            data: data,
            borderColor: "#007bff",
            backgroundColor: "rgba(0, 123, 255, 0.1)",
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Number of Documents",
            },
          },
          x: {
            title: {
              display: true,
              text: "Date",
            },
          },
        },
      },
    });
  }

  function createDiseasesChart(diseases) {
    const ctx = document.getElementById("diseasesChart").getContext("2d");

    if (diseasesChart) {
      diseasesChart.destroy();
    }

    const labels = diseases.map((d) => d.disease_name);
    const data = diseases.map((d) => d.count);
    const backgroundColors = generateColors(diseases.length);

    diseasesChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Frequency",
            data: data,
            backgroundColor: backgroundColors,
            borderColor: backgroundColors.map((c) => c.replace("0.8", "1")),
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const disease = diseases[context.dataIndex];
                return `${disease.disease_name}: ${disease.count} cases (${disease.percentage}%)`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Frequency",
            },
          },
        },
      },
    });
  }

  function createLabsChart(labs) {
    const ctx = document.getElementById("labsChart").getContext("2d");

    if (labsChart) {
      labsChart.destroy();
    }

    const labels = labs.map((l) => l.lab_name);
    const data = labs.map((l) => l.count);
    const backgroundColors = generateColors(labs.length);

    labsChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: backgroundColors,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: "right",
            labels: {
              boxWidth: 12,
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const lab = labs[context.dataIndex];
                return `${lab.lab_name}: ${lab.count} tests (${lab.percentage}%)`;
              },
            },
          },
        },
      },
    });
  }

  function createDiseaseTrendChart(trendData) {
    const ctx = document.getElementById("diseaseTrendChart").getContext("2d");

    if (diseaseTrendChart) {
      diseaseTrendChart.destroy();
    }

    const labels = trendData.map((point) => point.date);
    const data = trendData.map((point) => point.count);

    diseaseTrendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Top Disease Frequency",
            data: data,
            borderColor: "#e74c3c",
            backgroundColor: "rgba(231, 76, 60, 0.1)",
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Frequency",
            },
          },
          x: {
            title: {
              display: true,
              text: "Date",
            },
          },
        },
      },
    });
  }

  // Helper functions
  function generateColors(count) {
    const colors = [
      "rgba(52, 152, 219, 0.8)", // Blue
      "rgba(46, 204, 113, 0.8)", // Green
      "rgba(155, 89, 182, 0.8)", // Purple
      "rgba(241, 196, 15, 0.8)", // Yellow
      "rgba(230, 126, 34, 0.8)", // Orange
      "rgba(231, 76, 60, 0.8)", // Red
      "rgba(26, 188, 156, 0.8)", // Teal
      "rgba(149, 165, 166, 0.8)", // Gray
    ];

    return colors.slice(0, count);
  }

  function showError(message) {
    // Could add a global error display
    console.error("Analytics Error:", message);
  }

  // Expose public API
  window.analyticsApp = {
    init: initAnalytics,
  };

  // Initialize when DOM is ready
  document.addEventListener("DOMContentLoaded", function () {
    // Only initialize on analytics page
    if (window.location.pathname.includes("/analytics/")) {
      window.analyticsApp.init();
    }
  });
})();
