# DigitalOcean deployment

This is deployment setup, not a claim that a Droplet has been provisioned. No server credentials or model keys belong in Git. The service needs one process and one job worker; do not scale replicas against the same SQLite volume.

## Local Windows PowerShell

Run from the repository Git root. The finalized local prototype is published on `main`; integration history remains on `service`:

```powershell
Get-Location
git rev-parse --show-toplevel
git status --short --branch
py -3.12 -m venv .venv  # Only if the virtual environment does not already exist.
.\.venv\Scripts\python.exe -m pip install -e '.[dev,verification]'
$env:DEPBRIDGE_PUBLIC_BASE_URL = 'http://127.0.0.1:8000'
$env:DEPBRIDGE_FRONTEND_DIR = 'demo_frontend'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn depbridge_service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

The service does not automatically load `.env`. Set environment variables in PowerShell, or pass an external environment file to Docker Compose. Do not activate a different Python installation. A 3.13 environment also works.

## DigitalOcean server only: Ubuntu/Linux commands

The following commands run over SSH on the DigitalOcean Droplet, **not in local PowerShell**. Use a Droplet with enough disk for clones and verification environments; the example limits the application container to 2 GiB RAM and two CPUs. Install Docker Engine and the Compose plugin using Docker's official Ubuntu instructions. Ensure Git is installed.

```sh
git clone --branch main https://github.com/sadiqdevarshi/H26_TeamApex_DepBridge.git /opt/depbridge
cd /opt/depbridge
sudo install -d -m 700 /etc/depbridge
sudo test -e /etc/depbridge/service.env || sudo install -m 600 deployment/service.env.example /etc/depbridge/service.env
sudoedit /etc/depbridge/service.env
```

For the initial IP-only deployment, set these values in `/etc/depbridge/service.env`:

```dotenv
DEPBRIDGE_PUBLIC_BASE_URL=http://DROPLET_IP
DEPBRIDGE_SITE_ADDRESS=:80
DEPBRIDGE_FRONTEND_DIR=/app/demo_frontend
DEPBRIDGE_ENGINE_MODE=auto
DEPBRIDGE_ALLOWED_REPOSITORIES=rishrek/LinkWatch
DEPBRIDGE_MAX_PENDING_JOBS=8
GEMINI_API_KEY=replace-on-server-only
```

Replace `DROPLET_IP` with the actual public IP. Allow inbound TCP 80 and restrict inbound SSH (22) to your own IP in the DigitalOcean Cloud Firewall. Keep API port 8000 unpublished. The template leaves model keys blank; enter a real key only in this server-side file. HTTP is for the initial IP-only demo. For a domain with HTTPS later, point DNS to the Droplet, allow TCP 443, set `DEPBRIDGE_SITE_ADDRESS` to the domain and `DEPBRIDGE_PUBLIC_BASE_URL` to its HTTPS origin, then recreate the containers.

```sh
# DigitalOcean server only
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml up -d --build
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml ps
curl --fail http://DROPLET_IP/api/health
curl --fail http://DROPLET_IP/static/start.html
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml logs --tail=100 api
```

The integrated backup from engine commit `fdfd236` provides `demo_frontend/index.html` and `demo_frontend/static/start.html`; the Docker build copies it and the default image serves it. Open `/static/start.html` to submit a repository. No Node build is required. When the primary frontend is confirmed pushed and reviewed, merge it through Git and set `DEPBRIDGE_FRONTEND_DIR=/app/frontend` in the server environment file. Rebuild after merging either component. Restarted queued/running jobs become honest failures rather than silently resuming repository execution.

Compose uses `${DEPBRIDGE_FRONTEND_DIR:-/app/demo_frontend}` rather than hardcoding the primary folder. Use absolute container paths in the server file: `/app/demo_frontend` for the backup or `/app/frontend` for the primary. The Dockerfile copies the repository including the backup and checks that both backup HTML files exist before completing the build. Configuration changes require recreating the API container; they do not require copying files over a teammate's frontend.

```sh
# DigitalOcean server only: update after reviewed Git integration
cd /opt/depbridge
git pull --ff-only origin main
sudo docker compose --env-file /etc/depbridge/service.env -f deployment/compose.yaml up -d --build
```

The named `depbridge_data` volume contains SQLite, work directories and captured artifacts. Back it up while the application is stopped; do not delete it on update. Capsules are generated from a stable saved record on demand. Stop the application with `docker compose ... stop`; avoid `down -v`, which deletes persistence.

## Execution boundary

This is a controlled event prototype with no account/authentication system. Only the configured target is allowed, and the job queue is bounded. Do not broaden repository access for a public multi-user deployment: the imported engine and its subprocesses execute repository-controlled code. The engine must isolate verification environments, enforce clone/execution time and disk limits, and remove model credentials from subprocess environments. The API container is non-root with limited resources, but is not a per-job security sandbox. Changing a key requires recreating the API container. No deployment has been verified until the actual server smoke checks pass.

Sources: [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/), [DigitalOcean firewall rules](https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
