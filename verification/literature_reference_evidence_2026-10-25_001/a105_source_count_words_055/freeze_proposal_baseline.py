"""Freeze code-only prospective inputs; no papers, pins or databases are read."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FILES = [
    "gene_annotation_episode/literature_kinetic_calculations.py",
    "gene_annotation_episode/literature_kinetic_inputs.py",
    "gene_annotation_episode/literature_kinetic_validation.py",
    "gene_annotation_episode/literature_kinetic_storage.py",
    "gene_annotation_episode/literature_assay_inputs.py",
    "gene_annotation_episode/literature_rate_native_inputs.py",
    "gene_annotation_episode/literature_partner_source_fields.py",
    "gene_annotation_episode/literature_experimental_contracts.py",
    "gene_annotation_episode/literature_experimental_prompt.py",
    "gene_annotation_episode/literature_episodes.py",
    "gene_annotation_episode/episode_services.py",
    "gene_annotation_episode/literature_rate_storage.py",
    "tests/test_literature_kinetic_calculations.py",
    "tests/test_literature_kinetic_inputs.py",
    "tests/test_literature_kinetic_storage.py",
    "tests/test_literature_kinetic_integration.py",
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    rows = {}
    for name in FILES:
        source = ROOT / name
        raw = source.read_bytes()
        target = OUT / "baseline_001" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        assert source.read_bytes() == raw == target.read_bytes(), name
        rows[name] = {"bytes": len(raw), "sha256": digest(raw)}
    result = {"scope": "prospective code dependencies at proposal time; not production release or new paper reading",
              "concurrent_owner_note": "054 owns kinetic storage; captured storage is only a point-in-time inspection copy, not a release baseline for later mutation",
              "production_or_test_edits": False, "files": rows}
    with (OUT / "BASELINE_001.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"baseline_files": len(rows), "production_or_test_edits": False}))


if __name__ == "__main__":
    main()
