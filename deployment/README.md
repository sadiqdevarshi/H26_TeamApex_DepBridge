# DigitalOcean deployment

This is deployment setup, not a claim that a Droplet has been provisioned. No server credentials or model keys belong in Git. The service needs one process and one job worker; do not scale replicas against the same SQLite volume.

## Local Windows PowerShell

Run from the repository Git root, on `service`:

```powershell
Get-Location
git rev-parse --show-toplevel
git status --short --branch
py -3.12 -m venv .venv  # Only if the virtual environment does not already exist.
.\.venv\Scripts\python.exe -m pip install -e '.[dev,verification]'
$env:DEPBRIDGE_PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn depbridge_service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

The service does not automatically load `.env`. Set environment variables in PowerShell, or pass an external environment file to Docker Compose. Do not activate a different Python installation. A 3.13 environment also works.

## DigitalOcean server only: Ubuntu/Linux commands

The following commands run over SSH on the DigitalOcean Droplet, **not in local PowerShell**. Use a Droplet with enough disk for clones and verification environments; the example limits the application container to 2 GiB RAM and two CPUs. Install Docker Engine and the Compose plugin using Docker's official Ubuntu instructions. Ensure Git is installed.

```sh
git clone --branch service https://github.com/sadiqdevarshi/H26_TeamApex_DepBridge.git /opt/depbridge
cd /opt/depbridge
sudo install -d -m 700 /etc/depbridge
sudo install -m 600 .env.example /etc/depbridge/service.env
sudoedit /etc/depbridge/service.env
```

Set these values in `/etc/depbridge/service.env`:

```dotenv
DEPBRIDGE_PUBLIC_BASE_URL=https://depbridge.example.org
DEPBRIDGE_SITE_ADDRESS=depbridge.example.org
DEPBRIDGE_ENGINE_MODE=auto
DEPBRIDGE_ALLOWED_REPOSITORIES=rishrek/LinkWatch
DEPBRIDGE_MAX_PENDING_JOBS=8
GEMINI_API_KEY=replace-on-server-only
```

Use the real domain, point its DNS to the Droplet, and allow inbound TCP 80/443. Restrict inbound SSH (22) to your own IP in the DigitalOcean Cloud Firewall. Keep API port 8000 unpublished. Caddy handles HTTPS for the domain. For an initial IP-only HTTP check, use `DEPBRIDGE_SITE_ADDRESS=:80` and `DEPBRIDGE_PUBLIC_BASE_URL=http://YOUR_DROPLET_IP` instead.

```sh
# DigitalOcean server only
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml up -d --build
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml ps
curl --fail https://depbridge.example.org/api/health
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml logs --tail=100 api
```

Merge/review the engine and frontend through Git before building the integrated image. The frontend must provide `frontend/index.html` and `frontend/static/`; no Node build is required for the handoff's static layout. Rebuild after merging either component. Restarted queued/running jobs become honest failures rather than silently resuming repository execution.

```sh
# DigitalOcean server only: update after reviewed Git integration
cd /opt/depbridge
git pull --ff-only origin service
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml up -d --build
```

The named `depbridge_data` volume contains SQLite, work directories and captured artifacts. Back it up while the application is stopped; do not delete it on update. Capsules are generated from a stable saved record on demand. Stop the application with `docker compose ... stop`; avoid `down -v`, which deletes persistence.

## Execution boundary

This is a controlled event prototype with no account/authentication system. Only the configured target is allowed, and the job queue is bounded. Do not broaden repository access for a public multi-user deployment: the imported engine and its subprocesses execute repository-controlled code. The engine must isolate verification environments, enforce clone/execution time and disk limits, and remove model credentials from subprocess environments. The API container is non-root with limited resources, but is not a per-job security sandbox. Changing a key requires recreating the API container. No deployment has been verified until the actual server smoke checks pass.

Sources: [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/), [DigitalOcean firewall rules](https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
