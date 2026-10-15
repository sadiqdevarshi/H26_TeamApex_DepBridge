"""Only boundary that imports the separately owned engine."""
from importlib import import_module
from copy import deepcopy


class EngineUnavailable(NotImplementedError):
    pass


class EngineAdapter:
    def __init__(self, mode="auto"):
        self.mode = mode

    def _module(self):
        if self.mode == "preview":
            raise EngineUnavailable("not implemented: engine disabled in explicit preview mode")
        try:
            module = import_module("depbridge_engine")
        except ModuleNotFoundError as exc:
            if exc.name == "depbridge_engine":
                raise EngineUnavailable("not implemented: depbridge_engine is not available in this checkout") from exc
            raise  # A missing engine dependency is a real failure, not preview data.
        if not all(callable(getattr(module, name, None)) for name in ("analyze_repository", "verify_candidate")):
            raise EngineUnavailable("not implemented: depbridge_engine must export analyze_repository and verify_candidate")
        return module

    def available(self):
        try:
            self._module()
            return True
        except (EngineUnavailable, ImportError):
            return False

    def analyze_repository(self, repository_url, ref, work_dir):
        result = deepcopy(self._module().analyze_repository(repository_url, ref, work_dir))
        if not isinstance(result, dict):
            raise ValueError("Engine analysis result must be a mapping")
        repository = result.get("repository", {})
        if repository.get("url", repository_url).lower().removesuffix(".git").rstrip("/") != repository_url.lower().rstrip("/"):
            raise ValueError("Engine analyzed a different repository URL")
        result["repository"] = {"revision": repository.get("revision")}
        ai = result.get("ai", {})
        if isinstance(ai.get("error"), str):
            ai["error"] = dict(code="model_unavailable" if ai.get("state") == "not_run" else "model_failed", message=ai["error"], retryable=True)
        for finding in result.get("findings", []):
            for evidence in finding.get("evidence", []):
                if "sourcepath" in evidence:
                    evidence["source_path"] = evidence.pop("sourcepath")
        return result

    def verify_candidate(self, repository_dir, finding, candidate, output_dir):
        result = deepcopy(self._module().verify_candidate(repository_dir, finding, candidate, output_dir))
        if not isinstance(result, dict):
            raise ValueError("Engine verification result must be a mapping")
        if "artifact_paths" in result:
            result["artifacts"] = result.pop("artifact_paths")
        if isinstance(result.get("error"), str):
            result["error"] = dict(code="verification_incomplete", message=result["error"], retryable=False)
        return result
