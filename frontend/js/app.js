// DepBridge Application Logic & Interactive Workflows

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

let currentActiveTab = 'findings';
let currentCodemodPkg = 'appdirs';
let currentDiffFileIndex = 0;
let currentFilter = 'all';
let currentManifest = 'all';

function initApp() {
  renderFindingsTable();
  renderTopologyCanvas();
  setupKeyboardShortcuts();
  setupFilterHandlers();
}

// ==========================================
// Tab Switching
// ==========================================
function switchTab(tabId) {
  const views = ['findings', 'codemod', 'verification', 'workspace', 'capsule'];
  views.forEach(v => {
    const el = document.getElementById('view-' + v);
    if (el) el.classList.add('hidden');
    
    const btn = document.getElementById('tab-' + v);
    if (btn) {
      btn.classList.remove('text-[#EA580C]', 'font-semibold', 'border-[#EA580C]');
      btn.classList.add('text-zinc-500', 'border-transparent');
    }
  });

  const activeView = document.getElementById('view-' + tabId);
  if (activeView) activeView.classList.remove('hidden');

  const activeBtn = document.getElementById('tab-' + tabId);
  if (activeBtn) {
    activeBtn.classList.add('text-[#EA580C]', 'font-semibold', 'border-[#EA580C]');
    activeBtn.classList.remove('text-zinc-500', 'border-transparent');
  }

  currentActiveTab = tabId;
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (tabId === 'workspace') {
    setTimeout(renderTopologyCanvas, 50);
  } else if (tabId === 'codemod') {
    renderCodemodView(currentCodemodPkg);
  }
}

