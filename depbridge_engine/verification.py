"""Bounded, focused comparison for the organizer's LinkWatch repository.

Virtual environments isolate packages, not hostile code. Serve this operation only
to trusted team users; do not expose it as a public arbitrary-code execution API.
"""
import ast
import difflib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .engine import declarations, github_url

CHECK_SCRIPT = r'''
import importlib.util, json, os, pathlib, tempfile
module_path, scratch = __import__('sys').argv[1:]
scratch = pathlib.Path(scratch)
scratch.mkdir(parents=True, exist_ok=True)
os.environ['HOME'] = str(scratch)
os.environ['XDG_CACHE_HOME'] = str(scratch / 'xdg')
os.environ.pop('LINKWATCH_CACHE_DIR', None)
spec = importlib.util.spec_from_file_location('depbridge_target_cache', module_path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = {}
def check(name, fn):
    try:
        value = fn()
        out[name] = {'passed': True, 'value': value}
    except Exception as e:
        out[name] = {'passed': False, 'error': type(e).__name__ + ': ' + str(e)}
def default_path():
    actual = str(m.cache_dir())
    assert pathlib.Path(actual).is_dir(), 'Cache directory not created'
    return actual
check('default_cache_directory', default_path)
os.environ['LINKWATCH_CACHE_DIR'] = str(scratch / 'override')
def override():
    assert pathlib.Path(m.cache_dir()) == scratch / 'override', 'Override ignored'
    return str(m.cache_dir())
check('cache_override', override)
def missing():
    target = pathlib.Path(m.cache_file())
    if target.exists(): target.unlink()
    assert m.load_results() == [], 'Missing cache did not produce empty list'
    return []
check('missing_cache', missing)
def roundtrip():
    value = [{'url': 'https://example.org', 'status': 200, 'label': 'café'}]
    m.save_results(value)
    assert m.load_results() == value, 'JSON roundtrip differs'
    return value
check('json_roundtrip', roundtrip)
print(json.dumps(out))
'''


def _environment():
    # Never forward model credentials or Git credentials to target code.
    allow = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    return {k: v for k, v in os.environ.items() if k.upper() in allow}


def _execute(args, cwd, timeout=90):
    start = time.monotonic()
    try:
        result = subprocess.run(args, cwd=cwd, env=_environment(), capture_output=True, text=True, timeout=timeout)
        log = result.stdout + result.stderr
        return {"status": "passed" if result.returncode == 0 else "failed", "exit_code": result.returncode,
                "duration_ms": int((time.monotonic()-start)*1000), "log_excerpt": log[-6000:],
                "log_truncated": len(log) > 6000, "full_log": log}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "blocked", "exit_code": None, "duration_ms": int((time.monotonic()-start)*1000),
                "log_excerpt": f"{type(exc).__name__}: {exc}", "log_truncated": False, "full_log": str(exc)}


