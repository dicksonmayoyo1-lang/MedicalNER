(function () {
  "use strict";

  // Private helper functions
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(dateString) {
    if (!dateString) return "Unknown";
    try {
      return new Date(dateString).toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  }

  // Main functions
  async function loadPatients(searchTerm = "") {
    try {
      const tbody = document.getElementById("patients-body");
      const loadingEl = document.getElementById("patients-loading");
      const contentEl = document.getElementById("patients-content");

      loadingEl.classList.remove("hidden");
      contentEl.classList.add("hidden");

      let url = "/doctor/patients";
      if (searchTerm) {
        url += `?search=${encodeURIComponent(searchTerm)}`;
      }

      const response = await window.medicalAPI.get(url);
      const patients = Array.isArray(response) ? response : [];

      // Update stats
      document.getElementById("total-patients").textContent = patients.length;
      const activeCount = patients.filter((p) => p.is_active !== false).length;
      document.getElementById("active-patients").textContent = activeCount;

      tbody.innerHTML = "";

      if (patients.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="6" class="text-center">No patients found</td></tr>';
        loadingEl.classList.add("hidden");
        contentEl.classList.remove("hidden");
        return;
      }

      patients.forEach((patient) => {
        const row = document.createElement("tr");
        const statusBadge =
          patient.is_active !== false
            ? '<span class="badge badge-success">Active</span>'
            : '<span class="badge badge-danger">Inactive</span>';

        row.innerHTML = `
          <td>${escapeHtml(patient.full_name || "Not set")}</td>
          <td>${escapeHtml(patient.username)}</td>
          <td>${escapeHtml(patient.email)}</td>
          <td>${formatDate(patient.created_at)}</td>
          <td>${statusBadge}</td>
          <td style="text-align:center">
            <button class="btn-small btn-primary" onclick="window.patientsApp.viewPatientDetail('${escapeHtml(
              patient.id
            )}')">
              <i class="fas fa-eye"></i> View
            </button>
            <button class="btn-small btn-success" onclick="window.patientsApp.viewPatientRecords('${escapeHtml(
              patient.id
            )}')" style="margin-left: 5px;">
              <i class="fas fa-file-medical"></i> Records
            </button>
          </td>
        `;
        tbody.appendChild(row);
      });

      loadingEl.classList.add("hidden");
      contentEl.classList.remove("hidden");
    } catch (err) {
      console.error("Error loading patients:", err);
      document.getElementById("patients-body").innerHTML =
        '<tr><td colspan="6" class="text-center error">Error loading patients: ' +
        escapeHtml(err.message) +
        "</td></tr>";
      document.getElementById("patients-loading").classList.add("hidden");
      document.getElementById("patients-content").classList.remove("hidden");
    }
  }

  async function viewPatientDetail(patientId) {
    try {
      if (!patientId) {
        alert("Invalid patient ID");
        return;
      }

      const response = await window.medicalAPI.get(
        `/doctor/patients/${patientId}`
      );
      const patient = response;

      if (!patient) {
        alert("Patient not found");
        return;
      }

      document.getElementById("patient-detail-title").textContent = `Patient: ${
        patient.full_name || patient.username
      }`;

      const detailHtml = `
        <div class="patient-detail">
          <div class="detail-section">
            <h4>Personal Information</h4>
            <p><strong>Full Name:</strong> ${escapeHtml(
              patient.full_name || "Not set"
            )}</p>
            <p><strong>Username:</strong> ${escapeHtml(patient.username)}</p>
            <p><strong>Email:</strong> ${escapeHtml(patient.email)}</p>
            <p><strong>Role:</strong> <span class="badge badge-success">${escapeHtml(
              patient.role.toUpperCase()
            )}</span></p>
            <p><strong>Status:</strong> ${
              patient.is_active !== false
                ? '<span class="badge badge-success">Active</span>'
                : '<span class="badge badge-danger">Inactive</span>'
            }</p>
            <p><strong>Account Created:</strong> ${formatDate(
              patient.created_at
            )}</p>
          </div>
        </div>
      `;

      document.getElementById("patient-detail-body").innerHTML = detailHtml;
      document
        .getElementById("patient-detail-modal")
        .classList.remove("hidden");
      document
        .getElementById("patient-detail-modal")
        .setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    } catch (err) {
      console.error("Error loading patient detail:", err);
      alert("Error loading patient details");
    }
  }

  function viewPatientRecords(patientId) {
    // Redirect to patient records view page
    window.location.href = `/frontend/modules/doctor/patients/patient-records.html?patient_id=${patientId}`;
  }

  function closePatientDetail() {
    document.getElementById("patient-detail-modal").classList.add("hidden");
    document
      .getElementById("patient-detail-modal")
      .setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // Expose public API
  window.patientsApp = {
    loadPatients,
    viewPatientDetail,
    viewPatientRecords,
    closePatientDetail,
  };

  // Initialize when DOM is ready
  document.addEventListener("DOMContentLoaded", function () {
    // Only initialize on manage patients page
    if (window.location.pathname.includes("/patients/manage")) {
      // Load initial data
      window.patientsApp.loadPatients();
    }
  });
})();
