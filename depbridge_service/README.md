# Service startup and frontend connection

Contract: frontend handoff version **1.0**. Base path `/api`; one Uvicorn process, one serial job worker, durable SQLite in `.depbridge/`. The adapter imports the engine when a job runs. No mock findings or verification results are supplied in production.

## Windows PowerShell startup

From `C:\Users\yadav\OneDrive\Desktop\H26_TeamApex_DepBridge`:

```powershell
Get-Location
git rev-parse --show-toplevel
git status --short --branch
# Only create a venv if absent: py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,verification]'
$env:DEPBRIDGE_PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn depbridge_service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Health: `http://127.0.0.1:8000/api/health`. Interactive API docs: `http://127.0.0.1:8000/docs`. API requests use the same origin. No CORS configuration or frontend API key is needed.

Use `-X utf8` on Windows because the imported engine writes Python check scripts containing Unicode. A default cp1252 interpreter can otherwise produce invalid script source. The Linux image sets `PYTHONUTF8=1`.

In a second PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m depbridge_cli health
.\.venv\Scripts\python.exe -m depbridge_cli analyze https://github.com/rishrek/LinkWatch --wait
.\.venv\Scripts\python.exe -m depbridge_cli status ANALYSIS_ID
.\.venv\Scripts\python.exe -m depbridge_cli verify ANALYSIS_ID FINDING_ID CANDIDATE_ID --wait
.\.venv\Scripts\python.exe -m depbridge_cli capsule ANALYSIS_ID --output .\capsule.zip
.\.venv\Scripts\python.exe -m depbridge_cli patch ANALYSIS_ID VERIFICATION_ID --output .\migration.diff
```

Use `--server https://YOUR_HOST` **before** the CLI subcommand, or set `DEPBRIDGE_SERVER`. The CLI performs HTTP requests and file downloads only. It does not clone or execute the target. Exit codes: 0 accepted/completed, 1 request/local error, 2 failed job, 3 completed verification with differences/inconclusive, 130 interrupted waiting. A partial analysis is printed honestly and exits 0. Downloads refuse existing destinations unless `--force`. Creation is not automatically retried; refresh status before resubmitting uncertain writes.

## Frontend teammate handoff

- Put the agreed static files in `frontend/index.html` and `frontend/static/` on your own branch; supply them through Git. The service never creates/edits them.
- The report route is `http://127.0.0.1:8000/reports/ANALYSIS_ID`; assets use `/static/`. Restart after the frontend first arrives so its static directory is mounted.
- POST `/api/analyses` with `repository_url` and optional `ref`. Use the returned `analysis_id`, `report_url`, `status_url`.
- Poll GET `/api/analyses/{analysis_id}` about every two seconds while the analysis or any verification is active. Stage labels reflect actual available progress; no percentage is returned.
- POST `/api/analyses/{analysis_id}/verifications` with `finding_id`, `candidate_id`. The 409 duplicate error includes `error.verification_id`.
- Errors always use `{ "error": { "code", "message", "retryable" } }`. Request validation is HTTP 422; unknown IDs are 404; busy export is 409; full queue is 429 with Retry-After.
- Downloads use server-provided URLs. Capsule is 409 before completed initial analysis or during active verification, including partial completed runs. Missing patch is 404. Report route is 503 with an explicit message until frontend files arrive.
- An unavailable engine produces a failed **live request**, `outcome=null`, `error.code=not_implemented`, a preview warning, null unassessed counts, empty findings, and no capsule. Do not substitute the handoff's design fixture automatically.
- For another computer on the same LAN, start the service with `--host 0.0.0.0`, set `DEPBRIDGE_PUBLIC_BASE_URL=http://YOUR_LAN_IP:8000` before startup, and allow the port in Windows Firewall deliberately. A teammate's separate-origin static server cannot call this API without an agreed proxy; integrate the files into this service for same-origin testing.

## Persistence, capsules, and scope

State survives restarts. Jobs interrupted by restart become `failed/service_restarted`; they are not automatically re-executed. A completed initial analysis may be success or partial. Capsule includes JSON, Markdown, escaped standalone HTML, provenance, manifest with SHA-256 hashes, explicit full-log artifacts and patches where produced. No capsule is fabricated for a failed scan.

New engine runs preserve actual argument vectors in both verification records and `commands.json`. Capsules also include the actual generated cache-check runner when referenced by recorded commands. Paths are recorded as executed; recreate local environments and substitute local paths before reproducing another machine's run.

Only `rishrek/LinkWatch` is enabled by default. `DEPBRIDGE_ALLOWED_REPOSITORIES` can be a comma-separated explicit allowlist; unrestricted repository execution is outside the prototype scope. Configure `DEPBRIDGE_PUBLIC_BASE_URL` explicitly for deployment, rather than trusting a caller-controlled Host header. Store all model keys in server environment variables. The service does not call the model itself or infer successful model access from a configured key.

The engine API and return contract is in [ENGINE_CONTRACT.md](ENGINE_CONTRACT.md). Deployment instructions are in [../deployment/README.md](../deployment/README.md). No actual repository analysis, model request, compatibility check or cloud deployment is claimed until performed with the real engine/server.

## Service checks

```powershell
.\.venv\Scripts\python.exe -m pytest depbridge_service/tests -q
.\.venv\Scripts\python.exe -m pip check
```

Service tests use explicitly controlled test engines to validate request/state/export behavior; they are not evidence of LinkWatch migration compatibility.

## Final integration acceptance

After the frontend teammate confirms their pushed branch and it is merged, restart the service with the model key configured server-side. Run this in a second local PowerShell window:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m depbridge_service.integration_check
```

This creates a **new** analysis and comparison, requires actual completed Gemma output, checks the same-origin report/assets, downloads capsule/patch files, and validates manifest hashes, recorded command arguments and the captured runner. Results are saved under a fresh ignored `.depbridge/acceptance/` directory. Missing model configuration/frontend, provider errors, unsupported comparisons or incomplete downloads fail honestly; existing output directories are not overwritten. Browser rendering still needs a visual check. Keep `main` unchanged until this complete workflow passes.
