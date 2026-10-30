"""Record source hashes and exact selected examples, under existing local_jobs.

All native measurements are loaded from full retained producer/worker sheets.
Only custody envelopes are synthetic fixtures. This audit launches no Infernal
program and establishes no Store authentication or episode integration.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import runpy

from gene_annotation_episode import infernal_preparation_result_views as views
from gene_annotation_episode.infernal_preparation_schema import PROGRAM_MODES

ROOT = Path(__file__).resolve().parents[2]
OUT = Path.cwd()
HELPERS = runpy.run_path(str(ROOT / "tests/test_infernal_preparation_result_views.py"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


source_paths = ["gene_annotation_episode/" + name + ".py" for name in (
    "infernal_preparation_result_views", "infernal_preparation_schema", "infernal_preparation_models",
    "infernal_preparation_artifacts", "infernal_preparation_statistics", "infernal_preparation_calculations",
    "infernal_preparation_emission", "infernal_preparation_emission_calculations", "native_infernal_preparation_worker",
    "communication", "domain")]
source_paths += ["tests/test_infernal_preparation_result_views.py", str(Path(__file__).relative_to(ROOT)),
    "verification/tool_graders_infernal_preparation_views_2026-10-26_253/run_tests.py"]
contracts = [ROOT / "verification/tool_graders_infernal_preparation_2026-10-26_247" / name
             for name in [*(f"INTERFACES_{i:03}.md" for i in range(1, 6)),
                          *(f"RESULT_HANDOFF_{i:03}.md" for i in range(1, 6))]]
source_paths.extend(str(p.relative_to(ROOT)) for p in contracts)
goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
case_records = []
for name, path, calculation_path in HELPERS["CASES"]:
    grading, occurrences = HELPERS["supplied"](name)
    catalog = views.preparation_projection_catalog(grading["operation"]["program"], grading["operation"]["mode"])
    counts = {}
    for collection, entry in catalog.items():
        if not entry["quantities"] and not entry["checks"]:
            continue
        selected = HELPERS["selector"](collection, entry["quantities"], entry["checks"])
        result = HELPERS["project"](grading, occurrences, selected)
        assert result == HELPERS["project"](json.loads(json.dumps(grading)), occurrences, selected)
        counts[collection] = result["population"]
    case_records.append({"case": name, "program": grading["operation"]["program"], "mode": grading["operation"]["mode"],
        "source_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in (path, calculation_path) if p is not None],
        "selected_decoded_population": counts})

examples = []
for name, collection, quantities, checks, kinds, wanted_artifacts in (
    ("C/prior_cmemit_stockholm", "calculations", ["components.gc_count", "components.gc_denominator", "components.gc_fraction_canonical", "components.gap_count", "components.column_count", "components.gap_fraction"], [], ["generated_sequence"], []),
    ("B/cmcalibrate_all_sidecars", "native_rows", ["values.mu_orig", "values.lambda"], [], ["calibration"], []),
    ("A/cmconvert_binary", "calculations", ["components.output_model_count", "components.output_byte_count"], ["output_population_complete"], [], ["converted_models", "stdout", "stderr"]),
    ("A/cmpress_retained_219", "calculations", [], ["artifact_signature", "artifact_payload_identity"], [], []),
    ("root/cmemit-consensus", "output_records", ["values.residue_count", "values.gc_count"], [], ["generated_sequence"], []),
):
    grading, occurrences = HELPERS["supplied"](name)
    available = grading["sheet"]["native_rows"] if collection == "native_rows" else grading["sheet"]["output_records"]
    selected_keys = [r["record_key"] for r in available if r["kind"] in kinds]
    rows = {"record_keys": selected_keys} if selected_keys else {"offset": 0, "limit": 1}
    selected = HELPERS["selector"](collection, quantities, checks, rows=rows,
        selected_artifacts=[{"direction": "output", "role": role, "ordinal": 0} for role in wanted_artifacts])
    examples.append({"case": name, "selector": selected, "projection": HELPERS["project"](grading, occurrences, selected)})

save("PROJECTION_EXAMPLES_001.json", examples)
save("CATALOG_001.json", {program: {mode: views.preparation_projection_catalog(program, mode) for mode in sorted(modes)}
                          for program, modes in PROGRAM_MODES.items()})
save("EVIDENCE_001.json", {"created_at": datetime.now(timezone.utc).isoformat(),
    "source_sha256": {p: digest(ROOT / p) for p in source_paths},
    "authoritative_goal_sha256": digest(goal), "case_count": len(case_records), "cases": case_records,
    "provenance": "Retained native measurements from producer248/249/250 and root247 full worker results; synthetic occurrence envelopes constructed only for pure-projection tests.",
    "new_native_executions": 0, "live_store_authentication_verified": False, "episode_communication_verified": False,
    "selection_replay_equal": True, "artifact_refs": "Test artifact IDs derive from retained actual content digests; this audit does not publish them to a Store.",
    "synthetic_cases": "Unavailable-cell, partial/unknown capture, differing check outcomes, working-copy occurrence, orphan aggregate, invalid shape and association mutations occur only in owned tests.",
    "array_policy": "No projection of full native arrays, HMM STATS, background arrays, sidecar series, or trace bodies. All remain in original retained data."})
print(json.dumps({"retained_native_cases": len(case_records), "saved_examples": len(examples),
    "program_mode_count": sum(len(modes) for modes in PROGRAM_MODES.values()), "new_native_executions": 0,
    "projection_source_sha256": digest(ROOT / source_paths[0])}, indent=2))