// ==========================================
// Findings Table Rendering & Filtering
// ==========================================
function renderFindingsTable() {
  const tbody = document.getElementById('findingsTableBody');
  if (!tbody) return;

  const data = window.DepBridgeData.packages;
  const query = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();

  let filtered = data.filter(pkg => {
    // Filter by type
    if (currentFilter === 'critical' && pkg.severity !== 'critical') return false;
    if (currentFilter === 'migrations' && !pkg.codemodAvailable) return false;
    if (currentFilter === 'healthy' && pkg.severity !== 'healthy') return false;

    // Filter by manifest
    if (currentManifest !== 'all' && pkg.manifestFile !== currentManifest) return false;

    // Search query
    if (query) {
      const matchName = pkg.name.toLowerCase().includes(query);
      const matchRec = pkg.recommendedCandidate.toLowerCase().includes(query);
      const matchManifest = pkg.manifest.toLowerCase().includes(query);
      const matchDesc = pkg.riskDescription.toLowerCase().includes(query);
      const matchEvidence = pkg.astEvidence.toLowerCase().includes(query);
      if (!matchName && !matchRec && !matchManifest && !matchDesc && !matchEvidence) {
        return false;
      }
    }

    return true;
  });

  document.getElementById('filteredCountLabel').innerText = 
    `Showing ${filtered.length} of ${window.DepBridgeData.repository.stats.totalPackages} analyzed dependencies`;

  tbody.innerHTML = filtered.map(pkg => {
    const isCritical = pkg.severity === 'critical';
    const isMedium = pkg.severity === 'medium';
    const isHealthy = pkg.severity === 'healthy';

    let severityBadge = '';
    if (isCritical) {
      severityBadge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-white border border-red-200 text-red-700 shadow-2xs">
        <span class="w-1.5 h-1.5 rounded-full bg-red-600 mr-1"></span> ${pkg.riskTitle}
      </span>`;
    } else if (isMedium) {
      severityBadge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-sans font-semibold bg-white border border-amber-200 text-amber-700">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1"></span> ${pkg.riskTitle}
      </span>`;
    } else {
      severityBadge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-sans font-medium bg-zinc-50 border border-zinc-200 text-zinc-700">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1"></span> ${pkg.riskTitle}
      </span>`;
    }

    let verificationBadge = '';
    if (pkg.verificationType === 'success') {
      verificationBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-sans font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
        ${pkg.verificationStatus}
      </span>`;
    } else if (pkg.verificationType === 'warning') {
      verificationBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-amber-50 text-amber-800 border border-amber-200">
        ${pkg.verificationStatus}
      </span>`;
    } else {
      verificationBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-sans font-medium bg-zinc-100 text-zinc-600">
        ${pkg.verificationStatus}
      </span>`;
    }

    const rowHighlight = isCritical ? 'bg-orange-50/20 hover:bg-orange-50/40 border-l-2 border-l-[#EA580C]' : 'hover:bg-zinc-50';

    return `
      <tr class="${rowHighlight} transition-colors table-row-item">
        <td class="py-2.5 px-3">
          <div class="flex items-center space-x-1.5">
            <span class="font-bold text-[#09090B] text-xs">${pkg.name}</span>
            <span class="text-zinc-500 text-[11px] font-mono">${pkg.constraint}</span>
            ${pkg.tag === 'CVE/EOL' ? `<span class="text-[9px] bg-red-100 text-red-700 px-1 rounded border border-red-200 font-sans font-bold">CVE/EOL</span>` : ''}
            ${pkg.tag === 'INCOMPATIBLE' ? `<span class="text-[9px] bg-red-100 text-red-700 px-1 rounded border border-red-200 font-sans font-bold">PY3.12+</span>` : ''}
            ${pkg.tag === 'V1→V2' ? `<span class="text-[9px] bg-amber-100 text-amber-800 px-1 rounded border border-amber-200 font-sans font-bold">V1→V2</span>` : ''}
          </div>
        </td>
        <td class="py-2.5 px-3 text-zinc-600 text-[11px]">
          <span class="bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200 font-mono">${pkg.manifest}</span>
        </td>
        <td class="py-2.5 px-3">
          ${severityBadge}
          <div class="text-[10px] text-zinc-500 font-sans mt-0.5 max-w-xs truncate">${pkg.riskDescription}</div>
        </td>
        <td class="py-2.5 px-3 text-zinc-700 cursor-pointer group" onclick="openInspectorDrawer('${pkg.id}')">
          <div class="font-sans font-medium text-zinc-900 group-hover:text-[#EA580C] flex items-center gap-1">
            <span>${pkg.astEvidence}</span>
            <span class="text-[10px] text-zinc-400 group-hover:text-[#EA580C]">↗</span>
          </div>
          <div class="text-[10px] text-zinc-500 truncate mt-0.5 font-mono">${pkg.callSitesSummary}</div>
        </td>
        <td class="py-2.5 px-3">
          <div class="font-bold text-zinc-900 flex items-center space-x-1">
            <span class="${pkg.recommendedCandidate !== 'None needed' ? 'text-[#EA580C]' : 'text-zinc-500'} font-mono">${pkg.recommendedCandidate}</span>
            <span class="text-zinc-500 text-[11px] font-mono">${pkg.recommendedConstraint}</span>
          </div>
          <div class="text-[10px] ${pkg.recommendedCandidate !== 'None needed' ? 'text-emerald-600' : 'text-zinc-400'} font-sans">${pkg.candidateNote}</div>
        </td>
        <td class="py-2.5 px-3">
          ${verificationBadge}
        </td>
        <td class="py-2.5 px-3 text-right">
          <div class="flex items-center justify-end space-x-1.5">
            <button onclick="openInspectorDrawer('${pkg.id}')" class="px-2 py-1 bg-white border border-zinc-300 hover:bg-zinc-50 text-zinc-700 rounded-[4px] text-[11px] font-sans font-medium transition-colors">
              Inspect
            </button>
            ${pkg.codemodAvailable ? `
              <button onclick="openCodemodView('${pkg.id}')" class="px-2.5 py-1 bg-[#EA580C] hover:bg-[#C2410C] text-white rounded-[4px] text-[11px] font-sans font-semibold transition-colors shadow-xs">
                Codemod →
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function setFilter(type) {
  currentFilter = type;
  const pills = ['all', 'critical', 'migrations', 'healthy'];
  pills.forEach(p => {
    const el = document.getElementById('filter-' + p);
    if (el) {
      el.classList.remove('bg-zinc-900', 'text-white');
      el.classList.add('bg-zinc-100', 'text-zinc-700');
    }
  });

  const current = document.getElementById('filter-' + type);
  if (current) {
    current.classList.add('bg-zinc-900', 'text-white');
    current.classList.remove('bg-zinc-100', 'text-zinc-700');
  }

  renderFindingsTable();
}

function setManifestFilter(manifest) {
  currentManifest = manifest;
  const btn = document.getElementById('manifestFilterBtn');
  if (btn) {
    btn.innerText = manifest === 'all' ? 'Manifest: All' : manifest;
  }
  renderFindingsTable();
}

function filterRows() {
  renderFindingsTable();
}

// ==========================================
// AST Inspector Drawer
// ==========================================
function openInspectorDrawer(pkgId) {
  const pkg = window.DepBridgeData.packages.find(p => p.id === pkgId);
  if (!pkg) return;

  const drawer = document.getElementById('inspectorDrawer');
  const overlay = document.getElementById('drawerOverlay');

  document.getElementById('drawerPkgName').innerText = pkg.name;
  document.getElementById('drawerPkgConstraint').innerText = pkg.constraint;
  document.getElementById('drawerRiskTitle').innerText = pkg.riskTitle;
  document.getElementById('drawerRiskDesc').innerText = pkg.riskDescription;
  document.getElementById('drawerManifestLoc').innerText = pkg.manifest;
  document.getElementById('drawerCandidate').innerText = `${pkg.recommendedCandidate} (${pkg.recommendedConstraint})`;

  // Render Call Sites
  const callSitesContainer = document.getElementById('drawerCallSites');
  if (pkg.callSites && pkg.callSites.length > 0) {
    callSitesContainer.innerHTML = pkg.callSites.map(cs => `
      <div class="p-2.5 rounded bg-zinc-50 border border-zinc-200 font-mono text-xs space-y-1">
        <div class="flex items-center justify-between text-[11px] text-zinc-500">
          <span class="font-semibold text-zinc-800">${cs.file}:${cs.line}</span>
          <span class="bg-zinc-200/80 px-1.5 py-0.2 rounded text-[10px] text-zinc-700">${cs.node}</span>
        </div>
        <div class="p-1.5 bg-[#090D16] text-zinc-200 rounded text-[11px] overflow-x-auto">
          <code>${escapeHtml(cs.code)}</code>
        </div>
        <div class="text-[10px] text-zinc-500 font-sans">${cs.context}</div>
      </div>
    `).join('');
  } else {
    callSitesContainer.innerHTML = `<div class="p-3 text-zinc-400 font-mono text-xs">No direct AST call sites detected.</div>`;
  }

  const codemodBtn = document.getElementById('drawerCodemodBtn');
  if (pkg.codemodAvailable) {
    codemodBtn.style.display = 'block';
    codemodBtn.onclick = () => {
      closeInspectorDrawer();
      openCodemodView(pkg.id);
    };
  } else {
    codemodBtn.style.display = 'none';
  }

  overlay.classList.remove('hidden');
  drawer.classList.remove('hidden');
  drawer.classList.add('animate-drawer');
}

function closeInspectorDrawer() {
  const drawer = document.getElementById('inspectorDrawer');
  const overlay = document.getElementById('drawerOverlay');
  if (drawer) drawer.classList.add('hidden');
  if (overlay) overlay.classList.add('hidden');
}

// ==========================================
// Codemod View
// ==========================================
function openCodemodView(pkgId) {
  currentCodemodPkg = pkgId;
  currentDiffFileIndex = 0;
  switchTab('codemod');
}

function renderCodemodView(pkgId) {
  const codemodData = window.DepBridgeData.codemods[pkgId] || window.DepBridgeData.codemods['appdirs'];
  if (!codemodData) return;

  document.getElementById('codemodTitle').innerText = codemodData.title;
  document.getElementById('originalPkgBadge').innerText = codemodData.originalSpec.package;
  document.getElementById('originalManifest').innerText = codemodData.originalSpec.manifest;
  document.getElementById('originalConstraint').innerText = codemodData.originalSpec.constraint;
  document.getElementById('originalIssueProfile').innerText = codemodData.originalSpec.issueProfile;

  document.getElementById('proposedPkgBadge').innerText = codemodData.proposedSpec.package;
  document.getElementById('proposedConstraint').innerText = codemodData.proposedSpec.targetConstraint;
  document.getElementById('proposedParity').innerText = codemodData.proposedSpec.apiParity;
  document.getElementById('proposedRationale').innerText = codemodData.proposedSpec.runtimeRationale;

  // Render Checklist
  const checklistContainer = document.getElementById('codemodChecklist');
  checklistContainer.innerHTML = codemodData.checklist.map((item, idx) => `
    <label class="flex items-start space-x-2 p-2 rounded bg-zinc-50 border border-zinc-200 text-xs font-mono cursor-pointer hover:bg-zinc-100/70 transition-colors">
      <input type="checkbox" id="check-${item.id}" ${item.checked ? 'checked' : ''} onchange="updateChecklistCount()" class="mt-0.5 accent-[#EA580C] rounded-[2px]" />
      <div>
        <div class="text-zinc-900 font-medium">${item.label}</div>
        <div class="text-zinc-400 text-[10px]">${item.desc}</div>
      </div>
    </label>
  `).join('');
  updateChecklistCount();

  // Render Diff File Tabs
  renderDiffFiles(codemodData.files);
}

function updateChecklistCount() {
  const checkboxes = document.querySelectorAll('#codemodChecklist input[type="checkbox"]');
  const total = checkboxes.length;
  let checked = 0;
  checkboxes.forEach(cb => { if (cb.checked) checked++; });
  const label = document.getElementById('checklistStatusLabel');
  if (label) {
    label.innerText = `${checked} of ${total} staged`;
  }
}

function renderDiffFiles(files) {
  const tabContainer = document.getElementById('diffFileTabs');
  if (!files || files.length === 0) return;

  tabContainer.innerHTML = files.map((f, idx) => `
    <button onclick="switchDiffFile(${idx})" class="font-mono text-[11px] px-2 py-0.5 rounded-[4px] font-semibold transition-colors ${idx === currentDiffFileIndex ? 'bg-white border border-zinc-300 text-zinc-900 shadow-2xs' : 'text-zinc-500 hover:text-zinc-800'}">
      ${f.name}
    </button>
  `).join('');

  const currentFile = files[currentDiffFileIndex] || files[0];
  document.getElementById('diffNodeBadge').innerText = currentFile.nodeType;
  document.getElementById('diffStatsBadge').innerText = currentFile.stats;

  // Render Code
  const codeContainer = document.getElementById('diffCodeBlock');
  codeContainer.innerHTML = currentFile.diff.map(line => {
    if (line.type === 'header') {
      return `<div class="text-zinc-500 select-none pb-2 border-b border-zinc-800 mb-2">${escapeHtml(line.text)}</div>`;
    } else if (line.type === 'del') {
      return `
        <div class="bg-red-950/60 text-red-300 px-1 -mx-1 border-l-2 border-red-500 flex font-mono">
          <span class="select-none text-red-500 w-8 inline-block">${line.line} -</span>
          <span class="font-semibold">${escapeHtml(line.text)}</span>
        </div>`;
    } else if (line.type === 'add') {
      return `
        <div class="bg-emerald-950/60 text-emerald-300 px-1 -mx-1 border-l-2 border-emerald-500 flex font-mono">
          <span class="select-none text-emerald-500 w-8 inline-block">${line.line} +</span>
          <span class="font-semibold">${escapeHtml(line.text)}</span>
        </div>`;
    } else {
      return `
        <div class="text-zinc-400 font-mono">
          <span class="select-none text-zinc-600 w-8 inline-block">${line.line || ''} |</span>
          <span>${escapeHtml(line.text)}</span>
        </div>`;
    }
  }).join('');
}

function switchDiffFile(index) {
  currentDiffFileIndex = index;
  const codemodData = window.DepBridgeData.codemods[currentCodemodPkg] || window.DepBridgeData.codemods['appdirs'];
  renderDiffFiles(codemodData.files);
}

function copyPatch() {
  const codemodData = window.DepBridgeData.codemods[currentCodemodPkg] || window.DepBridgeData.codemods['appdirs'];
  const currentFile = codemodData.files[currentDiffFileIndex] || codemodData.files[0];
  const patchText = currentFile.diff.map(d => d.text).join('\n');
  navigator.clipboard.writeText(patchText).then(() => {
    showToast(`Patch copied for ${currentFile.name}`);
  }).catch(() => {
    showToast('Patch copied to clipboard');
  });
}

// ==========================================
// Deterministic Verification Simulation
// ==========================================
function retriggerVerification() {
  const terminal = document.getElementById('candidateTerminalLogs');
  const statusBadge = document.getElementById('verificationStatusBadge');
  const durLabel = document.getElementById('verificationDurationLabel');

  statusBadge.innerText = 'RUNNING IN EPHEMERAL DOCKER...';
  statusBadge.className = 'bg-orange-100 text-[#EA580C] border border-orange-200 text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold animate-pulse';

  terminal.innerHTML = `
    <div class="text-zinc-500">$ pytest tests/ -q</div>
    <div class="text-zinc-400">Spinning up sandbox container python:3.11-slim...</div>
    <div class="text-[#EA580C] font-mono animate-pulse">Running test harness (34 test cases)...</div>
  `;

  let step = 0;
  const timer = setInterval(() => {
    step++;
    if (step === 1) {
      terminal.innerHTML += `<div class="text-emerald-400">..................................</div>`;
    } else if (step === 2) {
      terminal.innerHTML += `
        <div class="bg-emerald-950/40 text-emerald-300 p-1.5 rounded border border-emerald-800/50 my-1 text-[10px]">
          <div>[✓] <span class="font-bold">Zero Deprecation Warnings:</span> platformdirs active.</div>
          <div class="text-emerald-400/80">    Deterministic cache path: /home/runner/.cache/LinkWatch</div>
        </div>
      `;
    } else if (step === 3) {
      clearInterval(timer);
      terminal.innerHTML += `
        <div class="text-emerald-400 font-bold">34 passed, 0 warnings in 1.28s. All checks green.</div>
        <div class="text-zinc-500 mt-2">$ echo $?</div>
        <div class="text-emerald-400 font-semibold">0</div>
      `;
      statusBadge.innerText = 'STABLE';
      statusBadge.className = 'bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold';
      durLabel.innerText = '1.28s';
      showToast('Sandbox verification passed: 0 regressions.');
    }
  }, 350);
}

// ==========================================
// Re-scan AST Engine Simulation
// ==========================================
function handleReScan() {
  const btn = document.getElementById('rescanBtn');
  const icon = document.getElementById('rescanIcon');
  icon.classList.add('animate-spin');
  btn.classList.add('opacity-75');

  showToast('Starting AST graph traversal across 43 source files...');

  setTimeout(() => {
    showToast('Resolving transitive constraints with PubGrub solver...');
  }, 400);

  setTimeout(() => {
    icon.classList.remove('animate-spin');
    btn.classList.remove('opacity-75');
    showToast('Static analysis complete. AST parity verified at 100%.');
    renderFindingsTable();
  }, 900);
}

// ==========================================
// Signed Capsule Real Exporter (.tar.gz / JSON)
// ==========================================
function downloadSignedCapsule() {
  const capsule = {
    _schema: "https://in-toto.io/attestation/v1.0",
    name: "depbridge-migration-capsule",
    target: window.DepBridgeData.repository.name,
    commit: window.DepBridgeData.repository.fullCommit,
    timestamp: new Date().toISOString(),
    generator: "DepBridge Static Analysis v1.4.2",
    hash: window.DepBridgeData.verification.hash,
    codemodsApproved: [
      {
        package: "appdirs",
        replacement: "platformdirs",
        version: "4.2.2",
        stagedFiles: [
          "src/micro_orchestrator/config.py",
          "src/micro_orchestrator/storage.py",
          "pyproject.toml"
        ]
      }
    ],
    attestation: {
      framework: "in-toto",
      predicateType: "https://depbridge.dev/predicates/v1/migration-evidence",
      testsRun: 34,
      testsPassed: 34,
      regressions: 0,
      exitCode: 0,
      signature: "MEYCIQDx9v1N5z4cI7r5K1s7+m8vF+s8aBcDeFgHiJkLmNoPqQ=="
    },
    rollbackPatch: `diff --git a/pyproject.toml b/pyproject.toml\n--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -28 +28 @@\n-   "platformdirs>=3.8.0,<5.0.0",\n+   "appdirs==1.4.4",`
  };

  const jsonStr = JSON.stringify(capsule, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `linkwatch-migration-${window.DepBridgeData.repository.commit}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast(`Downloaded signed evidence capsule: linkwatch-migration-${window.DepBridgeData.repository.commit}.json`);
}

// ==========================================
// Repository Topology Visualizer (SVG/Canvas)
// ==========================================
function renderTopologyCanvas() {
  const container = document.getElementById('topologyGraphContainer');
  if (!container) return;

  const width = container.clientWidth || 800;
  const height = 360;

  const nodes = [
    { id: "root", label: "rishrek/LinkWatch", type: "root", x: width * 0.15, y: height * 0.5, r: 24, color: "#EA580C" },
    { id: "config", label: "config.py", type: "file", x: width * 0.40, y: height * 0.25, r: 16, color: "#3B82F6" },
    { id: "storage", label: "storage.py", type: "file", x: width * 0.40, y: height * 0.75, r: 16, color: "#3B82F6" },
    { id: "appdirs", label: "appdirs (1.4.4)", type: "dep-critical", x: width * 0.68, y: height * 0.35, r: 18, color: "#EF4444" },
    { id: "platformdirs", label: "platformdirs", type: "candidate", x: width * 0.90, y: height * 0.35, r: 18, color: "#10B981" },
    { id: "nose", label: "nose (1.3.7)", type: "dep-critical", x: width * 0.68, y: height * 0.75, r: 18, color: "#EF4444" },
    { id: "pytest", label: "pytest (8.1)", type: "candidate", x: width * 0.90, y: height * 0.75, r: 18, color: "#10B981" },
    { id: "requests", label: "requests", type: "dep-healthy", x: width * 0.45, y: height * 0.5, r: 14, color: "#10B981" }
  ];

  const links = [
    { from: "root", to: "config" },
    { from: "root", to: "storage" },
    { from: "root", to: "requests" },
    { from: "config", to: "appdirs" },
    { from: "storage", to: "appdirs" },
    { from: "appdirs", to: "platformdirs", dashed: true },
    { from: "root", to: "nose" },
    { from: "nose", to: "pytest", dashed: true }
  ];

  let svgContent = `
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" class="overflow-visible select-none">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#CBD5E1" />
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#10B981" />
        </marker>
      </defs>
  `;

  // Draw Links
  links.forEach(link => {
    const source = nodes.find(n => n.id === link.from);
    const target = nodes.find(n => n.id === link.to);
    if (source && target) {
      const stroke = link.dashed ? "#10B981" : "#E2E8F0";
      const dash = link.dashed ? "stroke-dasharray='4 3'" : "";
      const marker = link.dashed ? "marker-end='url(#arrow-green)'" : "marker-end='url(#arrow)'";
      svgContent += `
        <line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" stroke="${stroke}" stroke-width="2" ${dash} ${marker} />
      `;
    }
  });

  // Draw Nodes
  nodes.forEach(node => {
    svgContent += `
      <g class="graph-node" onclick="handleNodeClick('${node.id}')">
        <circle cx="${node.x}" cy="${node.y}" r="${node.r}" fill="${node.color}" />
        <circle cx="${node.x}" cy="${node.y}" r="${node.r + 4}" fill="none" stroke="${node.color}" stroke-width="1.5" stroke-opacity="0.3" />
        <text x="${node.x}" y="${node.y + node.r + 15}" text-anchor="middle" font-family="Fira Code, monospace" font-size="10" fill="#334155" font-weight="600">${node.label}</text>
      </g>
    `;
  });

  svgContent += `</svg>`;
  container.innerHTML = svgContent;
}

function handleNodeClick(nodeId) {
  if (nodeId === 'appdirs' || nodeId === 'platformdirs') {
    openCodemodView('appdirs');
  } else if (nodeId === 'nose' || nodeId === 'pytest') {
    openCodemodView('nose');
  } else if (nodeId === 'config' || nodeId === 'storage') {
    openInspectorDrawer('appdirs');
  } else {
    showToast(`AST Node inspected: ${nodeId}`);
  }
}

// ==========================================
// Toast System
// ==========================================
function showToast(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button onclick="this.parentElement.remove()" class="text-zinc-400 hover:text-white ml-2 text-xs">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 3500);
}

// ==========================================
// Keyboard Shortcuts & Helpers
// ==========================================
function setupKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === '1') switchTab('findings');
    else if (e.key === '2') switchTab('codemod');
    else if (e.key === '3') switchTab('verification');
    else if (e.key === '4') switchTab('workspace');
    else if (e.key === '5') switchTab('capsule');
    else if (e.key === '/') {
      e.preventDefault();
      document.getElementById('searchInput')?.focus();
    } else if (e.key === 'Escape') {
      closeInspectorDrawer();
    }
  });
}

function setupFilterHandlers() {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      renderFindingsTable();
    });
  }
}

function toggleTheme() {
  document.body.classList.toggle('dark-theme');
  const isDark = document.body.classList.contains('dark-theme');
  showToast(isDark ? 'Cyber Dark mode enabled' : 'Enterprise Light mode enabled');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

window.switchTab = switchTab;
window.setFilter = setFilter;
window.setManifestFilter = setManifestFilter;
window.filterRows = filterRows;
window.openCodemodView = openCodemodView;
window.openInspectorDrawer = openInspectorDrawer;
window.closeInspectorDrawer = closeInspectorDrawer;
window.switchDiffFile = switchDiffFile;
window.copyPatch = copyPatch;
window.retriggerVerification = retriggerVerification;
window.handleReScan = handleReScan;
window.downloadSignedCapsule = downloadSignedCapsule;
window.handleNodeClick = handleNodeClick;
window.toggleTheme = toggleTheme;
