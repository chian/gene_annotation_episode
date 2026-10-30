"""Freeze current reader repairs and their genuine old synthetic dependencies."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / "pin_001"


def main():
    if PIN.exists():
        raise RuntimeError("Never overwrite a retained snapshot")
    directories = ["gene_annotation_episode", "method_loop", "tests",
        "verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_repository_071/pin_004",
        "verification/literature_reference_evidence_2026-10-25_001/a105_primary_active_site_review_151/pin_001",
        "verification/literature_reference_evidence_2026-10-25_001/a105_missing_input_semantics_156/legacy_v1"]
    files = set()
    for directory in directories:
        folder = ROOT / directory
        if not folder.is_dir():
            raise RuntimeError("Missing actual verification dependency: " + directory)
        files.update(path for path in folder.rglob("*") if path.is_file()
            and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts
            and path.suffix not in (".pyc", ".log"))
    for directory in ("a105_missing_input_semantics_156", "a105_structural_scalar_reader_157"):
        folder = ROOT / "verification/literature_reference_evidence_2026-10-25_001" / directory
        files.update(path for path in folder.glob("*.py") if path.is_file())
    digests = {}
    for source in sorted(files):
        relative = source.relative_to(ROOT)
        raw = source.read_bytes()
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        digests[str(relative)] = hashlib.sha256(raw).hexdigest()
    changed = [name for name, digest in digests.items()
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    (HERE / "PIN_001.json").write_text(json.dumps({"files": digests,
        "live_files_changed_during_capture": changed}, indent=2) + "\n")
    print(json.dumps({"snapshot": str(PIN), "file_count": len(digests),
        "live_files_changed_during_capture": changed}))
    return bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
