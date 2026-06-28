(function () {
  function applyConfig(config) {
    const root = document.getElementById("bookmd-content");
    root.style.setProperty("--bookmd-font-size", `${config.font_size || 18}px`);
    root.style.setProperty("--bookmd-line-height", config.line_height || 1.75);
    root.dataset.layout = config.layout || "paged";
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
    const media = src ? `<img src="${escapeHtml(src)}" alt="${escapeHtml(caption)}">` : "";
    return `<figure class="bookmd-block bookmd-source-mark ${className}" data-block-id="${escapeHtml(id)}">${media}<figcaption class="bookmd-caption">${escapeHtml(caption)}</figcaption></figure>`;
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
    return `<a class="bookmd-reference" href="${escapeHtml(href)}">${escapeHtml(label)}</a>`;
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

  function nearestVisibleBlockId() {
    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    document.querySelectorAll(".bookmd-block[data-block-id]").forEach((node) => {
      const rect = node.getBoundingClientRect();
      const distance = Math.abs(rect.top);
      if (distance < bestDistance) {
        best = node.dataset.blockId || "";
        bestDistance = distance;
      }
    });
    return best || "";
  }

  function currentProgress() {
    return {
      scroll_y: window.scrollY || 0,
      block_id: nearestVisibleBlockId(),
    };
  }

  function restoreProgress(progress) {
    if (progress && progress.block_id && jumpToBlock(progress.block_id)) return true;
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
    searchInChapter,
    clearSearchHighlights,
    currentProgress,
    restoreProgress,
  };
})();
