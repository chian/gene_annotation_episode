"""Index retained test artifacts and current sources; perform no calculation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def save(name, value):
    (directory / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


owned = [root / "gene_annotation_episode/native_blast_database_metadata.py",
         root / "tests/test_native_blast_database_metadata.py", directory / "run_checks.py", Path(__file__)]
modules = ["blast_report_collection", "blast_program_context", "blast_search", "blast_pairwise_grader",
           "blast_sequence_database", "blast_database_grader", "blast_reference_metadata", "blast_profile_inputs",
           "blast_profile_calculators", "blast_pssm_inputs", "blast_pssm_master_inputs", "blast_pssm_calculators",
           "blast_iteration_inputs", "blast_iteration_calculators", "blast_vdb_inputs", "blast_vdb_calculators",
           "native_blast_database_contracts", "domain", "local_jobs"]
contract_dir = root / "verification/tool_graders_native_blast_database_result_contract_2026-10-26_314"
contracts = [contract_dir / "PROPOSED_CONTRACT_001.md", directory / "CONTRACT_001.md", *sorted(contract_dir.glob("CONTRACT_ADDENDUM_*.md"))]
goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
save("SOURCE_HASHES_001.json", dict(recorded_at=datetime.now(timezone.utc).isoformat(),
    scope="Current post-check_011 source snapshot. M-owned production/test bytes were unchanged during check_011; shared files remain independently owned.",
    owned=[identity(p) for p in owned], read_only_dependencies=[identity(root / "gene_annotation_episode" / (m + ".py")) for m in modules],
    contracts=[identity(p) for p in contracts], immutable_goal=identity(goal)))

receipts = []
for check in sorted(directory.glob("check_*/receipt.json")):
    receipt = json.loads(check.read_text())
    stdout = check.with_name("stdout.txt")
    summaries = [line for line in stdout.read_text().splitlines() if " passed" in line or "no tests ran" in line]
    receipts.append(dict(receipt=identity(check), stdout=identity(stdout), stderr=identity(check.with_name("stderr.txt")),
        returncode=receipt["returncode"], summaries=summaries[-1:], policy=receipt["metadata"]["policy"],
        elapsed_seconds=receipt["metadata"].get("elapsed_seconds"), observed_scratch_bytes=receipt["metadata"].get("observed_scratch_bytes")))
save("TEST_RECEIPTS_001.json", dict(checks=receipts, final_check="check_011", failed_receipts_retained=True))

test_root = directory / "check_011/pytest-of-chia/pytest-0"
cases = [("sequence", "test_metadata_path_numerical_s0", "sequence"),
         ("rps_profile", "test_metadata_path_profile_mod0", "profile"),
         ("rpst_profile", "test_metadata_path_profile_mod1", "profile"),
         ("vdb_duplicates", "test_vdb_demonstrated_duplicat0", "vdb"),
         ("vdb_gbseq_codons", "test_gbseq_actual_binding_feat0", "gbseq")]
examples = []
for name, folder, stem in cases:
    base = test_root / folder
    inputs = json.loads((base / (stem + "-inputs.json")).read_text())
    calc = json.loads((base / (stem + "-calculations.json")).read_text())
    artifacts = [identity(base / (stem + suffix)) for suffix in ("-inputs.json", "-sheets.json", "-calculations.json")]
    retained = list(dict.fromkeys(r["path"] for r in inputs["artifact_catalog"]["entries"] + inputs["artifact_catalog"]["retained_sources"]))
    if name == "sequence":
        component = calc["searches"][0]["sequence_components"]["components"]
        values = dict(hit_measurements=component["database_sheet"]["hits"][0]["measurements"],
            selected_query_coverage=component["selected_query_coverage"][0],
            function_weights={k: component["function_weights"][k] for k in
                ("function_masses", "unadjusted_probabilities", "representation_adjusted_probabilities")})
    elif name in {"rps_profile", "rpst_profile"}:
        values = dict(model={k: calc["models"][0][k] for k in
            ("query_unit", "paired_query_units", "paired_model_positions", "query_coverage", "model_coverage")},
            hsp_model=calc["hsps"][0]["model_matches"][0])
    elif name == "vdb_duplicates":
        values = dict(origin_bound_subject_count=calc["membership"]["origin_bound_subject_count"],
            demonstrated_group_count=calc["sequence_groups"]["demonstrated_group_count"],
            duplicate_subject_representations=calc["sequence_groups"]["duplicate_subject_representations"],
            observed_origin_sample_count=calc["sample_groups"]["observed_origin_sample_count"],
            full_query_coverage=calc["subjects"][0]["full_query_coverage"])
    else:
        feature = calc["feature_components"][0]
        values = dict(translation_map=feature["translation_map"], feature_paired_residue_coverage=feature["feature_paired_residue_coverage"],
            identical_query_feature_residues=feature["hsp_rows"][0]["identical_query_feature_residues"])
    examples.append(dict(name=name, evidence="Synthetic captured-input/report fixtures using actual public M and numerical dependency functions; no native database execution.",
        artifacts=artifacts, captured_inputs=[identity(Path(p)) for p in retained], saved_calculation_excerpt=values))
save("EXAMPLES_001.json", dict(source_check="check_011", examples=examples))
print(json.dumps(dict(source_files=len(owned)+len(modules), retained_receipts=len(receipts), examples=len(examples))))
