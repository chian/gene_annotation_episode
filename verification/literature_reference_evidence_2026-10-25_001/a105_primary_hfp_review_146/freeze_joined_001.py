"""Freeze current integration code and only the required external test assets."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / "pin_001"


def wanted(path):
    return (path.is_file() and "__pycache__" not in path.parts
            and ".pytest_cache" not in path.parts and path.suffix != ".pyc")


def main():
    if PIN.exists():
        raise RuntimeError("Retained snapshots are never overwritten")
    paths = []
    for directory in ("gene_annotation_episode", "method_loop", "tests"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if wanted(path))
    required = [
        "research/experimental_scoring_review_2026-10-23/a105_assay_validity_case_145/primary.xml",
        "verification/a105_literature_prompt_surface_144/run_configured_primary_144.py",
        "verification/literature_reference_evidence_2026-10-25_001/parent_population_information_023/population_catalog_before.json",
    ]
    paths.extend(ROOT / name for name in required)
    files = {}
    for source in sorted(set(paths)):
        relative = source.relative_to(ROOT)
        raw = source.read_bytes()
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files[str(relative)] = hashlib.sha256(raw).hexdigest()
    changed = [name for name, digest in files.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    result = {"scope": "Joined A105 reader integration and compatibility checks; no scientific completeness claim",
              "files": files, "live_files_changed_during_capture": changed}
    (HERE / "PIN_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"snapshot": str(PIN), "files": len(files),
                      "bytes": sum((PIN / name).stat().st_size for name in files),
                      "live_files_changed_during_capture": changed}))
    return bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
