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
    root.innerHTML = payload.html || renderMarkdown(payload.markdown || "");
    if (window.renderMathInElement) {
      window.renderMathInElement(root, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\(", right: "\\)", display: false },
        ],
      });
    }
    bindBlockEvents(root);
  }

  function renderMarkdown(markdown) {
    const lines = markdown.split(/\r?\n/);
    const html = [];
    let trace = null;
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      const traceMatch = line.match(/^<!-- block_id: ([^;]+); page: ([^;]+); bbox: (.+) -->$/);
      if (traceMatch) {
        trace = traceMatch[1];
        continue;
      }

      if (line.startsWith(":::figure") || line.startsWith(":::formula") || line.startsWith(":::table")) {
        const kind = line.slice(3).split(/\s+/)[0];
        const id = readAttribute(line, "id") || trace || "";
        const src = readAttribute(line, "src") || "";
        const captionLines = [];
        while (index + 1 < lines.length && lines[index + 1] !== ":::") {
          index += 1;
          captionLines.push(lines[index]);
        }
        index += 1;
        html.push(renderAssetBlock(kind, id, src, captionLines.join("\n")));
        trace = null;
        continue;
      }

      if (line.startsWith(":::bilingual")) {
        const source = [];
        const target = [];
        let section = "target";
        while (index + 1 < lines.length && lines[index + 1] !== ":::") {
          index += 1;
          if (lines[index] === "---source---") {
            section = "source";
          } else if (section === "source") {
            source.push(lines[index]);
          } else {
            target.push(lines[index]);
          }
        }
        index += 1;
        html.push(`<section class="bookmd-block bookmd-source-mark bookmd-bilingual" data-block-id="${escapeHtml(trace || "")}"><div>${escapeHtml(target.join("\n"))}</div><div class="bookmd-bilingual-source">${escapeHtml(source.join("\n"))}</div></section>`);
        trace = null;
        continue;
      }

      if (!line.trim()) {
        continue;
      }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        html.push(`<h${heading[1].length} class="bookmd-block bookmd-source-mark" data-block-id="${escapeHtml(trace || "")}">${escapeHtml(heading[2])}</h${heading[1].length}>`);
      } else {
        html.push(`<p class="bookmd-block bookmd-source-mark" data-block-id="${escapeHtml(trace || "")}">${escapeHtml(line)}</p>`);
      }
      trace = null;
    }
    return html.join("\n");
  }

  function renderAssetBlock(kind, id, src, caption) {
    const className = `bookmd-${kind}`;
    const media = src ? `<img src="${escapeHtml(src)}" alt="${escapeHtml(caption)}">` : "";
    return `<figure class="bookmd-block bookmd-source-mark ${className}" data-block-id="${escapeHtml(id)}">${media}<figcaption class="bookmd-caption">${escapeHtml(caption)}</figcaption></figure>`;
  }

  function readAttribute(text, name) {
    const match = text.match(new RegExp(`${name}="([^"]*)"`));
    return match ? match[1] : "";
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function bindBlockEvents(root) {
    root.querySelectorAll("[data-block-id]").forEach((node) => {
      node.addEventListener("click", () => {
        const block_id = node.dataset.blockId;
        if (window.AndroidBookMD && block_id && window.AndroidBookMD.onSourceMapRequested) {
          window.AndroidBookMD.onSourceMapRequested(block_id);
        } else if (window.AndroidBookMD && block_id) {
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

  function jumpToBlock(blockId) {
    const selector = `[data-block-id="${cssEscape(blockId)}"]`;
    const node = document.querySelector(selector);
    if (!node) return false;
    node.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    node.classList.add("bookmd-current-block");
    return true;
  }

  function searchInChapter(query) {
    clearSearchHighlights();
    if (!query) return [];
    const results = [];
    document.querySelectorAll(".bookmd-block").forEach((node) => {
      const text = node.textContent || "";
      const index = text.toLowerCase().indexOf(query.toLowerCase());
      if (index < 0) return;
      const blockId = node.dataset.blockId || "";
      results.push({ block_id: blockId, text });
      node.innerHTML = highlightText(text, query);
    });
    return results;
  }

  function clearSearchHighlights() {
    document.querySelectorAll(".bookmd-search-hit").forEach((node) => {
      const parent = node.parentElement;
      if (!parent) return;
      parent.replaceChildren(document.createTextNode(parent.textContent || ""));
    });
  }

  function highlightText(text, query) {
    const escapedText = escapeHtml(text);
    const escapedQuery = escapeHtml(query);
    return escapedText.replace(
      new RegExp(escapeRegExp(escapedQuery), "gi"),
      (match) => `<mark class="bookmd-search-hit">${match}</mark>`,
    );
  }

  function cssEscape(value) {
    if (window.CSS && window.CSS.escape) return window.CSS.escape(value);
    return String(value).replaceAll('"', '\\"');
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  window.BookMDReader = {
    loadChapter,
    applyConfig,
    renderMarkdown,
    jumpToBlock,
    searchInChapter,
    clearSearchHighlights,
  };
})();
