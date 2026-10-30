"""Mechanical reproduction of already reviewed042 operands, in a fresh folder.

This does not visually inspect the image, read another paper or establish a
sampling model. The original packet and its historical outputs stay unchanged.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]
PACKET = BASE / "a105_binding_case_042"
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    reset = json.loads((BASE / "BINDING_PARENT_RESET_042.json").read_bytes())
    assert reset["status"] == "complete"
    manifest = json.loads((PACKET / "FILE_MANIFEST.json").read_bytes())
    for row in manifest["files"]:
        path = PACKET / row["path"]
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"]
    before = {str(p.relative_to(PACKET)): digest(p) for p in PACKET.rglob("*") if p.is_file()}
    destination = OUT / "reproduced_001"
    destination.mkdir()
    shutil.copyfile(PACKET / "table3.jpg", destination / "table3.jpg")
    script = PACKET / "calculate_case.py"
    # The fully inspected script derives its output directory from __file__.
    # Giving that directory a fresh parent-owned location preserves originals.
    with redirect_stdout(io.StringIO()):
        exec(compile(script.read_text(), str(script), "exec"), {
            "__file__": str(destination / "calculate_case.py"),
            "__name__": "parent042_mechanical_reproduction",
        })
    outputs = ("TABLE3_RETAINED_VISUAL_TRANSCRIPTION.json", "NUMERICAL_CELLS.json",
               "PROPOSED_FOUR_CELL_ARITHMETIC.json", "CALCULATION_RECEIPT.json")
    for name in outputs:
        assert json.loads((destination / name).read_bytes()) == json.loads((PACKET / name).read_bytes()), name
    after = {str(p.relative_to(PACKET)): digest(p) for p in PACKET.rglob("*") if p.is_file()}
    assert before == after
    numerical = json.loads((destination / "NUMERICAL_CELLS.json").read_bytes())
    assert len(numerical) == 10
    assert all(row["model_without_source"]["cells"]["source_profile_log_ratio"]["value"] is None
               for row in numerical)
    result = {
        "status": "passed", "owner_manifest_entries_verified": len(manifest["files"]),
        "original_packet_files_unchanged": len(before),
        "pure_source_derived_comparisons_reproduced": 10,
        "four_cell_research_arithmetic_reproduced": 4,
        "matching_original_output_files": list(outputs),
        "image_bytes_read": "copied and hashed for existing locator custody; no parent visual inspection",
        "new_primary_acquisition_or_paper_read": False,
        "model_calls": 0, "Store_or_episode_execution": False,
        "finite_source_likelihood_or_overall_A105_grade_claim": False,
        "script_sha256": digest(script),
    }
    with (OUT / "RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