def verify_candidate(repository_dir, finding, candidate, output_dir):
    repo, output = Path(repository_dir).resolve(), Path(output_dir).resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Verification output must be outside the analyzed repository.")
    output.mkdir(parents=True, exist_ok=True)
    limitations = ["Focused cache-module checks only; full LinkWatch suite was not executed.",
                   "Results apply to the recorded runtime and platform only.",
                   "Virtual environments isolate packages, not operating-system access; this adapter is for the trusted organizer repository."]
    response = {"outcome": "inconclusive", "environment": {"python_version": platform.python_version(), "platform": platform.platform()},
                "checks": [], "limitations": limitations, "error": None, "patch_path": None, "artifact_paths": []}
    if finding.get("dependency_name") != "appdirs" or candidate.get("replacement_name") != "platformdirs":
        response["error"] = "Only the appdirs-to-platformdirs comparison is currently implemented."
        return response
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    if github_url(remote).lower() != "https://github.com/rishrek/linkwatch":
        response["error"] = "Execution is limited to the organizer-provided LinkWatch origin."
        return response
    if any(p.is_symlink() for p in repo.rglob("*")):
        response["error"] = "Verification does not support repositories containing symlinks."
        return response
    # Locate the real module and require a supported import shape.
    modules = []
    for item in finding.get("usage", []):
        path = (repo / item["path"]).resolve()
        if repo not in path.parents or not path.is_file():
            continue
        text = path.read_text()
        if all(f"def {name}(" in text for name in ("cache_dir", "cache_file", "save_results", "load_results")):
            modules.append((path, text))
    if len(modules) != 1:
        response["error"] = "Could not identify one cache module with the supported API."
        return response
    source, original_text = modules[0]
    tree = ast.parse(original_text)
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "appdirs"]
    if len(imports) != 1 or any(n.name != "user_cache_dir" for n in imports[0].names):
        response["error"] = "The observed appdirs API is outside the supported migration adapter."
        return response
    records, _ = declarations(repo)
    appdir_records = [r for r in records if r["name"] == "appdirs"]
    pins = {r["requirement"] for r in appdir_records if r["specifier"].startswith("==")}
    if len(pins) != 1:
        response["error"] = "A unique pinned baseline appdirs requirement is needed for reproducible installation."
        return response
    candidate_repo = output / "candidate"
    if candidate_repo.exists():
        raise ValueError("Use a fresh verification output directory.")
    shutil.copytree(repo, candidate_repo, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"), symlinks=True)
    rel_source = source.relative_to(repo)
    lines = original_text.splitlines(keepends=True)
    node = imports[0]
    if node.lineno != node.end_lineno:
        response["error"] = "Multiline appdirs import is not supported by this adapter."
        return response
    lines[node.lineno-1] = lines[node.lineno-1].replace("from appdirs import", "from platformdirs import", 1)
    (candidate_repo / rel_source).write_text("".join(lines))
    script = output / "check_cache.py"
    script.write_text(CHECK_SCRIPT)
    uv = shutil.which("uv")
    sides = {}
    for label, dependency, tree_root in (("original", next(iter(pins)), repo), ("candidate", "platformdirs", candidate_repo)):
        envdir = output / (label + "-venv")
        creation = _execute([sys.executable, "-m", "venv", "--without-pip" if uv else "--clear", str(envdir)], output)
        python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        install = creation
        if creation["status"] == "passed":
            args = [uv, "pip", "install", "--python", str(python), dependency] if uv else [str(python), "-m", "pip", "install", dependency]
            install = _execute(args, output, timeout=120)
        sides[label] = {"installation": install}
        if install["status"] == "passed":
            version = _execute([str(python), "-c", "import importlib.metadata as m; print(m.version('" + ("appdirs" if label == "original" else "platformdirs") + "'))"], output)
            response["environment"][label + "_dependency_version"] = version["log_excerpt"].strip()
            behavior = _execute([str(python), str(script), str(tree_root / rel_source), str(output / "check-home")], output, timeout=20)
            sides[label]["behavior"] = behavior
            try:
                sides[label]["values"] = json.loads(behavior["full_log"].splitlines()[0]) if behavior["status"] == "passed" else {}
            except (ValueError, IndexError):
                sides[label]["values"] = {}
        else:
            sides[label]["values"] = {}
    install_check = {"check_id": "installation", "name": "Install selected dependency in isolated environment", "scope": "installation",
                     "original": sides["original"]["installation"], "candidate": sides["candidate"]["installation"],
                     "comparison_note": "Only the dependency under comparison is installed; this is not a full project install."}
    response["checks"].append(install_check)
    for name in ("default_cache_directory", "cache_override", "missing_cache", "json_roundtrip"):
        row = {"check_id": name, "name": name.replace("_", " ").capitalize(), "scope": "focused"}
        values = []
        for side in ("original", "candidate"):
            value = sides[side]["values"].get(name)
            parent = sides[side].get("behavior", sides[side]["installation"])
            row[side] = {"status": ("passed" if value["passed"] else "failed") if value else "blocked",
                         "exit_code": parent["exit_code"], "duration_ms": parent["duration_ms"],
                         "log_excerpt": json.dumps(value) if value else parent["log_excerpt"], "log_truncated": False}
            values.append(value.get("value") if value and value["passed"] else None)
        equal = values[0] == values[1]
        row["comparison_note"] = "Observed values match." if equal and values[0] is not None else "Values differ or could not both be observed."
        row["observed_match"] = equal and all(row[s]["status"] == "passed" for s in ("original", "candidate"))
        response["checks"].append(row)
    version = response["environment"].get("candidate_dependency_version")
    if version:
        for declaration in appdir_records:
            path = candidate_repo / declaration["path"]
            path.write_text(path.read_text().replace(declaration["requirement"], "platformdirs==" + version))
        patches = []
        for relative in sorted({rel_source.as_posix(), *(r["path"] for r in appdir_records)}):
            before, after = (repo / relative).read_text(), (candidate_repo / relative).read_text()
            patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/" + relative, tofile="b/" + relative))
        patch = output / "migration.diff"
        patch.write_text("".join(patches))
        response["patch_path"] = str(patch)
        response["artifact_paths"].append(str(patch))
    statuses = [c[s]["status"] for c in response["checks"] for s in ("original", "candidate")]
    if "blocked" in statuses:
        response["outcome"] = "inconclusive"
    elif "failed" in statuses or not all(c.get("observed_match", True) for c in response["checks"]):
        response["outcome"] = "differences_found"
    else:
        response["outcome"] = "supported"
    full_logs = output / "execution-logs.json"
    full_logs.write_text(json.dumps(sides, indent=2))
    response["artifact_paths"].append(str(full_logs))
    for row in response["checks"]:
        for side in ("original", "candidate"):
            row[side].pop("full_log", None)
    (output / "verification.json").write_text(json.dumps(response, indent=2))
    return response
