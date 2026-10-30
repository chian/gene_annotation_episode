"""Retain a bounded current checkout and the required original runtime fixture."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / "pin_003"
EXCLUDED = set()


def wanted(path):
    return (path.is_file() and "__pycache__" not in path.parts
            and ".pytest_cache" not in path.parts and path.suffix != ".pyc"
            and path.name not in EXCLUDED)


def main():
    if PIN.exists():
        raise RuntimeError("Never overwrite a retained source snapshot")
    paths = []
    for directory in ("gene_annotation_episode", "method_loop", "tests"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if wanted(p))
    required = ["verification/a105_literature_prompt_surface_144/run_configured_primary_144.py"]
    paths.extend(ROOT / name for name in required)
    files = {}
    for source in sorted(set(paths)):
        relative = source.relative_to(ROOT)
        raw = source.read_bytes()
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files[str(relative)] = hashlib.sha256(raw).hexdigest()
    result = {"scope": "Current fresh source-evidence API and exact compact-contract callers; no original scientific source inspected",
              "files": files, "excluded_in_progress_workload": sorted(EXCLUDED)}
    (HERE / "PIN_003.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"snapshot": str(PIN), "files": len(files),
                      "bytes": sum((PIN / name).stat().st_size for name in files)}))


if __name__ == "__main__":
    main()
