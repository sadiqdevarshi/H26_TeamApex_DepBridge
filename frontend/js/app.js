// DepBridge Application Logic & Interactive Workflows
// Updated with Humanist Sans (IBM Plex Sans), Code Mono (IBM Plex Mono), Calm Palette

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
      btn.classList.remove('active');
    }
  });

  const activeView = document.getElementById('view-' + tabId);
  if (activeView) activeView.classList.remove('hidden');

  const activeBtn = document.getElementById('tab-' + tabId);
  if (activeBtn) {
    activeBtn.classList.add('active');
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

  const countLabel = document.getElementById('filteredCountLabel');
  if (countLabel) {
    countLabel.innerText = `Showing ${filtered.length} of ${window.DepBridgeData.repository.stats.totalPackages} analyzed dependencies`;
  }

  tbody.innerHTML = filtered.map(pkg => {
    const isCritical = pkg.severity === 'critical';
    const isMedium = pkg.severity === 'medium';
    const isHealthy = pkg.severity === 'healthy';

    let severityBadge = '';
    if (isCritical) {
      severityBadge = `<span class="status-pill status-pill-critical">${pkg.riskTitle}</span>`;
    } else if (isMedium) {
      severityBadge = `<span class="status-pill status-pill-warning">${pkg.riskTitle}</span>`;
    } else {
      severityBadge = `<span class="status-pill status-pill-pass">✓ ${pkg.riskTitle}</span>`;
    }

    let verificationBadge = '';
    if (pkg.verificationType === 'success') {
      verificationBadge = `<span class="status-pill status-pill-pass">✓ ${pkg.verificationStatus}</span>`;
    } else if (pkg.verificationType === 'warning') {
      verificationBadge = `<span class="status-pill status-pill-warning">${pkg.verificationStatus}</span>`;
    } else {
      verificationBadge = `<span class="status-pill status-pill-neutral">${pkg.verificationStatus}</span>`;
    }

    const rowClass = isCritical ? 'highlight-critical' : '';

    return `
      <tr class="${rowClass}">
        <td>
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-code font-semibold text-[15px] text-[#1A1A1A]">${pkg.name}</span>
            <span class="font-code text-[14px] text-[#667085]">${pkg.constraint}</span>
            ${pkg.tag === 'CVE/EOL' ? `<span class="status-pill status-pill-critical" style="height: 22px; padding: 0 6px; font-size: 12px;">CVE/EOL</span>` : ''}
            ${pkg.tag === 'INCOMPATIBLE' ? `<span class="status-pill status-pill-critical" style="height: 22px; padding: 0 6px; font-size: 12px;">Python 3.12+</span>` : ''}
            ${pkg.tag === 'V1→V2' ? `<span class="status-pill status-pill-warning" style="height: 22px; padding: 0 6px; font-size: 12px;">v1→v2</span>` : ''}
          </div>
        </td>
        <td>
          <span class="font-code text-[14px] text-[#344054]">${pkg.manifest}</span>
        </td>
        <td>
          <div>${severityBadge}</div>
          <div class="text-[13px] text-[#667085] mt-1 max-w-xs truncate">${pkg.riskDescription}</div>
        </td>
        <td class="cursor-pointer group" onclick="openInspectorDrawer('${pkg.id}')">
          <div class="font-medium text-[#1A1A1A] text-[14px] group-hover:text-[#D9480F] flex items-center gap-1">
            <span>${pkg.astEvidence}</span>
            <span class="text-[#667085] group-hover:text-[#D9480F]">↗</span>
          </div>
          <div class="text-[13px] text-[#667085] font-code mt-0.5 truncate">${pkg.callSitesSummary}</div>
        </td>
        <td>
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="font-code text-[14px] font-semibold ${pkg.recommendedCandidate !== 'None needed' ? 'text-[#1E4E8C]' : 'text-[#667085]'}">${pkg.recommendedCandidate}</span>
            <span class="font-code text-[13px] text-[#667085]">${pkg.recommendedConstraint}</span>
          </div>
          <div class="text-[13px] ${pkg.recommendedCandidate !== 'None needed' ? 'text-[#1E4E8C]' : 'text-[#667085]'} mt-0.5">${pkg.candidateNote}</div>
        </td>
        <td>
          ${verificationBadge}
        </td>
        <td class="text-right">
          <div class="flex items-center justify-end gap-2">
            <button onclick="openInspectorDrawer('${pkg.id}')" class="btn-sm-secondary">
              Inspect
            </button>
            ${pkg.codemodAvailable ? `
              <button onclick="openCodemodView('${pkg.id}')" class="btn-sm-primary">
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
      el.classList.remove('active');
    }
  });

  const current = document.getElementById('filter-' + type);
  if (current) {
    current.classList.add('active');
  }

  renderFindingsTable();
}

