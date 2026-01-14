// Navigation Loader - Add to existing shared JS or create new file
document.addEventListener("DOMContentLoaded", () => {
  // Highlight active link
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".nav-links a");

  navLinks.forEach((link) => {
    const href = link.getAttribute("href");
    // Normalize paths for comparison
    const normalizedHref = href.replace("/frontend/", "").replace(/^\//, "");
    const normalizedPath = currentPath.replace("/frontend/", "").replace(/^\//, "");
    if (normalizedPath.includes(normalizedHref) || currentPath === href) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });
});
