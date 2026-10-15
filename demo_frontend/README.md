# Independent demo frontend

This backup does not alter the separately owned `frontend/` directory. No build
step, external fonts, dependencies, model keys, or mock results are required.

Merge origin/engine into the service integration branch, then set:

PowerShell: `$env:DEPBRIDGE_FRONTEND_DIR = 'demo_frontend'`

Ubuntu: `export DEPBRIDGE_FRONTEND_DIR=demo_frontend`

Restart the service. Open `/static/start.html` to submit the first repository.
The app then navigates to `/reports/{analysis_id}`. The service's existing root
route does not serve a landing page; this frontend does not modify service code.
Use `/reports/{id}` to reopen a report. Requests use the same origin as the API.

When the primary frontend is ready, change DEPBRIDGE_FRONTEND_DIR to `frontend`
and restart. Service owns its route configuration; no file overwrite is needed.

The Docker image must COPY demo_frontend if selecting this folder in deployment;
the integration owner should verify its Dockerfile before using this backup.
