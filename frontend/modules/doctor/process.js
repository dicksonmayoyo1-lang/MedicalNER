// script.js
// Add to existing pages for auth protection
document.addEventListener("DOMContentLoaded", function () {
  // Check if user is authenticated
  const auth = AuthMiddleware.checkAuth();
  if (!auth) {
    // Will redirect to login
    return;
  }

  // Update navigation to show user info
  updateNavigationWithUser(auth.user);
});

function updateNavigationWithUser(user) {
  const userInfo = document.createElement("div");
  userInfo.className = "user-info";
  userInfo.innerHTML = `
        <span class="user-role">${user.role}</span>
        <span class="user-name">${user.full_name || user.username}</span>
        <button class="btn-logout" onclick="AuthApp.logout()">Logout</button>
    `;

  const nav = document.querySelector(".app-nav");
  if (nav) {
    nav.appendChild(userInfo);
  }
}
const submitBtn = document.getElementById("submit-btn");
const textInput = document.getElementById("text-input");
const fileInput = document.getElementById("file-input");
const jsonOutput = document.getElementById("json-output");
const metadataOutput = document.getElementById("metadata-output");
const extractedTextDiv = document.getElementById("extracted-text");
const highlightOutput = document.getElementById("highlight-output");
const summaryOutput = document.getElementById("summary-output");
const showJsonCheckbox = document.getElementById("show-json");

const viewFullTextBtn = document.getElementById("view-full-text-btn");
const viewFullTableBtn = document.getElementById("view-full-table-btn");
const viewFullHighlightBtn = document.getElementById("view-full-highlight-btn");

// Modal elements
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");
const modalClose = document.getElementById("modal-close");
const modalClose2 = document.getElementById("modal-close-2");
const modalBackdrop = document.getElementById("modal-backdrop");
const modalCopy = document.getElementById("modal-copy");
// Add this after your existing variable declarations
const fileCountSpan = document.getElementById("file-count");

// Add this event listener for file input changes
fileInput.addEventListener("change", () => {
  const count = fileInput.files.length;
  fileCountSpan.textContent = count > 0 ? `${count} file(s) selected` : "";
});

// Escape HTML helper
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

// Build entity table (unchanged)
function buildEntityTableForMatches(diseases, labs) {
  const diseaseRows = (diseases || [])
    .map((e) => {
      return `<tr>
      <td>${escapeHtml(e.entity || e.text || "")}</td>
      <td>${escapeHtml(e.label || e.entity_type || "DISEASE")}</td>
      <td style="text-align:right">${(e.confidence || 0).toFixed(3)}</td>
    </tr>`;
    })
    .join("");

  const labRows = (labs || [])
    .map((l) => {
      const name = l.test_name || l.text || l.test || "";
      const value =
        l.value_extracted || l.value || l.value_extracted || l.value || "-";
      const unit =
        l.unit ||
        (typeof value === "string" && value.split(" ").slice(-1)[0]) ||
        "-";
      const range = l.reference_range || l.normal_range || "-";
      const conf = (l.confidence || l.conf || 0).toFixed(3);
      return `<tr>
      <td>${escapeHtml(name)}</td>
      <td style="text-align:center">${escapeHtml(value)}</td>
      <td style="text-align:center">${escapeHtml(unit)}</td>
      <td style="text-align:center">${escapeHtml(range)}</td>
      <td style="text-align:right">${conf}</td>
    </tr>`;
    })
    .join("");

  return `
    <h3>Diseases</h3>
    ${
      diseaseRows
        ? `<table class="entity-table"><thead><tr><th>Entity</th><th>Label</th><th>Confidence</th></tr></thead><tbody>${diseaseRows}</tbody></table>`
        : "<p class='small'>No disease entities found.</p>"
    }
    <h3>Lab Results</h3>
    ${
      labRows
        ? `<table class="entity-table"><thead><tr><th>Test</th><th>Value</th><th>Unit</th><th>Reference</th><th>Confidence</th></tr></thead><tbody>${labRows}</tbody></table>`
        : "<p class='small'>No lab results found.</p>"
    }
  `;
}

