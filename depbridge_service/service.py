from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import traceback
from threading import BoundedSemaphore
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import ValidationError

from .engine import EngineAdapter, EngineUnavailable
from .models import AnalysisResult, VerificationResult
from .store import Store
from .process_lock import ProcessLock


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    return f"{prefix}_{uuid4().hex}"


class ServiceError(Exception):
    def __init__(self, status, code, message, retryable=False, **details):
        self.status = status
        self.error = dict(code=code, message=message, retryable=retryable, **details)
        super().__init__(message)


def redact(value):
    """Prevent configured credentials from appearing in records or exported logs."""
    secrets = [v for k, v in os.environ.items() if v and len(v) >= 8 and any(
        word in k.upper() for word in ("API_KEY", "TOKEN", "PASSWORD", "SECRET")
    )]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def artifact_path(root: Path, supplied: str):
    root = root.resolve()
    path = Path(supplied)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("Artifact must be inside its engine output directory")
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError("Symlink artifacts are not supported")
    relative = resolved.relative_to(root)
    if any(p.startswith(".") or p in {"repo", "secrets"} for p in relative.parts):
        raise ValueError("Hidden files and repository files cannot be exported")
    generated_runner = resolved.parent == root and resolved.name == "check_cache.py"
    if resolved.suffix.lower() not in {".txt", ".log", ".json", ".diff", ".patch", ".md"} and not generated_runner:
        raise ValueError("Only explicit text evidence artifacts can be exported")
    if not resolved.is_file() or resolved.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Artifact is absent or exceeds 10 MiB")
    return resolved


