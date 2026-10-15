# Engine integration

Requires Python 3.12/3.13, `packaging`, `google-genai`. Verification requires
`uv` on PATH or a working pip-enabled venv installation. No target package needs
to be installed into the service environment.

```python
from depbridge_engine import analyze_repository, verify_candidate
report = analyze_repository(repository_url, ref=None, work_dir=fresh_job_directory)
result = verify_candidate(job_directory / "repo", finding, candidate, fresh_comparison_directory)
```

Both functions are blocking: call them in your worker, never the HTTP event loop.
Service owns IDs, persistence, timestamps, status/stage transitions, capsule ZIP
and public download URLs. Engine returns dictionaries matching the frontend
contract; verification returns local `patch_path` and `artifact_paths` for service
to validate and convert to download routes. Never expose arbitrary local paths.

Set GEMINI_API_KEY or GOOGLE_API_KEY in the server environment and optionally
GEMMA_MODEL (default gemma-4-26b-a4b-it). Actual hosted availability and applicable
terms must be checked on the account. Missing keys or failed calls are explicit
and leave reference recipes labeled as such. This is not a completed Gemma demo
until a real model request succeeds.

Risk coverage is bounded and visible in coverage.limitations. Inspection clones
public HTTPS GitHub repos and never executes their code. Verification currently
executes only the organizer LinkWatch cache module; it uses separate venvs and
does not provide OS-level sandboxing. Keep verification access restricted to the
team/trusted demo, not an anonymous public execution endpoint. No full-suite or
security-audit claims are made.

Run engine tests: `python -m pytest depbridge_engine/tests -q`.
