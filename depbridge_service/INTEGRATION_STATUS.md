# Confirmed local integration milestone

## Latest integration checkpoint

The primary frontend is now integrated from the exact confirmed branch `origin/Frontend`, commit `c6cdbfc`. The lowercase remote alias points to the same commit but collides on Windows; the integration used explicit ref fetches. The README-only merge conflict retained the reviewed service release documentation. Engine and frontend source remain identical to their imported commits.

The live primary uses the teammate's visual shell with a service-owned v1 API adapter. Imported fixture data, timer-based verification and synthetic signature exports are not loaded. Primary entry is `/`; reports are `/reports/{analysis_id}`; Docker/Compose default to `/app/frontend`, with `/app/demo_frontend` retained as fallback. No Node build is required.

Fresh primary-UI run: analysis `ana_0d8a89080bd7464abcd3ca894e570741`, comparison `ver_b24a5ac90a854a81b5bd5d1c4333b98d`, target revision `f52f3930c8e7c33d934ccf614955a38e26984bd5`. Browser submission and polling worked; selected installation and four focused cache checks completed as `supported`; real capsule and patch downloads succeeded. The report remains `partial`, `ai.state=not_run` because no server-side key is configured here. Full-suite and Linux verification remain untested. Final service/engine suites: **24 passed**; package build and Compose configuration checks pass. Docker image build and actual cloud hosting remain unverified.

## Previous backup integration checkpoint

Engine `e78c3f1` and backup UI `fdfd236` were merged through Git into `service`. At this earlier checkpoint the primary frontend had not yet been merged. The backup is selected with `DEPBRIDGE_FRONTEND_DIR=demo_frontend` for local PowerShell and `/app/demo_frontend` inside the container. The user authorized finalizing and publishing the tested local integration to `main`, with remaining model/deployment gaps disclosed. Historical test counts below describe their recorded checkpoints.

A new analysis `ana_4489bda41f1a45598b5170f085ea18bd` was submitted from `/static/start.html` and resolved LinkWatch revision `f52f3930c8e7c33d934ccf614955a38e26984bd5`. Its new comparison `ver_b6050cc9326e4f2ebcbdb17887e5fa8c` completed as `supported` for the selected installations and four focused cache checks. Capsule and patch downloads succeeded through the actual browser UI. The capsule contains actual argument vectors in `commands.json` and the captured generated runner. The report shows the real partial state and model-unavailable message; it does not substitute mock data.

**Full live Gemma acceptance remains blocked:** this machine has no configured `GEMINI_API_KEY` or `GOOGLE_API_KEY`. The new analysis is explicitly `partial`, `ai.state=not_run`, with reference recipes. The automated acceptance command fails its model preflight honestly. A further new analysis and comparison with an actual completed model call is required before declaring the entire live model workflow passed. Publication of the local prototype does not change that evidence boundary.

Deployment includes an IP-only server template (`deployment/service.env.example`), a configurable container frontend directory, and a Docker build check for both backup HTML files. Actual server secrets stay outside Git. No DigitalOcean deployment or container image build is claimed.

## Earlier checkpoint (retained history)

Recorded 15 October 2026. This is evidence of local Windows execution, not DigitalOcean deployment or complete Track 1 readiness.

- Engine commit `2b8e045` was fetched from `origin/engine` and imported unchanged through Git. No engine/frontend source was edited by the service implementation.
- Service and engine test suites: **15 passed**. One upstream test-client deprecation warning remains; dependency consistency checks pass.
- Real target: `https://github.com/rishrek/LinkWatch`, exact revision `f52f3930c8e7c33d934ccf614955a38e26984bd5`.
- Local analysis `ana_45ff68853a344bffbe573b7a62624e7b`: completed, **partial**. Fourteen declared dependencies, three flagged dependencies, three reference proposals. These are bounded engine observations, not an exhaustive risk assessment.
- Gemma state: **not_run** because no server model key was configured. Reference recipes remain explicitly labeled. A configured key alone will not prove a model call succeeded.
- Local verification `ver_0915c6c9b49f41eb954bf7809ea1306c`: selected appdirs-to-platformdirs comparison completed as **supported**, using appdirs 1.4.4 and platformdirs 4.13.0 on Windows/Python 3.12.10. Both selected installations passed; default cache directory, cache override, missing cache, and JSON roundtrip checks passed on both sides. Full project installation and full LinkWatch test suite were not executed. Other platforms are unverified.
- A proposed migration patch was produced. Review is still required before adoption; the upstream target was not changed.
- Engine command arguments are absent from check records. Full returned logs are retained, and the service explicitly marks exact command reproduction incomplete. This needs engine coordination for stronger reproducibility.
- Docker Compose configuration validates. A Docker image build was not verified because Docker Desktop's Linux engine was not running. No Droplet credentials or domain were supplied, and no cloud deployment is claimed.

On the machine that performed this run, use `http://127.0.0.1:8000/api/analyses/ana_45ff68853a344bffbe573b7a62624e7b` for the actual response. A separate clone must run the startup commands in `README.md` and create its own analysis; localhost URLs and analysis IDs are local to this service's persistence.

The static frontend is owned by the frontend teammate. Until their files are integrated through Git, the API is usable while `/reports/{analysis_id}` returns an explicit 503 explaining the absent frontend. API contract and connection instructions are in `README.md`; engine normalization is documented in `ENGINE_CONTRACT.md`.
