"""Record already completed verification metadata; run no science or tests."""
from pathlib import Path
import hashlib
import json
import re

packet = Path(__file__).resolve().parent
repo = packet.parents[1]
goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
owned = ("gene_annotation_episode/episode_services.py", "gene_annotation_episode/episode_bindings.py",
    "gene_annotation_episode/scientific_process_episodes.py", "tests/test_protein_structure_alignment_preflight.py")
pins = [{"path": path, "sha256": hashlib.sha256((repo / path).read_bytes()).hexdigest(),
         "byte_length": (repo / path).stat().st_size} for path in owned]
(packet / "SOURCE_PINS_001.json").write_text(json.dumps(pins, indent=2) + "\n")
attempts = []
for path in sorted(packet.glob("check[0-9][0-9][0-9]")):
    receipt = json.loads((path / "receipt.json").read_text())
    request = json.loads((path / "selected_request.json").read_text())
    stdout = (path / "stdout.txt").read_text()
    summaries = [line for line in stdout.splitlines()
                 if re.search(r"\b(?:passed|failed|errors?)\b.*\bin\s+[0-9.]+s", line)]
    snapshot = json.loads((path / "source_pins_before.json").read_text())
    attempts.append({"run": path.name, "summary": summaries[-1] if summaries else None,
        "returncode": receipt["returncode"], "metadata": receipt.get("metadata"),
        "executed_snapshot_pins_unchanged": receipt["executed_snapshot_pins_unchanged"],
        "owned_live_source_pins_unchanged": receipt["owned_live_source_pins_unchanged"],
        "live_source_drift": receipt["live_source_drift"],
        "preflight_baseline_origin": request.get("preflight_baseline_origin"),
        "owned_executed_pins": [row for row in snapshot if row["path"] in owned],
        "selected_request": str(path.relative_to(repo) / "selected_request.json"),
        "receipt": str(path.relative_to(repo) / "receipt.json"),
        "stdout": str(path.relative_to(repo) / "stdout.txt")})
value = {"version": "protein_structure_alignment_preflight_verification_001",
    "goal_path": str(goal), "goal_sha256": hashlib.sha256(goal.read_bytes()).hexdigest(),
    "scope": "380/015 service and scientific-process alignment/estimate preflight only",
    "new_cases": 79, "all_new_cases_passed_common_snapshot": "check005",
    "current_owned_pins": pins, "attempts": attempts,
    "interpretation": "Counts overlap across attempts; do not sum them as unique coverage.",
    "authority_qualification": "Injected received-authority public ports exercise this seam only. Actual frozen typed protein receipt integration remains root-owned and unverified here.",
    "numerical_example_assertions": {"ordinary_dna_rna_protein_global_alignment": {
        "paired_positions": 4, "identity_fraction": 1, "denominator": "four identical paired sequence positions",
        "execution": "actual ToolRegistry/native local alignment inside bounded verification"}},
    "unchanged_accounting": {"fixed_rows": 308, "accepted_rows": 112,
        "protein_capability_accepted_by_this_work": False}}
(packet / "VERIFICATION_001.json").write_text(json.dumps(value, indent=2) + "\n")
print(json.dumps({"owned_pins": pins, "attempts": [
    {"run": row["run"], "summary": row["summary"], "returncode": row["returncode"],
     "snapshot_unchanged": row["executed_snapshot_pins_unchanged"]} for row in attempts]}, indent=2))
