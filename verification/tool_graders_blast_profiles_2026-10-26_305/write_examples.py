"""Offline verification outputs, not scientific profile-search measurements."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from gene_annotation_episode.blast_pairwise_grader import alignment_components
from gene_annotation_episode.blast_profile_inputs import populate_blast_profile_sheet
from gene_annotation_episode.blast_profile_calculators import calculate_blast_profile_components
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from test_blast_profile_inputs import make_inputs, provenance, synthetic_hit, synthetic_hsp
from test_blast_profile_calculators import tabular_inputs

DEST = Path(sys.argv[1]).resolve()
DEST.mkdir(exist_ok=True)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


examples = {
    "rps_base": make_inputs(), "translated_reverse": make_inputs("rpstblastn", reverse=True),
    "delta_qualified_domain": make_inputs("deltablast"), "delta_unknown_stage": make_inputs("deltablast"),
    "native_model_length_conflict": make_inputs(), "unbound_query": make_inputs("rpstblastn", reverse=True),
    "missing_threshold": make_inputs(), "wrong_archive_member": make_inputs(archive=True),
    "zero_hit_report": make_inputs(hits=[]), "missing_report": make_inputs(hits=[], missing_hits=True),
    "failed_zero_hit_report": make_inputs(hits=[], native_returncode=2, producer_complete=False),
    "malformed_table_row": tabular_inputs(reverse=True),
    "bare_table6": tabular_inputs(format_name="tabular6", malformed=False, delimiter="@"),
    "old_table_without_layout": tabular_inputs(malformed=False),
    "same_family_models": make_inputs(hits=[synthetic_hit(), synthetic_hit(2, start=21)]),
    "same_version_unknown_release": make_inputs(), "ambiguous_model_links": make_inputs(),
    "source_bound_query_missing_digest": make_inputs(),
    "literal_general_model_identifier": make_inputs(),
    "tampered_row_map": make_inputs(),
}
examples["delta_unknown_stage"]["search_binding"]["stage"] = None
examples["native_model_length_conflict"]["profile_records"][0]["num_columns"] = 120
examples["unbound_query"]["query_binding"] = None
examples["source_bound_query_missing_digest"]["query_binding"]["sequence_sha256"] = None
examples["literal_general_model_identifier"]["profile_records"][0]["model_identifier"] = {
    "namespace": "CDD", "value": "gnl|CDD|1001", "version": None}
examples["missing_threshold"]["profile_records"][0]["specific_bits_threshold"] = None
examples["wrong_archive_member"]["report_source"]["member_ordinal"] = 2
del examples["old_table_without_layout"]["search"]["normalized"]["native"]["table_layout"]
examples["same_family_models"]["model_relations"] = [{"left_profile_key": "profile_1", "right_profile_key": "profile_2",
    "relation": "same_family", "provenance": provenance("/explicit_family_relation")}]
examples["same_version_unknown_release"]["search_binding"]["database_identity"]["release"] = None
examples["same_version_unknown_release"]["profile_records"][0]["database_identity"]["release"] = None
second = deepcopy(examples["ambiguous_model_links"]["profile_records"][0])
second["profile_key"] = "second_model"
examples["ambiguous_model_links"]["profile_records"].append(second)
binding = deepcopy(examples["ambiguous_model_links"]["profile_bindings"][0])
binding["profile_key"] = "second_model"
examples["ambiguous_model_links"]["profile_bindings"].append(binding)
examples["tampered_row_map"]["search"]["row_map"][0]["hsp_ordinals"] = [9]
hit = synthetic_hit(positions=30)
overlap = synthetic_hsp(start=21, positions=30, bits=43.12345678901234)
overlap.update(hit_from=21, hit_to=50)
hit["hsps"].append(overlap)
examples["overlapping_hsp_union"] = make_inputs(hits=[hit])
hit = synthetic_hit()
hit["description"].insert(0, "malformed description")
hit["hsps"].insert(0, None)
examples["original_malformed_ordinals"] = make_inputs(hits=[None, hit])
hit = synthetic_hit()
hit["hsps"].append({"bit_score": 45, "align_len": 20, "identity": 10, "gaps": 0})
examples["incomplete_geometry"] = make_inputs(hits=[hit])
examples["selected_query"] = make_inputs(hits=[synthetic_hit(start=21, positions=30)], selected=[20, 60], query_length=40)

index = []
for name, inputs in examples.items():
    sheet = populate_blast_profile_sheet(**inputs)
    components = calculate_blast_profile_components(sheet)
    save(DEST / name / "sheet.json", sheet)
    # Recalculation after a real JSON persistence boundary; no acquisition.
    loaded = json.loads((DEST / name / "sheet.json").read_text())
    assert calculate_blast_profile_components(loaded) == components
    save(DEST / name / "components.json", components)
    model = components["models"][0] if components["models"] else None
    index.append({"name": name, "evidence_kind": "synthetic_profile_context", "status": components["status"],
        "hsp_count": len(components["hsps"]), "model_count": len(components["models"]),
        "first_model": {key: model[key] for key in ("paired_query_units", "paired_model_positions", "query_coverage", "model_coverage")}
            if model is not None else None,
        "issue_codes": sorted({issue["code"] for issue in components["issues"]})})

manifest = json.loads((ROOT / "verification/tool_graders_blast_collection_2026-10-26_293/native_fixtures/manifest.json").read_text())
native_index = []
for case in ("blastn_reverse", "blastp_gaps", "blastx_reverse", "tblastn_reverse", "tblastx_frames"):
    pair = []
    for fmt in ("json15", "tabular7"):
        entry = next(row for row in manifest if row["name"] == case + "_" + fmt)
        raw = (ROOT / entry["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        search = parse_blast_report_collection({"report": raw}, artifacts=[entry["artifact"]], invocation=entry["invocation"])["searches"][0]
        assert search["program_context"]["scientific_mode"] == "pairwise"
        components = []
        for hit in search["normalized"]["hits"]:
            for hsp in hit["hsps"]:
                components.append(alignment_components(hsp, program=search["program_context"]["geometry_program"],
                    query_length=search["normalized"]["query"]["length"], reference_length=hit["length"],
                    coordinate_convention="blast_json2" if fmt == "json15" else "directional"))
        save(DEST / "retained_paired_geometry_only" / (entry["name"] + ".json"), {
            "evidence_kind": "genuine_retained_paired_output_shared_geometry_only",
            "original_fixture": entry, "search": search, "geometry_components": components})
        pair.append(components)
        native_index.append({"name": entry["name"], "path": entry["path"], "sha256": entry["sha256"],
            "evidence_kind": "genuine_retained_paired_output_shared_geometry_only", "hsp_count": len(components)})
    assert [row["pairs"] for row in pair[0]] == [row["pairs"] for row in pair[1]]
    assert [row["counts"] for row in pair[0]] == [row["counts"] for row in pair[1]]
save(DEST / "INDEX.json", {"synthetic_profile_examples": index, "retained_geometry": native_index,
    "native_profile_search_observed": False, "live_profile_search_executed": False,
    "profile_resource_binding_verified": False, "profile_episode_return_verified": False})
print(json.dumps({"synthetic_examples": len(index), "retained_paired_geometry_artifacts": len(native_index),
                  "destination": str(DEST)}, indent=2))
