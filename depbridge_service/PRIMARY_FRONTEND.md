# Primary frontend integration

The exact confirmed branch is `origin/Frontend`, commit `c6cdbfc`. The remote also contains a lowercase `frontend` branch pointing to the same commit. Windows cannot store both remote refs under those names with the current Git backend. Do not delete remote branches, force-push or migrate Git storage to work around this. Use an explicit fetch when updating:

```powershell
git fetch origin refs/heads/Frontend:refs/remotes/origin/Frontend refs/heads/engine:refs/remotes/origin/engine refs/heads/main:refs/remotes/origin/main refs/heads/service:refs/remotes/origin/service
```

The frontend is plain HTML/CSS/JS; no npm install or build is required for FastAPI/Docker serving. Its optional npm scripts only launch a static development server. The visual source loads IBM Plex fonts from Google and Tailwind from a CDN. These browser-side resources need network access; system fonts and service-owned layout CSS provide fallback styling.

## Real service data

The imported frontend's original JS contains design fixtures, timer-based test simulations and synthetic signatures. Those scripts are **not loaded in the live service**. `depbridge_service/ui.py` preserves the primary header/navigation and theme, replaces fixture sections before first paint, and loads `depbridge_service/static/primary.js` to render the actual v1 API. The original frontend and engine source files remain unchanged. Their standalone mock preview is not evidence of service behavior.

- `/` is repository submission; `/reports/{analysis_id}` fetches the actual saved report.
- Primary CSS is served at `/static/css/styles.css`; live integration JS/CSS at `/service-ui/primary.js` and `/service-ui/primary.css`.
- Existing `/static/start.html` and `/static/index.html` entry URLs redirect to the live primary page.
- Analysis Report shows actual findings, evidence, declarations, proposals and limitations.
- Migration proposals shows real recommendations and supported comparison actions; no staged codemod execution is invented.
- Verification renders original/candidate outcomes, scopes, commands and supplied log excerpts.
- Usage locations replaces the mock topology graph with recorded static usage.
- Exit Capsule uses only server-provided download URLs; no signed attestation is claimed.
- Polling uses one analysis endpoint. Duplicate active comparisons resume the existing job; exports remain blocked during active verification.

## Start locally: Windows PowerShell

From the repository root:

```powershell
$env:DEPBRIDGE_FRONTEND_DIR = 'frontend'
$env:DEPBRIDGE_PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn depbridge_service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. To select the unchanged backup, set `DEPBRIDGE_FRONTEND_DIR=demo_frontend` and restart. Inside the Docker image use `/app/frontend` or `/app/demo_frontend`. Both folders are copied and checked during build. No model keys belong in either frontend.

The model remains untested without a configured server-side key. Windows focused comparison evidence is not a Linux/full-suite result. Docker image build and DigitalOcean hosting remain unverified until performed on the deployment machine.
