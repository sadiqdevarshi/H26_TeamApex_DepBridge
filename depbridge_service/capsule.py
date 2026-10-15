from hashlib import sha256
from html import escape
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from .service import ServiceError, now, redact


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def build_capsule(service, analysis_id):
    # Hold the same lock as submission to prevent an export racing verification.
    with service.store.lock:
        record = service.get(analysis_id)
        reason = service.export_reason(record)
        if reason:
            raise ServiceError(409, "capsule_unavailable", reason, record["status"] in {"queued", "running"} or record["status"] == "completed")
        public = service.public(record)
        exported_at = now()
        text = json.dumps(public, ensure_ascii=False, indent=2)
        repository = public["repository"]
        report = (
            f"# DepBridge Dependency Exit Capsule\n\n"
            f"Repository: {repository['url']}\n\nRevision: {repository['revision'] or 'Not established'}\n\n"
            f"Analysis: {analysis_id}\n\nOutcome: {public['outcome']}\n\nExported at: {exported_at}\n\n"
            "Observed findings, recommendations and executed checks remain separate in analysis.json.\n"
            "A proposal is not proof of compatibility. A passing selected check is limited to its recorded scope and environment.\n\n"
            "## Warnings and unresolved coverage\n\n"
            + "\n".join(f"- {line}" for line in public["warnings"] + public["coverage"]["limitations"])
            + "\n\n## Complete record\n\n```json\n" + text + "\n```\n"
        )
        html = (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>DepBridge offline report</title><style>body{font:16px system-ui;margin:2rem auto;max-width:72rem;padding:0 1rem}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f9;padding:1rem}</style>'
            '<h1>DepBridge offline report</h1><p>Recorded evidence and limitations. Recommendations are not executed results.</p>'
            f'<pre>{escape(report)}</pre></html>'
        )
        reproduction = (
            "# Reproduction and interpretation\n\n"
            "1. Inspect analysis.json for the exact repository revision, observed environment, evidence sources, model provenance, and limitations.\n"
            "2. Clone the recorded public repository in a separate workspace and check out its recorded exact revision. If null, reproduction is incomplete.\n"
            "3. Use the Python and package versions actually recorded by the engine, not the service package list.\n"
            "4. Review each original/candidate check's command and full logs under artifacts/. Missing commands/logs are an explicit reproduction gap.\n"
            "5. Review patches before applying them on your own branch. A patch can accompany an inconclusive or failed comparison.\n"
            "6. Repeat the recorded checks in isolated environments. No upstream repository was modified by this export.\n\n"
            "No generic test command is presented as an executed check. Unsupported platforms and unexecuted checks remain unverified.\n"
        )
        entries = {
            "analysis.json": encode(public), "findings.json": encode(public["findings"]),
            "verifications.json": encode(public["verifications"]), "report.md": report.encode(),
            "report.html": html.encode(), "REPRODUCE.md": reproduction.encode(),
            "provenance.json": encode(dict(schema_version="1.0", exported_at=exported_at,
                analysis_updated_at=record["updated_at"], repository=repository, environment=public["environment"],
                ai=public["ai"], service_package_versions=record["_service_versions"],
                limitations=["Service package versions describe the service, not the target verification environment."])),
        }
        for index, supplied in enumerate(record["_artifacts"]):
            path = (service.settings.data_dir / supplied).resolve()
            if not path.is_relative_to(service.settings.data_dir) or not path.is_file() or path.is_symlink():
                raise ServiceError(409, "artifact_unavailable", "A recorded evidence artifact is unavailable; capsule export is blocked.")
            entries[f"artifacts/{index:03d}-{path.name}"] = redact(path.read_text(encoding="utf-8")).encode()
        for verification_id, supplied in record["_patches"].items():
            path = service.settings.data_dir / supplied
            entries[f"patches/{verification_id}.diff"] = redact(path.read_text(encoding="utf-8")).encode()
        manifest = dict(schema_version="1.0", analysis_id=analysis_id, exported_at=exported_at,
                        files=[dict(path=name, size_bytes=len(content), sha256=sha256(content).hexdigest()) for name, content in sorted(entries.items())])
        entries["manifest.json"] = encode(manifest)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        return buffer.getvalue()
