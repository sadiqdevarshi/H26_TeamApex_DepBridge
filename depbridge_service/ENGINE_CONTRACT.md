# Engine adapter contract v1

The user supplied these synchronous imports and owns their signatures:

```python
from depbridge_engine import analyze_repository, verify_candidate
analyze_repository(repository_url, ref, work_dir)
verify_candidate(repository_dir, finding, candidate, output_dir)
```

`work_dir`, `repository_dir`, and `output_dir` are absolute `pathlib.Path` objects. The engine retrieves into **`work_dir / "repo"`**. It resolves the requested ref and returns the exact revision. It must not operate on the DepBridge application checkout. Calls run serially in one worker thread; no asyncio coroutine, shell command, network response, or engine dictionary may claim job completion directly.

The supplied signatures did not specify return schemas. The service boundary is aligned with engine commit `e78c3f1` from `origin/engine`, imported unchanged through Git. `depbridge_service/engine.py` calls the real engine functions and normalizes the known engine differences: extra repository identity fields, string AI/verification errors, evidence `sourcepath`, and verification `artifact_paths`. Declaration metadata, observed comparison matches and original/candidate dependency versions are retained. Current models strictly reject other unknown fields so incompatibilities surface as `engine_contract_error` instead of silently losing evidence. Further changes belong in the service adapter, not teammate files.

## Analysis return

A JSON-compatible mapping accepted by `depbridge_service.models.AnalysisResult`:

```python
{
    "repository": {"revision": "<actual exact commit hash, or None for a partial run>"},
    "outcome": "success",  # or "partial", only after real inspection
    "environment": {"python_version": "<observed>", "platform": "<observed>", "package_versions": {}},
    "coverage": {"scanned_files": 0, "excluded_files": 0, "unsupported_formats": [], "limitations": []},
    "summary": {"dependencies_discovered": 0},  # None means unknown; 0 means assessed and none
    "ai": {"model_name": None, "model_version": None, "access_method": None, "state": "not_run", "error": None},
    "findings": [],
    "warnings": [],
    "artifacts": [],  # explicit relative text artifact paths inside work_dir, outside repo/
}
```

This is a shape example, not live data. Do not return these counts without assessing them. `success` requires an exact revision. A failed model call after successful inspection should return `partial`, actual findings, AI error, and warnings. Missing data remains null or a recorded limitation. No placeholder model identity is supplied by the service.

Findings and candidates follow the frontend handoff fields. See `models.py` for nested field names. Optional engine finding/candidate IDs are preserved privately. The service replaces their public IDs and supplies the original normalized finding and candidate mappings back to verification. Preserve evidence IDs for candidate `evidence_ids` references; the service remaps both evidence IDs and candidate references for the public API. `verification_supported` defaults false; only enable it for an implemented comparison.

The service computes flagged findings, proposal counts and completed-comparison counts. It owns API URLs, timestamps, UUIDs, job lifecycle and persistence. The engine owns observed environment, coverage, declared dependency totals, evidence, model provenance and check results.

## Verification return

A JSON-compatible mapping accepted by `VerificationResult`:

```python
{
    "outcome": "inconclusive",  # supported / differences_found / inconclusive
    "environment": {"python_version": None, "platform": None, "package_versions": {}},
    "checks": [],
    "limitations": ["Explain checks that could not execute."],
    "patch_path": None,  # optional .diff/.patch, relative to output_dir or confined absolute path
    "artifacts": [],  # full log files, commands, reproduction notes, etc. inside output_dir
}
```

Each check contains `name`, `scope` (`installation`, `focused`, `full_suite`), `original`, `candidate`, and optional `comparison_note` and `check_id`. Each side has `status`, `exit_code`, `duration_ms`, `log_excerpt`, `log_truncated`, and optional `command` as a list of arguments. Status is `passed`, `failed`, `blocked`, `not_run`, or `skipped`. A pass requires exit code zero. `supported` requires at least one actual check with both original and candidate passing; empty, blocked or failing checks cannot produce supported. A failing baseline must remain visible and distinguishable from a migration difference.

Keep full logs in explicitly listed text artifacts; API excerpts are capped at 8,000 characters per side. Explicit `.txt`, `.log`, `.json`, `.diff`, `.patch`, `.md` artifacts are copied. The service also captures `check_cache.py` directly inside output_dir when an actual recorded command references it. Paths must stay inside their output directory, contain no hidden components/symlinks, and exclude `repo/`. Limit 10 MiB/file and 30 MiB/job. Do not include credentials or environment dumps. The service also redacts configured secret values when saving/exporting text. Return a patch with warnings even for an inconclusive comparison when useful; do not present it as verified. Engine commit `e78c3f1` supplies actual `command` arguments; the API retains them and the capsule indexes them in `commands.json`. Older saved runs still disclose their missing-command reproduction gap. A new analysis/comparison is required to establish results from the updated engine.

## Failure and execution ownership

Raise `NotImplementedError` for missing operations. An absent engine yields a persisted failed analysis with `error.code=not_implemented`, never a completed fixture or downloadable capsule. Actual live requests keep `data_mode=live` because they are real requests, with an explicit service integration preview warning on unavailable engine operations. No fake findings are inserted.

Other exceptions produce failed jobs. Invalid returns produce `engine_contract_error`; this preserves the service and exposes an integration problem. The initial API stage remains `retrieving` during the blocking analyze call; finer progress requires a future callback contract. No fabricated stage progression or percentages are emitted.

Use timeouts and bounded clones/checks. Keep credentials server-side, and strip them from verification subprocess environments. Separate baseline and candidate environments; preserve the original repository/revision so repeat comparisons remain reproducible. No upstream pushes or pull requests are part of these calls.

## Dependency coordination

Root runtime dependencies include the user-confirmed `packaging` and `google-genai`, plus FastAPI/Uvicorn. The optional `verification` extra contains `appdirs`, `platformdirs`, and `pytest`; `dev` adds HTTP test support. Tell the integration owner before adding more dependencies or changing versions. Teammate changes must arrive through Git; another laptop's WSL paths are not accessible here.
