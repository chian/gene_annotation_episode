"""Retain bounded checks and before/after code identities; no source copying."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTS = [
    "tests/test_literature_rate_meaning_delivery_143.py",
    "tests/test_literature_parent_population_information.py",
    str((HERE / "test_primary_meaning_delivery_143.py").relative_to(ROOT)),
]


def fingerprint():
    paths = set(ROOT.joinpath("gene_annotation_episode").rglob("*.py"))
    paths.update(ROOT.joinpath("tests").glob("*.py"))
    paths.update(HERE.glob("*.py"))
    paths.add(HERE.parent / "a105_primary_control_delivery_139/test_primary_delivery_139.py")
    paths.add(HERE.parent / "a105_optical_parent_repair_138/read_primary_controls_001.py")
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    label = sys.argv[1]
    before = fingerprint()
    save("PIN_" + label + ".json", before)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "tests")))
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", *TESTS,
        "--basetemp", str(HERE / ("run" + label)), "--junitxml", str(HERE / ("pytest" + label + ".xml"))]
    with (HERE / ("pytest" + label + ".log")).open("w") as output:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT)
    after = fingerprint()
    changed = {path: {"before": before.get(path), "after": after.get(path)}
        for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)}
    save("RESULT_" + label + ".json", {"command": command, "returncode": result.returncode,
        "fingerprinted_files": len(before), "changed_during_checks": changed,
        "scope": "Engineering choices/controllers; known published Table2 data and explicitly synthetic guard fixtures. No live-model interpretation or complete A105 adequacy claim."})
    print(json.dumps({"returncode": result.returncode, "changed": changed}))
    sys.exit(result.returncode if result.returncode else int(bool(changed)))
