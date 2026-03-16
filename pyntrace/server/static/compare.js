/**
 * compare.js — Scan Comparison Module (Phase 2)
 * Exposes: window.CompareState, window.CompareModal, window.injectCompareCheckboxes
 */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ §1
   * CompareState — tracks which scans are selected for comparison
   * ------------------------------------------------------------------ */
  const CompareState = {
    _selected: [],        // array of scan-row objects
    _bar: null,           // floating compare bar DOM element
    _maxCompare: 4,

    add(row) {
      if (this._selected.find(r => r.id === row.id)) return;
      if (this._selected.length >= this._maxCompare) {
        _toast(`Max ${this._maxCompare} scans for comparison`, 'warn');
        return;
      }
      this._selected.push(row);
      this._render();
    },

    remove(id) {
      this._selected = this._selected.filter(r => r.id !== id);
      this._render();
      // uncheck the checkbox in the table
      const cb = document.querySelector(`[data-compare-id="${id}"]`);
      if (cb) cb.checked = false;
    },

    clear() {
      this._selected = [];
      this._render();
      document.querySelectorAll('[data-compare-id]').forEach(cb => (cb.checked = false));
    },

    get count() { return this._selected.length; },

    _render() {
      if (!this._bar) this._bar = _buildBar();
      if (this._selected.length === 0) {
        this._bar.hidden = true;
        return;
      }
      this._bar.hidden = false;
      const chips = this._bar.querySelector('.cmp-chips');
      chips.innerHTML = this._selected
        .map(r => `<span class="cmp-chip">${_esc(r.model || r.id)}
            <button class="cmp-chip-rm" aria-label="Remove ${_esc(r.model || r.id)}"
              onclick="CompareState.remove(${r.id})">×</button></span>`)
        .join('');
      const btn = this._bar.querySelector('.cmp-open-btn');
      btn.textContent = `Compare (${this._selected.length})`;
      btn.disabled = this._selected.length < 2;
    },
  };

  function _buildBar() {
    const bar = document.createElement('div');
    bar.className = 'cmp-bar glass';
    bar.id = 'cmpBar';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Scan comparison selection');
    bar.innerHTML = `
      <span class="cmp-bar-label">Compare:</span>
      <div class="cmp-chips" role="list" aria-label="Selected scans"></div>
      <button class="cmp-open-btn btn-accent" onclick="CompareModal.open()" disabled>Compare (0)</button>
      <button class="cmp-clear-btn btn-ghost" onclick="CompareState.clear()">Clear</button>`;
    document.body.appendChild(bar);
    _injectBarCSS();
    return bar;
  }

  /* ------------------------------------------------------------------ §2
   * injectCompareCheckboxes — adds checkboxes to an existing data table
   * Call after buildTable() for the security tab
   * ------------------------------------------------------------------ */
  function injectCompareCheckboxes(tableEl, rows) {
    if (!tableEl) return;
    const thead = tableEl.querySelector('thead tr');
    const tbody = tableEl.querySelector('tbody');
    if (!thead || !tbody) return;

    // Header checkbox column
    const th = document.createElement('th');
    th.scope = 'col';
    th.innerHTML = '<span class="sr-only">Select for comparison</span>';
    thead.insertBefore(th, thead.firstChild);

    // Body checkboxes
    const trs = tbody.querySelectorAll('tr');
    trs.forEach((tr, i) => {
      const row = rows[i];
      if (!row) return;
      const td = document.createElement('td');
      td.innerHTML = `<label class="cmp-checkbox-label">
        <input type="checkbox" class="cmp-checkbox" data-compare-id="${row.id}"
          aria-label="Select scan ${_esc(row.model || row.id)} for comparison"
          onchange="CompareState[this.checked?'add':'remove'](${JSON.stringify(JSON.stringify(row)).slice(1,-1)})">
      </label>`;
      // Store row as data attribute for safety
      const cb = td.querySelector('input');
      cb._scanRow = row;
      cb.onchange = function () {
        if (this.checked) CompareState.add(row);
        else CompareState.remove(row.id);
      };
      tr.insertBefore(td, tr.firstChild);
    });
  }

  /* ------------------------------------------------------------------ §3
   * CompareModal — side-by-side scan diff + radar charts
   * ------------------------------------------------------------------ */
  const CompareModal = {
    _el: null,
    _charts: [],

    open() {
      if (CompareState.count < 2) {
        _toast('Select at least 2 scans to compare', 'warn');
        return;
      }
      if (!this._el) this._el = _buildModal();
      _renderModalContent(this._el, CompareState._selected, this._charts);
      this._el.hidden = false;
      document.body.classList.add('modal-open');
      this._el.querySelector('.cmp-modal-close').focus();
    },

    close() {
      if (this._el) this._el.hidden = true;
      document.body.classList.remove('modal-open');
      this._charts.forEach(c => { try { c.destroy(); } catch (_) {} });
      this._charts = [];
    },
  };

  function _buildModal() {
    const m = document.createElement('div');
    m.className = 'cmp-modal-backdrop';
    m.id = 'cmpModal';
    m.setAttribute('role', 'dialog');
    m.setAttribute('aria-modal', 'true');
    m.setAttribute('aria-label', 'Scan comparison');
    m.hidden = true;
    m.innerHTML = `
      <div class="cmp-modal">
        <div class="cmp-modal-header">
          <h2 class="cmp-modal-title">Compare Scans</h2>
          <div class="cmp-modal-actions">
            <button class="btn-ghost btn-sm" onclick="ExportManager&&ExportManager.exportJSON(CompareState._selected,'compare')">Export JSON</button>
            <button class="cmp-modal-close btn-ghost btn-icon" aria-label="Close comparison modal" onclick="CompareModal.close()">✕</button>
          </div>
        </div>
        <div class="cmp-modal-body" id="cmpModalBody"></div>
      </div>`;
    // Close on backdrop click
    m.addEventListener('click', e => { if (e.target === m) CompareModal.close(); });
    // Close on Escape
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !m.hidden) CompareModal.close(); });
    document.body.appendChild(m);
    _injectModalCSS();
    return m;
  }

  function _renderModalContent(modal, scans, chartRefs) {
    const body = modal.querySelector('#cmpModalBody');
    const cols = scans.length;

    // --- stat rows ---
    const STATS = [
      { key: 'model',            label: 'Model',           fmt: v => _esc(v || '—') },
      { key: 'vulnerability_rate', label: 'Vuln Rate',     fmt: v => v != null ? `${(v*100).toFixed(1)}%` : '—', better: 'min' },
      { key: 'total_attacks',    label: 'Attacks',          fmt: v => v ?? '—' },
      { key: 'total_vulnerabilities', label: 'Vulnerabilities', fmt: v => v ?? '—', better: 'min' },
      { key: 'total_cost',       label: 'Total Cost',       fmt: v => v != null ? `$${v.toFixed(4)}` : '—', better: 'min' },
      { key: 'avg_latency_ms',   label: 'Avg Latency',      fmt: v => v != null ? `${Math.round(v)}ms` : '—', better: 'min' },
      { key: 'model_provider',   label: 'Provider',         fmt: v => _esc(v || '—') },
      { key: 'status',           label: 'Status',           fmt: v => _esc(v || '—') },
    ];

    // Determine best values for numeric comparisons
    const bests = {};
    STATS.forEach(s => {
      if (!s.better) return;
      const vals = scans.map(sc => sc[s.key]).filter(v => v != null);
      if (!vals.length) return;
      bests[s.key] = s.better === 'min' ? Math.min(...vals) : Math.max(...vals);
    });

    let statsHtml = `
      <div class="cmp-grid" style="--cmp-cols:${cols}">
        <div class="cmp-grid-header">
          <div class="cmp-label-col"></div>
          ${scans.map((s, i) => `
            <div class="cmp-scan-header">
              <span class="cmp-scan-title">${_esc(s.model || `Scan ${i+1}`)}</span>
              <span class="cmp-scan-id">ID: ${s.id}</span>
            </div>`).join('')}
        </div>`;

    STATS.forEach(s => {
      statsHtml += `<div class="cmp-row">
        <div class="cmp-label-col">${s.label}</div>
        ${scans.map(sc => {
          const val = sc[s.key];
          const rendered = s.fmt(val);
          let badge = '';
          if (s.better && val != null && bests[s.key] != null) {
            if (val === bests[s.key]) badge = ' <span class="cmp-best" aria-label="Best value">✓ best</span>';
          }
          return `<div class="cmp-cell">${rendered}${badge}</div>`;
        }).join('')}
      </div>`;
    });
    statsHtml += '</div>';

    // --- radar chart area ---
    const radarIds = scans.map((_, i) => `cmpRadar${i}`);
    const radarHtml = `
      <div class="cmp-charts-row">
        <h3 class="cmp-section-title">Attack Exposure — Side by Side</h3>
        <div class="cmp-radars" style="--cmp-cols:${Math.min(cols, 2)}">
          ${scans.map((s, i) => `
            <div class="cmp-radar-wrap">
              <div class="cmp-radar-title">${_esc(s.model || `Scan ${i+1}`)}</div>
              <canvas id="${radarIds[i]}" width="280" height="280" aria-label="Attack radar for ${_esc(s.model || `Scan ${i+1}`)}"></canvas>
            </div>`).join('')}
        </div>
      </div>`;

    // --- vulnerability breakdown table ---
    const breakdownHtml = _buildBreakdownTable(scans);

    body.innerHTML = statsHtml + radarHtml + breakdownHtml;

    // Draw radars after DOM insertion
    setTimeout(() => {
      scans.forEach((scan, i) => {
        const canvas = document.getElementById(radarIds[i]);
        if (!canvas) return;
        const chart = _drawCompareRadar(canvas, scan);
        if (chart) chartRefs.push(chart);
      });
    }, 50);
  }

  function _buildBreakdownTable(scans) {
    // Collect all plugin names across all scans
    const allPlugins = new Set();
    scans.forEach(s => {
      if (!s.results_json) return;
      let results;
      try { results = typeof s.results_json === 'string' ? JSON.parse(s.results_json) : s.results_json; } catch (_) { return; }
      if (Array.isArray(results)) results.forEach(r => r.plugin && allPlugins.add(r.plugin));
    });
    if (!allPlugins.size) return '';

    const plugins = [...allPlugins].sort();
    let html = `
      <div class="cmp-breakdown">
        <h3 class="cmp-section-title">Plugin Breakdown</h3>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Plugin breakdown comparison table">
          <table class="data-table" aria-label="Plugin breakdown">
            <thead><tr>
              <th scope="col">Plugin</th>
              ${scans.map(s => `<th scope="col">${_esc(s.model || s.id)}</th>`).join('')}
            </tr></thead>
            <tbody>`;
    plugins.forEach(plugin => {
      html += `<tr><td>${_esc(plugin)}</td>`;
      scans.forEach(s => {
        let results = [];
        try { results = typeof s.results_json === 'string' ? JSON.parse(s.results_json) : (s.results_json || []); } catch (_) {}
        const matching = results.filter(r => r.plugin === plugin);
        const vuln = matching.filter(r => r.vulnerable).length;
        const total = matching.length;
        const rate = total ? vuln / total : null;
        const color = rate == null ? '' : rate > 0.15 ? 'var(--c-danger)' : rate > 0.05 ? 'var(--c-warn)' : 'var(--c-success)';
        html += `<td style="color:${color}">${rate != null ? `${(rate*100).toFixed(0)}% (${vuln}/${total})` : '—'}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
    return html;
  }

  function _drawCompareRadar(canvas, scan) {
    if (!window.Chart) return null;
    const PLUGINS = ['Injection','Jailbreak','PII','Leakage','MultiAgent','Toolchain'];
    let results = [];
    try { results = typeof scan.results_json === 'string' ? JSON.parse(scan.results_json) : (scan.results_json || []); } catch (_) {}

    const data = PLUGINS.map(p => {
      const key = p.toLowerCase();
      const matching = results.filter(r =>
        r.plugin && r.plugin.toLowerCase().includes(key)
      );
      if (!matching.length) return 0;
      return Math.round((matching.filter(r => r.vulnerable).length / matching.length) * 100);
    });

    return new window.Chart(canvas, {
      type: 'radar',
      data: {
        labels: PLUGINS,
        datasets: [{
          label: scan.model || `Scan ${scan.id}`,
          data,
          backgroundColor: 'rgba(192,132,252,0.15)',
          borderColor: '#c084fc',
          borderWidth: 2,
          pointBackgroundColor: '#c084fc',
          pointRadius: 3,
        }],
      },
      options: {
        responsive: false,
        plugins: { legend: { display: false } },
        scales: {
          r: {
            min: 0, max: 100,
            ticks: { color: '#859ab5', stepSize: 25, font: { size: 10 } },
            grid: { color: '#25254a' },
            pointLabels: { color: '#b8c5d6', font: { size: 11 } },
            angleLines: { color: '#25254a' },
          },
        },
      },
    });
  }

  /* ------------------------------------------------------------------ §4
   * CSS injection helpers
   * ------------------------------------------------------------------ */
  function _injectBarCSS() {
    if (document.getElementById('cmp-bar-css')) return;
    const s = document.createElement('style');
    s.id = 'cmp-bar-css';
    s.textContent = `
      .cmp-bar {
        position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
        display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
        padding: 0.75rem 1.25rem; border-radius: 12px;
        border: 1px solid var(--c-border); z-index: 900;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        max-width: min(90vw, 800px);
      }
      .cmp-bar[hidden] { display: none !important; }
      .cmp-bar-label { font-size: 0.8rem; color: var(--c-t2); font-weight: 600; white-space: nowrap; }
      .cmp-chips { display: flex; gap: 0.5rem; flex-wrap: wrap; flex: 1; }
      .cmp-chip {
        display: inline-flex; align-items: center; gap: 0.25rem;
        padding: 0.2rem 0.6rem; border-radius: 20px;
        background: rgba(192,132,252,0.15); border: 1px solid rgba(192,132,252,0.3);
        font-size: 0.8rem; color: var(--c-t1);
      }
      .cmp-chip-rm {
        background: none; border: none; cursor: pointer;
        color: var(--c-t3); padding: 0; line-height: 1; font-size: 1rem;
      }
      .cmp-chip-rm:hover { color: var(--c-danger); }
      .cmp-open-btn {
        padding: 0.45rem 1.1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
        background: var(--c-accent); color: #000; border: none; cursor: pointer;
        transition: opacity .2s;
      }
      .cmp-open-btn:disabled { opacity: 0.4; cursor: default; }
      .cmp-open-btn:not(:disabled):hover { opacity: 0.85; }
      .cmp-clear-btn {
        padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.8rem;
        background: transparent; color: var(--c-t3); border: 1px solid var(--c-border); cursor: pointer;
      }
      .cmp-clear-btn:hover { color: var(--c-danger); border-color: var(--c-danger); }
      .cmp-checkbox-label { display: flex; align-items: center; justify-content: center; cursor: pointer; }
      .cmp-checkbox { width: 15px; height: 15px; accent-color: var(--c-accent); cursor: pointer; }
    `;
    document.head.appendChild(s);
  }

  function _injectModalCSS() {
    if (document.getElementById('cmp-modal-css')) return;
    const s = document.createElement('style');
    s.id = 'cmp-modal-css';
    s.textContent = `
      .cmp-modal-backdrop {
        position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
        display: flex; align-items: center; justify-content: center;
        z-index: 1000; padding: 1rem;
      }
      .cmp-modal-backdrop[hidden] { display: none !important; }
      .cmp-modal {
        background: var(--c-surface); border: 1px solid var(--c-border);
        border-radius: 16px; max-width: min(1000px, 95vw); width: 100%;
        max-height: 85vh; display: flex; flex-direction: column;
        box-shadow: 0 24px 64px rgba(0,0,0,0.6);
      }
      .cmp-modal-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--c-border);
      }
      .cmp-modal-title { font-size: 1.1rem; font-weight: 700; color: var(--c-t1); margin: 0; }
      .cmp-modal-actions { display: flex; gap: 0.5rem; align-items: center; }
      .cmp-modal-body { overflow-y: auto; padding: 1.5rem; flex: 1; }
      .cmp-modal-close {
        width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
        background: transparent; border: 1px solid var(--c-border); border-radius: 8px;
        color: var(--c-t2); cursor: pointer; font-size: 1rem;
      }
      .cmp-modal-close:hover { background: var(--c-card); color: var(--c-danger); }

      /* Grid layout */
      .cmp-grid { border: 1px solid var(--c-border); border-radius: 10px; overflow: hidden; margin-bottom: 1.5rem; }
      .cmp-grid-header, .cmp-row {
        display: grid;
        grid-template-columns: 140px repeat(var(--cmp-cols), 1fr);
      }
      .cmp-grid-header {
        background: var(--c-card); padding: 0.75rem 0;
        border-bottom: 1px solid var(--c-border);
      }
      .cmp-row { border-bottom: 1px solid var(--c-border); }
      .cmp-row:last-child { border-bottom: none; }
      .cmp-row:hover { background: rgba(255,255,255,0.02); }
      .cmp-label-col { padding: 0.65rem 1rem; color: var(--c-t3); font-size: 0.8rem; font-weight: 600; }
      .cmp-scan-header { padding: 0.65rem 1rem; display: flex; flex-direction: column; gap: 0.15rem; }
      .cmp-scan-title { color: var(--c-t1); font-weight: 700; font-size: 0.9rem; }
      .cmp-scan-id { color: var(--c-t3); font-size: 0.75rem; }
      .cmp-cell { padding: 0.65rem 1rem; color: var(--c-t1); font-size: 0.85rem; }
      .cmp-best { color: var(--c-success); font-size: 0.75rem; font-weight: 600; margin-left: 0.3rem; }

      /* Radar charts */
      .cmp-charts-row { margin-bottom: 1.5rem; }
      .cmp-section-title { color: var(--c-t2); font-size: 0.85rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: .08em; margin: 0 0 1rem; }
      .cmp-radars {
        display: grid;
        grid-template-columns: repeat(var(--cmp-cols), 1fr);
        gap: 1.5rem;
      }
      .cmp-radar-wrap { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
      .cmp-radar-title { color: var(--c-t1); font-size: 0.85rem; font-weight: 600; }

      /* Breakdown table */
      .cmp-breakdown { margin-bottom: 1rem; }

      /* Modal open body lock */
      body.modal-open { overflow: hidden; }

      @media (max-width: 600px) {
        .cmp-radars { grid-template-columns: 1fr !important; }
        .cmp-grid-header, .cmp-row {
          grid-template-columns: 100px repeat(var(--cmp-cols), 1fr);
        }
      }
    `;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ §5
   * Utilities (local copies — independent of index.html globals)
   * ------------------------------------------------------------------ */
  function _esc(str) {
    return String(str ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function _toast(msg, type) {
    if (typeof window.toast === 'function') { window.toast(msg, type); return; }
    console.warn('[compare]', msg);
  }

  /* ------------------------------------------------------------------ §6
   * Public exports
   * ------------------------------------------------------------------ */
  window.CompareState = CompareState;
  window.CompareModal = CompareModal;
  window.injectCompareCheckboxes = injectCompareCheckboxes;

})();
