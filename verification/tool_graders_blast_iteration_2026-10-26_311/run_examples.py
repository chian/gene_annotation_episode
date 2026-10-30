"""Export complete numerical examples through the bounded local_jobs binding."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent


def worker(destination):
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
    from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
    from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
    from tests.test_blast_iteration_inputs import (make_inputs, from_collection, add_pair, add_pssm, add_members,
        add_convergence, operand, hsp)
    from tests.test_blast_iteration_calculators import table_inputs
    from tests.test_blast_sequence_database import invocation

    destination.mkdir()
    manifest, summaries = [], {}

    def save(name, arguments, classification, *, sources=(), warmer=False):
        sheet = populate_blast_iteration_sheet(**arguments)
        components = calculate_blast_iteration_components(sheet)
        files = {}
        objects = {"sheet": sheet, "components": components}
        if warmer:
            objects["components_temperature2"] = calculate_blast_iteration_components(sheet, sequence_model={"temperature_bits": 2})
        for kind, data in objects.items():
            path = destination / (name + "." + kind + ".json")
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            files[kind] = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest.append(dict(example=name, classification=classification, files=files, retained_sources=list(sources)))
        return components

    args = make_inputs([["A", "B", "B"], ["B", "C"]])
    add_pair(args)
    pkey = add_pssm(args)
    add_members(args, pkey)
    add_convergence(args)
    result = save("synthetic_sequence_sets_membership", args,
        "Synthetic searches, checkpoint and supplied membership/convergence records; no native membership or convergence decoder.", warmer=True)
    comparison = result["round_comparisons"][0]
    summaries["sequence_sets_membership"] = {
        "raw_hits": [s["counts"]["reported_hit_count"]["value"] for s in result["searches"]],
        "target_counts_and_changes": {k: comparison[k]["value"] for k in
            ("earlier_target_count", "later_target_count", "added_count", "removed_count", "retained_count")},
        "first_search_function_weights": result["searches"][0]["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"],
        "membership_counts": {k: result["inclusion_observations"][0][k]["value"] for k in
            ("member_record_count", "observed_unique_member_count", "duplicate_member_count", "included_sequence_count")},
        "native_state_in_supplied_record": result["searches"][0]["native_converged"]}
    incomplete = deepcopy(args)
    incomplete["sequence_metadata"][0]["sequence_identity_bindings"].pop()
    result = save("synthetic_incomplete_returned_identity", incomplete, "Synthetic missing full-target identity; observed subset retained, complete differences unavailable.")
    summaries["incomplete_identity"] = {"earlier_known_rows": len(result["round_comparisons"][0]["earlier_targets"]),
        "added_count": result["round_comparisons"][0]["added_count"]}

    args = make_inputs([["P1", "P2"], ["P2", "P3"]], program="deltablast", stages=["domain_database"]*2,
                       query=operand(length=100, selected_interval=None))
    add_pair(args, basis="profile_model_identifier")
    result = save("synthetic_delta_domains", args, "Synthetic DELTA domain-stage relations and model records, using delivered 305 calculations unchanged.")
    summaries["delta_domains"] = {"bits": result["searches"][0]["profile_components"]["hsps"][0]["native_components"]["native_scores"]["bit_score"],
        "threshold_margin": result["searches"][0]["profile_components"]["hsps"][0]["model_matches"][0]["specific_bits_margin"],
        "query_coverage": result["searches"][0]["profile_components"]["models"][0]["query_coverage"],
        "model_coverage": result["searches"][0]["profile_components"]["models"][0]["model_coverage"],
        "differences": [result["round_comparisons"][0][k+"_count"]["value"] for k in ("added", "removed", "retained")]}

    args = make_inputs([["A"]], raw_searches=[dict(query_id="q", query_title="q", query_len=8,
        hits=[False, dict(len=10, description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[None, hsp(40)])])])
    result = save("synthetic_malformed_native_rows", args, "Synthetic malformed raw JSON rows preserving original ordinals and valid sibling measurements.")
    summaries["malformed_rows"] = {k: v["value"] for k, v in result["searches"][0]["counts"].items()}
    result = save("synthetic_partial_table", table_inputs(malformed=True, delimiter="@"), "Synthetic table7 with explicit @ layout and one unassignable row.")
    summaries["partial_table"] = {k: v["value"] for k, v in result["searches"][0]["counts"].items()}

    args = make_inputs([["A"], ["A"], ["A"]], labels=[7, 7, 11], stages=[None]*3, program="deltablast")
    args["search_bindings"] = []
    for i in range(3):
        add_pssm(args, key=f"unassociated-{i}", role=None)
    result = save("synthetic_unknown_delta_stage", args, "Synthetic native labels 7,7,11 and three unassociated synthetic checkpoints; no inferred stage, biological round, or final result.")
    summaries["unknown_stage"] = {"native_labels": [s["native_iteration"]["value"] for s in result["searches"]],
        "biological_rounds": [s["biological_round"]["value"] for s in result["searches"]], "pssm_artifacts": len(result["pssms"])}

    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey, ())
    args["inclusion_records"][0]["evidence"]["original_record"] = []
    result = save("synthetic_complete_empty_membership", args, "Synthetic complete membership record with empty retained original list; measured zero identifiers.")
    summaries["empty_membership"] = result["inclusion_observations"][0]["included_sequence_count"]
    args = make_inputs()
    add_convergence(args)
    add_convergence(args, False, key="conflicting_explicit_state")
    save("synthetic_conflicting_convergence", args, "Synthetic contradictory supplied native states at one exact search scope; no log parsing.")

    args = from_collection(parse_blast_report_collection({}, artifacts=[], invocation=invocation()))
    sources = []
    for name in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn"):
        path = ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306/sources" / name
        contents = path.read_bytes()
        sources.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(contents).hexdigest(), size_bytes=len(contents)))
        args["pssm_sheets"].append(read_blast_pssm(contents, format="scoremat_asn_text", artifact_key=name,
                                                 source_ref="retained:upstream-306/"+name))
    result = save("retained_upstream_pssm_inputs", args,
        "Actual retained upstream NCBI checkpoint input bytes; no new native search. Empty synthetic invocation envelope supplies no search/stage/round/association.", sources=sources)
    summaries["upstream_pssms"] = [dict(artifact=p["artifact_key"], dimensions=p["components"]["matrices"][0]["dimensions"],
        master_length=p["components"]["matrices"][0]["master"]["decoded_length"]) for p in result["pssms"]]
    (destination / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (destination / "NUMERICAL_SUMMARY.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))


if "--worker" in sys.argv:
    worker(Path(sys.argv[-1]))
else:
    from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
    run = BASE / sys.argv[1]
    run.mkdir()
    temporary = run / "temporary"
    temporary.mkdir()
    command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).resolve()), "--worker", str(run / "filled")]
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    result = run_local_job(command, cwd=run, policy=policy,
        env={"PYTHONPATH": str(ROOT), "TMPDIR": str(temporary), "PYTHONDONTWRITEBYTECODE": "1"},
        stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
    (run / "receipt.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
        stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())
    print(json.dumps({"returncode": result.returncode, "receipt": str(run / "receipt.json")}))
    raise SystemExit(result.returncode)
