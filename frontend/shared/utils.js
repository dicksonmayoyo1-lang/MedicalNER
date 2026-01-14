// Shared utility functions
window.Utils = {
  escapeHtml(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  },

  formatDate(dateStr) {
    if (!dateStr) return "Unknown";
    return new Date(dateStr).toLocaleString();
  },

  getRiskColor(riskLevel) {
    switch (riskLevel?.toUpperCase()) {
      case "HIGH":
        return "#dc3545";
      case "MEDIUM":
        return "#ffc107";
      case "LOW":
        return "#28a745";
      default:
        return "#6c757d";
    }
  },

  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },
};