// computeOffsetsForLab and highlightText (unchanged from your code)
function computeOffsetsForLab(source, lab) {
  if (lab.start && lab.end && lab.start < lab.end)
    return { start: lab.start, end: lab.end };

  const name = lab.test_name || lab.text || lab.test || "";
  const value = lab.value_extracted || lab.value || "";

  if (name && value) {
    const combined = `${name}`.trim();
    const idx = source.toLowerCase().indexOf(combined.toLowerCase());
    if (idx >= 0) {
      return { start: idx, end: idx + combined.length };
    }
  }

  if (name) {
    const idx = source.toLowerCase().indexOf(name.toLowerCase());
    if (idx >= 0) return { start: idx, end: idx + name.length };
  }

  if (value) {
    const idx = source.toLowerCase().indexOf(String(value).toLowerCase());
    if (idx >= 0) return { start: idx, end: idx + String(value).length };
  }

  return { start: 0, end: 0 };
}

function highlightText(sourceText, diseaseEntities, labEntities) {
  if (!sourceText || sourceText.trim().length === 0)
    return `<pre class="plain-text">No source text available.</pre>`;

  const ents = [];

  (diseaseEntities || []).forEach((d) => {
    const start = typeof d.start === "number" && d.start >= 0 ? d.start : -1;
    const end = typeof d.end === "number" && d.end > start ? d.end : -1;
    if (start >= 0 && end > 0) {
      ents.push({
        start,
        end,
        label: d.label || d.entity_type || "DISEASE",
        text: d.entity || d.text,
        category: "disease",
        confidence: d.confidence || 1,
      });
    } else {
      const idx = sourceText
        .toLowerCase()
        .indexOf((d.entity || d.text || "").toLowerCase());
      if (idx >= 0)
        ents.push({
          start: idx,
          end: idx + (d.entity || d.text || "").length,
          label: d.label || d.entity_type || "DISEASE",
          text: d.entity || d.text,
          category: "disease",
          confidence: d.confidence || 1,
        });
    }
  });

  (labEntities || []).forEach((l) => {
    const offs = computeOffsetsForLab(sourceText, l);
    if (offs.start >= 0 && offs.end > offs.start) {
      ents.push({
        start: offs.start,
        end: offs.end,
        label: l.test_name || l.text || "LAB",
        text: (l.test_name || l.text || "").trim(),
        category: "lab",
        confidence: l.confidence || 1,
        meta: l,
      });
    }
  });

  if (ents.length === 0)
    return `<pre class="plain-text">${escapeHtml(sourceText)}</pre>`;

  ents.sort((a, b) => a.start - b.start || a.end - b.end);
  const merged = [];
  for (const e of ents) {
    if (!merged.length) {
      merged.push(e);
      continue;
    }
    const last = merged[merged.length - 1];
    if (e.start <= last.end) {
      last.end = Math.max(last.end, e.end);
      if (
        (e.category === "disease" && last.category !== "disease") ||
        e.confidence > last.confidence
      ) {
        last.label = e.label;
        last.category = e.category;
        last.confidence = e.confidence;
        last.meta = e.meta;
      }
    } else {
      merged.push(e);
    }
  }

  let out = "";
  let lastIdx = 0;
  for (const e of merged) {
    if (e.start > lastIdx) {
      out += `<span class="plain-text">${escapeHtml(
        sourceText.slice(lastIdx, e.start)
      )}</span>`;
    }
    const cls =
      e.category === "disease" ? "highlight-disease" : "highlight-lab";
    const tooltip = `${e.label}${
      e.meta && e.meta.value_extracted ? " • " + e.meta.value_extracted : ""
    } • conf:${(e.confidence || 0).toFixed(3)}`;
    out += `<span class="${cls}" title="${escapeHtml(tooltip)}">${escapeHtml(
      sourceText.slice(e.start, e.end)
    )}</span>`;
    lastIdx = e.end;
  }
  if (lastIdx < sourceText.length)
    out += `<span class="plain-text">${escapeHtml(
      sourceText.slice(lastIdx)
    )}</span>`;

  return out;
}

// Normalize server response
function normalizeResponse(resp) {
  const metadata = resp.metadata || {};
  const sourceText = resp.extracted_text || resp.text || "";
  const diseases =
    resp.disease_ner && resp.disease_ner.entities
      ? resp.disease_ner.entities
      : resp.diseases || [];
  const labs =
    resp.lab_rag && resp.lab_rag.matches
      ? resp.lab_rag.matches
      : resp.lab_results || [];
  const summary =
    (resp.summary_block && (resp.summary_block.clinical_summary || "")) ||
    resp.summary ||
    resp.text ||
    "";
  return { metadata, sourceText, diseases, labs, summary };
}

