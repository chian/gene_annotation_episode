"""Verify the final044 runtime proof and independently reconstruct its patch."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OWNER = BASE / "a105_subset_forwarding_044"
OUT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def apply_file(old, lines):
    result, cursor, i = [], 0, 0
    while i < len(lines):
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
        assert match, lines[i]
        first, old_count = int(match[1]), int(match[2] or 1)
        new_count = int(match[4] or 1)
        start = first - 1 if old_count else first
        assert cursor <= start
        result.extend(old[cursor:start])
        cursor, consumed, added = start, 0, 0
        i += 1
        while i < len(lines) and not lines[i].startswith("@@ "):
            line = lines[i]
            assert line[:1] in (" ", "+", "-")
            if line[:1] in (" ", "-"):
                assert old[cursor] == line[1:]
                cursor += 1
                consumed += 1
            if line[:1] in (" ", "+"):
                result.append(line[1:])
                added += 1
            i += 1
        assert (consumed, added) == (old_count, new_count)
    result.extend(old[cursor:])
    return "".join(result).encode()


def main():
    receipt = json.loads((OWNER / "FINAL_RECEIPT_005.json").read_bytes())
    assert receipt["generation"] == "005" and receipt["exit_code"] == 0
    assert receipt["source_hashes_before_and_after_equal"]
    assert receipt["terminal_result"] == "129 passed in 333.26s (0:05:33)"
    assert (OWNER / "FINAL_CHECKS_005.txt").read_text().splitlines()[-1] == receipt["terminal_result"]
    preservation = json.loads((OUT / "PRESERVATION_RECEIPT_005.json").read_bytes())
    for name, expected in receipt["owned_source_sha256"].items():
        assert digest((ROOT / name).read_bytes()) == expected, name
    for name, expected in preservation["current_existing_source_sha256"].items():
        assert receipt["owned_source_sha256"][name] == expected
    patch = (OWNER / "IMPLEMENTATION_005.patch").read_bytes()
    assert digest(patch) == receipt["patch_sha256"]
    sections, i = {}, 0
    lines = patch.decode().splitlines(keepends=True)
    while i < len(lines):
        assert lines[i].startswith("--- baseline/")
        baseline_name = lines[i].strip().removeprefix("--- ")
        assert lines[i + 1].startswith("+++ ")
        name = lines[i + 1][4:].strip()
        assert name not in sections
        i += 2
        start = i
        while i < len(lines) and not lines[i].startswith("--- "):
            i += 1
        contents = apply_file((OWNER / baseline_name).read_text().splitlines(keepends=True), lines[start:i])
        assert contents == (ROOT / name).read_bytes(), name
        sections[name] = digest(contents)
        target = OUT / "reconstruction_005" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(contents)
    assert set(sections) == set(preservation["current_existing_source_sha256"])
    old = json.loads((OWNER / "PRE044_OPTICAL_FORMAT_RECEIPT_005.json").read_bytes())
    assert old["status"] == "passed" and old["all_SQL_unchanged"]
    assert old["source_artifacts_forbidden"] and old["parsers_calculators_forbidden"]
    assert not old["new_base_receive_used_to_create_fixture"]
    result = {
        "status": "passed", "generation": "005",
        "owner_terminal_result": receipt["terminal_result"],
        "source_hashes_and_parent_preservation_match": True,
        "both_existing_files_reconstructed_from_frozen_patch": sections,
        "read_coverage": "complete original base/C7/optical; all044 proposals and final285-line patch; complete new tests with final corrections; runtime redelivery and full C4 admission",
        "independent_parent_baseline_repro": "one received cell expanded to ten before044",
        "verification_scope": "18 synthetic input variants across16 typed namespaces; nested scripted shared loop; separate controlled two-boundary C4 fixture; revised-return and read-only no-binding-table reconstruction",
        "exact_pre044_optical_receipt_format_preserved": True,
        "tests_repeated_by_parent": False,
        "actual_model_or_primary_source_science_claim": False,
        "old_manual_without_original_runtime_proof": "explicit unavailable-binding limitation; no backfilled receipt",
        "full_goal_or_A105_complete": False,
    }
    with (OUT / "FINAL_PARENT_REVIEW_005.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
