(function () {
  function applyConfig(config) {
    const root = document.getElementById("bookmd-content");
    root.style.setProperty("--bookmd-font-size", `${config.font_size || 18}px`);
    root.style.setProperty("--bookmd-line-height", config.line_height || 1.75);
    root.dataset.layout = config.layout || "paged";
    root.dataset.theme = config.theme || "light";
  }

  function loadChapter(payload) {
    const root = document.getElementById("bookmd-content");
    applyConfig(payload.config || {});
    root.innerHTML = payload.html || "";
    bindBlockEvents(root);
  }

  function bindBlockEvents(root) {
    root.querySelectorAll("[data-block-id]").forEach((node) => {
      node.addEventListener("click", () => {
        const block_id = node.dataset.blockId;
        if (window.AndroidBookMD && block_id) {
          window.AndroidBookMD.onBlockSelected(block_id);
        }
      });
    });

    root.querySelectorAll(".bookmd-figure img, .bookmd-table img").forEach((image) => {
      image.addEventListener("click", () => {
        if (window.AndroidBookMD) {
          window.AndroidBookMD.onImageSelected(image.getAttribute("src"));
        }
      });
    });
  }

  window.BookMDReader = {
    loadChapter,
    applyConfig,
  };
})();
