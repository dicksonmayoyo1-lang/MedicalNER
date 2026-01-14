(function () {
  "use strict";

  function bindModal(options) {
    const {
      modalId = "modal",
      titleId = "modal-title",
      bodyId = "modal-body",
      closeSelectors = ["#modal-close", "#modal-close-2", "#modal-backdrop"],
      copyButtonId = "modal-copy",
    } = options || {};

    const modal = document.getElementById(modalId);
    const titleEl = document.getElementById(titleId);
    const bodyEl = document.getElementById(bodyId);
    const copyBtn = copyButtonId ? document.getElementById(copyButtonId) : null;

    if (!modal || !titleEl || !bodyEl) {
      return { show: function () {}, hide: function () {} };
    }

    function show(title, htmlContent, asHtml) {
      titleEl.textContent = title || "";
      if (asHtml) {
        bodyEl.innerHTML = htmlContent;
      } else {
        bodyEl.textContent = htmlContent;
      }
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function hide() {
      modal.setAttribute("aria-hidden", "true");
      bodyEl.innerHTML = "";
      document.body.style.overflow = "";
    }

    closeSelectors.forEach(function (sel) {
      const el = document.querySelector(sel);
      if (el) {
        el.addEventListener("click", hide);
      }
    });

    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        try {
          const text = bodyEl.innerText || bodyEl.textContent || "";
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = "Copied ✓";
          setTimeout(function () {
            copyBtn.textContent = "Copy";
          }, 1500);
        } catch (err) {
          copyBtn.textContent = "Failed";
          setTimeout(function () {
            copyBtn.textContent = "Copy";
          }, 1500);
        }
      });
    }

    return { show: show, hide: hide };
  }

  window.Modal = { bind: bindModal };
})();
