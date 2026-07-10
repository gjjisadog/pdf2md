(function () {
  let progressReportTimer = 0;
  let resizeTimer = 0;
  let touchStartX = 0;
  let touchStartY = 0;
  let currentConfig = {};
  const pageState = {
    pageIndex: 0,
    pageCount: 1,
  };

  function applyConfig(config) {
    currentConfig = config || {};
    const root = document.getElementById("bookmd-content");
    root.style.setProperty("--bookmd-font-size", `${config.font_size || 18}px`);
    root.style.setProperty("--bookmd-line-height", config.line_height || 1.75);
    root.dataset.layout = config.layout || "paged";
    document.body.dataset.bookmdLayout = root.dataset.layout;
    root.dataset.theme = config.theme || "light";
    root.dataset.languageMode = config.language_mode || config.default_mode || "zh";
    root.setAttribute("data-language-mode", root.dataset.languageMode);
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
    setupPagination();
    reportProgress();
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

      if (line.startsWith("```")) {
        const language = line.slice(3).trim();
        const codeLines = [];
        while (index + 1 < lines.length && !lines[index + 1].startsWith("```")) {
          index += 1;
          codeLines.push(lines[index]);
        }
        index += 1;
        html.push(wrapTrace(renderCodeFence(language, codeLines), trace));
        trace = null;
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

      if (isMarkdownTableStart(lines, index)) {
        const tableLines = [];
        while (index < lines.length && /^\|.+\|$/.test(lines[index])) {
          tableLines.push(lines[index]);
          index += 1;
        }
        index -= 1;
        html.push(wrapTrace(renderMarkdownTable(tableLines), trace));
        trace = null;
        continue;
      }

      const footnote = line.match(/^\[\^([^\]]+)\]:\s*(.+)$/);
      if (footnote) {
        html.push(renderFootnote(footnote[1], footnote[2]));
        trace = null;
        continue;
      }

      if (!line.trim()) {
        continue;
      }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        const slug = slugify(heading[2]);
        html.push(`<h${heading[1].length} id="${slug}" class="bookmd-block bookmd-source-mark" data-block-id="${escapeHtml(trace || "")}">${renderInline(heading[2])}</h${heading[1].length}>`);
      } else {
        html.push(`<p class="bookmd-block bookmd-source-mark" data-block-id="${escapeHtml(trace || "")}">${renderInline(line)}</p>`);
      }
      trace = null;
    }
    return html.join("\n");
  }

  function wrapTrace(html, trace) {
    if (!trace) return html;
    return `<section class="bookmd-block bookmd-source-mark" data-block-id="${escapeHtml(trace)}">${html}</section>`;
  }

  function renderAssetBlock(kind, id, src, caption) {
    const className = `bookmd-${kind}`;
    const media = src
      ? `<div class="bookmd-media-frame" tabindex="0"><img src="${escapeHtml(src)}" alt="${escapeHtml(caption)}" loading="lazy" decoding="async"></div>`
      : "";
    const captionHtml = caption ? `<figcaption class="bookmd-caption">${escapeHtml(caption)}</figcaption>` : "";
    return `<figure class="bookmd-block bookmd-source-mark ${className}" data-block-id="${escapeHtml(id)}">${media}${captionHtml}</figure>`;
  }

  function renderCodeFence(language, lines) {
    return `<pre class="bookmd-code"><code data-language="${escapeHtml(language)}">${escapeHtml(lines.join("\n"))}</code></pre>`;
  }

  function isMarkdownTableStart(lines, index) {
    return (
      /^\|.+\|$/.test(lines[index] || "") &&
      /^\|[\s:-]+\|/.test(lines[index + 1] || "")
    );
  }

  function renderMarkdownTable(lines) {
    const rows = lines.map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));
    const header = rows[0] || [];
    const body = rows.slice(2);
    const th = header.map((cell) => `<th>${renderInline(cell)}</th>`).join("");
    const trs = body.map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`).join("");
    return `<div class="bookmd-table-scroll"><table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
  }

  function renderFootnote(id, text) {
    return `<aside class="bookmd-footnote" id="fn-${escapeHtml(id)}">${renderInline(text)}</aside>`;
  }

  function renderReferenceLink(label, href) {
    const safeHref = sanitizeReferenceHref(href);
    return `<a class="bookmd-reference" href="${escapeHtml(safeHref)}">${escapeHtml(label)}</a>`;
  }

  function sanitizeReferenceHref(href) {
    const value = String(href || "").trim();
    const lower = value.toLowerCase();
    if (!value) return "#";
    if (lower.startsWith("http://") || lower.startsWith("https://")) return value;
    if (value.startsWith("#")) return value;
    if (!value.includes(":")) return value;
    if (lower.startsWith("javascript:") || lower.startsWith("file:") || lower.startsWith("content:") || lower.startsWith("data:") || lower.startsWith("intent:")) return "#";
    return "#";
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => renderReferenceLink(label, href))
      .replace(/\[\^([^\]]+)\]/g, (_match, id) => `<sup><a class="bookmd-footnote-ref" href="#fn-${escapeHtml(id)}">[${escapeHtml(id)}]</a></sup>`);
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
    bindRootSourceMapEvents(root);

    root.querySelectorAll("[data-block-id]").forEach((node) => {
      if (node.dataset.blockEventsBound === "true") return;
      node.dataset.blockEventsBound = "true";
      const blockId = node.dataset.blockId;
      if (blockId) {
        node.setAttribute("role", "button");
        node.setAttribute("tabindex", "0");
        node.setAttribute("aria-label", `source block ${blockId}`);
        installNativeSourceLink(node, blockId);
      }
      node.addEventListener("click", () => requestSourceMap(node.dataset.blockId));
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          requestSourceMap(node.dataset.blockId);
        }
      });
    });

    root.querySelectorAll(".bookmd-figure img, .bookmd-formula img, .bookmd-table img").forEach((image) => {
      if (image.dataset.mediaEventsBound === "true") return;
      image.dataset.mediaEventsBound = "true";
      image.addEventListener("click", () => {
        if (window.AndroidBookMD) {
          window.AndroidBookMD.onImageSelected(image.getAttribute("src"));
        }
      });
    });
  }

  function bindRootSourceMapEvents(root) {
    if (root.dataset.sourceMapEventsBound === "true") return;
    root.dataset.sourceMapEventsBound = "true";

    root.addEventListener("click", (event) => {
      const target = event.target && event.target.closest ? event.target : null;
      const block = target ? target.closest("[data-block-id]") : null;
      if (block && block.dataset.blockId) requestSourceMap(block.dataset.blockId);
    });

    root.addEventListener("touchend", (event) => {
      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch) return;
      if (Math.abs(touch.clientX - touchStartX) > 12 || Math.abs(touch.clientY - touchStartY) > 12) return;
      const target = document.elementFromPoint(touch.clientX, touch.clientY);
      const block = target && target.closest ? target.closest("[data-block-id]") : null;
      if (block && block.dataset.blockId) requestSourceMap(block.dataset.blockId);
    }, { passive: true });
  }

  function requestSourceMap(blockId) {
    if (window.AndroidBookMD && blockId && window.AndroidBookMD.onSourceMapRequested) {
      window.AndroidBookMD.onSourceMapRequested(blockId);
    } else if (window.AndroidBookMD && blockId) {
      window.AndroidBookMD.onBlockSelected(blockId);
    }
  }

  function installNativeSourceLink(node, blockId) {
    if (!currentConfig.native_source_links) return;
    if (node.querySelector(":scope > .bookmd-source-link-overlay")) return;
    const link = document.createElement("a");
    link.className = "bookmd-source-link-overlay";
    link.href = `bookmd-source://${encodeURIComponent(blockId)}`;
    link.setAttribute("aria-label", `source block ${blockId}`);
    node.appendChild(link);
  }

  function isPagedLayout() {
    const root = document.getElementById("bookmd-content");
    return root.dataset.layout === "paged";
  }

  function pageStep() {
    const root = document.getElementById("bookmd-content");
    const style = window.getComputedStyle(root);
    const gap = Number.parseFloat(style.columnGap || "0") || 0;
    return Math.max(1, root.clientWidth + gap);
  }

  function setupPagination() {
    const root = document.getElementById("bookmd-content");
    if (!root.dataset.paginationBound) {
      root.dataset.paginationBound = "true";
      root.addEventListener("scroll", scheduleProgressReport, { passive: true });
      root.addEventListener("touchstart", onTouchStart, { passive: true });
      root.addEventListener("touchend", onTouchEnd, { passive: true });
      window.addEventListener("resize", schedulePaginationRefresh);
    }
    refreshPagination();
  }

  function schedulePaginationRefresh() {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      refreshPagination();
      reportProgress();
    }, 150);
  }

  function refreshPagination() {
    const root = document.getElementById("bookmd-content");
    if (!isPagedLayout()) {
      pageState.pageIndex = 0;
      pageState.pageCount = 1;
      root.dataset.pageNumber = "1";
      root.dataset.pageCount = "1";
      return;
    }
    const step = pageStep();
    pageState.pageCount = Math.max(1, Math.ceil(root.scrollWidth / step));
    pageState.pageIndex = clamp(Math.round(root.scrollLeft / step), 0, pageState.pageCount - 1);
    root.dataset.pageNumber = String(pageState.pageIndex + 1);
    root.dataset.pageCount = String(pageState.pageCount);
  }

  function goToPage(pageIndex, behavior) {
    const root = document.getElementById("bookmd-content");
    refreshPagination();
    const target = clamp(pageIndex, 0, pageState.pageCount - 1);
    pageState.pageIndex = target;
    root.scrollTo({
      left: target * pageStep(),
      top: 0,
      behavior: behavior || "smooth",
    });
    refreshPagination();
    reportProgress();
    return target;
  }

  function nextPage() {
    return goToPage(pageState.pageIndex + 1);
  }

  function previousPage() {
    return goToPage(pageState.pageIndex - 1);
  }

  function onTouchStart(event) {
    const touch = event.changedTouches && event.changedTouches[0];
    if (!touch) return;
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
  }

  function onTouchEnd(event) {
    if (!isPagedLayout()) return;
    const touch = event.changedTouches && event.changedTouches[0];
    if (!touch) return;
    const dx = touch.clientX - touchStartX;
    const dy = touch.clientY - touchStartY;
    if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy)) return;
    if (dx < 0) {
      nextPage();
    } else {
      previousPage();
    }
  }

  function jumpToBlock(blockId) {
    const selector = `[data-block-id="${cssEscape(blockId)}"]`;
    const node = document.querySelector(selector);
    if (!node) return false;
    node.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    node.classList.add("bookmd-current-block");
    refreshPagination();
    return true;
  }

  function nearestVisibleBlockId() {
    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    document.querySelectorAll(".bookmd-block[data-block-id]").forEach((node) => {
      const rect = node.getBoundingClientRect();
      const distance = isPagedLayout()
        ? Math.abs(rect.left) + Math.abs(rect.top)
        : Math.abs(rect.top);
      if (distance < bestDistance) {
        best = node.dataset.blockId || "";
        bestDistance = distance;
      }
    });
    return best || "";
  }

  function currentProgress() {
    refreshPagination();
    const root = document.getElementById("bookmd-content");
    return {
      scroll_x: root.scrollLeft || window.scrollX || 0,
      scroll_y: window.scrollY || 0,
      page_index: pageState.pageIndex,
      page_count: pageState.pageCount,
      block_id: nearestVisibleBlockId(),
    };
  }

  function reportProgress() {
    if (!window.AndroidBookMD || !window.AndroidBookMD.onReadingProgressChanged) return;
    const progress = currentProgress();
    if (window.AndroidBookMD.onReadingProgressChangedPayload) {
      window.AndroidBookMD.onReadingProgressChangedPayload(JSON.stringify(progress));
    } else {
      window.AndroidBookMD.onReadingProgressChanged(progress.block_id || "", progress.scroll_y || 0);
    }
  }

  function scheduleProgressReport() {
    window.clearTimeout(progressReportTimer);
    progressReportTimer = window.setTimeout(reportProgress, 300);
  }

  function restoreProgress(progress) {
    if (progress && progress.block_id && jumpToBlock(progress.block_id)) return true;
    if (isPagedLayout() && progress && Number.isFinite(progress.page_index)) {
      goToPage(progress.page_index, "auto");
      return true;
    }
    if (isPagedLayout() && progress && Number.isFinite(progress.scroll_x)) {
      document.getElementById("bookmd-content").scrollTo({ left: progress.scroll_x, top: 0, behavior: "auto" });
      refreshPagination();
      return true;
    }
    if (progress && Number.isFinite(progress.scroll_y)) {
      window.scrollTo(0, progress.scroll_y);
      return true;
    }
    return false;
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
      if (!node.dataset.originalHtml) {
        node.dataset.originalHtml = node.innerHTML;
      }
      node.innerHTML = highlightText(text, query);
    });
    bindBlockEvents(document.getElementById("bookmd-content"));
    return results;
  }

  function clearSearchHighlights() {
    document.querySelectorAll(".bookmd-block[data-original-html]").forEach((node) => {
      node.innerHTML = node.dataset.originalHtml;
      delete node.dataset.originalHtml;
    });
    bindBlockEvents(document.getElementById("bookmd-content"));
  }

  function blockIdAtPoint(x, y) {
    const target = document.elementFromPoint(x, y);
    const block = target && target.closest ? target.closest("[data-block-id]") : null;
    return block && block.dataset.blockId ? block.dataset.blockId : "";
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

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function slugify(value) {
    return String(value)
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9\u4e00-\u9fa5_-]/g, "");
  }

  window.BookMDReader = {
    loadChapter,
    applyConfig,
    renderMarkdown,
    jumpToBlock,
    nextPage,
    previousPage,
    goToPage,
    searchInChapter,
    clearSearchHighlights,
    blockIdAtPoint,
    currentProgress,
    reportProgress,
    restoreProgress,
    setupPagination,
  };

  window.addEventListener("scroll", scheduleProgressReport, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") reportProgress();
  });
})();
