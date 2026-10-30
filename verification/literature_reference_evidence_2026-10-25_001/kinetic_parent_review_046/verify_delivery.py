"""Verify reviewed reader046 delivery without repeating its synthetic suite."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OWNER = BASE / "a105_kinetic_reader_046"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    path = OWNER / "FINAL_RECEIPT_001.json"
    assert digest(path.read_bytes()) == "7a934accc8afb7af9539bdb6fa142ab150e7e202928fb676942fd72338284e81"
    receipt = json.loads(path.read_bytes())
    assert receipt["status"] == "passed" and receipt["exit_code"] == 0
    for group in ("owned_new_source_sha256", "actual_dependency_sha256"):
        for name, expected in receipt[group].items():
            assert digest((ROOT / name).read_bytes()) == expected, name
    log = (OWNER / "CHECKS_001.txt").read_bytes()
    assert digest(log) == receipt["output_sha256"]
    assert log.decode().splitlines()[-1] == "105 passed in 0.62s"
    patch = (OWNER / "NEW_FILES_001.patch").read_bytes()
    assert digest(patch) == receipt["patch_sha256"]
    rebuilt, current = {}, None
    for line in patch.decode().splitlines(keepends=True):
        if line.startswith("+++ "):
            current = line[4:].strip().removeprefix("b/")
            assert current not in rebuilt
            rebuilt[current] = ""
        elif line.startswith("--- "):
            assert line.strip() == "--- /dev/null"
        elif line.startswith("@@ "):
            assert "-0,0" in line
        else:
            assert current is not None and line.startswith("+")
            rebuilt[current] += line[1:]
    assert set(rebuilt) == set(receipt["owned_new_source_sha256"])
    for name, contents in rebuilt.items():
        assert contents.encode() == (ROOT / name).read_bytes(), name
    result = {
        "status": "passed", "scope": "parent review of pure046 generation001",
        "read_coverage": "complete initial398-line module and403-line tests plus all final correction bodies and appended tests; final420/495 lines",
        "parent_findings_corrected": [
            "qualified confidence levels cannot become exact statistical levels",
            "exact reversed CI endpoints cannot hide in float rounding",
            "distinct CI endpoints cannot manufacture zero-width precision",
        ],
        "owner_terminal_result": receipt["terminal_result"],
        "actual_helpers_and045_hashes_verified": True,
        "both_new_files_reconstructed_from_patch": True,
        "tests_repeated_by_parent": False,
        "new_paper_or_packet_read": False,
        "source_authorization_owner": "calling adapter, not this reader",
        "static_dependency_labels": "expected fingerprints; future storage must authenticate actual implementation",
        "remaining": [
            "selected LiteratureEpisodes operation/storage and typed subset rendering",
            "source-supported examples under reviewed experimental meanings",
            "covariance/model source reader where scientifically supported",
            "broader A105 scoring components and later literature axes",
        ],
        "complete_A105_sheet": False,
    }
    with (Path(__file__).resolve().parent / "RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
