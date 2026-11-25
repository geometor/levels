(function () {
  "use strict";

  const svgCache = new Map();

  async function fetchSvgText(url) {
    if (svgCache.has(url)) {
      return svgCache.get(url);
    }
    const resp = await fetch(url, { cache: "no-cache" });
    if (!resp.ok) {
      throw new Error(`Failed to load SVG: ${url} (${resp.status})`);
    }
    const text = await resp.text();
    svgCache.set(url, text);
    return text;
  }

  function parseViewBox(svgEl) {
    const vbAttr = svgEl.getAttribute("viewBox");
    if (vbAttr) {
      const parts = vbAttr.trim().split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts.every((n) => Number.isFinite(n))) {
        return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
      }
    }
    const w = parseFloat(svgEl.getAttribute("width")) || 1000;
    const h = parseFloat(svgEl.getAttribute("height")) || 1000;
    return { x: 0, y: 0, w, h };
  }

  function getUnitsPerPx(rect, vb) {
    const w = rect.width || 720;
    const h = rect.height || 720;
    return Math.max(vb.w / w, vb.h / h);
  }

  function scaleViewElements(svgEl, vb) {
    if (!svgEl || !vb) return;
    const rect = svgEl.getBoundingClientRect();
    const unitsPerPx = getUnitsPerPx(rect, vb);

    svgEl.querySelectorAll("circle.geom-point").forEach((pt) => {
      const baseR = parseFloat(pt.getAttribute("data-base-r") || "5.5");
      pt.setAttribute("r", (baseR * unitsPerPx).toFixed(4));
    });

    svgEl.querySelectorAll("text.geom-label").forEach((lbl) => {
      const ay = parseFloat(lbl.getAttribute("data-anchor-y") || "0");
      const oy = parseFloat(lbl.getAttribute("data-offset-y") || "-14");
      const baseFont = parseFloat(lbl.getAttribute("data-base-font") || "16");
      lbl.setAttribute("y", (ay + oy * unitsPerPx).toFixed(4));
      lbl.setAttribute("font-size", (baseFont * unitsPerPx).toFixed(4));
    });
  }

  function applyViewBox(svgEl, vb) {
    svgEl.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    scaleViewElements(svgEl, vb);
  }

  function attachPanZoom(stageEl, getSvgEl, getState, setState) {
    let dragging = false;
    let startClientX = 0;
    let startClientY = 0;
    let startVb = null;

    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(() => {
        const svgEl = getSvgEl();
        const state = getState();
        if (svgEl && state) scaleViewElements(svgEl, state.current);
      }).observe(stageEl);
    }

    stageEl.addEventListener(
      "wheel",
      (ev) => {
        const svgEl = getSvgEl();
        const state = getState();
        if (!svgEl || !state) return;
        ev.preventDefault();

        const rect = svgEl.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const scaleFactor = ev.deltaY < 0 ? 0.85 : 1 / 0.85;
        const nextW = Math.min(
          state.initial.w * 8,
          Math.max(state.initial.w * 0.02, state.current.w * scaleFactor)
        );
        const nextH = (nextW / state.current.w) * state.current.h;

        const unitsPerPx = getUnitsPerPx(rect, state.current);
        const renderedW = state.current.w / unitsPerPx;
        const renderedH = state.current.h / unitsPerPx;
        const offsetX = rect.left + (rect.width - renderedW) * 0.5;
        const offsetY = rect.top + (rect.height - renderedH) * 0.5;
        const relX = (ev.clientX - offsetX) / renderedW;
        const relY = (ev.clientY - offsetY) / renderedH;

        const nextVb = {
          x: state.current.x + (state.current.w - nextW) * relX,
          y: state.current.y + (state.current.h - nextH) * relY,
          w: nextW,
          h: nextH,
        };
        setState({ initial: state.initial, current: nextVb });
        applyViewBox(svgEl, nextVb);
      },
      { passive: false }
    );

    stageEl.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const state = getState();
      if (!state) return;
      dragging = true;
      startClientX = ev.clientX;
      startClientY = ev.clientY;
      startVb = { ...state.current };
      stageEl.classList.add("is-dragging");
      stageEl.setPointerCapture(ev.pointerId);
    });

    stageEl.addEventListener("pointermove", (ev) => {
      if (!dragging || !startVb) return;
      const svgEl = getSvgEl();
      const state = getState();
      if (!svgEl || !state) return;
      const rect = svgEl.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const unitsPerPx = getUnitsPerPx(rect, startVb);
      const dx = (ev.clientX - startClientX) * unitsPerPx;
      const dy = (ev.clientY - startClientY) * unitsPerPx;
      const nextVb = {
        x: startVb.x - dx,
        y: startVb.y - dy,
        w: startVb.w,
        h: startVb.h,
      };
      setState({ initial: state.initial, current: nextVb });
      applyViewBox(svgEl, nextVb);
    });

    function endDrag(ev) {
      if (!dragging) return;
      dragging = false;
      startVb = null;
      stageEl.classList.remove("is-dragging");
      if (ev && stageEl.hasPointerCapture(ev.pointerId)) {
        stageEl.releasePointerCapture(ev.pointerId);
      }
    }

    stageEl.addEventListener("pointerup", endDrag);
    stageEl.addEventListener("pointercancel", endDrag);
  }

  function zoomCentered(svgEl, state, factor) {
    if (!svgEl || !state) return state;
    const nextW = Math.min(
      state.initial.w * 8,
      Math.max(state.initial.w * 0.02, state.current.w * factor)
    );
    const nextH = (nextW / state.current.w) * state.current.h;
    const nextVb = {
      x: state.current.x + (state.current.w - nextW) * 0.5,
      y: state.current.y + (state.current.h - nextH) * 0.5,
      w: nextW,
      h: nextH,
    };
    applyViewBox(svgEl, nextVb);
    return { initial: state.initial, current: nextVb };
  }

  function mountSvgIntoStage(stageEl, svgText) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgText, "image/svg+xml");
    const svgEl = doc.documentElement;
    if (!svgEl || svgEl.nodeName.toLowerCase() !== "svg") {
      throw new Error("Invalid SVG document");
    }
    svgEl.removeAttribute("width");
    svgEl.removeAttribute("height");
    svgEl.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svgEl.classList.add("geometor-svg-canvas");
    const initial = parseViewBox(svgEl);
    const state = { initial, current: { ...initial } };
    stageEl.replaceChildren(svgEl);
    scaleViewElements(svgEl, initial);
    requestAnimationFrame(() => scaleViewElements(svgEl, initial));
    return { svgEl, state };
  }

  function syncFullscreenButton(container) {
    const btn = container.querySelector('[data-action="fullscreen"]');
    if (!btn) return;
    const isFs =
      document.fullscreenElement === container ||
      container.classList.contains("is-fullscreen");
    btn.textContent = isFs ? "✕" : "⛶";
    btn.title = isFs ? "Exit fullscreen (f)" : "Fullscreen (f)";
  }

  async function toggleFullscreen(container) {
    if (document.fullscreenElement === container) {
      await document.exitFullscreen();
      container.classList.remove("is-fullscreen");
    } else if (container.requestFullscreen) {
      try {
        await container.requestFullscreen();
      } catch (_) {
        container.classList.toggle("is-fullscreen");
      }
    } else {
      container.classList.toggle("is-fullscreen");
    }
    syncFullscreenButton(container);
  }

  function wireFullscreen(container) {
    const btn = container.querySelector('[data-action="fullscreen"]');
    if (btn) {
      btn.addEventListener("click", () => toggleFullscreen(container));
    }
    document.addEventListener("fullscreenchange", () => {
      if (document.fullscreenElement !== container) {
        container.classList.remove("is-fullscreen");
      }
      syncFullscreenButton(container);
    });
  }

  async function initStandaloneViewer(container) {
    const src = container.dataset.src;
    const caption = container.dataset.caption || "";
    if (!src) return;

    container.tabIndex = 0;
    container.innerHTML = `
      <div class="gsv-stage" title="Scroll to zoom, drag to pan"></div>
      <div class="gsv-toolbar">
        <div class="gsv-zoom-group">
          <button type="button" class="gsv-btn" data-action="zoom-in" title="Zoom in">+</button>
          <button type="button" class="gsv-btn" data-action="zoom-out" title="Zoom out">−</button>
          <button type="button" class="gsv-btn" data-action="reset" title="Reset view">Reset</button>
          <button type="button" class="gsv-btn" data-action="fullscreen" title="Fullscreen (f)">⛶</button>
        </div>
        <div class="gsv-hint">Scroll to zoom · Drag to pan · f fullscreen</div>
      </div>
      ${caption ? `<div class="gsv-caption">${caption}</div>` : ""}
    `;

    wireFullscreen(container);
    const stageEl = container.querySelector(".gsv-stage");
    let svgEl = null;
    let vbState = null;

    attachPanZoom(
      stageEl,
      () => svgEl,
      () => vbState,
      (next) => {
        vbState = next;
      }
    );

    container.querySelector('[data-action="zoom-in"]').addEventListener("click", () => {
      vbState = zoomCentered(svgEl, vbState, 0.78);
    });
    container.querySelector('[data-action="zoom-out"]').addEventListener("click", () => {
      vbState = zoomCentered(svgEl, vbState, 1 / 0.78);
    });
    container.querySelector('[data-action="reset"]').addEventListener("click", () => {
      if (!svgEl || !vbState) return;
      vbState = { initial: vbState.initial, current: { ...vbState.initial } };
      applyViewBox(svgEl, vbState.current);
    });

    try {
      const svgText = await fetchSvgText(src);
      const mounted = mountSvgIntoStage(stageEl, svgText);
      svgEl = mounted.svgEl;
      vbState = mounted.state;
    } catch (err) {
      stageEl.innerHTML = `<div class="gsv-error">${err.message}</div>`;
    }
  }

  async function initSwitcher(container) {
    const manifestUrl = container.dataset.manifest;
    const baseUrl = container.dataset.base || manifestUrl.replace(/[^/]+$/, "");
    const intervalMs = Number(container.dataset.interval) || 1500;
    if (!manifestUrl) return;

    container.tabIndex = 0;
    container.innerHTML = `
      <div class="gsv-main">
        <div class="gsv-stage" title="Scroll to zoom, drag to pan"></div>
        <aside class="gsv-inspector" aria-label="Golden section details"></aside>
      </div>
      <div class="gsv-toolbar">
        <div class="gsv-transport-group">
          <button type="button" class="gsv-btn" data-action="prev" title="Previous frame">◀ Prev</button>
          <button type="button" class="gsv-btn gsv-btn-primary" data-action="play" title="Play / Pause">▶ Play</button>
          <button type="button" class="gsv-btn" data-action="next" title="Next frame">Next ▶</button>
          <span class="gsv-counter">0 / 0</span>
        </div>
        <div class="gsv-zoom-group">
          <button type="button" class="gsv-btn" data-action="zoom-in" title="Zoom in">+</button>
          <button type="button" class="gsv-btn" data-action="zoom-out" title="Zoom out">−</button>
          <button type="button" class="gsv-btn" data-action="reset" title="Reset view">Reset</button>
          <button type="button" class="gsv-btn" data-action="fullscreen" title="Fullscreen (f)">⛶</button>
        </div>
      </div>
      <div class="gsv-scrubber-row">
        <input type="range" class="gsv-scrubber" min="0" max="0" value="0" aria-label="Frame selector" />
      </div>
      <div class="gsv-caption">Loading frames…</div>
    `;

    wireFullscreen(container);
    const stageEl = container.querySelector(".gsv-stage");
    const inspectorEl = container.querySelector(".gsv-inspector");
    const playBtn = container.querySelector('[data-action="play"]');
    const counterEl = container.querySelector(".gsv-counter");
    const scrubberEl = container.querySelector(".gsv-scrubber");
    const captionEl = container.querySelector(".gsv-caption");

    let frames = [];
    let index = 0;
    let timer = null;
    let svgEl = null;
    let vbState = null;
    let renderToken = 0;

    function clearHighlights() {
      if (svgEl) {
        svgEl.querySelectorAll(".is-highlighted").forEach((el) => {
          el.classList.remove("is-highlighted");
        });
      }
      inspectorEl.querySelectorAll(".is-hovered").forEach((el) => {
        el.classList.remove("is-hovered");
      });
    }

    function highlightPoint(ptId) {
      clearHighlights();
      if (!ptId) return;
      if (svgEl) {
        svgEl.querySelectorAll(`[data-pt-id="${CSS.escape(ptId)}"]`).forEach((el) => {
          el.classList.add("is-highlighted");
        });
      }
      inspectorEl.querySelectorAll(`tr[data-pt-id="${CSS.escape(ptId)}"]`).forEach((row) => {
        row.classList.add("is-hovered");
      });
    }

    function highlightSegment(role) {
      clearHighlights();
      if (!role) return;
      const key = role.toLowerCase();
      if (svgEl) {
        const selector =
          key === "ratio"
            ? "[data-seg-role]"
            : `[data-seg-role="${CSS.escape(key)}"]`;
        svgEl.querySelectorAll(selector).forEach((el) => {
          el.classList.add("is-highlighted");
        });
      }
      inspectorEl.querySelectorAll(`tr[data-seg-role="${CSS.escape(key)}"]`).forEach((row) => {
        row.classList.add("is-hovered");
      });
    }

    function escHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function renderInspector(frame) {
      const pts = Array.isArray(frame.points) ? frame.points : [];
      const segs = Array.isArray(frame.segments) ? frame.segments : [];
      if (!pts.length && !segs.length) {
        inspectorEl.innerHTML = "";
        return;
      }

      function fmtMath(tex, alg) {
        return tex ? `\\(${escHtml(tex)}\\)` : escHtml(alg || "");
      }

      const ptRows = pts
        .map(
          (p) => `
          <tr data-pt-id="${escHtml(p.id)}">
            <td class="gsv-pt-id">${escHtml(p.id)}</td>
            <td>
              <div class="gsv-alg">${fmtMath(p.x_tex, p.x_alg)}</div>
              <div class="gsv-num">${escHtml(p.x_num)}</div>
            </td>
            <td>
              <div class="gsv-alg">${fmtMath(p.y_tex, p.y_alg)}</div>
              <div class="gsv-num">${escHtml(p.y_num)}</div>
            </td>
          </tr>`
        )
        .join("");

      const segRows = segs
        .map((s) => {
          const roleLower = s.role.toLowerCase();
          const segKey = roleLower === "major" || roleLower === "minor" ? roleLower : "ratio";
          const roleCls =
            segKey === "major"
              ? "gsv-seg-major"
              : segKey === "minor"
                ? "gsv-seg-minor"
                : "gsv-seg-ratio";
          return `
          <tr data-seg-role="${escHtml(segKey)}">
            <td class="${roleCls}">${escHtml(s.role)}</td>
            <td>${escHtml(s.label)}</td>
            <td>
              <div class="gsv-alg">${fmtMath(s.len_tex, s.len_alg)}</div>
              <div class="gsv-num">${escHtml(s.len_num)}</div>
            </td>
          </tr>`;
        })
        .join("");

      inspectorEl.innerHTML = `
        <div>
          <h4 class="gsv-section-title">Golden Points (Algebraic &amp; Float)</h4>
          <table class="gsv-table">
            <thead>
              <tr><th>Pt</th><th>x</th><th>y</th></tr>
            </thead>
            <tbody>${ptRows}</tbody>
          </table>
        </div>
        <div>
          <h4 class="gsv-section-title">Golden Segments (Major &amp; Minor)</h4>
          <table class="gsv-table">
            <thead>
              <tr><th>Segment</th><th>Points</th><th>Length</th></tr>
            </thead>
            <tbody>${segRows}</tbody>
          </table>
        </div>
      `;

      inspectorEl.querySelectorAll("tr[data-pt-id]").forEach((row) => {
        row.addEventListener("mouseenter", () => highlightPoint(row.dataset.ptId));
        row.addEventListener("mouseleave", clearHighlights);
      });
      inspectorEl.querySelectorAll("tr[data-seg-role]").forEach((row) => {
        row.addEventListener("mouseenter", () => highlightSegment(row.dataset.segRole));
        row.addEventListener("mouseleave", clearHighlights);
      });

      if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
        window.MathJax.typesetPromise([inspectorEl]).catch(() => {});
      } else if (window.MathJax && window.MathJax.Hub) {
        window.MathJax.Hub.Queue(["Typeset", window.MathJax.Hub, inspectorEl]);
      }
    }

    stageEl.addEventListener("pointerover", (ev) => {
      const target = ev.target;
      if (!target || !target.getAttribute) return;
      const ptId = target.getAttribute("data-pt-id");
      if (ptId) {
        highlightPoint(ptId);
        return;
      }
      const segRole = target.getAttribute("data-seg-role");
      if (segRole) {
        highlightSegment(segRole);
      }
    });
    stageEl.addEventListener("pointerout", (ev) => {
      const target = ev.target;
      if (!target || !target.getAttribute) return;
      if (target.getAttribute("data-pt-id") || target.getAttribute("data-seg-role")) {
        clearHighlights();
      }
    });

    attachPanZoom(
      stageEl,
      () => svgEl,
      () => vbState,
      (next) => {
        vbState = next;
      }
    );

    async function showFrame(nextIndex) {
      if (!frames.length) return;
      index = ((nextIndex % frames.length) + frames.length) % frames.length;
      const frame = frames[index];
      const token = ++renderToken;

      counterEl.textContent = `${index + 1} / ${frames.length}`;
      scrubberEl.value = String(index);
      captionEl.textContent = frame.caption || frame.src;
      renderInspector(frame);

      const svgUrl = frame.src.startsWith("/") || frame.src.includes("://")
        ? frame.src
        : baseUrl + frame.src;

      try {
        const svgText = await fetchSvgText(svgUrl);
        if (token !== renderToken) return;
        const mounted = mountSvgIntoStage(stageEl, svgText);
        svgEl = mounted.svgEl;
        vbState = mounted.state;
      } catch (err) {
        if (token !== renderToken) return;
        stageEl.innerHTML = `<div class="gsv-error">${err.message}</div>`;
      }
    }

    function stopPlayback() {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
      playBtn.textContent = "▶ Play";
      playBtn.classList.remove("is-playing");
    }

    function startPlayback() {
      if (timer !== null || frames.length <= 1) return;
      playBtn.textContent = "⏸ Pause";
      playBtn.classList.add("is-playing");
      timer = setInterval(() => {
        showFrame(index + 1);
      }, intervalMs);
    }

    container.querySelector('[data-action="prev"]').addEventListener("click", () => {
      stopPlayback();
      showFrame(index - 1);
    });
    container.querySelector('[data-action="next"]').addEventListener("click", () => {
      stopPlayback();
      showFrame(index + 1);
    });
    playBtn.addEventListener("click", () => {
      if (timer !== null) {
        stopPlayback();
      } else {
        startPlayback();
      }
    });
    scrubberEl.addEventListener("input", () => {
      stopPlayback();
      showFrame(Number(scrubberEl.value));
    });

    container.querySelector('[data-action="zoom-in"]').addEventListener("click", () => {
      vbState = zoomCentered(svgEl, vbState, 0.78);
    });
    container.querySelector('[data-action="zoom-out"]').addEventListener("click", () => {
      vbState = zoomCentered(svgEl, vbState, 1 / 0.78);
    });
    container.querySelector('[data-action="reset"]').addEventListener("click", () => {
      if (!svgEl || !vbState) return;
      vbState = { initial: vbState.initial, current: { ...vbState.initial } };
      applyViewBox(svgEl, vbState.current);
    });

    container.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        stopPlayback();
        showFrame(index - 1);
      } else if (ev.key === "ArrowRight") {
        ev.preventDefault();
        stopPlayback();
        showFrame(index + 1);
      } else if (ev.key === " ") {
        ev.preventDefault();
        if (timer !== null) stopPlayback();
        else startPlayback();
      }
    });

    try {
      const resp = await fetch(manifestUrl, { cache: "no-cache" });
      if (!resp.ok) {
        throw new Error(`Failed to load manifest: ${manifestUrl} (${resp.status})`);
      }
      frames = await resp.json();
      if (!Array.isArray(frames) || frames.length === 0) {
        captionEl.textContent = "No frames available.";
        return;
      }
      scrubberEl.max = String(frames.length - 1);
      await showFrame(0);
    } catch (err) {
      captionEl.textContent = err.message;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".geometor-svg-viewer").forEach(initStandaloneViewer);
    document.querySelectorAll(".geometor-svg-switcher").forEach(initSwitcher);

    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "f" && ev.key !== "F") return;
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      const tag = (ev.target && ev.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      const viewers = Array.from(
        document.querySelectorAll(".geometor-svg-switcher, .geometor-svg-viewer")
      );
      if (!viewers.length) return;
      const target =
        viewers.find((v) => v === document.fullscreenElement) ||
        viewers.find((v) => v.contains(document.activeElement)) ||
        viewers.find((v) => v.matches(":hover")) ||
        viewers[0];
      if (target) {
        ev.preventDefault();
        toggleFullscreen(target);
      }
    });
  });
})();
