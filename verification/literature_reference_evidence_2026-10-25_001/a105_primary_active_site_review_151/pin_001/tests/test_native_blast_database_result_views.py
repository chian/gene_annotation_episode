"""Frozen restrictions and closed family schemas; no interpretation on replay."""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode import native_blast_database_result_views as views
from gene_annotation_episode import native_blast_database_result_worker as worker
from tests.test_native_blast_database_result_worker import (
    CALCULATION_ID, calculate_rows, psi_sheets, profile_sheets, vdb_sheets, family, metric)


def selector(*projections):
    return dict(version="native_blast_database_result_selector_v1", acquisition="complete_bound_bundle",
        metadata_inputs=[], retained_sources=[], projections=list(projections))


def projection(name="hsp", metrics=("native_score_bits",), booleans=(), rows=None):
    return dict(family=name, metrics=list(metrics), booleans=list(booleans), rows=rows or {"offset": 0, "limit": 10})


def test_all_closed_families_and_exact_publication_sources():
    original_families = {
        "search", "hsp", "sequence_hit", "vdb_subject", "sequence_group", "sequence_function",
        "sequence_population", "sequence_taxonomy", "sequence_quality", "sequence_record_quality",
        "profile_model", "profile_hsp_model", "profile_overlap", "iteration_inclusion", "iteration_comparison",
        "vdb_membership", "vdb_sequence_group", "vdb_sample", "vdb_feature", "vdb_feature_hsp", "vdb_taxonomy",
        "vdb_quality", "vdb_population", "vdb_population_function", "pssm_matrix", "pssm_position", "pssm_cell",
        "iteration_convergence"}
    assert len(original_families) == 28
    assert set(views.FUNCTION_FAMILIES) == {"vdb_function_summary", "vdb_function", "vdb_function_contribution", "vdb_function_census"}
    catalog = views.native_blast_database_metric_definitions()
    assert set(catalog) == original_families | set(views.FUNCTION_FAMILIES) == set(views._IDENTITIES)
    assert catalog["iteration_convergence"] == {}
    for name, definitions in catalog.items():
        schema = views.native_blast_database_row_schema(name)
        assert schema["additionalProperties"] is False
        assert "source_ref" not in schema["properties"]
        for definition in definitions.values():
            assert set(definition) == {"inputs", "formula", "units", "population", "denominator", "origin", "coordinates", "uncertainty", "missingness"}
    sources = views.native_blast_database_fact_sources()
    original_sources = {"execution_blast_database_" + f + "_rows" for f in original_families} | {
        "execution_blast_database_result_refs", "execution_blast_database_failures", "execution_blast_database_acquisition"}
    assert len(original_sources) == 31
    assert set(sources) == original_sources | {"execution_blast_database_" + f + "_rows" for f in views.FUNCTION_FAMILIES} | {views.SAVED_INPUT_SOURCE}
    for name in catalog:
        source = "execution_blast_database_" + name + "_rows"
        assert sources[source]["report_schema"]["x-source"] == source
        assert set(sources[source]["report_schema"]["items"]["properties"]) - set(views.native_blast_database_row_schema(name)["properties"]) == {
            "source_ref", "observation_ref", "subject_ref", "reference_refs", "publication_status"}
    descriptor_array = sources[views.SAVED_INPUT_SOURCE]["report_schema"]
    assert descriptor_array["x-source"] == views.SAVED_INPUT_SOURCE
    descriptor = descriptor_array["items"]
    assert descriptor["additionalProperties"] is False
    assert set(descriptor["properties"]) == set(descriptor["required"]) == {
        "schema", "original_result_receipt", "manifest_artifact_ref", "manifest_sha256", "sheets_artifact_ref",
        "sheets_sha256", "collection_artifact_ref", "collection_sha256", "input_interpretation_id", "original_calculation_id"}
    assert descriptor["properties"]["schema"] == {"const": "native_blast_vdb_function_saved_input_v1"}
    address = descriptor["properties"]["original_result_receipt"]
    assert address["additionalProperties"] is False
    assert set(address["properties"]) == set(address["required"]) == {"source_ref", "run_id", "episode_id", "operation_key", "receipt_sha256"}


@pytest.mark.parametrize("change", [
    lambda s: s.update(unknown=True),
    lambda s: s["projections"][0].update(metrics=["unrelated"]),
    lambda s: s["projections"][0].update(booleans=["geometry_complete"]),
    lambda s: s["projections"][0].update(metrics=[]),
    lambda s: s["projections"][0]["rows"].update(offset=True),
    lambda s: s["projections"][0]["rows"].update(offset=1.0),
    lambda s: s["projections"].append(deepcopy(s["projections"][0])),
])
def test_selector_rejects_extra_undefined_duplicate_and_untyped_values(change):
    s = selector(projection()); change(s)
    with pytest.raises(ValueError):
        views.validate_native_blast_database_result_selector(s, program="psiblast")


def test_boolean_only_query_convergence_and_family_program_restriction():
    s = selector(projection("iteration_convergence", metrics=(), booleans=("native_converged",)))
    assert views.validate_native_blast_database_result_selector(s, program="psiblast") == s
    with pytest.raises(ValueError):
        views.validate_native_blast_database_result_selector(s, program="rpsblast")


