"""Build a fresh wheel in a staged copy, then verify from outside the checkout."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PYTHON = ROOT / ".venv/bin/python"
EXPECTED_PIN = "6431e9b48d6015056915c610f125653a9bbb886e0195bd1a24a1fc531896a809"


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def run(stage, command, cwd, env=None):
    started = time.monotonic()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    (HERE / (stage + ".stdout")).write_text(result.stdout)
    (HERE / (stage + ".stderr")).write_text(result.stderr)
    save(stage + "-result.json", {"command": [str(value) for value in command], "cwd": str(cwd),
                                 "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - started})
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


assert not (HERE / "verification.json").exists(), "retain prior run evidence; never overwrite it"
run("serialize", [PYTHON, "-B", HERE / "serialize_fixtures.py"], ROOT)
wheel_dir = HERE / "wheels"
wheel_dir.mkdir()
with tempfile.TemporaryDirectory(prefix="homology-wheel-repaired-") as temporary:
    work = Path(temporary)
    source = work / "source"
    source.mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", source / "pyproject.toml")
    for name in ("gene_annotation_episode", "method_loop"):
        shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    for pattern in ("LICENSE*", "README*"):
        for path in ROOT.glob(pattern):
            if path.is_file():
                shutil.copyfile(path, source / path.name)
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    run("build", [PYTHON, "-m", "pip", "wheel", "--no-deps", "--no-cache-dir", "--wheel-dir", wheel_dir, source], work, environment)
    wheel, = wheel_dir.glob("*.whl")
    wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    save("WHEEL.json", {"wheel": str(wheel.relative_to(ROOT)), "sha256": wheel_hash,
                        "byte_count": wheel.stat().st_size, "scientific_implementation_expected_pin": EXPECTED_PIN})
    installed = work / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
    result = run("isolated", [PYTHON, "-I", "-B", HERE / "verify_isolated.py", installed, ROOT, HERE, EXPECTED_PIN], work, environment)
    summary = json.loads((HERE / "verification.json").read_text())
    summary.update(wheel=str(wheel.relative_to(ROOT)), wheel_sha256=wheel_hash)
    save("verification.json", summary)
    print(result.stdout)
