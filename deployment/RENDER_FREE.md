# Free full-stack Render demo

Deploy branch `deploy-render` as one Docker Web Service, plan **Free**,
Dockerfile `deployment/Dockerfile.render`, root build context `.`.
Health endpoint: `/api/health`. No database, persistent disk, paid worker,
or GPU is required. Set `GEMINI_API_KEY` as a Render secret and
`GEMMA_MODEL=gemma-4-26b-a4b-it`. `render.yaml` also supports Blueprint setup.

The root URL serves the real working live UI (`demo_frontend`). The separately
authored `frontend/` is preserved, but currently contains simulated data and
must not replace the live UI until wired to the API. All report and download
routes share the service origin, so no CORS configuration is necessary.

The start script reads Render's PORT and RENDER_EXTERNAL_URL; generated CLI,
report and download links use the public HTTPS origin, not localhost.

CLI from any laptop with the project installed:
`python -m depbridge_cli --server https://YOUR-SERVICE.onrender.com health`
`python -m depbridge_cli --server https://YOUR-SERVICE.onrender.com analyze https://github.com/rishrek/LinkWatch --wait`

Free Render instances sleep after 15 minutes without inbound traffic. Local
SQLite jobs and generated files disappear on restart, redeploy, or sleep.
Download capsules and patches before leaving the demo; this is temporary demo
hosting, not persistent production storage. First requests after sleep are slow.
Free-tier CPU and RAM are limited; compare one migration at a time.

No arbitrary repositories are enabled. Repository code executes only through
the existing bounded organizer-target adapter, without model credentials in
the subprocess environment. No full-project suite success is claimed.

Official sources: https://render.com/docs/free and https://render.com/docs/docker
