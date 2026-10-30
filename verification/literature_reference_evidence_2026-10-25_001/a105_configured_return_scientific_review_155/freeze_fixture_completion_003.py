"""Complete test inputs in a new snapshot, preserving every pin002 code byte."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "pin_002"
TARGET = HERE / "pin_003"
FIXTURES = (
    "primary_pdx_partner_015/PUBLISHER_RESULTS_RENDERING_001.txt",
    "primary_pdx_partner_015/PUBLISHER_METHODS_RENDERING_001.txt",
    "primary_partner_matched_017_research/PRIMARY_PMC_001.html",
    "primary_partner_matched_017_research/PRIMARY_ARTICLE_TEXT_001.txt",
)


def main():
    if TARGET.exists():
        raise RuntimeError("Never overwrite a retained snapshot")
    previous = json.loads((HERE / "PIN_002.json").read_text())["files"]
    digests = {}
    for name, expected in previous.items():
        raw = (SOURCE / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected:
            raise RuntimeError("Source snapshot changed: " + name)
        path = TARGET / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        digests[name] = digest
    for name in FIXTURES:
        relative = "verification/literature_reference_evidence_2026-10-25_001/" + name
        raw = (ROOT / relative).read_bytes()
        path = TARGET / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        digests[relative] = hashlib.sha256(raw).hexdigest()
    result = {"scope": "Identical pin002 code/tests/helpers with four existing retained test inputs added. No paper interpretation or scientific claims from fixture copying.",
        "parent_snapshot": str(SOURCE), "parent_code_and_test_bytes_unchanged": True,
        "added_fixture_paths": list(FIXTURES), "files": digests}
    (HERE / "PIN_003.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"snapshot": str(TARGET), "file_count": len(digests),
        "parent_code_and_test_bytes_unchanged": True, "added_fixture_count": len(FIXTURES)}))


if __name__ == "__main__":
    main()
