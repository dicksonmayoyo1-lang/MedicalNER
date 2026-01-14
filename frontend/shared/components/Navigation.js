(function () {
  "use strict";

  // Base URL for all frontend links (can be overridden before this script loads)
  const FRONTEND_BASE = window.FRONTEND_BASE || "/frontend";

  const navigationConfig = {
    doctor: [
      { name: "Dashboard", path: `${FRONTEND_BASE}/modules/doctor/dashboard.html` },
      { name: "Patient Management", path: `${FRONTEND_BASE}/modules/doctor/patients/manage.html` },
      { name: "Medical Screening", path: `${FRONTEND_BASE}/modules/doctor/screening/screening.html` },
      { name: "Analytics", path: `${FRONTEND_BASE}/modules/doctor/analytics/analytics.html` },
      { name: "Profile", path: `${FRONTEND_BASE}/modules/doctor/profile/profile.html` },
    ],
    patient: [
      { name: "Dashboard", path: `${FRONTEND_BASE}/modules/patient/dashboard.html` },
      { name: "My Records", path: `${FRONTEND_BASE}/modules/patient/records/view.html` },
      { name: "Profile", path: `${FRONTEND_BASE}/modules/patient/profile/profile.html` },
    ],
  };

  function buildNavHtml(role, user) {
    const items = navigationConfig[role] || [];
    const currentPath = window.location.pathname;

    const linksHtml = items
      .map((item) => {
        const active = currentPath === item.path;
        return `<a href="${item.path}" class="nav-link${active ? " active" : ""}">
          <span>${item.name}</span>
        </a>`;
      })
      .join("");

    const userHtml = user
      ? `<div class="user-info">
            <span class="user-role">${user.role}</span>
            <span class="user-name">${user.full_name || user.username}</span>
            <button class="btn-logout" id="nav-logout-btn">Logout</button>
         </div>`
      : "";

    return `
      <nav class="app-nav">
        <div class="nav-container">
          <div class="nav-brand">
            <h1>Medical RAG</h1>
          </div>
          <div class="nav-links">
            ${linksHtml}
          </div>
          ${userHtml}
        </div>
      </nav>
    `;
  }

  function renderNavigation(options) {
    const { role, user, containerId = "navigation" } = options;
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = buildNavHtml(role, user);

    // Attach logout handler if AuthApp is available
    const logoutBtn = document.getElementById("nav-logout-btn");
    if (logoutBtn && window.AuthApp && typeof window.AuthApp.logout === "function") {
      logoutBtn.addEventListener("click", function (e) {
        e.preventDefault();
        window.AuthApp.logout();
      });
    }
  }

  window.Navigation = {
    config: navigationConfig,
    render: renderNavigation,
  };
})();
