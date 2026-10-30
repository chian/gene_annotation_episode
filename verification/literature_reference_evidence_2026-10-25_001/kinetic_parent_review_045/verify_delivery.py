"""Check reviewed pure045 artifacts; no source acquisition or test repetition."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OWNER = BASE / "a105_kinetic_components_045"
OUT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    receipt_path = OWNER / "FINAL_RECEIPT_001.json"
    assert digest(receipt_path.read_bytes()) == "85b2056b0c4c60044198445af01dda00717bb38d2c98aa92f9620475eaa6da6b"
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["status"] == "passed" and receipt["test_exit_code"] == 0
    for name, expected in receipt["files"].items():
        assert digest((ROOT / name).read_bytes()) == expected, name
    for name, expected in receipt["existing_dependency_snapshot"].items():
        assert digest((ROOT / name).read_bytes()) == expected, name
    assert (OWNER / "CHECKS_001.txt").read_text().splitlines()[-1] == "133 passed in 0.53s"
    # These are full additions. Reconstruct both files directly from the
    # frozen patch instead of trusting a filename/count in the owner receipt.
    rebuilt, current = {}, None
    for line in (OWNER / "FULL_PATCH_001.patch").read_text().splitlines(keepends=True):
        if line.startswith("+++ "):
            current = line[4:].strip()
            assert current not in rebuilt
            rebuilt[current] = ""
        elif line.startswith("--- "):
            assert line.strip() == "--- /dev/null"
        elif line.startswith("@@ "):
            assert "-0,0" in line
        else:
            assert current is not None and line.startswith("+")
            rebuilt[current] += line[1:]
    assert set(rebuilt) == {
        "gene_annotation_episode/literature_kinetic_calculations.py",
        "tests/test_literature_kinetic_calculations.py",
    }
    for name, contents in rebuilt.items():
        assert contents.encode() == (ROOT / name).read_bytes(), name
    result = {
        "status": "passed", "scope": "parent review of pure045 generation001",
        "full_module_and_tests_read": True,
        "owner_terminal_result": receipt["test_terminal_result"],
        "owner_files_and_dependency_hashes_verified": True,
        "both_new_files_reconstructed_from_frozen_patch": True,
        "tests_repeated_by_parent": False,
        "new_paper_or_packet_read": False,
        "selected_LiteratureEpisodes_integration": False,
        "complete_A105_sheet": False,
        "source_model_and_covariance_truth_proved": False,
        "remaining": [
            "reader046 and source-supported populated examples",
            "selected storage and typed integration with ownership-safe reconstruction",
            "case-grounded validity/isolation/specificity and dependence compilation",
        ],
    }
    with (OUT / "RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
