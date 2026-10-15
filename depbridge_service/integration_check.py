"""Run the live acceptance workflow; never substitute design fixtures for failures."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.error import URLError
from zipfile import BadZipFile, ZipFile

from depbridge_cli.main import Client, segment, wait


def check_capsule(content, analysis_id, verification_id):
    with ZipFile(BytesIO(content)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Capsule ZIP integrity check failed")
        manifest = json.loads(archive.read("manifest.json"))
        for item in manifest["files"]:
            actual = archive.read(item["path"])
            if len(actual) != item["size_bytes"] or sha256(actual).hexdigest() != item["sha256"]:
                raise ValueError("Capsule manifest does not match its contents")
        record = json.loads(archive.read("analysis.json"))
        if record["analysis_id"] != analysis_id or record["ai"]["state"] != "completed":
            raise ValueError("Capsule does not contain this new real Gemma analysis")
        verification = next(v for v in record["verifications"] if v["verification_id"] == verification_id)
        if not verification["checks"] or any(not check[side].get("command")
                for check in verification["checks"] for side in ("original", "candidate")):
            raise ValueError("Capsule is missing actual verification command arguments")
        commands = json.loads(archive.read("commands.json"))["records"]
        expected = [(check["check_id"], side, check[side]["command"])
                    for check in verification["checks"] for side in ("original", "candidate")]
        observed = [(row["check_id"], row["side"], row["command"]) for row in commands if row["verification_id"] == verification_id]
        if observed != expected:
            raise ValueError("Capsule command inventory differs from recorded results")
        if not any(name.endswith("-check_cache.py") for name in archive.namelist()):
            raise ValueError("Capsule is missing the actual focused-check runner")
        if archive.read(f"patches/{verification_id}.diff") == b"":
            raise ValueError("Capsule patch is empty")
        return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--repository", default="https://github.com/rishrek/LinkWatch")
    parser.add_argument("--ref")
    parser.add_argument("--wait-timeout", type=float, default=600)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or Path(".depbridge") / "acceptance" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    summary = dict(status="failed", analysis_id=None, verification_id=None)
    output_created = False
    try:
        output.mkdir(parents=True, exist_ok=False)
        output_created = True
        if args.wait_timeout <= 0:
            raise ValueError("--wait-timeout must be positive")
        client = Client(args.server)
        summary["server"] = client.origin
        health = client.json("/api/health")
        (output / "health.json").write_text(json.dumps(health, indent=2), encoding="utf-8")
        if not health["engine_available"] or not health["model_configured"] or not health["frontend_available"]:
            raise ValueError("Live acceptance requires the engine, a configured server-side model key, and the integrated frontend. No analysis was created.")
        created = client.json("/api/analyses", dict(repository_url=args.repository, ref=args.ref))
        analysis_id = summary["analysis_id"] = created["analysis_id"]
        print(json.dumps(dict(stage="analysis_submitted", **created)), flush=True)
        record, analysis = wait(client, analysis_id, args.wait_timeout)
        (output / "analysis.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        if analysis["status"] != "completed" or record["ai"]["state"] != "completed":
            raise ValueError("New analysis did not complete a real Gemma request. Inspect the saved analysis record; no fixture was substituted.")
        if record["data_mode"] != "live" or not record["repository"]["revision"]:
            raise ValueError("Analysis must be live and resolve an exact revision")
        with client.open(f"/reports/{segment(analysis_id)}") as response:
            if response.headers.get_content_type() != "text/html":
                raise ValueError("Report route did not return HTML")
            html = response.read()
        (output / "report.html").write_bytes(html)
        for asset in ("app.js", "styles.css"):
            with client.open(f"/static/{asset}") as response:
                if not response.read():
                    raise ValueError(f"Frontend asset is empty: {asset}")
        finding = next(f for f in record["findings"] if f["dependency_name"] == "appdirs")
        candidate = next(c for c in finding["candidates"] if c["replacement_name"] == "platformdirs" and c["verification_supported"])
        submitted = client.json(f"/api/analyses/{segment(analysis_id)}/verifications",
                                dict(finding_id=finding["finding_id"], candidate_id=candidate["candidate_id"]))
        verification_id = summary["verification_id"] = submitted["verification_id"]
        print(json.dumps(dict(stage="verification_submitted", **submitted)), flush=True)
        record, verification = wait(client, analysis_id, args.wait_timeout, verification_id)
        (output / "analysis.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        if verification["status"] != "completed" or not verification["patch_url"]:
            raise ValueError("New verification failed or produced no downloadable patch")
        client.download(f"/api/analyses/{segment(analysis_id)}/capsule.zip", output / "capsule.zip")
        client.download(f"/api/analyses/{segment(analysis_id)}/patches/{segment(verification_id)}.diff", output / "migration.diff")
        exported = check_capsule((output / "capsule.zip").read_bytes(), analysis_id, verification_id)
        if verification["outcome"] != "supported":
            raise ValueError("Delivery completed, but selected comparison was not supported; inspect recorded differences or blockers")
        summary.update(status="passed", revision=exported["repository"]["revision"],
                       model=exported["ai"]["model_version"], comparison_outcome=verification["outcome"],
                       check_count=len(verification["checks"]), report_url=created["report_url"],
                       limitations=verification["limitations"])
        return_code = 0
    except (RuntimeError, ValueError, OSError, URLError, BadZipFile, KeyError, StopIteration) as exc:
        summary["error"] = str(exc) or type(exc).__name__
        return_code = 1
    if output_created:
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(dict(**summary, output=str(output.resolve())), indent=2))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