// Display results
function displayResultsFromResponse(resp) {
  const { metadata, sourceText, diseases, labs, summary } =
    normalizeResponse(resp);

  // metadata
  metadataOutput.innerHTML = Object.keys(metadata).length
    ? Object.entries(metadata)
        .map(
          ([k, v]) =>
            `<div><strong>${escapeHtml(
              k
            )}:</strong> <span class="small">${escapeHtml(
              String(v)
            )}</span></div>`
        )
        .join("")
    : "<span class='small'>No metadata</span>";

  // extracted text (show truncated via CSS collapsed)
  extractedTextDiv.classList.add("collapsed");
  extractedTextDiv.innerHTML = escapeHtml(sourceText || textInput.value);

  // tables (truncated block)
  jsonOutput.classList.add("collapsed");
  jsonOutput.innerHTML = buildEntityTableForMatches(diseases, labs);

  // highlighted text (truncated)
  highlightOutput.classList.add("collapsed");
  highlightOutput.innerHTML = highlightText(
    sourceText || textInput.value,
    diseases,
    labs
  );

  // summary (display directly)
  summaryOutput.innerHTML = summary
    ? escapeHtml(
        typeof summary === "string"
          ? summary
          : summary.clinical_summary || summary
      )
    : "<span class='small'>No summary available</span>";

  // optionally show raw JSON as an expandable block appended under json-output
  if (showJsonCheckbox && showJsonCheckbox.checked) {
    const raw = document.createElement("pre");
    raw.textContent = JSON.stringify(resp, null, 2);
    jsonOutput.appendChild(document.createElement("hr"));
    jsonOutput.appendChild(raw);
  }
}

// Modal helpers
function showModal(title, htmlContent, asHtml = true) {
  modalTitle.textContent = title || "Full content";
  if (asHtml) {
    modalBody.innerHTML = htmlContent;
  } else {
    modalBody.textContent = htmlContent;
  }
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function hideModal() {
  modal.setAttribute("aria-hidden", "true");
  modalBody.innerHTML = "";
  document.body.style.overflow = "";
}

modalClose.addEventListener("click", hideModal);
modalClose2.addEventListener("click", hideModal);
modalBackdrop.addEventListener("click", hideModal);

// copy modal body to clipboard
modalCopy.addEventListener("click", async () => {
  try {
    const text = modalBody.innerText || modalBody.textContent || "";
    await navigator.clipboard.writeText(text);
    modalCopy.textContent = "Copied ✓";
    setTimeout(() => (modalCopy.textContent = "Copy"), 1500);
  } catch (err) {
    modalCopy.textContent = "Failed";
    setTimeout(() => (modalCopy.textContent = "Copy"), 1500);
  }
});

// 'View full' button handlers
viewFullTextBtn.addEventListener("click", () => {
  showModal("Extracted text (full)", extractedTextDiv.innerHTML, true);
});
viewFullTableBtn.addEventListener("click", () => {
  // show entity tables and optional raw JSON if present
  showModal("Entities & Lab Results (full)", jsonOutput.innerHTML, true);
});
viewFullHighlightBtn.addEventListener("click", () => {
  showModal("Highlighted text (full)", highlightOutput.innerHTML, true);
});

// submit handler (fetches and displays summary as part of response)
// Replace the existing submitBtn event listener with this:

submitBtn.addEventListener("click", async () => {
  // Get all selected files (allow multiple)
  const files = fileInput.files;

  if (files.length > 0) {
    // If multiple files selected, use the new endpoint
    if (files.length > 1) {
      const formData = new FormData();

      // Append all files
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
      formData.append("icd_map", false);

      try {
        const resp = await fetch(
          "http://localhost:8000/predict_multiple_pdfs_summary",
          {
            method: "POST",
            body: formData,
          }
        );

        if (!resp.ok) {
          const txt = await resp.text();
          alert("Server error: " + txt);
          return;
        }

        const data = await resp.json();

        // Check if it's a multi-document response
        if (isMultiDocumentResponse(data)) {
          displayMultiDocumentResults(data);
        } else {
          // Fallback to single document display
          displayResultsFromResponse(data);
        }
      } catch (err) {
        alert("Error: " + err);
      }
    } else {
      // Single file - use existing endpoint
      const formData = new FormData();
      formData.append("file", files[0]);
      formData.append("icd_map", false);

      try {
        const resp = await fetch("http://localhost:8000/predict_pdf", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) {
          const txt = await resp.text();
          alert("Server error: " + txt);
          return;
        }

        const data = await resp.json();
        displayResultsFromResponse(data);
      } catch (err) {
        alert("Error: " + err);
      }
    }
  } else if (textInput.value.trim() !== "") {
    // Text input - use existing endpoint
    const payload = { text: textInput.value, icd_map: false };
    try {
      const resp = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const txt = await resp.text();
        alert("Server error: " + txt);
        return;
      }
      const data = await resp.json();
      displayResultsFromResponse(data);
    } catch (err) {
      alert("Error: " + err);
    }
  } else {
    alert("Please enter text or upload PDF(s).");
  }
});

