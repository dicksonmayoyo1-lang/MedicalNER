(function () {
  "use strict";

  let currentPatientId = null;
  let currentPatient = null;

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
      const date = new Date(dateString);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    } catch (e) {
      return dateString;
    }
  }

  function formatDateShort(dateString) {
    if (!dateString) return "Unknown";
    try {
      return new Date(dateString).toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  }

  // Main functions
  async function init(patientId) {
    currentPatientId = patientId;
    
    // Load patient info first
    await loadPatientInfo(patientId);
    
    // Then load records
    await loadRecords();
  }

  async function loadPatientInfo(patientId) {
    try {
      const response = await window.medicalAPI.get(`/doctor/patients/${patientId}`);
      currentPatient = response;
      
      const patientInfoEl = document.getElementById("patient-info");
      if (currentPatient) {
        patientInfoEl.textContent = `Patient: ${currentPatient.full_name || currentPatient.username} (${currentPatient.email})`;
      } else {
        patientInfoEl.textContent = "Patient information not available";
      }
    } catch (err) {
      console.error("Error loading patient info:", err);
      document.getElementById("patient-info").textContent = "Error loading patient information";
    }
  }

  async function loadRecords() {
    try {
      const loadingEl = document.getElementById("records-loading");
      const contentEl = document.getElementById("records-content");
      const recordsListEl = document.getElementById("records-list");

      loadingEl.classList.remove("hidden");
      contentEl.classList.add("hidden");

      const response = await window.medicalAPI.get(
        `/doctor/patients/${currentPatientId}/records`
      );
      const records = Array.isArray(response) ? response : [];

      // Update stats
      document.getElementById("total-records").textContent = records.length;
      const totalDiseases = records.reduce((sum, r) => sum + (r.diseases_count || 0), 0);
      const totalLabs = records.reduce((sum, r) => sum + (r.labs_count || 0), 0);
      document.getElementById("total-diseases").textContent = totalDiseases;
      document.getElementById("total-labs").textContent = totalLabs;

      recordsListEl.innerHTML = "";

      if (records.length === 0) {
        recordsListEl.innerHTML =
          '<div class="empty-state"><i class="fas fa-file-medical"></i><p>No records found for this patient</p></div>';
        loadingEl.classList.add("hidden");
        contentEl.classList.remove("hidden");
        return;
      }

      records.forEach((record) => {
        const recordCard = document.createElement("div");
        recordCard.className = "record-card";
        
        const hasSummary = record.summary_preview && record.summary_preview.trim() !== "";
        
        recordCard.innerHTML = `
          <div class="record-card-header">
            <div class="record-title">
              <i class="fas fa-file-pdf"></i>
              <span>${escapeHtml(record.original_filename || "Unknown file")}</span>
            </div>
            <div class="record-date">${formatDateShort(record.upload_timestamp)}</div>
          </div>
          <div class="record-card-body">
            <div class="record-stats">
              <span class="stat-badge">
                <i class="fas fa-virus"></i> ${record.diseases_count || 0} Diseases
              </span>
              <span class="stat-badge">
                <i class="fas fa-flask"></i> ${record.labs_count || 0} Lab Results
              </span>
            </div>
            ${hasSummary ? `
              <div class="record-summary-preview">
                <strong>Summary:</strong> ${escapeHtml(record.summary_preview)}
              </div>
            ` : ""}
          </div>
          <div class="record-card-footer">
            <button class="btn btn-primary btn-small" onclick="window.patientRecordsApp.viewRecordDetail('${escapeHtml(record.id)}')">
              <i class="fas fa-eye"></i> View Details
            </button>
          </div>
        `;
        
        recordsListEl.appendChild(recordCard);
      });

      loadingEl.classList.add("hidden");
      contentEl.classList.remove("hidden");
    } catch (err) {
      console.error("Error loading records:", err);
      document.getElementById("records-list").innerHTML =
        '<div class="empty-state error"><i class="fas fa-exclamation-triangle"></i><p>Error loading records: ' +
        escapeHtml(err.message) +
        "</p></div>";
      document.getElementById("records-loading").classList.add("hidden");
      document.getElementById("records-content").classList.remove("hidden");
    }
  }

  async function viewRecordDetail(recordId) {
    try {
      if (!recordId) {
        alert("Invalid record ID");
        return;
      }

      const response = await window.medicalAPI.get(
        `/doctor/patients/${currentPatientId}/records/${recordId}`
      );
      const record = response;

      if (!record) {
        alert("Record not found");
        return;
      }

      document.getElementById("record-detail-title").textContent = 
        `Record: ${record.original_filename || "Unknown"}`;

      // Format diseases
      let diseasesHtml = "";
      if (record.diseases && record.diseases.length > 0) {
        diseasesHtml = '<div class="entities-section"><h4><i class="fas fa-virus"></i> Diseases Detected</h4><div class="entities-list">';
        record.diseases.forEach((disease) => {
          diseasesHtml += `
            <div class="entity-item">
              <span class="entity-text">${escapeHtml(disease.text || disease.entity || "Unknown")}</span>
              ${disease.icd_code ? `<span class="entity-code">ICD: ${escapeHtml(disease.icd_code)}</span>` : ""}
              ${disease.score ? `<span class="entity-score">Confidence: ${(disease.score * 100).toFixed(1)}%</span>` : ""}
            </div>
          `;
        });
        diseasesHtml += "</div></div>";
      } else {
        diseasesHtml = '<div class="entities-section"><h4><i class="fas fa-virus"></i> Diseases Detected</h4><p class="no-data">No diseases detected</p></div>';
      }

      // Format lab results
      let labsHtml = "";
      if (record.lab_results && record.lab_results.length > 0) {
        labsHtml = '<div class="entities-section"><h4><i class="fas fa-flask"></i> Lab Results</h4><div class="entities-list">';
        record.lab_results.forEach((lab) => {
          labsHtml += `
            <div class="entity-item">
              <span class="entity-text">${escapeHtml(lab.text || lab.entity || "Unknown")}</span>
              ${lab.value ? `<span class="entity-value">Value: ${escapeHtml(lab.value)}</span>` : ""}
              ${lab.normal_range ? `<span class="entity-range">Normal: ${escapeHtml(lab.normal_range)}</span>` : ""}
              ${lab.unit ? `<span class="entity-unit">Unit: ${escapeHtml(lab.unit)}</span>` : ""}
            </div>
          `;
        });
        labsHtml += "</div></div>";
      } else {
        labsHtml = '<div class="entities-section"><h4><i class="fas fa-flask"></i> Lab Results</h4><p class="no-data">No lab results detected</p></div>';
      }

      // Format summary
      let summaryHtml = "";
      if (record.summary) {
        const summaryText = record.summary.clinical_summary || record.summary;
        if (summaryText) {
          summaryHtml = `
            <div class="detail-section">
              <h4><i class="fas fa-file-medical-alt"></i> Clinical Summary</h4>
              <div class="summary-box">${escapeHtml(summaryText)}</div>
            </div>
          `;
        }
      }

      // Format metadata
      let metadataHtml = "";
      if (record.metadata) {
        metadataHtml = '<div class="detail-section"><h4><i class="fas fa-info-circle"></i> Metadata</h4><div class="metadata-box">';
        for (const [key, value] of Object.entries(record.metadata)) {
          metadataHtml += `<p><strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(value))}</p>`;
        }
        metadataHtml += "</div></div>";
      }

      const detailHtml = `
        <div class="record-detail">
          <div class="detail-section">
            <h4><i class="fas fa-file"></i> File Information</h4>
            <p><strong>Filename:</strong> ${escapeHtml(record.original_filename || "Unknown")}</p>
            <p><strong>Upload Date:</strong> ${formatDate(record.upload_timestamp)}</p>
            <p><strong>Patient ID:</strong> ${escapeHtml(record.patient_id || "Unknown")}</p>
          </div>
          
          ${summaryHtml}
          
          ${diseasesHtml}
          
          ${labsHtml}
          
          <div class="detail-section">
            <h4><i class="fas fa-align-left"></i> Extracted Text</h4>
            <div class="text-preview">${escapeHtml(record.extracted_text || "No text extracted")}</div>
          </div>
          
          ${metadataHtml}
        </div>
      `;

      document.getElementById("record-detail-body").innerHTML = detailHtml;
      document.getElementById("record-detail-modal").classList.remove("hidden");
      document.getElementById("record-detail-modal").setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    } catch (err) {
      console.error("Error loading record detail:", err);
      alert("Error loading record details: " + err.message);
    }
  }

  function closeRecordDetail() {
    document.getElementById("record-detail-modal").classList.add("hidden");
    document.getElementById("record-detail-modal").setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // Expose public API
  window.patientRecordsApp = {
    init,
    loadRecords,
    viewRecordDetail,
    closeRecordDetail,
  };
})();