class Service:
    def __init__(self, settings, engine=None):
        self.settings = settings
        self.process_lock = ProcessLock(settings.data_dir)
        self.store = Store(settings.data_dir)
        self.engine = engine or EngineAdapter(settings.engine_mode)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="depbridge")
        self.slots = BoundedSemaphore(settings.max_pending_jobs)
        self.recover()

    def close(self):
        try:
            self.executor.shutdown(wait=True)
        finally:
            self.process_lock.close()

    def recover(self):
        with self.store.lock:
            for record in self.store.all():
                changed = False
                if record["status"] in {"queued", "running"}:
                    record.update(status="failed", stage="finished", outcome=None, error=self.interrupted())
                    changed = True
                for verification in record["verifications"]:
                    if verification["status"] in {"queued", "running"}:
                        verification.update(status="failed", stage="finished", outcome=None, error=self.interrupted())
                        verification["updated_at"] = now()
                        changed = True
                if changed:
                    self.save(record)

    @staticmethod
    def interrupted():
        return dict(code="service_restarted", message="Service restarted before this job finished. Submit a new job to retry.", retryable=True)

    def get(self, analysis_id):
        record = self.store.get(analysis_id)
        if record is None:
            raise ServiceError(404, "analysis_not_found", "Analysis not found.")
        return record

    def urls(self, analysis_id):
        origin = self.settings.public_base_url
        return dict(status_url=f"{origin}/api/analyses/{analysis_id}", report_url=f"{origin}/reports/{analysis_id}")

    @staticmethod
    def export_reason(record):
        if record["status"] != "completed":
            return "Initial analysis has not completed; no capsule is available."
        if any(v["status"] in {"queued", "running"} for v in record["verifications"]):
            return "A verification is active; wait before exporting a stable snapshot."
        return None

    def public(self, record):
        result = {k: v for k, v in record.items() if not k.startswith("_")}
        result["verifications"] = [dict(verification, patch_url=(
            f"{self.settings.public_base_url}/api/analyses/{record['analysis_id']}/patches/{verification['verification_id']}.diff"
            if verification["verification_id"] in record["_patches"] else None
        )) for verification in record["verifications"]]
        for verification in result["verifications"]:
            verification["limitations"] = list(verification["limitations"])
            if verification["checks"] and any(not check[side].get("command")
                    for check in verification["checks"] for side in ("original", "candidate")):
                verification["limitations"].append("The engine did not supply every executed command's arguments; exact command reproduction is incomplete. Consult the full logs and engine source.")
        reason = self.export_reason(record)
        result["downloads"] = dict(
            capsule_available=reason is None,
            capsule_url=f"{self.settings.public_base_url}/api/analyses/{record['analysis_id']}/capsule.zip" if reason is None else None,
            unavailable_reason=reason,
        )
        return redact(result)

    def save(self, record):
        record["updated_at"] = now()
        self.store.save(record)

    def normalize_repository(self, url):
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise ServiceError(422, "invalid_repository", "Use a valid public GitHub HTTPS URL.") from exc
        if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or parsed.query or parsed.fragment
                or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", parsed.path)):
            raise ServiceError(422, "invalid_repository", "Use a public https://github.com/owner/repository URL without credentials, query or fragment.")
        name = parsed.path.strip("/").removesuffix(".git")
        if name.lower() not in self.settings.allowed_repositories:
            raise ServiceError(422, "repository_not_allowed", "This prototype only analyzes repositories explicitly enabled by the server operator.")
        return f"https://github.com/{name}", name

    def reserve(self):
        if not self.slots.acquire(blocking=False):
            raise ServiceError(429, "capacity_exceeded", "The single worker's queue is full. Retry later.", True)

    def submit(self, function, *args):
        def run():
            try:
                function(*args)
            finally:
                self.slots.release()
        try:
            self.executor.submit(run)
        except RuntimeError:
            self.slots.release()
            raise ServiceError(503, "service_stopping", "Service is stopping.", True)

    def create(self, request):
        url, name = self.normalize_repository(request.repository_url)
        with self.store.lock:
            self.reserve()
            analysis_id = identifier("ana")
            stamp = now()
            record = dict(
                schema_version="1.0", data_mode="live", analysis_id=analysis_id, status="queued", stage="queued", outcome=None,
                repository=dict(url=url, name=name, requested_ref=request.ref, revision=None),
                environment=dict(python_version=None, platform=None), created_at=stamp, updated_at=stamp,
                coverage=dict(scanned_files=None, excluded_files=None, unsupported_formats=[], limitations=[]),
                summary=dict(dependencies_discovered=None, dependencies_flagged=None, migration_proposals=None, completed_comparisons=0),
                ai=dict(model_name=None, model_version=None, access_method=None, state="not_run", error=None),
                findings=[], verifications=[], warnings=[], error=None,
                _inputs={}, _artifacts=[], _patches={}, _service_versions=self.versions(),
            )
            try:
                self.store.save(record)
            except Exception:
                self.slots.release()
                raise
            self.submit(self.analyze, analysis_id)
            return dict(analysis_id=analysis_id, status="queued", **self.urls(analysis_id))

    @staticmethod
    def versions():
        packages = {}
        for name in ("depbridge", "fastapi", "uvicorn", "packaging", "google-genai", "appdirs", "platformdirs", "pytest"):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                pass
        return packages

    def work_dir(self, analysis_id):
        path = self.settings.data_dir / "jobs" / analysis_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def capture_artifacts(self, root, paths, destination):
        """Copy only explicit, confined text artifacts into service-owned immutable storage."""
        destination.mkdir(parents=True, exist_ok=True)
        stored = []
        total = 0
        for index, supplied in enumerate(paths):
            path = artifact_path(root, supplied)
            total += path.stat().st_size
            if total > 30 * 1024 * 1024:
                raise ValueError("Evidence exceeds 30 MiB per job")
            content = redact(path.read_text(encoding="utf-8", errors="replace"))
            target = destination / f"{index:03d}-{path.name}"
            target.write_text(content, encoding="utf-8")
            stored.append(str(target.relative_to(self.settings.data_dir)))
        return stored

    def failure(self, exc):
        if isinstance(exc, (EngineUnavailable, NotImplementedError)):
            return dict(code="not_implemented", message="not implemented: the requested engine operation is unavailable.", retryable=False)
        if isinstance(exc, (ValidationError, ValueError, TypeError, KeyError)):
            return dict(code="engine_contract_error", message="Engine returned an invalid result or artifact. See the engine adapter contract.", retryable=False)
        return dict(code="engine_failed", message="Engine execution failed. No successful result is claimed; inspect server-side diagnostics.", retryable=True)

    def analyze(self, analysis_id):
        try:
            with self.store.lock:
                record = self.get(analysis_id)
                record.update(status="running", stage="retrieving")
                self.save(record)
            work = self.work_dir(analysis_id)
            result = AnalysisResult.model_validate(self.engine.analyze_repository(
                record["repository"]["url"], record["repository"]["requested_ref"], work
            )).model_dump()
            result = redact(result)
            artifacts = self.capture_artifacts(work, result.pop("artifacts"), work / "captured" / "analysis")
            with self.store.lock:
                record = self.get(analysis_id)
                record["repository"]["revision"] = result["repository"]["revision"]
                for key in ("environment", "coverage", "summary", "ai", "warnings", "outcome"):
                    record[key] = result[key]
                # Public IDs belong to the service; retain original engine inputs privately.
                for finding in result["findings"]:
                    source_finding = json.loads(json.dumps(finding))
                    finding_id = identifier("fnd")
                    finding["finding_id"] = finding_id
                    evidence_ids = {}
                    for evidence in finding["evidence"]:
                        original_id = evidence["evidence_id"]
                        evidence["evidence_id"] = identifier("evd")
                        if original_id:
                            if original_id in evidence_ids:
                                raise ValueError("Duplicate engine evidence ID")
                            evidence_ids[original_id] = evidence["evidence_id"]
                    for index, candidate in enumerate(finding["candidates"]):
                        candidate_id = identifier("can")
                        record["_inputs"][candidate_id] = dict(finding=source_finding, candidate=source_finding["candidates"][index])
                        candidate["candidate_id"] = candidate_id
                        candidate["evidence_ids"] = [evidence_ids[value] for value in candidate["evidence_ids"]]
                        if not candidate["verification_supported"] and not candidate["unsupported_reason"]:
                            candidate["unsupported_reason"] = "not implemented: engine does not support verification of this proposal."
                record["findings"] = result["findings"]
                record["summary"]["dependencies_flagged"] = len({finding["dependency_name"] for finding in record["findings"]})
                record["summary"]["migration_proposals"] = sum(len(f["candidates"]) for f in record["findings"])
                record["summary"]["completed_comparisons"] = 0
                record["_artifacts"] = artifacts
                record.update(status="completed", stage="finished", error=None)
                self.save(record)
        except Exception as exc:
            self.diagnostic(analysis_id, exc)
            with self.store.lock:
                record = self.get(analysis_id)
                error = self.failure(exc)
                record.update(status="failed", stage="finished", outcome=None, error=error)
                if error["code"] == "not_implemented":
                    record["warnings"].append("Service integration preview: analysis engine is not implemented. No repository scan or tests have run.")
                self.save(record)

    def diagnostic(self, analysis_id, exc):
        # Private diagnostics never appear in the API or capsule.
        try:
            detail = "".join(traceback.format_exception(exc))
            with (self.work_dir(analysis_id) / "service-diagnostics.log").open("a", encoding="utf-8") as output:
                output.write(redact(f"{now()}\n{detail}\n"))
        except OSError:
            pass

    def verify(self, analysis_id, request):
        with self.store.lock:
            record = self.get(analysis_id)
            if record["status"] != "completed":
                raise ServiceError(409, "analysis_not_ready", "Complete the initial analysis before requesting verification.")
            finding = next((f for f in record["findings"] if f["finding_id"] == request.finding_id), None)
            candidate = next((c for c in finding["candidates"] if c["candidate_id"] == request.candidate_id), None) if finding else None
            if candidate is None:
                raise ServiceError(404, "candidate_not_found", "Finding/candidate pair not found in this analysis.")
            for existing in record["verifications"]:
                if existing["finding_id"] == request.finding_id and existing["candidate_id"] == request.candidate_id and existing["status"] in {"queued", "running"}:
                    raise ServiceError(409, "verification_active", "This comparison is already active.", verification_id=existing["verification_id"])
            if not candidate["verification_supported"]:
                raise ServiceError(422, "verification_not_supported", candidate["unsupported_reason"] or "This candidate has no executable comparison.")
            self.reserve()
            verification_id = identifier("ver")
            stamp = now()
            record["verifications"].append(dict(
                verification_id=verification_id, finding_id=request.finding_id, candidate_id=request.candidate_id,
                status="queued", stage="queued", outcome=None, environment=dict(python_version=None, platform=None),
                checks=[], limitations=[], error=None, patch_url=None, created_at=stamp, updated_at=stamp,
            ))
            try:
                self.save(record)
            except Exception:
                self.slots.release()
                raise
            self.submit(self.run_verification, analysis_id, verification_id)
            return dict(verification_id=verification_id, status="queued", analysis_id=analysis_id)

    def run_verification(self, analysis_id, verification_id):
        def locate(record):
            return next(v for v in record["verifications"] if v["verification_id"] == verification_id)
        try:
            with self.store.lock:
                record = self.get(analysis_id)
                verification = locate(record)
                verification.update(status="running", stage="verifying", updated_at=now())
                inputs = record["_inputs"][verification["candidate_id"]]
                self.save(record)
            work = self.work_dir(analysis_id)
            repository = work / "repo"
            if not repository.is_dir() or repository.is_symlink():
                raise ValueError("Engine did not retrieve the target into work_dir/repo")
            output = work / "verifications" / verification_id
            output.mkdir(parents=True, exist_ok=True)
            result = VerificationResult.model_validate(self.engine.verify_candidate(
                repository, inputs["finding"], inputs["candidate"], output
            )).model_dump()
            result = redact(result)
            paths = result.pop("artifacts")
            patch_path = result.pop("patch_path")
            # Retain the full engine-supplied check record before capping API excerpts.
            (output / "execution-record.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            paths.append("execution-record.json")
            # Retain the actual generated runner referenced by recorded command arguments.
            # Restrict this exception to the known engine runner directly inside output_dir.
            runner = output / "check_cache.py"
            if runner.is_file() and any(str(runner) in (check[side].get("command") or [])
                    for check in result["checks"] for side in ("original", "candidate")):
                paths.append("check_cache.py")
            if patch_path:
                if Path(patch_path).suffix.lower() not in {".diff", ".patch"}:
                    raise ValueError("Patch must be a .diff or .patch artifact")
                paths.append(patch_path)
            artifacts = self.capture_artifacts(output, paths, work / "captured" / verification_id)
            with self.store.lock:
                record = self.get(analysis_id)
                verification = locate(record)
                verification.update(result, status="completed", stage="finished", updated_at=now())
                for check in verification["checks"]:
                    check["check_id"] = identifier("chk")
                    for side in (check["original"], check["candidate"]):
                        text = side["log_excerpt"]
                        if text is not None and len(text) > 8000:
                            side["log_excerpt"] = text[:8000]
                            side["log_truncated"] = True
                record["_artifacts"].extend(artifacts)
                if patch_path:
                    record["_patches"][verification_id] = artifacts[-1]
                    verification["patch_url"] = f"{self.settings.public_base_url}/api/analyses/{analysis_id}/patches/{verification_id}.diff"
                record["summary"]["completed_comparisons"] = sum(v["status"] == "completed" for v in record["verifications"])
                self.save(record)
        except Exception as exc:
            self.diagnostic(analysis_id, exc)
            with self.store.lock:
                record = self.get(analysis_id)
                locate(record).update(status="failed", stage="finished", outcome=None, error=self.failure(exc), updated_at=now())
                self.save(record)
