"""Authenticate frozen test milestones and code pins; no run/provider-state read."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
OWNER = BASE / "a105_kinetic_integration_047"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    milestones = {}
    for generation, count in (("004", 203), ("005", 99), ("006", 68)):
        receipt_path = OWNER / f"VERIFY_{generation}_RECEIPT.json"
        receipt = json.loads(receipt_path.read_bytes())
        assert receipt["exit_code"] == 0 and receipt["owned_files_stable"]
        log = OWNER / receipt["log"]
        terminal = log.read_text().splitlines()[-1]
        assert terminal.startswith(f"{count} passed in "), terminal
        for name, expected in receipt["sha256"].items():
            assert digest(OWNER / f"snapshot_{generation}" / name) == expected, name
        milestones[generation] = {"count": count, "terminal": terminal,
            "receipt_sha256": digest(receipt_path), "log_sha256": digest(log),
            "all_eight_snapshot_hashes_match": len(receipt["sha256"]) == 8}
    pins = {}
    expected_manifests = {
        "024": "77d12c3fa01403640d47aa8c38a3a4f7b0f9d06c9408f94537e010f865ce6940",
        "030": "2616012239523f24d41ce1c9d04d08ab7bd6c75ee7f1e10943172e39b090c2df",
    }
    for label, expected in expected_manifests.items():
        pin = BASE / f"literature_model_run_{label}/pin_001"
        manifest_path = pin / "SOURCE_MANIFEST.json"
        assert digest(manifest_path) == expected
        manifest = json.loads(manifest_path.read_bytes())
        names = set()
        for row in manifest["files"]:
            name = row["pin_relative_path"]
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            names.add(name)
            path = pin / name
            assert path.stat().st_size == row["size"], name
            assert digest(path) == row["sha256"], name
        actual = {str(p.relative_to(pin)) for p in pin.rglob("*") if p.is_file()}
        assert actual == names | {"SOURCE_MANIFEST.json"}
        pins[label] = {"manifest_sha256": expected, "files_verified": len(names),
                       "unmanifested_files": 0}
    result = {"passed": True, "milestones": milestones,
        "milestone_counts_overlap_not_additive": True, "pins": pins,
        "scope": "Immutable source-code/test artifacts only; not live-model scientific success or source truth"}
    with (OUT / "TERMINAL_AND_PIN_REVIEW_006.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "frozen_test_milestones": len(milestones),
                      "pin_files_verified": {k: v["files_verified"] for k, v in pins.items()}}))


if __name__ == "__main__":
    main()
