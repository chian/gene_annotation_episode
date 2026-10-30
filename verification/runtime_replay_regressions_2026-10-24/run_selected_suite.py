"""Repeat the original selected suite without overwriting its failure evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from diagnose import ROOT, hashes, write_json


def main():
    output = Path(__file__).resolve().parent / "selected-suite"
    output.mkdir(exist_ok=False)
    source = ROOT / "verification/runtime_original_controller_input_2026-10-24/RUN.json"
    original = json.loads(source.read_text())
    command = [argument if not argument.startswith("--junitxml=") else
        "--junitxml=" + str(output / "pytest.xml") for argument in original["command"]]
    command.extend(["--basetemp=" + str(output / "pytest-temp"), "-p", "no:cacheprovider"])
    before = hashes()
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    with (output / "pytest.txt").open("w") as log:
        completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    after = hashes()
    write_json(output / "RUN.json", {
        "command": command, "cwd": str(ROOT), "original_suite_manifest": str(source),
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - tick, "exit_code": completed.returncode,
        "source_sha256_before": before, "source_sha256_after": after,
        "source_versions_unchanged": before == after,
        "verification_kind": "same_selected_generic_replay_and_original_completion_regressions_after_two_fixture_repairs",
    })
    assert before == after, "inspected shared source changed during selected suite"
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
