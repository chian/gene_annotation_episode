"""Run the ordinary configured source investigation from a verified code pin."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_004"
DIRECTORY = HERE / "configured_primary_005"
sys.path[:0] = [str(PIN), str(PIN / "tests")]


def write_status(value):
    (HERE / "CONFIGURED_STATUS_005.json").write_text(json.dumps(value, indent=2)+"\n")


def main():
    files = json.loads((HERE / "PIN_004.json").read_text())["files"]
    changed = [name for name, expected in files.items()
               if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != expected]
    if changed:
        raise RuntimeError("prepared_runtime_snapshot_changed")
    path = PIN / "verification/a105_literature_prompt_surface_144/run_configured_primary_144.py"
    spec = importlib.util.spec_from_file_location("configured_source_caller_005", path)
    caller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caller)
    prepared = json.loads((DIRECTORY / "prepared_caller.json").read_text())
    start = time.time()
    status = {"state": "started", "started_unix": start,
              "runtime_snapshot": str(PIN), "directory": str(DIRECTORY),
              "scope": "Actual configured model, original source bytes, ordinary workflow/controller; no preselected measurements, scripted actions or scientific completion claim"}
    write_status(status)
    try:
        summary = asyncio.run(caller.execute(DIRECTORY, prepared))
    except Exception as error:
        write_status({**status, "state": "failed", "finished_unix": time.time(),
                      "exception_type": type(error).__name__, "message": str(error)})
        raise SystemExit(1)
    (DIRECTORY / "execution_summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    write_status({**status, "state": "returned", "finished_unix": time.time(),
                  "summary_path": str(DIRECTORY / "execution_summary.json")})


if __name__ == "__main__":
    main()