function setManifestFilter(manifest) {
  currentManifest = manifest;
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
      <div class="p-3 rounded-[6px] bg-[#F7F7F5] border border-[#E5E5E0] space-y-1.5">
        <div class="flex items-center justify-between text-[13px]">
          <span class="font-code font-semibold text-[#1A1A1A]">${cs.file}:${cs.line}</span>
          <span class="status-pill status-pill-neutral" style="height: 22px; padding: 0 8px; font-size: 12px;">${cs.node}</span>
        </div>
        <div class="p-2.5 bg-[#1C1C1E] text-[#E5E5EA] rounded-[6px] text-[13px] font-code overflow-x-auto">
          <code>${escapeHtml(cs.code)}</code>
        </div>
        <div class="text-[13px] text-[#475467]">${cs.context}</div>
      </div>
    `).join('');
  } else {
    callSitesContainer.innerHTML = `<div class="p-4 text-[#667085] text-[14px]">No direct AST call sites detected.</div>`;
  }

  const codemodBtn = document.getElementById('drawerCodemodBtn');
  if (pkg.codemodAvailable) {
    codemodBtn.style.display = 'inline-flex';
    codemodBtn.onclick = () => {
      closeInspectorDrawer();
      openCodemodView(pkg.id);
    };
  } else {
    codemodBtn.style.display = 'none';
  }

  overlay.classList.remove('hidden');
  drawer.classList.remove('hidden');
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
    <label class="flex items-start gap-3 p-3 rounded-[6px] bg-[#FAFAF8] border border-[#E5E5E0] text-[14px] cursor-pointer hover:bg-white transition-colors">
      <input type="checkbox" id="check-${item.id}" ${item.checked ? 'checked' : ''} onchange="updateChecklistCount()" class="mt-1 w-4 h-4 accent-[#D9480F] rounded" />
      <div>
        <div class="text-[#1A1A1A] font-medium">${item.label}</div>
        <div class="text-[#667085] text-[13px] mt-0.5">${item.desc}</div>
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
    <button onclick="switchDiffFile(${idx})" class="h-[32px] px-3 rounded-[6px] font-code text-[13px] font-medium transition-colors ${idx === currentDiffFileIndex ? 'bg-white border border-[#D0D5DD] text-[#1A1A1A]' : 'text-[#475467] hover:text-[#1A1A1A]'}">
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
      return `<div class="text-[#8E8E93] select-none pb-2 border-b border-[#3A3A3C] mb-2 font-code text-[13px]">${escapeHtml(line.text)}</div>`;
    } else if (line.type === 'del') {
      return `
        <div class="diff-del-row flex font-code text-[13px]">
          <span class="select-none text-[#F87171] w-10 inline-block shrink-0">${line.line} -</span>
          <span>${escapeHtml(line.text)}</span>
        </div>`;
    } else if (line.type === 'add') {
      return `
        <div class="diff-add-row flex font-code text-[13px]">
          <span class="select-none text-[#60A5FA] w-10 inline-block shrink-0">${line.line} +</span>
          <span>${escapeHtml(line.text)}</span>
        </div>`;
    } else {
      return `
        <div class="text-[#D1D1D6] font-code text-[13px] py-0.5 flex">
          <span class="select-none text-[#636366] w-10 inline-block shrink-0">${line.line || ''} |</span>
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

  statusBadge.innerText = 'Running in ephemeral sandbox...';
  statusBadge.className = 'status-pill status-pill-warning';

  terminal.innerHTML = `
    <div class="text-[#8E8E93]">$ pytest tests/ -q</div>
    <div class="text-[#AEAEB2]">Spinning up sandbox container python:3.11-slim...</div>
    <div class="text-[#FDBA74]">Running test harness (34 test cases)...</div>
  `;

  let step = 0;
  const timer = setInterval(() => {
    step++;
    if (step === 1) {
      terminal.innerHTML += `<div class="text-[#93C5FD]">..................................</div>`;
    } else if (step === 2) {
      terminal.innerHTML += `
        <div class="bg-[#242A38] text-[#93C5FD] p-2.5 rounded-[6px] border border-[#2B3950] my-2 text-[13px]">
          <div>[✓] <span class="font-bold">Zero deprecation warnings:</span> platformdirs active.</div>
          <div class="text-[#BFDBFE]">    Deterministic cache path: /home/runner/.cache/LinkWatch</div>
        </div>
      `;
    } else if (step === 3) {
      clearInterval(timer);
      terminal.innerHTML += `
        <div class="text-[#93C5FD] font-semibold mt-1">34 passed, 0 warnings in 1.28s. All checks passed.</div>
        <div class="text-[#8E8E93] mt-2">$ echo $?</div>
        <div class="text-[#93C5FD] font-semibold">0</div>
      `;
      statusBadge.innerHTML = '✓ Stable';
      statusBadge.className = 'status-pill status-pill-pass';
      durLabel.innerText = '1.28s';
      showToast('Sandbox verification passed: zero regressions detected.');
    }
  }, 350);
}

