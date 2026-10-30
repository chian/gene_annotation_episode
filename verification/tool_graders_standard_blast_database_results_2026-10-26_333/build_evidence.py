"""Index existing R333 receipts and artifacts; performs no scientific calculation."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


owned = [ROOT / group / (prefix + part + ".py") for group, prefix in
    (("gene_annotation_episode", "native_blast_standard_database_"), ("tests", "test_native_blast_standard_database_"))
    for part in ("calculators", "result_views", "result_worker")]
native = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges"
sources = [*owned,
    Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt"),
    ROOT / "verification/tool_graders_standard_blast_database_plan_2026-10-26_327/PROPOSED_PLAN_001.md",
    *[ROOT / "verification/tool_graders_standard_blast_database_plan_2026-10-26_327" / f"CONTRACT_ADDENDUM_{number:03}.md" for number in range(1, 5)],
    native / "blastx_range_reverse_json15/attempt/report.json", native / "blastx_range_reverse_tabular7/attempt/report.tsv"]
receipts = []
for directory in sorted(HERE.glob("check[0-9][0-9][0-9]")):
    receipt = json.loads((directory / "receipt.json").read_bytes())
    receipts.append(dict(name=directory.name, files=[record(directory / name) for name in ("receipt.json", "stdout.txt", "stderr.txt")],
        returncode=receipt["returncode"], policy=receipt["metadata"]["policy"], elapsed_seconds=receipt["metadata"]["elapsed_seconds"],
        pytest_summary=(directory / "stdout.txt").read_text().splitlines()[-1]))
generations = []
for path in sorted({p.resolve() for p in (HERE / "check007/pytest-tmp").glob("*/generation-*/worker-manifest.json")}):
    manifest = json.loads(path.read_bytes())
    generations.append(dict(manifest=record(path), status=manifest["status"], calculation_id=manifest["calculation_id"],
        input_identity=manifest["input_identity"], input_interpretation_id=manifest["input_interpretation_id"],
        input_implementation_sha256=manifest["input_implementation_sha256"], implementation_manifest_sha256=manifest["implementation_manifest_sha256"],
        counts=manifest["counts"], failures=manifest["failures"], artifact_records=manifest["artifacts"],
        actual_present_artifacts=[dict(role=r["role"], **record(path.parent / r["relative_path"])) for r in manifest["artifacts"]]))
request_path = next((HERE / "check007/pytest-tmp").glob("test_R7_complete_artifacts_exac*/generation-1.request.json"))
request = json.loads(request_path.read_bytes())
evidence = dict(version="standard_blast_database_R333_evidence_v1", scope="R field definitions, pure calculators/views and actual-file worker",
    index_note="003 records the final78-case run after the narrow malformed-HSP length correction, parser terminology and approved PSSM exception regression. Earlier001/002 indices and77-pass receipt remain unchanged. Current-directory symlinks are deduplicated. Some fault tests deliberately mutate original/saved bytes after sealing; actual_present_artifacts distinguishes current hashes from historical artifact_records.",
    final_test_result=dict(passed=78, failed=0, receipt="check007/receipt.json", substantive_command=".venv/bin/python -B verification/tool_graders_standard_blast_database_results_2026-10-26_333/run_checks.py check007"),
    source_files=[record(path) for path in sources], implementation_at_test=request["implementation"], implementation_request=record(request_path),
    receipts=receipts, frozen_generations=generations,
    known_number_assertions=dict(kernel_T1=[.8, .2], kernel_T2=[2 / 3, 1 / 3], census_100_10=[2 / 7, 5 / 7],
        taxa_AAB=dict(comparable_pairs=3, same_pairs=1, same_pair_fraction=1 / 3, target_A_fraction=2 / 3),
        quality_percentages=dict(completeness95=.95, contamination125=1.25), translated_overlap_nt=9,
        malformed_HSP=dict(reported_query_length=12, reported_reference_length=15, native_score_bits=None, paired_query_units=None, qualified_paired_query_units=None, geometry_available=False),
        PSSM_calculator_exception=dict(artifact_key="query", components=None, preserved_native_score_bits=20, preserved_qualified_reference_nt=9, fabricated_PSSM_rows=0),
        tblastn_80aa=dict(query_coverage=1, reference_paired_nt=240, reference_length_nt=243, reference_coverage=240 / 243),
        blastx_range=dict(reported_query_length_nt=186, full_query_length_nt=244, selected_interval=[29, 215],
            qualified_paired_query_nt=186, full_query_coverage=186 / 244, first_reverse_query_interval=[212, 215], raw_reported_query_coverage=None)),
    evidence_kinds=dict(source_inspection=True, deterministic_numerical_tests=True, immutable_file_worker_tests=True,
        synthetic_standard_database_inputs=True, unchanged_retained_paired_format_tests=True,
        real_database_execution=False, live_API=False, live_HPC=False, episode_communication=False),
    remaining=["E336 owns selected episode/consumer/return/publication integration and its proof.",
        "Live standard database execution requires an explicitly selected prepared HPC deployment and is not authorized here.",
        "API route work remains separately recorded.",
        "Native database-path versus semantic census-name equality retains unchanged303 limitation.",
        "Whole-contig functions cannot be inferred from feature-only metadata; absent full sequence identity and census remain unavailable."],
    objective_reset="Complete immutable objective and all16 design principles reread verbatim; accepted327 contract and additive001/002/003/004 reread before closeout.")
destination = HERE / "HANDOFF_EVIDENCE_003.json"
with destination.open("x") as stream:
    json.dump(evidence, stream, indent=2, sort_keys=True); stream.write("\n")
print(json.dumps(dict(evidence=str(destination), source_count=len(sources), generation_count=len(generations))))
