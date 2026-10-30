"""Retain a bounded current checkout and the required original runtime fixture."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / "pin_001"
EXCLUDED = {"literature_rate_meaning_delivery.py", "literature_rate_meaning_render.py",
            "test_literature_rate_meaning_delivery_143.py"}


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
    required = [
        "verification/literature_reference_evidence_2026-10-25_001/parent_population_information_023/population_catalog_before.json",
        "verification/literature_reference_evidence_2026-10-25_001/a105_primary_control_delivery_139/test_primary_delivery_139.py",
        "verification/literature_reference_evidence_2026-10-25_001/a105_optical_parent_repair_138/ROOT_ARTICLE_TEXT_001.txt",
        "verification/literature_reference_evidence_2026-10-25_001/a105_optical_parent_repair_138/read_primary_controls_001.py",
        "research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin",
    ]
    paths.extend(ROOT / name for name in required)
    historical = ROOT / "verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_repository_071/pin_004"
    paths.extend(p for p in historical.rglob("*") if wanted(p))
    files = {}
    for source in sorted(set(paths)):
        relative = source.relative_to(ROOT)
        raw = source.read_bytes()
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files[str(relative)] = hashlib.sha256(raw).hexdigest()
    result = {"scope": "Current joined implementation plus one exact untouched historical runtime for compatibility verification; no historical dependency substituted into current code",
              "files": files, "excluded_in_progress_workload": sorted(EXCLUDED)}
    (HERE / "PIN_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"snapshot": str(PIN), "files": len(files),
                      "bytes": sum((PIN / name).stat().st_size for name in files)}))


if __name__ == "__main__":
    main()
