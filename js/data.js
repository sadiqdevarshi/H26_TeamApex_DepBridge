// DepBridge Data Store - Repository Topology, AST Findings, Codemods, and Sandbox Results

window.DepBridgeData = {
  repository: {
    name: "rishrek/LinkWatch",
    branch: "main",
    commit: "d96a36f",
    fullCommit: "d96a36f890c25b41e3a79d718b201a07c125bb90",
    pythonRange: ">=3.10, <3.13",
    astEngine: "libcst v1.1.0",
    solver: "PubGrub-py 0.5.2",
    parsedNodes: 1482,
    sourceFiles: 43,
    manifests: [
      { name: "pyproject.toml", path: "pyproject.toml", lines: 68, depsCount: 14, status: "AST Synced" },
      { name: "requirements.txt", path: "requirements.txt", lines: 24, depsCount: 7, status: "AST Synced" },
      { name: "setup.cfg", path: "setup.cfg", lines: 52, depsCount: 3, status: "AST Synced" }
    ],
    stats: {
      totalPackages: 24,
      attentionNeeded: 4,
      deprecated: 2,
      migrationsReady: 3,
      healthy: 20,
      coverage: "75.0%"
    }
  },

  packages: [
    {
      id: "appdirs",
      name: "appdirs",
      constraint: "==1.4.4",
      manifest: "pyproject.toml:28",
      manifestFile: "pyproject.toml",
      manifestLine: 28,
      severity: "critical",
      tag: "CVE/EOL",
      riskTitle: "[Critical] Stale / Abandoned",
      riskDescription: "Unmaintained since May 2020. Breaks XDG directory specification on modern Linux distros and misidentifies Application Support path on macOS Sonoma & Sequoia.",
      astEvidence: "4 call sites across 2 files",
      callSitesSummary: "user_cache_dir, user_data_dir",
      callSites: [
        { file: "src/micro_orchestrator/config.py", line: 14, node: "ImportFrom", code: "from appdirs import user_cache_dir, user_data_dir", context: "Configuration paths initialization" },
        { file: "src/micro_orchestrator/config.py", line: 20, node: "Call", code: "return Path(user_cache_dir(APP_NAME, APP_AUTHOR))", context: "Returns primary local cache root" },
        { file: "src/micro_orchestrator/storage.py", line: 8, node: "ImportFrom", code: "import appdirs", context: "Storage module initialization" },
        { file: "src/micro_orchestrator/storage.py", line: 34, node: "Call", code: "appdirs.user_data_dir('LinkWatch', roaming=True)", context: "Persistent app state directory resolver" }
      ],
      recommendedCandidate: "platformdirs",
      recommendedConstraint: ">=3.8.0, <5.0.0",
      candidateNote: "Drop-in replacement candidate",
      verificationStatus: "Passed (34/34 tests)",
      verificationType: "success",
      hasCodemod: true,
      hasInspection: true,
      codemodAvailable: true
    },
    {
      id: "nose",
      name: "nose",
      constraint: "==1.3.7",
      manifest: "setup.cfg:45",
      manifestFile: "setup.cfg",
      manifestLine: 45,
      severity: "critical",
      tag: "INCOMPATIBLE",
      riskTitle: "[Critical] Legacy Test Runner",
      riskDescription: "Completely incompatible with Python >=3.12 syntax and removed imp module. Upstream project has been dead for nearly a decade.",
      astEvidence: "8 call sites across 3 test files",
      callSitesSummary: "nose.tools (assert_equal, raises, with_setup)",
      callSites: [
        { file: "tests/test_collector.py", line: 4, node: "ImportFrom", code: "from nose.tools import assert_equal, assert_true", context: "Legacy assertions in collector test suite" },
        { file: "tests/test_collector.py", line: 28, node: "Call", code: "assert_equal(res.status_code, 200)", context: "Equality assertion rewrite candidate" },
        { file: "tests/test_parser.py", line: 3, node: "ImportFrom", code: "from nose.tools import raises", context: "Exception decorator wrapper" },
        { file: "tests/test_storage.py", line: 12, node: "Call", code: "assert_equal(storage.get_item('key'), 'val')", context: "Storage assertion" }
      ],
      recommendedCandidate: "pytest",
      recommendedConstraint: ">=8.1.0",
      candidateNote: "Requires assertion rewrite codemod",
      verificationStatus: "Inconclusive",
      verificationType: "warning",
      hasCodemod: true,
      hasInspection: true,
      codemodAvailable: true
    },
    {
      id: "pydantic",
      name: "pydantic",
      constraint: ">1.10.0, <2.0.0",
      manifest: "requirements.txt:12",
      manifestFile: "requirements.txt",
      manifestLine: 12,
      severity: "medium",
      tag: "V1→V2",
      riskTitle: "[Medium] Major Version Jump",
      riskDescription: "V1 syntax in use. Core schema parsing misses performance benefits of Rust-based v2 and blocks Python 3.13 modern type syntax.",
      astEvidence: "11 call sites across 4 files",
      callSitesSummary: "BaseModel, validator, Field",
      callSites: [
        { file: "src/micro_orchestrator/models.py", line: 6, node: "ImportFrom", code: "from pydantic import BaseModel, validator, Field", context: "Schema definition base" },
        { file: "src/micro_orchestrator/models.py", line: 18, node: "Decorator", code: "@validator('url')", context: "V1 validator decorator target for @field_validator" },
        { file: "src/micro_orchestrator/models.py", line: 42, node: "Attribute", code: "class Config: orm_mode = True", context: "V1 Config class target for model_config" },
        { file: "src/micro_orchestrator/client.py", line: 15, node: "Call", code: "PayloadModel.parse_raw(payload_bytes)", context: "V1 parser method target for model_validate_json" }
      ],
      recommendedCandidate: "pydantic",
      recommendedConstraint: ">=2.6.0",
      candidateNote: "pydantic.v1 shim synthesis ready",
      verificationStatus: "Passed",
      verificationType: "success",
      hasCodemod: true,
      hasInspection: true,
      codemodAvailable: true
    },
    {
      id: "requests",
      name: "requests",
      constraint: ">=2.31.0",
      manifest: "pyproject.toml:26",
      manifestFile: "pyproject.toml",
      manifestLine: 26,
      severity: "healthy",
      tag: "HEALTHY",
      riskTitle: "[Healthy] Active Maintenance",
      riskDescription: "Active maintenance, up to date with zero known vulnerabilities and standard urllib3 compatibility.",
      astEvidence: "16 call sites across 5 files",
      callSitesSummary: "Session, get, post, RequestException",
      callSites: [
        { file: "src/micro_orchestrator/client.py", line: 5, node: "ImportFrom", code: "import requests", context: "HTTP client backend" },
        { file: "src/micro_orchestrator/client.py", line: 22, node: "Call", code: "self.session = requests.Session()", context: "Connection pooling instance" }
      ],
      recommendedCandidate: "None needed",
      recommendedConstraint: "Current satisfies all bounds",
      candidateNote: "None needed",
      verificationStatus: "Passed",
      verificationType: "success",
      hasCodemod: false,
      hasInspection: true,
      codemodAvailable: false
    },
    {
      id: "urllib3",
      name: "urllib3",
      constraint: ">=2.0.7, <3.0.0",
      manifest: "pyproject.toml:29",
      manifestFile: "pyproject.toml",
      manifestLine: 29,
      severity: "healthy",
      tag: "HEALTHY",
      riskTitle: "[Healthy] Modern HTTP Core",
      riskDescription: "Version 2.x active with TLS 1.3 support and optimized socket connection pooling.",
      astEvidence: "6 call sites across 2 files",
      callSitesSummary: "Retry, Timeout, PoolManager",
      callSites: [
        { file: "src/micro_orchestrator/client.py", line: 8, node: "ImportFrom", code: "from urllib3.util import Retry", context: "HTTP backoff configuration" }
      ],
      recommendedCandidate: "None needed",
      recommendedConstraint: "Current satisfies all bounds",
      candidateNote: "None needed",
      verificationStatus: "Passed",
      verificationType: "success",
      hasCodemod: false,
      hasInspection: true,
      codemodAvailable: false
    },
    {
      id: "rich",
      name: "rich",
      constraint: ">=13.7.0",
      manifest: "requirements.txt:18",
      manifestFile: "requirements.txt",
      manifestLine: 18,
      severity: "healthy",
      tag: "HEALTHY",
      riskTitle: "[Healthy] Terminal UI & Logging",
      riskDescription: "Modern rich terminal rendering library with zero deprecation warnings.",
      astEvidence: "9 call sites across 3 files",
      callSitesSummary: "Console, Table, Progress",
      callSites: [
        { file: "src/micro_orchestrator/cli.py", line: 6, node: "ImportFrom", code: "from rich.console import Console", context: "CLI formatting" }
      ],
      recommendedCandidate: "None needed",
      recommendedConstraint: "Current satisfies all bounds",
      candidateNote: "None needed",
      verificationStatus: "Passed",
      verificationType: "success",
      hasCodemod: false,
      hasInspection: true,
      codemodAvailable: false
    }
  ],

  codemods: {
    appdirs: {
      title: "Migration: appdirs → platformdirs",
      targetPkg: "platformdirs 4.2.2",
      originalSpec: {
        package: "appdirs 1.4.4",
        status: "DEPRECATED",
        manifest: "pyproject.toml (line 28)",
        constraint: "appdirs == 1.4.4",
        issueProfile: "Package abandoned since May 2020. Breaks XDG directory specification compliance on modern Linux distros and misidentifies Application Support path on macOS Sonoma/Sequoia."
      },
      proposedSpec: {
        package: "platformdirs 4.2.2",
        status: "DROP-IN REPLACEMENT",
        targetConstraint: "platformdirs >= 3.8.0, < 5.0.0",
        apiParity: "100% Identical Signatures",
        runtimeRationale: "Direct maintained fork of appdirs by the Tox organization. Exports identical function signatures: user_cache_dir and user_data_dir with zero kwargs incompatibilities."
      },
      checklist: [
        { id: "c1", label: "Bump dependency constraint in pyproject.toml", desc: "Remove appdirs, append platformdirs", checked: true },
        { id: "c2", label: "Refactor import in config.py", desc: "AST transform: appdirs → platformdirs", checked: true },
        { id: "c3", label: "Refactor import in storage.py", desc: "AST transform: appdirs.user_data_dir", checked: true },
        { id: "c4", label: "Run deterministic sandbox test runner", desc: "Verify pytest suite in ephemeral Docker layer", checked: true }
      ],
      files: [
        {
          id: "config_py",
          name: "src/micro_orchestrator/config.py",
          nodeType: "AST Node: ImportFrom",
          stats: "Unified Diff (2 additions, 2 deletions)",
          diff: [
            { type: "header", text: "@@ -11,7 +11,7 @@ from typing import Optional, Dict, Any" },
            { type: "context", line: 11, text: "import os" },
            { type: "context", line: 12, text: "import sys" },
            { type: "context", line: 13, text: "from pathlib import Path" },
            { type: "del", line: 14, text: "- from appdirs import user_cache_dir, user_data_dir" },
            { type: "add", line: 14, text: "+ from platformdirs import user_cache_dir, user_data_dir" },
            { type: "context", line: 15, text: "" },
            { type: "context", line: 16, text: "APP_NAME = \"LinkWatch\"" },
            { type: "context", line: 17, text: "APP_AUTHOR = \"rishrek\"" },
            { type: "context", line: 18, text: "" },
            { type: "context", line: 19, text: "def get_cache_root() -> Path:" },
            { type: "context", line: 20, text: "    return Path(user_cache_dir(APP_NAME, APP_AUTHOR))" }
          ]
        },
        {
          id: "storage_py",
          name: "src/micro_orchestrator/storage.py",
          nodeType: "AST Node: Import & Call",
          stats: "Unified Diff (2 additions, 2 deletions)",
          diff: [
            { type: "header", text: "@@ -7,6 +7,6 @@ from pathlib import Path" },
            { type: "del", line: 8, text: "- import appdirs" },
            { type: "add", line: 8, text: "+ import platformdirs as appdirs  # backward compatibility alias" },
            { type: "context", line: 9, text: "import json" },
            { type: "context", line: 10, text: "import logging" },
            { type: "del", line: 34, text: "- data_path = appdirs.user_data_dir('LinkWatch', roaming=True)" },
            { type: "add", line: 34, text: "+ data_path = appdirs.user_data_dir('LinkWatch', roaming=True, ensure_exists=True)" }
          ]
        },
        {
          id: "pyproject_toml",
          name: "pyproject.toml",
          nodeType: "Manifest TOML Node: dependencies",
          stats: "Unified Diff (1 addition, 1 deletion)",
          diff: [
            { type: "header", text: "@@ -26,5 +26,5 @@ dependencies = [" },
            { type: "context", line: 26, text: "    \"requests>=2.31.0\"," },
            { type: "context", line: 27, text: "    \"urllib3>=2.0.7\"," },
            { type: "del", line: 28, text: "-   \"appdirs==1.4.4\"," },
            { type: "add", line: 28, text: "+   \"platformdirs>=3.8.0,<5.0.0\"," },
            { type: "context", line: 29, text: "    \"rich>=13.7.0\"," }
          ]
        }
      ]
    },

    nose: {
      title: "Migration: nose → pytest",
      targetPkg: "pytest >= 8.1.0",
      originalSpec: {
        package: "nose 1.3.7",
        status: "DEAD UPSTREAM",
        manifest: "setup.cfg (line 45)",
        constraint: "nose == 1.3.7",
        issueProfile: "Deprecation of imp module in Python 3.12 completely breaks test discovery and execution."
      },
      proposedSpec: {
        package: "pytest >= 8.1.0",
        status: "INDUSTRY STANDARD",
        targetConstraint: "pytest >= 8.1.0",
        apiParity: "Assertion Rewriting Required",
        runtimeRationale: "Replace assert_equal() calls with native python assert expressions."
      },
      checklist: [
        { id: "n1", label: "Remove nose from setup.cfg test extras", desc: "Replace with pytest", checked: true },
        { id: "n2", label: "AST Codemod: Rewrite nose.tools.assert_equal", desc: "Transform assert_equal(a, b) -> assert a == b", checked: true },
        { id: "n3", label: "AST Codemod: Convert @raises decorator to pytest.raises", desc: "Wrap test body in with pytest.raises(Exc):", checked: false },
        { id: "n4", label: "Run test suite verification sandbox", desc: "Execute pytest in container", checked: true }
      ],
      files: [
        {
          id: "test_collector_py",
          name: "tests/test_collector.py",
          nodeType: "AST Node: Call (Assertion)",
          stats: "Unified Diff (3 additions, 3 deletions)",
          diff: [
            { type: "header", text: "@@ -3,5 +3,5 @@ import unittest" },
            { type: "del", line: 4, text: "- from nose.tools import assert_equal, assert_true" },
            { type: "add", line: 4, text: "+ import pytest" },
            { type: "context", line: 27, text: "    res = collector.fetch('https://example.com')" },
            { type: "del", line: 28, text: "-   assert_equal(res.status_code, 200)" },
            { type: "add", line: 28, text: "+   assert res.status_code == 200" }
          ]
        }
      ]
    }
  },

  verification: {
    hash: "sha256:7f01cba88e24f61e89c3b881907de38cbb5920a1",
    duration: "1.28s",
    exitCode: 0,
    testsTotal: 34,
    testsPassed: 34,
    warnings: 0,
    originalOutput: [
      { text: "$ pytest tests/ -q", type: "cmd" },
      { text: "============================= test session starts ==============================", type: "info" },
      { text: "platform linux -- Python 3.11.8, pytest-7.4.4, pluggy-1.4.0", type: "info" },
      { text: "rootdir: /sandbox/target/LinkWatch", type: "info" },
      { text: "..................................", type: "pass" },
      { text: "[!] DeprecationWarning: appdirs is unmaintained and deprecated.", type: "warn" },
      { text: "    from appdirs import user_cache_dir (src/micro_orchestrator/config.py:14)", type: "warn-sub" },
      { text: "34 passed, 2 warnings in 1.42s", type: "amber" },
      { text: "$ echo $?", type: "cmd" },
      { text: "0", type: "text" }
    ],
    candidateOutput: [
      { text: "$ pytest tests/ -q", type: "cmd" },
      { text: "============================= test session starts ==============================", type: "info" },
      { text: "platform linux -- Python 3.11.8, pytest-7.4.4, pluggy-1.4.0", type: "info" },
      { text: "rootdir: /sandbox/target/LinkWatch", type: "info" },
      { text: "..................................", type: "pass" },
      { text: "[✓] Zero Deprecation Warnings: platformdirs active.", type: "success" },
      { text: "    Deterministic cache path: /home/runner/.cache/LinkWatch", type: "success-sub" },
      { text: "34 passed, 0 warnings in 1.28s. All checks green.", type: "green" },
      { text: "$ echo $?", type: "cmd" },
      { text: "0", type: "text" }
    ]
  }
};
