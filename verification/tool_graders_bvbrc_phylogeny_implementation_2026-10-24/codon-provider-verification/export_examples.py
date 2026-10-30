"""Export populated C sheets and verify saved JSON with all I/O/readers blocked."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy

from run_tests import HERE, ROOT, STAGING, establish_overlay


def digest(path):
    data = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main():
    imports = establish_overlay()
    test = runpy.run_path(str(STAGING / "tests" / "test_bvbrc_codon_tree_provider.py"))
    fixture, native_fixture = test["fixture"], test["native_fixture"]
    cases = {}
    cases["retained_native_nine_row"] = (native_fixture(), "retained_official_native_artifacts")
    cases["source_syntax_hand_components"] = (fixture(), "synthetic_values_in_actual_current_source_syntax")
    cases["source_syntax_consistent_selection"] = (fixture(membership_bytes=(
        b"F1\tProteins\t\ta\tc\td\tdeletedParalogs: \tb\n"
        b"F1\tCodons\t\ta\tc\tlacking CodonAlignment for F1: \td\n")),
        "synthetic_values_in_actual_current_source_syntax")
    history = fixture()
    test["historical"](history)
    cases["historical_frequency_hand_values"] = (history, "synthetic_exact_pretrim_operands")
    for completeness in ("complete", "unknown", "partial", "truncated"):
        case = fixture()
        test["historical"](case, complete=completeness, empty=True)
        cases["historical_empty_" + completeness] = (case, "synthetic_explicit_historical_population")
    cases["null_alignment_usable_tree"] = (fixture(include_alignment=False), "synthetic_partial_input")
    partial = fixture()
    partial["assembly"]["family_matrices"][0]["rows"].pop(3)
    partial["assembly"]["family_matrices"][0]["completeness"] = "partial"
    cases["partial_matrix_unknown_absence"] = (partial, "synthetic_incomplete_matrix")
    unknown = fixture()
    unknown["assembly"]["family_matrices"] = []
    unknown["documents"]["parsed"]["analyses"][0]["explicit_family_matrix_id"] = None
    unknown["joins"]["feature_genomes"] = []
    cases["unknown_namespace_raw_tables_retained"] = (unknown, "synthetic_missing_metadata")
    cases["duplicate_native_feature_occurrences"] = (fixture(membership_bytes=(
        b"F1\tProteins\t\ta\ta\nF2\tProteins\t\te\nF2\tCodons\t\te\n")), "synthetic_native_duplicate")
    cases["main_group_optional_distinct"] = (test["with_requested_sets"](fixture()), "synthetic_explicit_request_sets")
    cases["actually_forwarded_optional"] = (test["forwarded_optional"](fixture()), "synthetic_observed_invocation")
    cases["complete_main_outside_optional"] = (test["scoped_outside_membership_fixture"](), "synthetic_scoped_complete_matrix")
    cases["complete_empty_main_outside_memberships"] = (test["scoped_outside_membership_fixture"](empty=True), "synthetic_scoped_complete_matrix")
    sample = test["model_sample_fixture"]()
    cases["explicit_sample_final_column_map"] = (sample, "retained_native_plus_explicit_synthetic_sample_witness")
    unmapped = deepcopy(sample)
    unmapped["assembly"]["model_associations"][-1]["sample_column_map"] = None
    cases["sample_correspondence_unknown"] = (unmapped, "retained_native_plus_unmapped_synthetic_sample")
    cases["aggregate_member_identity_unknown"] = (test["sequence_member_fixture"](), "synthetic_unqualified_shared_container")
    cases["exact_original_member_identity"] = (test["sequence_member_fixture"](exact=True), "synthetic_exact_original_content_and_pointer")
    examples = HERE / "examples"
    examples.mkdir(exist_ok=True)
    manifest, replays = [], []
    for name, (args, classification) in cases.items():
        result = test["provider"].extract_codon_tree_sheet(**args)
        assert result["value"] is not None, (name, result)
        sheet = result["value"]
        params = test["params"](sheet)
        if args["assembly"]["historical_frequencies"]:
            params["worst_sequence_population_id"] = "historical"
        components = test["grader"].calculate_codon_tree(sheet, params)
        payloads = {"supplied": args, "sheet": sheet, "parameters": params, "components": components,
                    "extraction_outcome": {"status": result["status"], "diagnostics": result["diagnostics"]}}
        files = {}
        for kind, value in payloads.items():
            path = examples / (name + "." + kind + ".json")
            path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            files[kind] = digest(path)
        # Load everything before the guard. Calculation sees only these saved
        # objects; acquisition, parsing and experiment execution are forbidden.
        saved_sheet = json.loads((examples / (name + ".sheet.json")).read_text())
        saved_params = json.loads((examples / (name + ".parameters.json")).read_text())
        saved_components = json.loads((examples / (name + ".components.json")).read_text())
        before = deepcopy((saved_sheet, saved_params))
        with test["offline_guard"]():
            replay = test["grader"].calculate_codon_tree(saved_sheet, saved_params)
        assert replay == saved_components, name
        assert (saved_sheet, saved_params) == before, name
        manifest.append({"name": name, "classification": classification, "extraction_status": result["status"],
            "files": files, "reader_outcomes": len(sheet["read_outcomes"]),
            "families": len(sheet["families"]), "genomes": len(sheet["genomes"]), "models": len(sheet["models"]),
            "missing_requirements": len(components["missing_requirements"]), "original_task_custody_verified": False,
            "live_scientific_execution": False})
        replays.append({"name": name, "exact_components_equal": True, "inputs_unchanged": True,
            "io_network_execution_readers_disabled": True, "sheet_sha256": files["sheet"]["sha256"],
            "parameters_sha256": files["parameters"]["sha256"], "components_sha256": files["components"]["sha256"]})
    native_dir = test["NATIVE"] / "test9_genome_dir"
    native_sources = [test["NATIVE"] / "test9_genome.ids", native_dir / "test9_genome.genomeGenePgfams.txt",
        native_dir / (test["BASE"] + ".phy"), native_dir / (test["BASE"] + ".partitions"),
        native_dir / ("RAxML_info." + test["BASE"]), native_dir / ("RAxML_bipartitions." + test["BASE"]),
        native_dir / "test9_genome_8taxa_10cds_10proteins.pgfamsAndGenesIncludedInAlignment.txt"]
    source_paths = [ROOT / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees" / p
        for p in ("service-scripts/App-CodonTree.pl", "app_specs/CodonTree.json", "scripts/p3x-build-codon-tree.py", "lib/phylocode.py")]
    receipt = {"imports": imports, "examples": manifest, "native_source_files": [digest(p) for p in native_sources],
        "inspected_producers": [digest(p) for p in source_paths], "replay_count": len(replays),
        "scope": "Pure provider extraction/validation/calculation only; no C4 custody, live job, or episode integration claim."}
    (HERE / "examples-manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (HERE / "offline-replays.json").write_text(json.dumps(replays, indent=2) + "\n")
    print(json.dumps({"exported_examples": len(manifest), "exact_guarded_replays": len(replays),
        "native_sources_hashed": len(native_sources), "live_jobs": 0}))


if __name__ == "__main__":
    main()