// Add this function to display multi-document results
function displayMultiDocumentResults(data) {
  const { metadata, documents, consolidated_summary } = data;

  // Display metadata
  metadataOutput.innerHTML = `
    <div><strong>Total Documents:</strong> ${metadata.total_documents}</div>
    <div><strong>Files:</strong> ${metadata.filenames.join(", ")}</div>
    <div><strong>Total Diseases Found:</strong> ${
      metadata.total_diseases_found
    }</div>
    <div><strong>Total Labs Found:</strong> ${metadata.total_labs_found}</div>
  `;

  // Display consolidated summary
  summaryOutput.innerHTML = consolidated_summary
    ? `<h3>Consolidated Summary (All Documents)</h3>
       <div class="summary-content">${escapeHtml(consolidated_summary)}</div>
       <hr>
       <h4>Individual Document Results:</h4>
       ${documents
         .map(
           (doc, idx) =>
             `<details>
            <summary>${
              doc.metadata.original_filename || `Document ${idx + 1}`
            } (${doc.diseases.length} diseases, ${
               doc.lab_results.length
             } labs)</summary>
            <div style="margin: 10px 0; padding: 10px; border-left: 3px solid var(--accent); background: #f9f9f9;">
              <h5>Document Summary:</h5>
              <div class="summary-content" style="margin-bottom: 10px;">${escapeHtml(
                doc.summary?.clinical_summary || "No summary available"
              )}</div>
              <h5>Extracted Entities:</h5>
              ${buildEntityTableForMatches(doc.diseases, doc.lab_results)}
            </div>
          </details>`
         )
         .join("")}`
    : "<span class='small'>No summary available</span>";

  // Clear other panels for multi-document view
  extractedTextDiv.innerHTML =
    "<p class='small'>Multiple documents uploaded. View individual document summaries above.</p>";
  jsonOutput.innerHTML = "";
  highlightOutput.innerHTML = "";
}

// Normalize server response for both single and multi-document
function normalizeResponse(resp) {
  // Check if this is a multi-document response
  if (resp.documents && Array.isArray(resp.documents)) {
    // It's a multi-document response - use the first document for single-document display compatibility
    if (resp.documents.length > 0) {
      const firstDoc = resp.documents[0];
      return {
        metadata: firstDoc.metadata || {},
        sourceText: firstDoc.text || "",
        diseases: firstDoc.diseases || [],
        labs: firstDoc.lab_results || [],
        summary: firstDoc.summary?.clinical_summary || firstDoc.summary || "",
      };
    }
  }

  // Single document response (original logic)
  const metadata = resp.metadata || {};
  const sourceText = resp.extracted_text || resp.text || "";
  const diseases =
    resp.disease_ner && resp.disease_ner.entities
      ? resp.disease_ner.entities
      : resp.diseases || [];
  const labs =
    resp.lab_rag && resp.lab_rag.matches
      ? resp.lab_rag.matches
      : resp.lab_results || [];
  const summary =
    (resp.summary_block && (resp.summary_block.clinical_summary || "")) ||
    resp.summary ||
    (typeof resp.summary === "object"
      ? resp.summary.clinical_summary
      : resp.summary) ||
    "";
  return { metadata, sourceText, diseases, labs, summary };
}

// Helper to detect if response is multi-document
function isMultiDocumentResponse(resp) {
  return (
    resp.documents && Array.isArray(resp.documents) && resp.consolidated_summary
  );
}

// Toggle patient ID input
document
  .getElementById("store-checkbox")
  ?.addEventListener("change", function () {
    document.getElementById("patient-id-input").style.display = this.checked
      ? "block"
      : "none";
  });

// Update submit handler to include storage options
// In your submitBtn event listener, modify the form data:
const store = document.getElementById("store-checkbox")?.checked || false;
const patientId = document.getElementById("patient-id")?.value || null;

// Add to your FormData or JSON payload:
// For PDF uploads:
formData.append("store", store);
if (patientId) formData.append("patient_id", patientId);

// For text input (modify your payload):
const payload = {
  text: textInput.value,
  icd_map: false,
  store: store,
  patient_id: patientId,
};
