(function () {
  "use strict";

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
  }

  function formatDateShort(dateStr) {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return escapeHtml(dateStr);
    return d.toLocaleDateString();
  }

  function getSelectedPatientId() {
    return document.getElementById("patient-select")?.value || "";
  }

  async function loadPatients() {
    const select = document.getElementById("patient-select");
    if (!select) return;

    // keep first option
    select.querySelectorAll("option:not(:first-child)").forEach((o) => o.remove());

    const patients = await window.medicalAPI.get("/doctor/patients");
    (patients || []).forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      const label = `${p.full_name || p.username} (${p.email || "no-email"})`;
      opt.textContent = label;
      select.appendChild(opt);
    });
  }

  function setFormEnabled(enabled) {
    const form = document.getElementById("prescribe-form");
    if (!form) return;
    form.querySelectorAll("input, textarea, button").forEach((el) => {
      if (el.id === "patient-select") return;
      el.disabled = !enabled;
    });
    const hint = document.getElementById("form-hint");
    if (hint) hint.style.display = enabled ? "none" : "block";
  }

  async function loadMedications() {
    const patientId = getSelectedPatientId();
    const activeOnly = document.getElementById("active-only")?.checked ?? true;

    const loading = document.getElementById("meds-loading");
    const empty = document.getElementById("meds-empty");
    const content = document.getElementById("meds-content");
    const list = document.getElementById("meds-list");

    loading?.classList.remove("hidden");
    empty?.classList.add("hidden");
    content?.classList.add("hidden");

    if (!patientId) {
      loading?.classList.add("hidden");
      empty?.classList.remove("hidden");
      if (list) list.innerHTML = "";
      setFormEnabled(false);
      return;
    }

    setFormEnabled(true);

    try {
      const meds = await window.medicalAPI.get(
        `/doctor/medications/patients/${encodeURIComponent(patientId)}`,
        { active_only: activeOnly }
      );

      loading?.classList.add("hidden");

      if (!meds || meds.length === 0) {
        empty?.classList.remove("hidden");
        content?.classList.add("hidden");
        if (list) list.innerHTML = "";
        return;
      }

      content?.classList.remove("hidden");
      empty?.classList.add("hidden");

      list.innerHTML = meds
        .map((m) => {
          const statusBadge = m.is_active
            ? '<span class="badge badge-success">Active</span>'
            : '<span class="badge badge-danger">Inactive</span>';

          const notes = m.notes
            ? `<div class="med-notes"><strong>Recommendations:</strong> ${escapeHtml(
                m.notes
              )}</div>`
            : "";

          const prescribedBy = m.prescribed_by
            ? `<div class="med-meta"><div><strong>Prescribed by:</strong> ${escapeHtml(
                m.prescribed_by
              )}</div></div>`
            : "";

          const deactivateBtn = m.is_active
            ? `<button class="btn btn-sm btn-danger" onclick="window.doctorMedsApp.deactivateMedication('${escapeHtml(
                m.id
              )}')"><i class="fas fa-ban"></i> Deactivate</button>`
            : "";

          return `
            <div class="med-card">
              <div class="med-card-header">
                <div>
                  <div class="med-title"><i class="fas fa-pills"></i> ${escapeHtml(
                    m.name
                  )}</div>
                </div>
                <div>${statusBadge}</div>
              </div>
              <div class="med-meta">
                <div><strong>Dosage:</strong> ${escapeHtml(m.dosage)}</div>
                <div><strong>Frequency:</strong> ${escapeHtml(m.frequency)}</div>
                <div><strong>Start:</strong> ${formatDateShort(m.start_date)}</div>
                <div><strong>End:</strong> ${formatDateShort(m.end_date)}</div>
              </div>
              ${prescribedBy}
              ${notes}
              <div class="med-actions">
                ${deactivateBtn}
              </div>
            </div>
          `;
        })
        .join("");
    } catch (e) {
      console.error("Error loading medications:", e);
      loading?.classList.add("hidden");
      empty?.classList.remove("hidden");
    }
  }

  async function prescribeMedication(e) {
    e.preventDefault();

    const patientId = getSelectedPatientId();
    if (!patientId) {
      alert("Please select a patient first.");
      return;
    }

    const name = document.getElementById("med-name")?.value?.trim();
    const dosage = document.getElementById("med-dosage")?.value?.trim();
    const frequency = document.getElementById("med-frequency")?.value?.trim();
    const start_date = document.getElementById("med-start-date")?.value;
    const end_date = document.getElementById("med-end-date")?.value || null;
    const notes = document.getElementById("med-notes")?.value?.trim() || null;

    if (!name || !dosage || !frequency || !start_date) {
      alert("Please fill in name, dosage, frequency and start date.");
      return;
    }

    const submitBtn = document.querySelector('#prescribe-form button[type="submit"]');
    const originalHtml = submitBtn?.innerHTML;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Prescribing...';
    }

    try {
      await window.medicalAPI.post(
        `/doctor/medications/patients/${encodeURIComponent(patientId)}`,
        {
          name,
          dosage,
          frequency,
          start_date,
          end_date,
          notes,
          prescribed_by: null, // backend will override with doctor id
        }
      );

      // Clear form
      document.getElementById("med-name").value = "";
      document.getElementById("med-dosage").value = "";
      document.getElementById("med-frequency").value = "";
      document.getElementById("med-start-date").value = "";
      document.getElementById("med-end-date").value = "";
      document.getElementById("med-notes").value = "";

      alert("Medication prescribed successfully.");
      await loadMedications();
    } catch (err) {
      console.error("Error prescribing medication:", err);
      alert(err?.message || "Error prescribing medication.");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml || "Prescribe";
      }
    }
  }

  async function deactivateMedication(medicationId) {
    if (!medicationId) return;
    if (!confirm("Deactivate this medication?")) return;

    try {
      await window.medicalAPI.put(`/doctor/medications/${encodeURIComponent(medicationId)}`, {
        is_active: false,
      });
      await loadMedications();
    } catch (err) {
      console.error("Error deactivating medication:", err);
      alert(err?.message || "Error deactivating medication.");
    }
  }

  function bindEvents() {
    document.getElementById("patient-select")?.addEventListener("change", () => {
      loadMedications();
    });

    document.getElementById("active-only")?.addEventListener("change", () => {
      loadMedications();
    });

    document.getElementById("refresh-btn")?.addEventListener("click", () => {
      loadMedications();
    });

    document.getElementById("prescribe-form")?.addEventListener("submit", prescribeMedication);
  }

  async function init() {
    try {
      setFormEnabled(false);
      await loadPatients();
      await loadMedications();
      bindEvents();
    } catch (e) {
      console.error("Failed to init doctor medications module:", e);
      document.getElementById("meds-loading")?.classList.add("hidden");
      document.getElementById("meds-empty")?.classList.remove("hidden");
    }
  }

  window.doctorMedsApp = {
    init,
    loadMedications,
    deactivateMedication,
  };
})();

