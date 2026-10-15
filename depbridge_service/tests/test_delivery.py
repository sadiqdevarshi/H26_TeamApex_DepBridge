"""Delivery tests only: controlled engine results are NOT LinkWatch execution evidence."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import time
from zipfile import ZipFile

from fastapi.testclient import TestClient
import pytest

from depbridge_cli.main import Client, main
from depbridge_service.app import create_app
from depbridge_service.config import Settings
from depbridge_service.engine import EngineAdapter
from depbridge_service.models import AnalysisResult, VerificationResult
from depbridge_service.integration_check import asset_paths, check_capsule, main as acceptance_main
from depbridge_service.service import Service, artifact_path


TARGET = "https://github.com/rishrek/LinkWatch"


class ControlledEngine:
    def __init__(self, *, gate=None, analysis_gate=None, supported=True, bad_artifact=False):
        self.gate = gate
        self.analysis_gate = analysis_gate
        self.supported = supported
        self.bad_artifact = bad_artifact
        self.received = None

    def available(self):
        return True

    def analyze_repository(self, repository_url, ref, work_dir):
        assert isinstance(work_dir, Path)
        assert repository_url == TARGET
        if self.analysis_gate:
            assert self.analysis_gate.wait(10)
        (work_dir / "repo").mkdir()
        return dict(repository=dict(revision="a" * 40), outcome="partial",
            environment=dict(python_version="3.12.10", platform="controlled-test-environment"),
            coverage=dict(scanned_files=1, excluded_files=0, limitations=["Controlled service test; no real repository was analyzed."]),
            summary=dict(dependencies_discovered=1), ai=dict(state="not_run"), warnings=[],
            findings=[dict(finding_id="engine-finding", dependency_name="test-only", declarations=[],
                risk_type="maintenance_signal", title="<script>alert('test')</script>",
                explanation="Controlled test finding", evidence_strength="needs_review", usage=[],
                evidence=[dict(evidence_id="engine-evidence", kind="test", title="test", observation="test")],
                candidates=[dict(candidate_id="engine-candidate", rationale="Controlled test", recommendation_source="test_fixture",
                    verification_supported=self.supported, evidence_ids=["engine-evidence"], limitations=[])], limitations=[])])

    def verify_candidate(self, repository_dir, finding, candidate, output_dir):
        assert repository_dir.name == "repo" and repository_dir.is_dir()
        self.received = (finding, candidate)
        if self.gate:
            assert self.gate.wait(10)
        (output_dir / "comparison.log").write_text("controlled complete log\n" + "x" * 9000, encoding="utf-8")
        (output_dir / "candidate.diff").write_text("--- a/test\n+++ b/test\n@@ -1 +1 @@\n-old\n+new\n", encoding="utf-8")
        # A failed baseline is kept separate from a passing candidate; never call this supported.
        return dict(outcome="inconclusive", environment=dict(platform="controlled-test-environment"),
            checks=[dict(name="Controlled comparison", scope="focused",
                original=dict(status="failed", exit_code=1, duration_ms=2, log_excerpt="x" * 9000, command=["test-only"]),
                candidate=dict(status="passed", exit_code=0, duration_ms=1, log_excerpt="controlled candidate output"),
                comparison_note="Baseline failed; migration safety is not established.")],
            limitations=["Controlled service test; no real checks were executed."], patch_path="candidate.diff",
            artifacts=["../outside.log"] if self.bad_artifact else ["comparison.log"])


def settings(tmp_path, **kwargs):
    return Settings(data_dir=tmp_path / "data", frontend_dir=tmp_path / "frontend",
                    public_base_url="http://testserver", **kwargs)


def poll(client, analysis_id, verification_id=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/api/analyses/{analysis_id}")
        assert response.status_code == 200
        record = response.json()
        item = next(v for v in record["verifications"] if v["verification_id"] == verification_id) if verification_id else record
        if item["status"] in {"completed", "failed"}:
            return record
        time.sleep(.01)
    pytest.fail("service job did not finish")


def create(client):
    response = client.post("/api/analyses", json=dict(repository_url=TARGET))
    assert response.status_code == 202
    assert response.json()["report_url"].startswith("http://testserver/reports/")
    return response.json()["analysis_id"]


def pair(record):
    finding = record["findings"][0]
    return dict(finding_id=finding["finding_id"], candidate_id=finding["candidates"][0]["candidate_id"])


def test_missing_engine_honestly_fails_and_persists(tmp_path):
    config = settings(tmp_path)
    with TestClient(create_app(config, EngineAdapter("preview"))) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        assert record["status"] == "failed"
        assert record["error"]["code"] == "not_implemented"
        assert record["outcome"] is None and record["findings"] == []
        assert record["summary"]["dependencies_discovered"] is None
        assert record["downloads"]["capsule_url"] is None
        assert client.get(f"/api/analyses/{analysis_id}/capsule.zip").status_code == 409
    with TestClient(create_app(config, EngineAdapter("preview"))) as client:
        assert client.get(f"/api/analyses/{analysis_id}").json() == record


def test_api_export_patch_ids_and_evidence(tmp_path):
    engine = ControlledEngine()
    config = settings(tmp_path)
    with TestClient(create_app(config, engine)) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        assert record["status"] == "completed" and record["outcome"] == "partial"
        finding = record["findings"][0]
        assert finding["finding_id"] != "engine-finding"
        assert finding["candidates"][0]["evidence_ids"] == [finding["evidence"][0]["evidence_id"]]
        assert not any(k.startswith("_") for k in record)
        response = client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record))
        assert response.status_code == 202
        verification_id = response.json()["verification_id"]
        record = poll(client, analysis_id, verification_id)
        verification = record["verifications"][0]
        assert verification["status"] == "completed"
        assert verification["outcome"] == "inconclusive"
        assert any("command reproduction is incomplete" in message for message in verification["limitations"])
        assert verification["checks"][0]["original"]["status"] == "failed"
        assert len(verification["checks"][0]["original"]["log_excerpt"]) == 8000
        assert verification["checks"][0]["original"]["log_truncated"] is True
        assert engine.received[0]["finding_id"] == "engine-finding"
        assert engine.received[1]["candidate_id"] == "engine-candidate"
        patch = client.get(verification["patch_url"])
        assert patch.status_code == 200 and patch.text.startswith("--- a/test")
        capsule = client.get(record["downloads"]["capsule_url"])
        assert capsule.status_code == 200
        with ZipFile(BytesIO(capsule.content)) as archive:
            names = archive.namelist()
            assert all(not name.startswith("/") and ".." not in Path(name).parts for name in names)
            assert {"analysis.json", "report.html", "REPRODUCE.md", "manifest.json", "provenance.json"} <= set(names)
            assert f"patches/{verification_id}.diff" in names
            assert b"<script>" not in archive.read("report.html")
            assert b"&lt;script&gt;" in archive.read("report.html")
            for item in json.loads(archive.read("manifest.json"))["files"]:
                assert sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
            full = next(name for name in names if name.endswith("execution-record.json"))
            assert len(json.loads(archive.read(full))["checks"][0]["original"]["log_excerpt"]) == 9000


def test_duplicate_verification_and_export_lock(tmp_path):
    gate = Event()
    with TestClient(create_app(settings(tmp_path), ControlledEngine(gate=gate))) as client:
        try:
            analysis_id = create(client)
            record = poll(client, analysis_id)
            first = client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record))
            assert first.status_code == 202
            duplicate = client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record))
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["verification_id"] == first.json()["verification_id"]
            assert client.get(f"/api/analyses/{analysis_id}/capsule.zip").status_code == 409
            assert not client.get(f"/api/analyses/{analysis_id}").json()["downloads"]["capsule_available"]
        finally:
            gate.set()
        poll(client, analysis_id, first.json()["verification_id"])


def test_bounded_queue_and_validation(tmp_path):
    gate = Event()
    with TestClient(create_app(settings(tmp_path, max_pending_jobs=1), ControlledEngine(analysis_gate=gate))) as client:
        for url in ("https://github.com/other/repo", "file:///tmp/repo", "https://user:pass@github.com/rishrek/LinkWatch", TARGET + "?token=secret"):
            response = client.post("/api/analyses", json=dict(repository_url=url))
            assert response.status_code == 422 and "error" in response.json()
        assert client.post("/api/analyses", json=dict(repository_url=TARGET, ref="--upload-pack=evil")).status_code == 422
        assert client.get("/api/analyses/missing").status_code == 404
        analysis_id = create(client)
        try:
            busy = client.post("/api/analyses", json=dict(repository_url=TARGET))
            assert busy.status_code == 429 and busy.headers["Retry-After"] == "5"
        finally:
            gate.set()
        poll(client, analysis_id)


def test_no_supported_outcome_without_actual_paired_passes():
    with pytest.raises(ValueError):
        VerificationResult.model_validate(dict(outcome="supported", environment={}, checks=[]))


def test_unsupported_verification_and_path_escape(tmp_path):
    with TestClient(create_app(settings(tmp_path), ControlledEngine(supported=False))) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        assert client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record)).json()["error"]["code"] == "verification_not_supported"
        assert client.get(f"/api/analyses/{analysis_id}/patches/missing.diff").status_code == 404
    with pytest.raises(ValueError):
        artifact_path(tmp_path, "../secret.log")
    hidden = tmp_path / ".env"
    hidden.write_text("secret")
    with pytest.raises(ValueError):
        artifact_path(tmp_path, str(hidden))


def test_invalid_artifact_fails_comparison_without_patch(tmp_path):
    with TestClient(create_app(settings(tmp_path), ControlledEngine(bad_artifact=True))) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        verification_id = client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record)).json()["verification_id"]
        record = poll(client, analysis_id, verification_id)
        verification = record["verifications"][0]
        assert verification["status"] == "failed" and verification["outcome"] is None
        assert verification["error"]["code"] == "engine_contract_error"
        assert verification["patch_url"] is None


def test_restart_recovery_and_single_process(tmp_path):
    config = settings(tmp_path)
    service = Service(config, ControlledEngine())
    with pytest.raises(RuntimeError, match="Another service process"):
        Service(config, ControlledEngine())
    service.store.save(dict(analysis_id="interrupted", status="running", stage="retrieving", outcome=None, error=None, verifications=[]))
    service.close()
    service = Service(config, ControlledEngine())
    try:
        record = service.get("interrupted")
        assert record["status"] == "failed" and record["error"]["code"] == "service_restarted"
    finally:
        service.close()


def test_frontend_same_origin_and_secret_redaction(tmp_path, monkeypatch):
    config = settings(tmp_path)
    config.frontend_dir.mkdir()
    (config.frontend_dir / "static").mkdir()
    (config.frontend_dir / "index.html").write_text("<!doctype html><title>controlled frontend</title>")
    (config.frontend_dir / "static" / "app.js").write_text("// controlled asset")
    monkeypatch.setenv("GEMINI_API_KEY", "service-test-secret-key")
    class SecretEngine(ControlledEngine):
        def analyze_repository(self, *args):
            result = super().analyze_repository(*args)
            result["warnings"] = ["test secret: service-test-secret-key"]
            (args[2] / "evidence.log").write_text("server key: service-test-secret-key", encoding="utf-8")
            result["artifacts"] = ["evidence.log"]
            return result
    with TestClient(create_app(config, SecretEngine())) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        assert record["warnings"] == ["test secret: [REDACTED]"]
        assert client.get(f"/reports/{analysis_id}").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/api/health").json()["model_configured"] is True
        with ZipFile(BytesIO(client.get(f"/api/analyses/{analysis_id}/capsule.zip").content)) as archive:
            assert all(b"service-test-secret-key" not in archive.read(name) for name in archive.namelist())


def test_cli_download_is_atomic_and_refuses_overwrite(tmp_path, monkeypatch):
    client = Client("http://localhost:8000")
    monkeypatch.setattr(client, "open", lambda path: BytesIO(b"controlled download"))
    destination = tmp_path / "capsule.zip"
    assert client.download("/test", destination) == str(destination.resolve())
    assert destination.read_bytes() == b"controlled download"
    with pytest.raises(ValueError, match="already exists"):
        client.download("/test", destination)
    monkeypatch.setattr(client, "open", lambda path: BytesIO(b"replacement"))
    client.download("/test", destination, force=True)
    assert destination.read_bytes() == b"replacement"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["capsule.zip"]


def test_cli_failure_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(Client, "json", lambda *args, **kwargs: dict(status="failed", error=dict(code="not_implemented")))
    assert main(["status", "test-analysis"]) == 2
    assert "not_implemented" in capsys.readouterr().out


def test_adapter_normalizes_pushed_engine_shapes(tmp_path, monkeypatch):
    raw = dict(repository=dict(url=TARGET, name="LinkWatch", requested_ref=None, revision="a" * 40),
        outcome="partial", environment={}, coverage={}, summary={},
        ai=dict(state="not_run", error="Model key is not configured"), warnings=[],
        findings=[dict(dependency_name="test", declarations=[dict(path="requirements.txt", requirement="test==1", name="test", specifier="==1", marker=None, group="requirements")],
            risk_type="conflicting_constraints", title="Test", explanation="Test", evidence_strength="confirmed", candidates=[], usage=[],
            evidence=[dict(kind="repository_metadata", title="Test", sourcepath="requirements.txt", observation="Test")])])
    verification = dict(outcome="inconclusive", environment=dict(original_dependency_version="1.4.4", candidate_dependency_version="4.0"),
                        checks=[], error="Could not execute comparison", artifact_paths=[], patch_path=None)
    module = SimpleNamespace(analyze_repository=lambda *args: raw, verify_candidate=lambda *args: verification)
    adapter = EngineAdapter()
    monkeypatch.setattr(adapter, "_module", lambda: module)
    result = AnalysisResult.model_validate(adapter.analyze_repository(TARGET, None, tmp_path))
    assert result.ai.error.code == "model_unavailable"
    assert result.findings[0].evidence[0].source_path == "requirements.txt"
    assert result.findings[0].declarations[0].group == "requirements"
    result = VerificationResult.model_validate(adapter.verify_candidate(tmp_path, {}, {}, tmp_path))
    assert result.error.code == "verification_incomplete"
    assert result.environment.candidate_dependency_version == "4.0"
    assert "sourcepath" in raw["findings"][0]["evidence"][0]  # Adapter does not mutate engine-owned data.


def test_capsule_preserves_recorded_commands_and_generated_runner(tmp_path):
    class RecordedCommandsEngine(ControlledEngine):
        def analyze_repository(self, *args):
            result = super().analyze_repository(*args)
            result["ai"] = dict(state="completed", model_name="controlled-test-only", model_version="controlled-test-only")
            return result

        def verify_candidate(self, *args):
            result = super().verify_candidate(*args)
            runner = args[3] / "check_cache.py"
            runner.write_text("# controlled test runner, not an actual LinkWatch execution\n", encoding="utf-8")
            for check in result["checks"]:
                for side in ("original", "candidate"):
                    check[side]["command"] = ["test-only-python", str(runner)]
            return result

    with TestClient(create_app(settings(tmp_path), RecordedCommandsEngine())) as client:
        analysis_id = create(client)
        record = poll(client, analysis_id)
        verification_id = client.post(f"/api/analyses/{analysis_id}/verifications", json=pair(record)).json()["verification_id"]
        record = poll(client, analysis_id, verification_id)
        assert not any("command reproduction is incomplete" in line for line in record["verifications"][0]["limitations"])
        content = client.get(f"/api/analyses/{analysis_id}/capsule.zip").content
        exported = check_capsule(content, analysis_id, verification_id)
        assert exported["verifications"][0]["checks"][0]["original"]["command"][0] == "test-only-python"
        with ZipFile(BytesIO(content)) as archive:
            runner_name = next(name for name in archive.namelist() if name.endswith("-check_cache.py"))
            assert archive.read(runner_name).startswith(b"# controlled test runner")


def test_acceptance_preserves_existing_output_directory(tmp_path, capsys):
    saved = tmp_path / "summary.json"
    saved.write_text("existing result", encoding="utf-8")
    assert acceptance_main(["--output", str(tmp_path)]) == 1
    assert saved.read_text(encoding="utf-8") == "existing result"


def test_acceptance_supports_inline_backup_and_external_primary_assets():
    assert asset_paths(b"<style>body{}</style><script>/* inline */</script>", "http://testserver", "/reports/id") == []
    html = b'<script src="/static/app.js"></script><link rel="stylesheet" href="/static/styles.css"><script src="https://other.invalid/x.js"></script>'
    assert asset_paths(html, "http://testserver", "/reports/id") == ["/static/app.js", "/static/styles.css"]
