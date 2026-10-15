# DepBridge - Enterprise Python Dependency Static Analysis

A high-density enterprise static analysis frontend built with modern web aesthetics, AST evidence visualization, codemod diff inspection, deterministic sandbox verification, and cryptographic migration evidence export.

## 🚀 Features

- **Analysis Report**: Interactive findings table with real-time severity filtering (Critical, Migrations Ready, Healthy), manifest filtering (`pyproject.toml`, `requirements.txt`, `setup.cfg`), and instant symbol search.
- **AST Inspector Drawer**: Slide-out drawer showing AST call sites, node types (`ImportFrom`, `Call`, `Attribute`), file lines, and upstream migration recipes.
- **Codemod Workspace & Diff Viewer**: 2-column specification comparison (Original vs Proposed), interactive execution checklist, multi-file unified diff viewer with line numbers and one-click patch copier.
- **Deterministic Verification Runner**: Dual live terminals simulating original vs candidate container runs (`python:3.11-slim`), warning elimination verification, and interactive "Rerun Sandbox" animation.
- **Workspace Topology & AST Graph**: Interactive SVG dependency call graph with clickable nodes for inspecting blast radius across files.
- **Exit Capsule Exporter**: One-click generation and browser download of signed in-toto attestation evidence bundles (`.json` / `.tar.gz`) with SHA256 evidence hashes and rollback scripts.
- **Cyber Dark & Enterprise Light Modes**: Theme toggle for low-light terminal work.
- **Keyboard Shortcuts**:
  - `[1-5]`: Switch between tabs (Findings, Codemod, Verification, Workspace, Capsule)
  - `[/]`: Focus instant search bar
  - `[Esc]`: Close inspector drawer

## 📁 Project Structure

```
frontend/
├── index.html            # Main application entrypoint
├── css/
│   └── styles.css        # Custom styles, terminal scanlines, diff highlighting, and animations
├── js/
│   ├── data.js           # Structured data store for AST findings, codemods, and verification
│   └── app.js            # Interactive workflows, tab switcher, filters, drawers, and exports
└── package.json          # Local dev server script
```

## 💻 Running Locally

### Option 1: Direct in Browser
Double-click `index.html` or open it directly in Chrome, Edge, or Firefox.

### Option 2: Python Local Server
```bash
python -m http.server 3000
```
Then navigate to `http://localhost:3000`.

### Option 3: Node / npm
```bash
npm start
```
