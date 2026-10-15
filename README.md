# DepBridge

**Team Apex | Dependency migration backed by evidence**

DepBridge inspects a public Python repository for supported dependency risks, maps observed usage, requests Gemma migration recommendations when configured, and compares an implemented replacement against selected checks. A browser report and downloadable Dependency Exit Capsule keep observations, recommendations, execution results and unresolved concerns together.

This is the team application repository. The initial analysis target is [rishrek/LinkWatch](https://github.com/rishrek/LinkWatch); the service does not push changes to that target or create upstream pull requests.

## Verified status

| Capability | Local evidence/status |
|---|---|
| FastAPI, CLI and persistent jobs | Implemented; one server process and one serial job worker |
| Actual analysis | LinkWatch revision `f52f3930c8e7c33d934ccf614955a38e26984bd5`; 14 declared dependencies, three flagged dependencies |
| Browser UI | Integrated backup in `demo_frontend/`; submission, polling and comparison tested |
| appdirs → platformdirs comparison | Both selected installations and four focused cache checks passed on Windows/Python 3.12.10 |
| Capsule/patch delivery | Actual browser/CLI downloads checked; capsule hashes, command records, generated runner and patch applicability verified |
| Live Gemma request | **Unverified locally: no key configured.** Recorded analyses are partial, with reference recipes |
| Docker image build | **Unverified: Docker's Linux engine was not running.** Compose configuration validates |
| Cloud hosting | **Unverified. No DigitalOcean deployment or public URL is claimed** |

The primary frontend remains a separate contribution. This release contains the tested backup UI. Publication to `main` is a local prototype release, not proof of complete model or deployment acceptance.

## Windows PowerShell setup

Requirements: Git, Python **3.12 or 3.13**, and outbound access to the allowed repository, evidence sources and package index. Model access also needs a valid server-side Google API key and applicable account access.

```powershell
git clone https://github.com/sadiqdevarshi/H26_TeamApex_DepBridge.git
Set-Location .\H26_TeamApex_DepBridge
Get-Location
git rev-parse --show-toplevel
git status --short --branch
py -3.12 -m venv .venv # Only if .venv does not already exist; 3.13 also works.
.\.venv\Scripts\python.exe -m pip install -e '.[dev,verification]'
$env:DEPBRIDGE_PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
$env:DEPBRIDGE_FRONTEND_DIR = 'demo_frontend'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn depbridge_service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Open [the entry page](http://127.0.0.1:8000/static/start.html), [API docs](http://127.0.0.1:8000/docs), or [health](http://127.0.0.1:8000/api/health). The report and API share an origin. UTF-8 mode supports the engine's generated scripts on Windows. No virtual-environment activation is needed.

Keep `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the service environment, outside Git. The service does **not** automatically load `.env`. A configured key does not establish a successful call: inspect the returned AI state. Never put keys in frontend files, URLs or committed examples.

## CLI

In a second PowerShell window, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m depbridge_cli analyze https://github.com/rishrek/LinkWatch --wait
.\.venv\Scripts\python.exe -m depbridge_cli status ANALYSIS_ID
.\.venv\Scripts\python.exe -m depbridge_cli verify ANALYSIS_ID FINDING_ID CANDIDATE_ID --wait
.\.venv\Scripts\python.exe -m depbridge_cli capsule ANALYSIS_ID --output .\capsule.zip
.\.venv\Scripts\python.exe -m depbridge_cli patch ANALYSIS_ID VERIFICATION_ID --output .\migration.diff
```

Use IDs and download availability from the actual record. For a remote server, set `DEPBRIDGE_SERVER` or put `--server http://DROPLET_IP` before the subcommand. Downloads refuse existing destinations by default. The CLI sends HTTP requests; inspection and verification run in the service.

## Architecture, API and dependencies

`CLI/browser → FastAPI → single worker → depbridge_engine → SQLite/artifacts → report/capsule`

The service owns IDs, timestamps, job state, persistence, public URLs and exports. The engine retrieves into `work_dir/repo`, inspects source, requests recommendations and returns comparison evidence through `analyze_repository(repository_url, ref, work_dir)` and `verify_candidate(repository_dir, finding, candidate, output_dir)`. The service adapter normalizes results and reports unavailable operations as `not_implemented`, never fabricated completion.

Version 1 routes are `POST /api/analyses`, `GET /api/analyses/{id}`, `POST /api/analyses/{id}/verifications`, `GET /api/analyses/{id}/capsule.zip`, `GET /api/analyses/{id}/patches/{verification_id}.diff`, `GET /reports/{id}`, and `GET /api/health`. The analysis record is the shared polling endpoint; export is blocked while verification is active.

Capsules contain structured results, offline HTML/Markdown, provenance, supplied full logs, actual argument vectors in `commands.json`, a captured check runner when referenced, available patches, available target license files and SHA-256 hashes. Original machine paths need adapting elsewhere. State is stored in ignored `.depbridge/`; interrupted jobs become explicit failures after restart.

Runtime dependencies: FastAPI, Uvicorn, packaging and google-genai. The `verification` extra adds appdirs, platformdirs and pytest; `dev` adds HTTP test support. See [third-party acknowledgments](THIRD_PARTY_NOTICES.md).

## Model disclosure

The configured default is **Google Gemma 4**, identifier `gemma-4-26b-a4b-it`, accessed through the hosted Gemini API and `google-genai`. It proposes rationale, steps, suggested checks and limitations from bounded observed context. Inspection and the implemented comparison adapter establish facts and executed results. Model weights are not bundled.

[MODEL_TERMS.md](MODEL_TERMS.md) records official sources, Apache-2.0 model licensing, separate hosted API terms and data handling. A hosted identifier is not an immutable weight revision. The recorded local runs did not call Gemma; their proposals remain labeled reference recipes.

## Validation and deployment

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest depbridge_service/tests depbridge_engine/tests -q
.\.venv\Scripts\python.exe -m pip check
# Requires configured model access and served UI; creates a new live analysis/comparison:
.\.venv\Scripts\python.exe -X utf8 -m depbridge_service.integration_check --start-path /static/start.html
```

The test suites include controlled fixtures and are not evidence of full LinkWatch compatibility. The local browser/comparison/download workflow was exercised with real repository evidence. The model acceptance command fails honestly when no key is configured. [Integration status](depbridge_service/INTEGRATION_STATUS.md) records the actual runs and gaps.

[DigitalOcean instructions](deployment/README.md) distinguish **Linux server commands** from local PowerShell. The IP-only template uses `DEPBRIDGE_SITE_ADDRESS=:80`, `DEPBRIDGE_PUBLIC_BASE_URL=http://DROPLET_IP` and `DEPBRIDGE_FRONTEND_DIR=/app/demo_frontend`. Replace the IP and keep keys in `/etc/depbridge/service.env`. Docker build and cloud hosting remain unverified.

## Limitations

- Only the explicitly allowed public LinkWatch target is enabled by default. Private repositories, local uncommitted changes and large-repository completeness are outside the demo.
- Rules cover appdirs/nose maintenance evidence and selected exact-pin conflicts. Static usage can miss dynamic/indirect imports; transitive dependencies and unsupported manifests are incomplete.
- Only the appdirs-to-platformdirs cache comparison is automated. Full project installation, full-suite tests and other platforms are unverified. Selected passing checks do not guarantee safety.
- There is no authentication or per-job OS sandbox. Virtual environments/container limits are not hostile-code isolation. Restrict verification to trusted demo use.
- One process/worker and SQLite are prototype choices. Do not run multiple replicas against the same data directory.
- Provider/evidence/network errors stay visible. Model availability, quota, cost and account eligibility are not guaranteed; live failures never become mock success.

## License and further documentation

Team Apex's original code is [MIT licensed](LICENSE). Dependencies, target source and model/API access retain their own licenses and terms. The starter README remains in Git history.

[Service setup and frontend handoff](depbridge_service/README.md) · [Engine adapter contract](depbridge_service/ENGINE_CONTRACT.md) · [Deployment](deployment/README.md)
