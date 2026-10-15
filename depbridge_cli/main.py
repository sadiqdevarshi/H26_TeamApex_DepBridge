import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


class Client:
    def __init__(self, origin, timeout=30):
        self.origin = origin.rstrip("/")
        parsed = urlsplit(self.origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise ValueError("--server must be an HTTP(S) origin without credentials")
        self.timeout = timeout

    def open(self, path, body=None):
        request = Request(self.origin + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Accept": "application/json", **({"Content-Type": "application/json"} if body is not None else {})})
        try:
            return urlopen(request, timeout=self.timeout)
        except HTTPError as exc:
            try:
                error = json.loads(exc.read())["error"]
                message = f"HTTP {exc.code} {error['code']}: {error['message']}"
                if error.get("verification_id"):
                    message += f" (existing verification: {error['verification_id']})"
            except (ValueError, KeyError, TypeError):
                message = f"HTTP {exc.code}: service request failed"
            raise RuntimeError(message) from exc

    def json(self, path, body=None):
        with self.open(path, body) as response:
            return json.load(response)

    def download(self, path, destination, force=False):
        destination = Path(destination).resolve()
        if destination.exists() and not force:
            raise ValueError(f"File already exists: {destination}; choose another path or use --force")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with self.open(path) as response, tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                temporary = Path(output.name)
                while block := response.read(1024 * 1024):
                    output.write(block)
            if force:
                temporary.replace(destination)
            else:
                # Hard link creates the final file exclusively, preventing an overwrite race.
                os.link(temporary, destination)
            return str(destination)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def segment(value):
    return quote(value, safe="")


def wait(client, analysis_id, timeout, verification_id=None):
    deadline = time.monotonic() + timeout
    path = f"/api/analyses/{segment(analysis_id)}"
    while True:
        record = client.json(path)
        item = next((v for v in record["verifications"] if v["verification_id"] == verification_id), None) if verification_id else record
        if item is None:
            raise RuntimeError("Verification not found in analysis record")
        if item["status"] in {"completed", "failed"}:
            return record, item
        if time.monotonic() >= deadline:
            raise TimeoutError("Polling timed out; the server-side job may still be running. Use status before resubmitting.")
        time.sleep(min(2, max(0, deadline - time.monotonic())))


def main(argv=None):
    parser = argparse.ArgumentParser(description="DepBridge thin service client")
    parser.add_argument("--server", default=os.getenv("DEPBRIDGE_SERVER", "http://127.0.0.1:8000"))
    parser.add_argument("--request-timeout", type=float, default=30)
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("repository_url")
    analyze.add_argument("--ref")
    for command in (analyze,):
        command.add_argument("--wait", action="store_true")
        command.add_argument("--wait-timeout", type=float, default=600)
    status = commands.add_parser("status")
    status.add_argument("analysis_id")
    status.add_argument("--wait", action="store_true")
    status.add_argument("--wait-timeout", type=float, default=600)
    verify = commands.add_parser("verify")
    verify.add_argument("analysis_id")
    verify.add_argument("finding_id")
    verify.add_argument("candidate_id")
    verify.add_argument("--wait", action="store_true")
    verify.add_argument("--wait-timeout", type=float, default=600)
    capsule = commands.add_parser("capsule")
    capsule.add_argument("analysis_id")
    capsule.add_argument("--output", type=Path)
    capsule.add_argument("--force", action="store_true")
    patch = commands.add_parser("patch")
    patch.add_argument("analysis_id")
    patch.add_argument("verification_id")
    patch.add_argument("--output", type=Path)
    patch.add_argument("--force", action="store_true")
    commands.add_parser("health")
    args = parser.parse_args(argv)
    try:
        if args.request_timeout <= 0 or getattr(args, "wait_timeout", 1) <= 0:
            raise ValueError("Timeouts must be positive")
        client = Client(args.server, args.request_timeout)
        terminal = None
        if args.command == "health":
            result = client.json("/api/health")
        elif args.command == "analyze":
            result = client.json("/api/analyses", dict(repository_url=args.repository_url, ref=args.ref))
            if args.wait:
                print(json.dumps(result, indent=2), flush=True)
                result, terminal = wait(client, result["analysis_id"], args.wait_timeout)
        elif args.command == "status":
            if args.wait:
                result, terminal = wait(client, args.analysis_id, args.wait_timeout)
            else:
                result = client.json(f"/api/analyses/{segment(args.analysis_id)}")
                terminal = result
        elif args.command == "verify":
            result = client.json(f"/api/analyses/{segment(args.analysis_id)}/verifications", dict(finding_id=args.finding_id, candidate_id=args.candidate_id))
            if args.wait:
                print(json.dumps(result, indent=2), flush=True)
                result, terminal = wait(client, args.analysis_id, args.wait_timeout, result["verification_id"])
        else:
            analysis = segment(args.analysis_id)
            if args.command == "capsule":
                path = f"/api/analyses/{analysis}/capsule.zip"
                output = args.output or Path(f"{args.analysis_id}-capsule.zip")
            else:
                path = f"/api/analyses/{analysis}/patches/{segment(args.verification_id)}.diff"
                output = args.output or Path(f"{args.verification_id}.diff")
            result = dict(saved_to=client.download(path, output, args.force))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if terminal and terminal["status"] == "failed":
            return 2
        if terminal and terminal.get("outcome") in {"differences_found", "inconclusive"}:
            return 3
        return 0
    except (ValueError, RuntimeError, OSError, URLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Stopped waiting; a submitted server job may still be running.", file=sys.stderr)
        return 130
