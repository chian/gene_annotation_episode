"""Capture only explicit help/version calls under the existing bounded runner.

This test executes no database operand, input preparation, search, installation,
or remote operation. It establishes executable CLI availability only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest


PROGRAMS = (
    "blast_formatter", "blast_formatter_vdb", "blast_vdb_cmd",
    "blastdb_aliastool", "blastdbcheck", "blastdbcmd", "convert2blastmask",
    "makeblastdb", "makembindex", "makeprofiledb",
)


def _pin(path):
    content = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content)}


def test_explicit_native_help_and_version_only():
    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the selected existing 529 bounded runner")
    attempt = Path(location)
    snapshot = Path(__file__).resolve().parents[1]
    selected = json.loads((attempt / "selected_native_executables.json").read_text())
    binaries = {Path(path).name: Path(path) for path in selected}
    assert set(binaries) == set(PROGRAMS)
    assert len(binaries) == len(selected)
    assert all(path.is_relative_to(snapshot) for path in binaries.values())
    destination = attempt / "temporary/blast_utility_help"
    destination.mkdir(exist_ok=False)
    environment = dict(os.environ)
    environment["BLAST_USAGE_REPORT"] = "false"
    environment["NCBI_DONT_USE_NCBIRC"] = "1"
    cases = []
    for program in PROGRAMS:
        executable = binaries[program]
        for mode in ("help", "version"):
            argv = [str(executable), "-" + mode]
            stdout = destination / (program + "." + mode + ".stdout")
            stderr = destination / (program + "." + mode + ".stderr")
            case = {"program": program, "mode": mode, "argv": argv,
                    "cwd": str(destination), "shell": False,
                    "executable": _pin(executable), "executed": False,
                    "returncode": None, "launch_error": None}
            with stdout.open("wb") as output, stderr.open("wb") as errors:
                try:
                    result = subprocess.run(argv, cwd=destination, env=environment,
                                            stdout=output, stderr=errors, check=False)
                except OSError as error:
                    case["launch_error"] = {"type": type(error).__name__,
                                            "errno": error.errno}
                else:
                    case.update(executed=True, returncode=result.returncode)
            case.update(stdout=_pin(stdout), stderr=_pin(stderr))
            cases.append(case)
            (destination / "CAPTURE_001.json").write_text(json.dumps({
                "record_type": "blast_utility_explicit_help_version_capture_v1",
                "policy": {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'swap_bytes': 0},
                "environment_overrides": {"BLAST_USAGE_REPORT": "false",
                                          "NCBI_DONT_USE_NCBIRC": "1"},
                "cases": cases,
                "limit": "CLI availability only; no database or native operation verified",
            }, indent=2) + "\n")
    assert len(cases) == 20
    assert all(case["executed"] and case["returncode"] == 0 for case in cases), cases
    assert all(case["stdout"]["size_bytes"] > 0 for case in cases), cases
