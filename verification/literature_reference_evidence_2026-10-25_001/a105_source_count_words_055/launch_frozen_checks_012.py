"""Freeze code/test bytes before running a bounded engineering pytest command."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    run = OUT / "frozen_checks_012"
    run.mkdir(exist_ok=False)
    pin = run / "pin"
    pin.mkdir()
    sources = []
    for directory in ("gene_annotation_episode", "method_loop"):
        sources.extend((path, path.relative_to(ROOT).as_posix()) for path in sorted((ROOT / directory).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    sources.extend((path, path.relative_to(ROOT).as_posix()) for path in sorted((ROOT / "tests").glob("*.py")))
    sources.extend(((ROOT / "pyproject.toml", "pyproject.toml"),
        (OUT / "run_frozen_checks_012.py", "run_frozen_checks_012.py"),
        (Path(__file__), "launch_frozen_checks_012.py")))
    files = {}
    for path, relative in sources:
        raw = path.read_bytes()
        target = pin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        files[relative] = {"source": str(path), "bytes": len(raw), "sha256": digest(raw)}
    for relative, row in files.items():
        assert digest(Path(row["source"]).read_bytes()) == row["sha256"], relative
        assert digest((pin / relative).read_bytes()) == row["sha256"], relative
    accepted = json.loads((OUT / "STAGE_008_MANIFEST.json").read_bytes())
    for relative, row in accepted["owned_files"].items():
        assert files[relative]["sha256"] == row["sha256"], relative
    assert files["gene_annotation_episode/literature_experimental_prompt.py"]["sha256"] == "77f177c6339b8872a910d6fbfcd38fc13b296fb33f7efbede44cfb8da49f6b3a"
    expected052 = {"literature_binding_interaction_storage.py": "0dd5b0bb", "literature_binding_interaction_validation.py": "f8bae57a",
        "literature_binding_interaction_render.py": "575ecbb0", "literature_episodes.py": "e38bd88b", "episode_services.py": "5a40cfd7"}
    for name, prefix in expected052.items():
        assert files["gene_annotation_episode/" + name]["sha256"].startswith(prefix), name
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "files": files,
        "meaning": "Frozen final055 synthetic engineering checks, not a scientific/model run; includes current052 generation"}
    manifest_path = pin / "PIN_MANIFEST.json"
    with manifest_path.open("x") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    manifest_sha = digest(manifest_path.read_bytes())
    command = [sys.executable, "-B", str(pin / "run_frozen_checks_012.py"), "--output", str(run), "--manifest-sha256", manifest_sha]
    environment = {**os.environ, "PYTHONPATH": str(pin) + ":" + str(pin / "tests"), "PYTHONDONTWRITEBYTECODE": "1"}
    started = datetime.now(timezone.utc).isoformat()
    with (run / "TERMINAL.log").open("xb") as stream:
        result = subprocess.run(command, cwd=pin, env=environment, stdout=stream, stderr=subprocess.STDOUT)
    for relative, row in files.items():
        assert digest((pin / relative).read_bytes()) == row["sha256"], relative
    receipt = {"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "exit_code": result.returncode, "pin_manifest_sha256": manifest_sha,
        "pin_files_verified": len(files), "pin_unchanged": True,
        "live_other_session_work_does_not_change_this_pin": True, "configured_model_run": False}
    with (run / "TERMINAL_RECEIPT.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"exit_code": result.returncode, "pin_files_verified": len(files), "manifest_sha256": manifest_sha}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