// ==========================================
// Re-scan AST Engine Simulation
// ==========================================
function handleReScan() {
  const btn = document.getElementById('rescanBtn');
  const icon = document.getElementById('rescanIcon');
  if (icon) icon.classList.add('animate-spin');
  if (btn) btn.disabled = true;

  showToast('Starting AST graph traversal across 43 source files...');

  setTimeout(() => {
    showToast('Resolving transitive constraints with PubGrub solver...');
  }, 400);

  setTimeout(() => {
    if (icon) icon.classList.remove('animate-spin');
    if (btn) btn.disabled = false;
    showToast('Static analysis complete. AST parity verified at 100%.');
    renderFindingsTable();
  }, 900);
}

// ==========================================
// Signed Capsule Real Exporter (.json)
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
// Repository Topology Visualizer (SVG)
// Colors: Blue for files, Red for deprecated, Blue-slate for replacements, Orange for repo. NO GREEN.
// ==========================================
function renderTopologyCanvas() {
  const container = document.getElementById('topologyGraphContainer');
  if (!container) return;

  const width = Math.min(container.clientWidth || 900, 1100);
  const height = 380;

  // Nodes Palette:
  // Root repo: #D9480F (Orange)
  // Source files: #2563EB (Blue)
  // Deprecated packages: #B42318 (Brick Red)
  // Replacement candidates & healthy: #1E4E8C (Blue-slate)
  const nodes = [
    { id: "root", label: "rishrek/LinkWatch", type: "root", x: width * 0.12, y: height * 0.5, r: 24, color: "#D9480F" },
    { id: "config", label: "config.py", type: "file", x: width * 0.38, y: height * 0.25, r: 16, color: "#2563EB" },
    { id: "storage", label: "storage.py", type: "file", x: width * 0.38, y: height * 0.75, r: 16, color: "#2563EB" },
    { id: "appdirs", label: "appdirs (1.4.4)", type: "dep-critical", x: width * 0.66, y: height * 0.35, r: 18, color: "#B42318" },
    { id: "platformdirs", label: "platformdirs (4.2)", type: "candidate", x: width * 0.90, y: height * 0.35, r: 18, color: "#1E4E8C" },
    { id: "nose", label: "nose (1.3.7)", type: "dep-critical", x: width * 0.66, y: height * 0.75, r: 18, color: "#B42318" },
    { id: "pytest", label: "pytest (8.1)", type: "candidate", x: width * 0.90, y: height * 0.75, r: 18, color: "#1E4E8C" },
    { id: "requests", label: "requests (2.31)", type: "dep-healthy", x: width * 0.42, y: height * 0.5, r: 15, color: "#1E4E8C" }
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
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#D0D5DD" />
        </marker>
        <marker id="arrow-blue" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#1E4E8C" />
        </marker>
      </defs>
  `;

  // Draw Links
  links.forEach(link => {
    const source = nodes.find(n => n.id === link.from);
    const target = nodes.find(n => n.id === link.to);
    if (source && target) {
      const stroke = link.dashed ? "#1E4E8C" : "#E5E5E0";
      const dash = link.dashed ? "stroke-dasharray='5 4'" : "";
      const marker = link.dashed ? "marker-end='url(#arrow-blue)'" : "marker-end='url(#arrow)'";
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
        <circle cx="${node.x}" cy="${node.y}" r="${node.r + 5}" fill="none" stroke="${node.color}" stroke-width="1.5" stroke-opacity="0.25" />
        <text x="${node.x}" y="${node.y + node.r + 18}" text-anchor="middle" font-family="'IBM Plex Sans', sans-serif" font-size="13" fill="#344054" font-weight="500">${node.label}</text>
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
    showToast(`AST node inspected: ${nodeId}`);
  }
}

// ==========================================
// Toast Notification
// ==========================================
function showToast(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'clean-toast';
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button onclick="this.parentElement.remove()" class="text-[#98A2B3] hover:text-white ml-3 text-[14px] cursor-pointer">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 3500);
}

// ==========================================
// Keyboard Shortcuts
// ==========================================
function setupKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

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

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}
