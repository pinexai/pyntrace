/**
 * charts.js — Phase 2 advanced chart components for pyntrace dashboard
 *
 * Depends on:
 *   - Chart.js 4 (loaded in <head> from cdn.jsdelivr.net)
 *   - Globals from index.html inline script: esc(), fmt(), openDetail(),
 *     _charts[], toast(), copyText()
 *
 * All public APIs exposed as window.* properties.
 * Load this AFTER the index.html inline <script> block.
 */
(function (w) {
  'use strict';

  /* ═══════════════════════════════════════════════════════
     §1 — SHARED UTILITIES
  ═══════════════════════════════════════════════════════ */

  const _CHART_OPTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(37,37,74,.6)' }, ticks: { color: '#94a3b8' } },
      y: { grid: { color: 'rgba(37,37,74,.6)' }, ticks: { color: '#94a3b8' }, beginAtZero: true },
    },
  };

  function _el(id) { return document.getElementById(id); }
  function _container(id) {
    const el = _el(id);
    if (!el) { console.warn('[charts.js] Container not found:', id); return null; }
    return el;
  }
  function _pushChart(c) { if (w._charts) w._charts.push(c); }

  /** Colour scale: 0→transparent, 1→danger red */
  function _heatColor(ratio) {
    const r = Math.round(248 * ratio);
    const g = Math.round(113 - 80 * ratio);
    const b = Math.round(113 - 80 * ratio);
    const a = 0.12 + ratio * 0.75;
    return `rgba(${r},${g},${b},${a})`;
  }

  /* ═══════════════════════════════════════════════════════
     §2 — MULTILINGUAL HEATMAP
  ═══════════════════════════════════════════════════════ */

  /**
   * renderMultilingualHeatmap(containerId, reports)
   * reports: array from /api/security/multilingual
   * Builds an HTML <table> heatmap: rows=languages, cols=attack_type.
   */
  function renderMultilingualHeatmap(containerId, reports) {
    const wrap = _container(containerId);
    if (!wrap) return;

    if (!reports || !reports.length) {
      wrap.innerHTML = '<div style="color:var(--c-t3);font-size:12px;padding:16px">No multilingual scan data yet. Run: <code style="color:var(--c-accent)">pyntrace scan --lang all myapp:chatbot</code></div>';
      return;
    }

    // Aggregate across reports: map[language][attack_type] = {hits, total}
    const langSet = new Set(), atkSet = new Set();
    const matrix = {}; // matrix[lang][atk] = {hits, total}

    reports.forEach(function (rep) {
      const langs = rep.languages || [];
      const atks  = Array.isArray(rep.attacks) ? rep.attacks : [];
      langs.forEach(function (lang) {
        langSet.add(lang);
        if (!matrix[lang]) matrix[lang] = {};
        atks.forEach(function (a) {
          const key = (a.attack_type || a.plugin || 'unknown').toLowerCase().slice(0, 20);
          atkSet.add(key);
          if (!matrix[lang][key]) matrix[lang][key] = { hits: 0, total: 0 };
          matrix[lang][key].total++;
          if (a.vulnerable) matrix[lang][key].hits++;
        });
      });
    });

    if (!langSet.size) {
      // Fallback: use most_vulnerable_language and safest_language as labels
      reports.forEach(function (r) {
        if (r.most_vulnerable_language) langSet.add(r.most_vulnerable_language);
        if (r.safest_language) langSet.add(r.safest_language);
      });
      if (!langSet.size) langSet.add('en');
      atkSet.add('injection').add('jailbreak').add('pii').add('other');
    }

    const langs = Array.from(langSet);
    const atks  = Array.from(atkSet).slice(0, 8);

    // Find global max rate for normalisation
    let maxRate = 0;
    langs.forEach(function (lang) {
      atks.forEach(function (atk) {
        const cell = (matrix[lang] || {})[atk];
        if (cell && cell.total) {
          const r = cell.hits / cell.total;
          if (r > maxRate) maxRate = r;
        }
      });
    });
    if (!maxRate) maxRate = 1;

    let h = '<div style="overflow-x:auto">'
          + '<table style="border-collapse:collapse;font-size:11px;width:100%">'
          + '<thead><tr><th style="padding:6px 10px;color:var(--c-t3);text-align:left;white-space:nowrap">Language</th>';
    atks.forEach(function (atk) {
      h += '<th style="padding:6px 8px;color:var(--c-t3);text-align:center;font-weight:600;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap">'
        + w.esc(atk) + '</th>';
    });
    h += '</tr></thead><tbody>';

    langs.forEach(function (lang) {
      h += '<tr>';
      h += '<td style="padding:6px 10px;color:var(--c-t2);font-weight:500;white-space:nowrap">' + w.esc(lang) + '</td>';
      atks.forEach(function (atk) {
        const cell = (matrix[lang] || {})[atk];
        const rate = cell && cell.total ? cell.hits / cell.total : 0;
        const ratio = maxRate ? rate / maxRate : 0;
        const bg    = _heatColor(ratio);
        const label = cell && cell.total
          ? (rate * 100).toFixed(0) + '%'
          : '—';
        const textColor = ratio > 0.6 ? '#fff' : 'var(--c-t2)';
        const title = cell
          ? `${lang} × ${atk}: ${cell.hits}/${cell.total} vulnerable`
          : `${lang} × ${atk}: no data`;
        h += `<td style="padding:6px 8px;text-align:center;background:${bg};color:${textColor};cursor:default;border-radius:2px" title="${w.esc(title)}">${label}</td>`;
      });
      h += '</tr>';
    });

    h += '</tbody></table></div>';
    wrap.innerHTML = h;
  }

  /* ═══════════════════════════════════════════════════════
     §3 — SWARM TOPOLOGY CANVAS
  ═══════════════════════════════════════════════════════ */

  /**
   * renderSwarmTopology(canvasId, swarmRow)
   * swarmRow: one row from /api/security/swarm
   * Draws agent nodes + directed edges on a <canvas>.
   */
  function renderSwarmTopology(canvasId, swarmRow) {
    const canvas = _el(canvasId);
    if (!canvas || !canvas.getContext) return;

    const ctx    = canvas.getContext('2d');
    const W      = canvas.width  = canvas.parentElement ? canvas.parentElement.clientWidth  || 480 : 480;
    const H      = canvas.height = canvas.parentElement ? canvas.parentElement.clientHeight || 280 : 280;
    const agents = (swarmRow && swarmRow.agents) || [];
    const rogue  = swarmRow ? (swarmRow.rogue_position || 0) : -1;
    const topo   = swarmRow ? (swarmRow.topology || 'star') : 'star';

    ctx.clearRect(0, 0, W, H);

    if (!agents.length) {
      // Draw placeholder
      const n = 4;
      const demoAgents = Array.from({ length: n }, function (_, i) { return { id: i, name: 'Agent ' + i, trust_score: 0.8 }; });
      _drawTopology(ctx, W, H, demoAgents, 0, topo, '#c084fc88');
      _drawLabel(ctx, W, H, 'No swarm data — showing placeholder topology');
      return;
    }

    _drawTopology(ctx, W, H, agents, rogue, topo, null);
  }

  function _drawTopology(ctx, W, H, agents, rogueIdx, topo, overrideColor) {
    const n = agents.length;
    if (!n) return;

    // Compute node positions based on topology
    const positions = _computePositions(W, H, n, topo);
    const R = 18; // node radius

    // Draw edges first
    ctx.save();
    for (let i = 0; i < n; i++) {
      let targets = [];
      if (topo === 'star') {
        if (i !== 0) targets = [0]; else targets = Array.from({ length: n - 1 }, function (_, k) { return k + 1; });
      } else if (topo === 'chain') {
        if (i < n - 1) targets = [i + 1];
      } else if (topo === 'mesh' || topo === 'hierarchical') {
        targets = Array.from({ length: n }, function (_, k) { return k; }).filter(function (k) { return k !== i && (topo === 'mesh' || k === i + 1 || k === Math.floor((i - 1) / 2)); });
      }
      targets.forEach(function (j) {
        const isCompromised = (i === rogueIdx || j === rogueIdx);
        ctx.beginPath();
        ctx.moveTo(positions[i].x, positions[i].y);
        ctx.lineTo(positions[j].x, positions[j].y);
        ctx.strokeStyle = isCompromised ? 'rgba(248,113,113,.6)' : 'rgba(192,132,252,.25)';
        ctx.lineWidth   = isCompromised ? 2 : 1;
        ctx.setLineDash(isCompromised ? [4, 3] : []);
        ctx.stroke();
        // Arrowhead
        _arrow(ctx, positions[i], positions[j], isCompromised ? 'rgba(248,113,113,.8)' : 'rgba(192,132,252,.5)');
      });
    }
    ctx.restore();

    // Draw nodes
    agents.forEach(function (agent, i) {
      const p      = positions[i];
      const isRogue = (i === rogueIdx);
      const color   = overrideColor || (isRogue ? '#f87171' : '#c084fc');
      const bgAlpha = isRogue ? '33' : '1a';

      // Shadow glow
      ctx.save();
      ctx.shadowColor = color;
      ctx.shadowBlur  = isRogue ? 12 : 6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, R, 0, Math.PI * 2);
      ctx.fillStyle = color + bgAlpha;
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth   = isRogue ? 2.5 : 1.5;
      ctx.stroke();
      ctx.restore();

      // Label
      ctx.fillStyle   = isRogue ? '#f87171' : '#e2e8f0';
      ctx.font        = '10px system-ui, sans-serif';
      ctx.textAlign   = 'center';
      ctx.textBaseline = 'middle';
      const label     = (agent.name || agent.id || ('A' + i)).toString().slice(0, 6);
      ctx.fillText(label, p.x, p.y);

      if (isRogue) {
        ctx.fillStyle = '#f87171';
        ctx.font      = '9px system-ui';
        ctx.fillText('⚠ rogue', p.x, p.y + R + 10);
      }
    });
  }

  function _computePositions(W, H, n, topo) {
    const cx = W / 2, cy = H / 2;
    const r  = Math.min(W, H) * 0.35;
    if (topo === 'chain') {
      const step = W / (n + 1);
      return Array.from({ length: n }, function (_, i) { return { x: step * (i + 1), y: cy }; });
    }
    if (topo === 'hierarchical') {
      const rows = Math.ceil(Math.log2(n + 1));
      const pos  = [];
      for (let i = 0; i < n; i++) {
        const row = Math.floor(Math.log2(i + 1));
        const colsInRow = Math.pow(2, row);
        const colIdx    = i - (colsInRow - 1);
        pos.push({ x: W * (colIdx + 1) / (colsInRow + 1), y: H * (row + 1) / (rows + 1) });
      }
      return pos;
    }
    // Star or mesh — circular layout
    return Array.from({ length: n }, function (_, i) {
      const angle = (2 * Math.PI * i / n) - Math.PI / 2;
      return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
  }

  function _arrow(ctx, from, to, color) {
    const dx   = to.x - from.x, dy = to.y - from.y;
    const len  = Math.sqrt(dx * dx + dy * dy);
    if (len < 2) return;
    const ux = dx / len, uy = dy / len;
    const tip = { x: to.x - ux * 20, y: to.y - uy * 20 };
    const headLen = 7;
    const angle   = Math.atan2(dy, dx);
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle   = color;
    ctx.lineWidth   = 1;
    ctx.beginPath();
    ctx.moveTo(tip.x, tip.y);
    ctx.lineTo(tip.x - headLen * Math.cos(angle - 0.4), tip.y - headLen * Math.sin(angle - 0.4));
    ctx.lineTo(tip.x - headLen * Math.cos(angle + 0.4), tip.y - headLen * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function _drawLabel(ctx, W, H, text) {
    ctx.save();
    ctx.fillStyle   = 'rgba(148,163,184,.6)';
    ctx.font        = '11px system-ui, sans-serif';
    ctx.textAlign   = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(text, W / 2, H - 6);
    ctx.restore();
  }

  /* ═══════════════════════════════════════════════════════
     §4 — LATENCY BOX PLOT (Chart.js floating bars)
  ═══════════════════════════════════════════════════════ */

  /**
   * makeBoxPlot(canvasId, reports)
   * reports: array from /api/latency
   * Renders min→p50 and p50→max as floating bars; p95/p99 as scatter.
   */
  function makeBoxPlot(canvasId, reports) {
    const canvas = _el(canvasId);
    if (!canvas || !w.Chart) return null;

    const labels = reports.map(function (r) { return (r.fn_name || r.id || 'fn').slice(0, 18); });

    // Floating bar: [low, high] per report
    const barLow  = reports.map(function (r) { return [r.min_ms || 0, r.p50_ms || r.mean_ms || 0]; });
    const barHigh = reports.map(function (r) { return [r.p50_ms || r.mean_ms || 0, r.max_ms || r.p99_ms || 0]; });
    const p95Pts  = reports.map(function (r, i) { return { x: i, y: r.p95_ms || 0 }; });
    const p99Pts  = reports.map(function (r, i) { return { x: i, y: r.p99_ms || 0 }; });

    const c = new w.Chart(canvas, {
      data: {
        labels: labels,
        datasets: [
          {
            type: 'bar',
            label: 'Min → P50',
            data: barLow,
            backgroundColor: 'rgba(74,222,128,.5)',
            borderColor: '#4ade80',
            borderWidth: 1,
            borderSkipped: false,
          },
          {
            type: 'bar',
            label: 'P50 → Max',
            data: barHigh,
            backgroundColor: 'rgba(192,132,252,.4)',
            borderColor: '#c084fc',
            borderWidth: 1,
            borderSkipped: false,
          },
          {
            type: 'scatter',
            label: 'P95',
            data: p95Pts,
            backgroundColor: '#fbbf24',
            pointRadius: 5,
            pointStyle: 'triangle',
          },
          {
            type: 'scatter',
            label: 'P99',
            data: p99Pts,
            backgroundColor: '#f87171',
            pointRadius: 5,
            pointStyle: 'rectRot',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 } } },
          tooltip: {
            callbacks: {
              title: function (items) { return items[0].label; },
              label: function (item) {
                const r = reports[item.dataIndex];
                if (!r) return item.dataset.label;
                return [
                  'Min: ' + (r.min_ms || 0).toFixed(0) + ' ms',
                  'P50: ' + (r.p50_ms || r.mean_ms || 0).toFixed(0) + ' ms',
                  'P95: ' + (r.p95_ms || 0).toFixed(0) + ' ms',
                  'P99: ' + (r.p99_ms || 0).toFixed(0) + ' ms',
                  'Max: ' + (r.max_ms || 0).toFixed(0) + ' ms',
                ];
              },
            },
          },
        },
        scales: {
          x: { grid: { color: 'rgba(37,37,74,.6)' }, ticks: { color: '#94a3b8' } },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(37,37,74,.6)' },
            ticks: { color: '#94a3b8', callback: function (v) { return v + ' ms'; } },
          },
        },
      },
    });
    _pushChart(c);
    return c;
  }

  /* ═══════════════════════════════════════════════════════
     §5 — SPAN WATERFALL
  ═══════════════════════════════════════════════════════ */

  /**
   * renderSpanWaterfall(containerId, traceStart, traceEnd, spans)
   * traceStart/traceEnd: unix timestamps (seconds, float)
   * spans: array of span objects with start_time, end_time, name, span_type
   */
  function renderSpanWaterfall(containerId, traceStart, traceEnd, spans) {
    const wrap = _container(containerId);
    if (!wrap) return;

    if (!spans || !spans.length) {
      wrap.innerHTML = '<div style="color:var(--c-t3);font-size:12px;padding:8px">No span data available.</div>';
      return;
    }

    const totalDur = (traceEnd - traceStart) || 1;
    const spanColors = { llm: '#c084fc', tool: '#38bdf8', retrieval: '#fbbf24', embed: '#818cf8', default: '#4ade80' };

    let h = '<div style="font-size:10px;color:var(--c-t3);margin-bottom:6px;display:flex;gap:12px">';
    Object.entries(spanColors).filter(function (e) { return e[0] !== 'default'; }).forEach(function (e) {
      h += '<span><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + e[1] + ';margin-right:4px"></span>' + e[0] + '</span>';
    });
    h += '</div><div style="position:relative">';

    spans.slice(0, 40).forEach(function (s) {
      const start = ((s.start_time - traceStart) / totalDur * 100).toFixed(2);
      const width = Math.max(0.5, ((s.end_time - s.start_time) / totalDur * 100)).toFixed(2);
      const dur   = s.end_time && s.start_time ? ((s.end_time - s.start_time) * 1000).toFixed(0) + 'ms' : '?';
      const color = spanColors[s.span_type] || spanColors.default;
      const title = `${s.name || 'span'} (${s.span_type || 'unknown'}) — ${dur}`;

      h += '<div style="display:grid;grid-template-columns:130px 1fr 55px;align-items:center;gap:8px;margin-bottom:5px">'
        + '<div style="font-size:11px;color:var(--c-t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + w.esc(title) + '">'
        + w.esc((s.name || 'span').slice(0, 20)) + '</div>'
        + '<div style="position:relative;height:10px;background:rgba(0,0,0,.3);border-radius:3px;overflow:hidden">'
        + '<div style="position:absolute;left:' + start + '%;width:' + width + '%;height:100%;background:' + color + ';border-radius:3px;min-width:3px" title="' + w.esc(title) + '"></div>'
        + '</div>'
        + '<div style="font-size:10px;color:var(--c-t3);text-align:right">' + dur + '</div>'
        + '</div>';
    });

    h += '</div>';
    if (spans.length > 40) {
      h += '<div style="font-size:11px;color:var(--c-t3);margin-top:4px">…and ' + (spans.length - 40) + ' more spans</div>';
    }
    wrap.innerHTML = h;
  }

  /* ═══════════════════════════════════════════════════════
     §6 — EXPORT MANAGER
  ═══════════════════════════════════════════════════════ */

  /**
   * ExportManager: { exportJSON, exportPDF, exportShareLink, renderButton }
   */
  var ExportManager = {
    exportJSON: function (filename, data) {
      try {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = filename + '-' + new Date().toISOString().slice(0, 10) + '.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        if (w.toast) w.toast('Downloaded ' + a.download, 'success');
      } catch (e) {
        if (w.toast) w.toast('Export failed: ' + e.message, 'error');
      }
    },

    exportPDF: function () {
      document.body.classList.add('print-mode');
      window.print();
      document.body.classList.remove('print-mode');
    },

    exportShareLink: function (tabName, params) {
      params = params || {};
      let hash = '#' + (tabName || 'security');
      const qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      if (qs) hash += '?' + qs;
      const url = window.location.origin + window.location.pathname + hash;
      if (w.copyText) {
        w.copyText(url);
      } else {
        navigator.clipboard.writeText(url).catch(function () {});
        if (w.toast) w.toast('Link copied to clipboard', 'success');
      }
    },

    /** Render a small export dropdown button into a container element */
    renderButton: function (containerEl, tabName, dataRef) {
      if (!containerEl) return;
      // Remove previous if any
      const old = containerEl.querySelector('.export-dropdown-wrap');
      if (old) old.remove();

      const wrap = document.createElement('div');
      wrap.className = 'export-dropdown-wrap';
      wrap.style.cssText = 'position:relative;display:inline-block';

      wrap.innerHTML =
        '<button class="btn btn-outline" style="font-size:11px;padding:4px 10px" aria-label="Export options" onclick="this.parentElement.querySelector(\'.export-menu\').classList.toggle(\'open\')">'
        + '<span aria-hidden="true">⬇</span> Export</button>'
        + '<div class="export-menu" style="display:none;position:absolute;right:0;top:calc(100% + 4px);background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r);padding:4px;z-index:220;min-width:140px;box-shadow:var(--sh)">'
        + '<button class="btn btn-ghost" style="width:100%;justify-content:flex-start;font-size:11px" onclick="ExportManager.exportJSON(\'' + (tabName || 'data') + '\',' + (dataRef || 'window._allData[window._tab]') + ');this.closest(\'.export-menu\').classList.remove(\'open\')">⬇ Download JSON</button>'
        + '<button class="btn btn-ghost" style="width:100%;justify-content:flex-start;font-size:11px" onclick="ExportManager.exportPDF();this.closest(\'.export-menu\').classList.remove(\'open\')">🖨 Export PDF</button>'
        + '<button class="btn btn-ghost" style="width:100%;justify-content:flex-start;font-size:11px" onclick="ExportManager.exportShareLink(\'' + (tabName || '') + '\');this.closest(\'.export-menu\').classList.remove(\'open\')">🔗 Copy Link</button>'
        + '</div>';

      // Close on outside click
      document.addEventListener('click', function handler(e) {
        if (!wrap.contains(e.target)) {
          const menu = wrap.querySelector('.export-menu');
          if (menu) menu.classList.remove('open');
        }
      });

      // Toggle CSS class → display
      const style = document.createElement('style');
      style.textContent = '.export-menu.open{display:block!important}';
      if (!document.getElementById('_exportMenuStyle')) {
        style.id = '_exportMenuStyle';
        document.head.appendChild(style);
      }

      containerEl.appendChild(wrap);
    },
  };

  /* ═══════════════════════════════════════════════════════
     §7 — CONFIG BUILDER MODAL
  ═══════════════════════════════════════════════════════ */

  /**
   * ConfigModal.open(tabName)  — opens the config builder
   * ConfigModal.close()        — removes the modal
   */
  var _configModal = null;

  var TAB_CONFIGS = {
    security: {
      title: 'New Security Scan',
      cmd: 'pyntrace scan',
      fields: [
        { key: 'fn',        label: 'Target function',  type: 'text',   placeholder: 'myapp:chatbot', required: true },
        { key: 'model',     label: 'Model',            type: 'select', options: ['gpt-4o','gpt-4o-mini','claude-3-5-sonnet','claude-3-haiku','gemini-1.5-pro'], placeholder: '(default)' },
        { key: 'attacks',   label: 'Attacks',          type: 'number', placeholder: '20', min: 1, max: 200 },
        { key: 'lang',      label: 'Languages',        type: 'text',   placeholder: 'en (comma-sep)' },
      ],
    },
    mcp: {
      title: 'New MCP Scan',
      cmd: 'pyntrace scan-mcp',
      fields: [
        { key: 'endpoint',  label: 'MCP endpoint URL', type: 'text',   placeholder: 'http://localhost:3000', required: true },
        { key: 'attacks',   label: 'Attacks',          type: 'number', placeholder: '20', min: 1, max: 100 },
      ],
    },
    eval: {
      title: 'New Eval Run',
      cmd: 'pyntrace eval run',
      fields: [
        { key: 'fn',        label: 'Function',         type: 'text',   placeholder: 'myapp:chatbot', required: true },
        { key: 'dataset',   label: 'Dataset',          type: 'text',   placeholder: 'dataset.csv' },
      ],
    },
    latency: {
      title: 'New Latency Test',
      cmd: 'pyntrace latency',
      fields: [
        { key: 'fn',        label: 'Function',         type: 'text',   placeholder: 'myapp:chatbot', required: true },
        { key: 'n',         label: 'Runs per prompt',  type: 'number', placeholder: '3', min: 1, max: 20 },
        { key: 'prompts',   label: 'Prompts file',     type: 'text',   placeholder: 'prompts.txt' },
      ],
    },
    compliance: {
      title: 'Generate Compliance Report',
      cmd: 'pyntrace compliance',
      fields: [
        { key: 'framework', label: 'Framework',        type: 'select', options: ['owasp_llm_top10','nist_ai_rmf','eu_ai_act','iso_42001'], placeholder: 'owasp_llm_top10' },
      ],
    },
  };

  function _buildCommand(tabName, values) {
    const cfg = TAB_CONFIGS[tabName];
    if (!cfg) return '';
    let cmd = cfg.cmd;
    const firstField = cfg.fields[0];
    if (firstField && values[firstField.key]) {
      cmd += ' ' + values[firstField.key];
    }
    cfg.fields.slice(1).forEach(function (f) {
      if (values[f.key]) cmd += ' --' + f.key + ' ' + values[f.key];
    });
    return cmd;
  }

  function _openConfigModal(tabName) {
    if (_configModal) _closeConfigModal();
    tabName = tabName || (w._tab || 'security');
    const cfg = TAB_CONFIGS[tabName] || TAB_CONFIGS.security;

    const backdrop = document.createElement('div');
    backdrop.id = '_configModalBackdrop';
    backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:205;display:flex;align-items:center;justify-content:center;padding:16px';
    backdrop.onclick = function (e) { if (e.target === backdrop) _closeConfigModal(); };

    let fieldsHtml = '';
    cfg.fields.forEach(function (f) {
      fieldsHtml += '<div style="margin-bottom:12px">'
        + '<label style="display:block;font-size:11px;color:var(--c-t3);margin-bottom:4px;text-transform:uppercase;letter-spacing:.4px">'
        + w.esc(f.label) + (f.required ? ' <span style="color:var(--c-danger)">*</span>' : '') + '</label>';
      if (f.type === 'select') {
        fieldsHtml += '<select id="_cfg_' + f.key + '" style="width:100%;background:var(--c-card);border:1px solid var(--c-border);color:var(--c-t1);border-radius:var(--r);padding:7px 10px;font-size:12px;outline:none">'
          + '<option value="">' + w.esc(f.placeholder || 'Select…') + '</option>'
          + f.options.map(function (o) { return '<option value="' + w.esc(o) + '">' + w.esc(o) + '</option>'; }).join('')
          + '</select>';
      } else {
        fieldsHtml += '<input id="_cfg_' + f.key + '" type="' + f.type + '" placeholder="' + w.esc(f.placeholder || '') + '"'
          + (f.min !== undefined ? ' min="' + f.min + '"' : '')
          + (f.max !== undefined ? ' max="' + f.max + '"' : '')
          + ' style="width:100%;background:var(--c-card);border:1px solid var(--c-border);color:var(--c-t1);border-radius:var(--r);padding:7px 10px;font-size:12px;outline:none" oninput="_updateConfigCmd()">';
      }
      fieldsHtml += '</div>';
    });

    backdrop.innerHTML =
      '<div style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-lg);width:100%;max-width:480px;box-shadow:var(--sh)">'
      + '<div style="display:flex;align-items:center;padding:14px 18px;border-bottom:1px solid var(--c-border)">'
      + '<span style="font-size:14px;font-weight:600;flex:1;color:var(--c-t1)">' + w.esc(cfg.title) + '</span>'
      + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:14px" onclick="_closeConfigModal()" aria-label="Close">✕</button>'
      + '</div>'
      + '<div style="padding:18px 18px 0">' + fieldsHtml + '</div>'
      + '<div style="padding:0 18px 14px">'
      + '<div style="font-size:10px;color:var(--c-t3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.4px">Generated command</div>'
      + '<div id="_configCmdBox" style="display:flex;align-items:center;gap:10px;background:rgba(0,0,0,.4);border:1px solid var(--c-border);border-radius:var(--r);padding:8px 12px;font-family:monospace;font-size:12px;color:var(--c-accent)">'
      + '<span id="_configCmdText">' + w.esc(cfg.cmd) + '</span>'
      + '<button class="copy-btn" style="margin-left:auto;flex-shrink:0" onclick="copyText(document.getElementById(\'_configCmdText\').textContent)">Copy</button>'
      + '</div>'
      + '</div>'
      + '<div style="padding:0 18px 18px;display:flex;justify-content:flex-end;gap:8px">'
      + '<button class="btn btn-ghost" onclick="_closeConfigModal()">Cancel</button>'
      + '<button class="btn btn-primary" onclick="_closeConfigModal();if(w.toast)w.toast(\'Command copied — run it in your terminal\',\'info\')" disabled id="_configRunBtn">Copy & Close</button>'
      + '</div>'
      + '</div>';

    document.body.appendChild(backdrop);
    _configModal = backdrop;

    // Wire up select fields too
    cfg.fields.forEach(function (f) {
      const el = document.getElementById('_cfg_' + f.key);
      if (el && f.type === 'select') {
        el.addEventListener('change', w._updateConfigCmd);
      }
    });

    // Initial update
    w._updateConfigCmd();

    // Focus first input
    const first = backdrop.querySelector('input, select');
    if (first) setTimeout(function () { first.focus(); }, 50);
  }

  function _closeConfigModal() {
    if (_configModal) {
      _configModal.remove();
      _configModal = null;
    }
  }

  // Called by oninput on config form fields
  function _updateConfigCmd() {
    const tabName = w._tab || 'security';
    const cfg = TAB_CONFIGS[tabName] || TAB_CONFIGS.security;
    const values = {};
    cfg.fields.forEach(function (f) {
      const el = document.getElementById('_cfg_' + f.key);
      if (el) values[f.key] = el.value.trim();
    });
    const cmd = _buildCommand(tabName, values);
    const cmdEl = document.getElementById('_configCmdText');
    if (cmdEl) cmdEl.textContent = cmd || cfg.cmd;
    const runBtn = document.getElementById('_configRunBtn');
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.onclick = function () {
        if (w.copyText) w.copyText(cmd || cfg.cmd);
        _closeConfigModal();
      };
    }
  }

  /* ═══════════════════════════════════════════════════════
     §8 — PRINT-MODE CSS (injected once)
  ═══════════════════════════════════════════════════════ */
  (function _injectPrintStyles() {
    if (document.getElementById('_printModeStyle')) return;
    const s = document.createElement('style');
    s.id = '_printModeStyle';
    s.textContent = `
      @media print {
        .app-sidebar, .app-header, .detail-panel, .overlay,
        .toast-container, .search-modal-backdrop { display: none !important; }
        body { overflow: auto; display: block; }
        .app-main { grid-area: unset !important; overflow: visible; }
        .main-content { padding: 0; max-width: 100%; }
      }
      body.print-mode .app-sidebar,
      body.print-mode .app-header,
      body.print-mode .detail-panel,
      body.print-mode .toast-container { display: none !important; }
      body.print-mode { overflow: auto; display: block; }
      body.print-mode .app-main { grid-area: unset !important; overflow: visible; }
    `;
    document.head.appendChild(s);
  })();

  /* ═══════════════════════════════════════════════════════
     §9 — PUBLIC API
  ═══════════════════════════════════════════════════════ */
  w.renderMultilingualHeatmap = renderMultilingualHeatmap;
  w.renderSwarmTopology       = renderSwarmTopology;
  w.makeBoxPlot               = makeBoxPlot;
  w.renderSpanWaterfall       = renderSpanWaterfall;
  w.ExportManager             = ExportManager;
  w.ConfigModal               = { open: _openConfigModal, close: _closeConfigModal };
  w._updateConfigCmd          = _updateConfigCmd;
  w._closeConfigModal         = _closeConfigModal;

})(window);