def test_frozen_projection_copies_cells_in_requested_order_and_no_recalculation(monkeypatch):
    _, rows = calculate_rows(psi_sheets())
    hsps = family(rows, "hsp")
    def forbidden(*a, **kw):
        raise AssertionError("frozen projection called interpretation")
    for name in ("calculate_native_blast_database_sheets", "build_native_blast_database_rows", "parse_blast_report_collection"):
        monkeypatch.setattr(worker, name, forbidden)
    chosen = [hsps[-1]["record_key"], hsps[0]["record_key"]]
    s = selector(projection(metrics=("reported_query_coverage", "native_score_bits"), rows={"record_keys": chosen}))
    result = views.project_native_blast_database_rows(rows, selector=s, calculation_id=CALCULATION_ID)
    assert result["failures"] == []
    output = result["families"][0]
    assert output["selected_record_keys"] == chosen
    for saved, actual in zip((hsps[-1], hsps[0]), output["rows"]):
        assert actual["measurements"] == [metric(saved, "reported_query_coverage"), metric(saved, "native_score_bits")]
        assert actual["component_refs"] == saved["component_refs"] and actual["booleans"] == []
    output["rows"][0]["measurements"][0]["value"] = -1
    assert metric(hsps[-1], "reported_query_coverage")["value"] == .5


def test_paging_end_empty_and_missing_explicit_key_are_distinct():
    _, rows = calculate_rows(psi_sheets())
    page = views.project_native_blast_database_rows(rows, selector=selector(projection(rows={"offset": 0, "limit": 1})), calculation_id=CALCULATION_ID)
    assert page["families"][0]["next_offset"] == 1
    empty = views.project_native_blast_database_rows(rows, selector=selector(projection(rows={"offset": 999, "limit": 1})), calculation_id=CALCULATION_ID)
    assert empty["families"][0]["rows"] == [] and empty["families"][0]["next_offset"] is None and empty["failures"] == []
    missing = views.project_native_blast_database_rows(rows, selector=selector(projection(rows={"record_keys": ["native_blast_database_row:absent"]})), calculation_id=CALCULATION_ID)
    assert missing["failures"][0]["detail_code"] == "explicit_row_missing"


@pytest.mark.parametrize("change", [
    lambda r: r.update(extra=True),
    lambda r: r["measurements"][0].update(value=float("nan")),
    lambda r: r["measurements"][0].update(value=True),
    lambda r: r["measurements"][0].update(unit="sample"),
    lambda r: r["measurements"][0].update(status="unavailable"),
    lambda r: r["identity"]["row_key"].update(hsp_ordinal=1.0),
    lambda r: r["measurements"].append(deepcopy(r["measurements"][0])),
    lambda r: r.update(calculation_id="b" * 64),
])
def test_row_replay_rejects_mutations_and_nonfinite_cells(change):
    _, rows = calculate_rows(psi_sheets(hit_sets=[["A"]]))
    row = deepcopy(family(rows, "hsp")[0]); change(row)
    with pytest.raises(ValueError):
        views.project_native_blast_database_rows([row], selector=selector(projection()), calculation_id=CALCULATION_ID)


def test_record_identity_independent_of_model_calculation_and_projection():
    sheets = psi_sheets(hit_sets=[["A", "B"]])
    _, first = calculate_rows(sheets)
    _, second = calculate_rows(sheets, model={"temperature_bits": 2}, calculation_id="b" * 64)
    assert [r["record_key"] for r in first] == [r["record_key"] for r in second]
    assert family(first, "sequence_function")[0]["calculation_id"] != family(second, "sequence_function")[0]["calculation_id"]
    assert metric(family(first, "sequence_function")[1], "function_mass")["value"] != metric(family(second, "sequence_function")[1], "function_mass")["value"]


def test_metadata_selector_tuple_identity_and_same_key_byte_constraint():
    selected = selector(projection())
    selected["metadata_inputs"] = [dict(input_key="same", consumer="query_identity", schema_id="schema1", artifact_ref="artifact:metadata", sha256="a" * 64, size_bytes=12),
        dict(input_key="same", consumer="profile", schema_id="schema2", artifact_ref="artifact:metadata", sha256="a" * 64, size_bytes=12)]
    assert views.validate_native_blast_database_result_selector(selected, program="psiblast") == selected
    duplicate = deepcopy(selected); duplicate["metadata_inputs"].append(deepcopy(selected["metadata_inputs"][0]))
    with pytest.raises(ValueError):
        views.validate_native_blast_database_result_selector(duplicate, program="psiblast")
    changed = deepcopy(selected); changed["metadata_inputs"][1]["sha256"] = "b" * 64
    with pytest.raises(ValueError):
        views.validate_native_blast_database_result_selector(changed, program="psiblast")


def test_cyclic_input_is_not_a_finite_json_selector():
    selected = selector(projection())
    selected["cycle"] = selected
    with pytest.raises(ValueError, match="finite_json_required"):
        views.validate_native_blast_database_result_selector(selected, program="psiblast")
