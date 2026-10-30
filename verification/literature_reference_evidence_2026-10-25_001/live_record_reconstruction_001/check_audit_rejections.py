#!/usr/bin/env python3
"""Controlled negative checks on NEW owned copies; never modify the run/pin."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode = True
OWNED = Path(__file__).resolve().parent
AUDIT = OWNED / "audit_live_reconstruction.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    snapshot, output = args.snapshot.resolve(), args.output_directory.resolve()
    assert snapshot.is_relative_to(OWNED) and output.is_relative_to(OWNED) and not output.exists()
    output.mkdir()
    manifest = json.loads((snapshot / "snapshot_manifest.json").read_text())
    receipt = json.loads((snapshot / "receipt.json").read_text())
    pin = manifest["pin"]
    checks = []
    for case, expected in (("tampered_saved_artifact", "artifact_digest_mismatch"),
                           ("tampered_operation_cells", "saved_operation_differs_from_action_outcome")):
        destination = output / case
        destination.mkdir()
        shutil.copyfile(snapshot / "snapshot_manifest.json", destination / "snapshot_manifest.json")
        shutil.copytree(snapshot / "state", destination / "state")
        first_sheet = receipt["sheet_checks"][0]
        if case == "tampered_saved_artifact":
            sha = first_sheet["payload_sha256"]
            path = destination / "state" / "artifacts" / sha[:2] / sha
            with path.open("ab") as handle:
                handle.write(b"\n")
        else:
            with sqlite3.connect(destination / "state" / "state.sqlite3") as db:
                table = "literature_" + first_sheet["route"] + "_operations"
                rowid, data = db.execute("SELECT rowid,outcome FROM " + table + " ORDER BY rowid LIMIT 1").fetchone()
                outcome = json.loads(data)
                cell = next(iter(outcome["result"]["cells"].values()))
                cell["value"] = 123456789.0
                db.execute("UPDATE " + table + " SET outcome=? WHERE rowid=?", (json.dumps(outcome), rowid))
        result = subprocess.run([sys.executable, "-B", str(AUDIT), "--pin", pin,
                                 "--reopen-owned-copy", str(destination)], capture_output=True, text=True)
        (destination / "stderr.txt").write_text(result.stderr)
        assert result.returncode != 0 and expected in result.stderr, case
        checks.append({"case": case, "status": "expected_rejection", "expected_error": expected,
                       "exit_code": result.returncode, "origin": "controlled_tampered_owned_copy"})
    result = subprocess.run([sys.executable, "-B", str(AUDIT), "--pin", pin,
        "--run", manifest["live_run"], "--output-directory", str(snapshot)], capture_output=True, text=True)
    assert result.returncode != 0 and "output_directory_must_be_new" in result.stderr
    (output / "reuse_stderr.txt").write_text(result.stderr)
    checks.append({"case": "existing_output_directory", "status": "expected_rejection",
                   "expected_error": "output_directory_must_be_new", "exit_code": result.returncode})
    summary = {"status": "passed", "checks": checks,
               "scope": "Engineering rejection checks only; no new deliveries, inference, or source interpretation; only owned copies mutated."}
    (output / "checks.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
