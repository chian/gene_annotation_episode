"""Synthetic selected-return tests; all execution is through the391 local job.

Fixture readers/calculators run before guards. These tests make no claim of an
authenticated native attempt, Store publication, or episode communication.
"""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import builtins
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode import protein_structure_result_views as v
from gene_annotation_episode import protein_structure_contracts as a
from gene_annotation_episode import protein_structure_calculations as calc
from gene_annotation_episode.protein_structure_sequences import inspect_structure

f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
b = import_module("verification.tool_graders_protein_structure_calculations_2026-10-27_389.fixture_helpers")


def select(family, members, fields, *, name="selected", offset=None, limit=1, delivery="values"):
    return {"projection_id": name, "family": family, "members": members, "fields": fields,
        "window": None if offset is None else {"offset_0based": offset, "limit": limit}, "delivery_kind": delivery}

def comparison(sheet=None, parameters=None):
    sheet = b.make_sheet() if sheet is None else sheet
    return {"kind": "comparison", "sheet": sheet, "components": calc.calculate_protein_structure_components(sheet, parameters=parameters or sheet["native_request"])}

def extracted(*, descriptor=True):
    _, _, seq, meta = f.fixture_pdb(role="single")
    return {"kind": "extraction", "sequence": seq, "metadata": meta, "descriptor": f.sequence_descriptor(seq) if descriptor else None}

def projected(result, selection):
    return v.project_protein_structure_results(result, selection=[selection])[0]

def fields(row):
    return {f["field"]: f for f in row["values"]}

def summary(result, *names):
    return projected(result, select("comparison_summary", {"kind": "comparison"}, list(names)))

def published(rows, result=None):
    """Synthetic D2-shaped envelope, explicitly not custody authentication."""
    output = {key: deepcopy(value) for key, value in rows.items() if key not in ("rows", "calculation_id")}
    output.update(version="protein_structure_projection_v1", custody=f.synthetic_custody(), calculation=None)
    if result is not None:
        comp = result["components"]
        output["calculation"] = {"calculation_id": rows["calculation_id"], "input_numerical_sha256": comp["input_numerical_sha256"],
            "components_file": f.identity(canonical(comp).encode(), "protein_structure_components_v1")}
    if rows["selection"]["delivery_kind"] == "values":
        output["delivery"] = {"kind": "values", "rows": deepcopy(rows["rows"])}
    else:
        table = {"version": "protein_structure_projection_table_v1", "rows": rows["rows"]}
        output["delivery"] = {"kind": "artifact", "table_file": f.identity(canonical(table).encode(), "protein_structure_projection_table_v1"),
            "row_count": rows["returned_count"], "allowed_use": "read_exact_selected_table"}
    return output

def forbid_projection_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Projection attempted I/O, native reading, or scientific computation")
    for module, names in (
        (calc, ["calculate_protein_structure_components", "fit_ca_transform", "validate_declared_transform", "resolve_pair_selection"]),
        (import_module("gene_annotation_episode.protein_structure_formats"), ["parse_pdb_structure", "parse_mmcif_structure"]),
        (import_module("gene_annotation_episode.protein_structure_sequences"), ["extract_structure_sequence", "inspect_structure"]),
        (import_module("gene_annotation_episode.protein_structure_metadata"), ["extract_native_structure_metadata"]),
        (import_module("gene_annotation_episode.protein_structure_correspondence"), ["correspondence_from_pairwise_sheet", "validate_explicit_residue_map"]),
        (import_module("gene_annotation_episode.sequence_ops"), ["align_pair"]),
        (import_module("gene_annotation_episode.biopython_pairwise_grader"), ["build_biopython_pairwise_sheet"]),
        (import_module("numpy.linalg"), ["svd"]),
        (builtins, ["open"]), (Path, ["open", "read_bytes", "read_text", "write_bytes", "write_text"]),
        (subprocess, ["Popen", "run"]), (socket, ["socket", "create_connection"]),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)


def test_exact_registry_has_no_wildcards_or_shared_type_redefinitions():
    assert set(v.PROTEIN_STRUCTURE_FIELD_REGISTRY) == {"comparison_summary", "transform", "site_measurements", "correspondence", "structure_coordinates", "native_uncertainty", "structure_inventory", "extracted_sequence"}
    assert len(v.PROTEIN_STRUCTURE_FIELD_REGISTRY["comparison_summary"]["comparison"]) == 45
    sources = v.protein_structure_fact_sources()
    assert set(sources) == {"execution_protein_structure_projections", "execution_protein_structure_saved_sheets", "execution_protein_structure_sequences", "execution_protein_structure_failures"}
    shared = a.protein_structure_schema_definitions()
    for source in sources.values():
        schema = source["report_schema"]
        assert all(schema["$defs"][key] == value for key, value in shared.items())
        assert schema["$id"] == "urn:gene-annotation:protein-structure:schema:" + digest({k: x for k, x in schema.items() if k != "$id"})
    assert len({s["report_schema"]["$id"] for s in sources.values()}) == 4
    sources["execution_protein_structure_sequences"]["report_schema"]["$defs"]["FileIdentity"]["additionalProperties"] = True
    assert v.protein_structure_fact_sources()["execution_protein_structure_sequences"]["report_schema"]["$defs"]["FileIdentity"]["additionalProperties"] is False


def test_aggregate_only_preserves_two_sequence_denominators_and_precision(monkeypatch, tmp_path):
    fixed = b.cif_case(b.TETRAHEDRON + [[1, 1, 1]], missing=(3,))
    moving = b.cif_case(b.TETRAHEDRON + [[1, 1, 1], [2, 2, 2]], role="moving")
    result = comparison(b.make_sheet(fixed, moving, pairs=[(0, 0), (1, 1), (2, 2), (3, 3)]))
    original = deepcopy(result)
    request = select("comparison_summary", {"kind": "comparison"}, ["fixed_correspondence_coverage", "moving_correspondence_coverage", "fixed_paired_coordinate_coverage", "moving_paired_coordinate_coverage", "mapped_pair_coordinate_coverage", "mapped_pair_count"])
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        output = projected(result, request)
    actual = fields(output["rows"][0])
    expectations = {"fixed_correspondence_coverage": (0.8, 4, 5), "moving_correspondence_coverage": (2/3, 4, 6),
        "fixed_paired_coordinate_coverage": (0.6, 3, 5), "moving_paired_coordinate_coverage": (0.5, 3, 6), "mapped_pair_coordinate_coverage": (0.75, 3, 4)}
    for name, (value, numerator, denominator) in expectations.items():
        assert actual[name]["value"]["value"] == value
        assert actual[name]["population"]["numerator"] == numerator
        assert actual[name]["population"]["denominator"] == denominator
        assert actual[name]["population"]["member_ids"] == []
    assert actual["mapped_pair_count"]["value"]["value"] == 4
    assert actual["mapped_pair_count"]["population"]["denominator"] is None
    assert output["coordinate_set"] is None and output["requested_count"] == output["matched_count"] == output["returned_count"] == 1
    assert set(actual) == set(request["fields"])
    assert not any(word in canonical(output) for word in ('"atoms"', '"coordinate_pairs"', '"residues"', '"site_measurements"'))
    assert result == original
    (tmp_path / "synthetic_coverage_projection.json").write_text(canonical(output) + "\n")


def test_held_out_two_angstrom_site_is_separate_from_four_fit_anchors(monkeypatch, tmp_path):
    fixed = f.fixture_pdb("AGSTV", coordinates=b.TETRAHEDRON + [[1, 1, 1]])
    moving = f.fixture_pdb("AGSTV", role="moving", chain="B", coordinates=b.TETRAHEDRON + [[1, 1, 3]])
    params = f.fit_parameters()
    params["fit_selection"] = {"kind": "explicit", "members": [{"kind": "correspondence_id", "correspondence_id": "map_" + str(i)} for i in range(4)]}
    params["evaluation_selection"] = {"kind": "explicit", "members": [{"kind": "sequence_position", "structure_role": "moving", "position_0based": 4}]}
    result = comparison(b.make_sheet(fixed, moving, parameters=params))
    request = select("site_measurements", {"kind": "evaluation_requests", "request_indices_0based": [0]}, ["distance", "distance_squared", "in_fit", "evaluated", "fixed_residue", "moving_residue"])
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        site = projected(result, request)
        aggregate = summary(result, "fit_used_count", "evaluation_used_count", "evaluation_sse", "evaluation_rmsd")
    values = fields(site["rows"][0])
    assert values["distance"]["value"]["value"] == pytest.approx(2)
    assert values["distance_squared"]["value"]["value"] == pytest.approx(4)
    assert values["distance"]["value"] == result["components"]["site_measurements"][0]["distance"]
    assert values["distance"]["population"]["denominator"] == 1
    assert values["distance"]["population"]["member_ids"] == ["map_4"]
    assert values["in_fit"]["value"] is False and values["evaluated"]["value"] is True
    assert values["fixed_residue"]["value"]["position_key"]["chain_key"]["chain_id"] == "A"
    assert values["moving_residue"]["value"]["position_key"]["chain_key"]["chain_id"] == "B"
    numerical = fields(aggregate["rows"][0])
    assert numerical["fit_used_count"]["value"]["value"] == 4 and numerical["evaluation_used_count"]["value"]["value"] == 1
    assert numerical["evaluation_rmsd"]["population"]["denominator"] == 1
    (tmp_path / "synthetic_held_out_projection.json").write_text(canonical({"site": site, "aggregate": aggregate}) + "\n")


def test_original_and_saved_recalculation_identities_and_modes_are_distinct():
    original = comparison()
    saved_sheet = deepcopy(original["sheet"])
    saved_sheet["native_baseline"] = deepcopy(original["components"])
    parameters = b.declared_parameters(saved_sheet, translation=[0, 0, 2])
    later = comparison(saved_sheet, parameters)
    original_rows = summary(original, "fit_rmsd", "evaluation_rmsd")
    later_rows = summary(later, "fit_rmsd", "evaluation_rmsd")
    assert later_rows["calculation_id"] != original_rows["calculation_id"]
    assert later_rows["rows"][0]["identity"]["scientific_mode"] == "evaluate_declared_transform_ca"
    assert saved_sheet["scientific_mode"] == "fit_then_evaluate_ca"
    assert fields(later_rows["rows"][0])["fit_rmsd"]["value"]["state"] == "not_applicable"
    assert fields(later_rows["rows"][0])["evaluation_rmsd"]["value"]["value"] == 2
    assert later["sheet"]["native_baseline"] == original["components"]


def test_transform_selected_fields_and_retained_alignment_do_not_rebuild(monkeypatch):
    result = comparison(b.make_sheet(retained=True))
    request = select("transform", {"kind": "transform"}, ["rotation", "translation", "fit_member_ids", "fixed_geometry_rank", "numerical_parameters", "identifiability"])
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        output = projected(result, request)
    values = fields(output["rows"][0])
    assert values["fit_member_ids"]["value"] == ["column_0", "column_1", "column_2", "column_3"]
    assert values["fixed_geometry_rank"]["value"]["value"] == 3
    assert values["fixed_geometry_rank"]["population"]["numerator"] == 3
    assert values["identifiability"]["value"] == "identifiable_fit"
    assert values["rotation"]["value"] == result["components"]["transform"]["rotation"]
    assert set(values) == set(request["fields"])


def test_correspondence_preserves_insertion_codes_and_explicit_unknown_requests():
    result = comparison()
    output = projected(result, select("correspondence", {"kind": "correspondence_rows", "correspondence_ids": ["map_1", "absent"]}, ["correspondence_row"]))
    crosswalk = fields(output["rows"][0])["correspondence_row"]["value"]
    assert crosswalk["fixed_position_key"]["residue_number"] == 10
    assert crosswalk["fixed_position_key"]["insertion_code"] == "A"
    assert crosswalk["moving_position_key"]["residue_number"] == 102
    assert output["rows"][1]["values"] == []
    assert output["requested_count"] == output["returned_count"] == 2 and output["matched_count"] == 1
    assert output["state"] == "partial"


def test_missing_explicit_sites_are_rows_and_windows_count_full_population():
    result = comparison()
    request = select("site_measurements", {"kind": "evaluation_requests", "request_indices_0based": [3, 99, 1]}, ["distance"], offset=1, limit=1)
    output = projected(result, request)
    assert (output["requested_count"], output["matched_count"], output["returned_count"], output["omitted_count"]) == (3, 2, 1, 2)
    assert output["rows"][0]["identity"] == {"kind": "unresolved_request", "request": {"kind": "evaluation_request", "request_index_0based": 99}}
    assert output["rows"][0]["issues"][0]["code"] == "selected_field_unavailable"
    assert output["rows"][0]["values"] == []


def test_extracted_sequence_one_requested_header_and_selected_map_row(monkeypatch):
    result = extracted()
    request = select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "explicit", "positions_0based": [1]}}, ["sequence_length", "residue_map_row"])
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        output = projected(result, request)
    assert output["requested_count"] == output["matched_count"] == output["returned_count"] == 2
    assert [row["identity"]["kind"] for row in output["rows"]] == ["sequence_header", "sequence_position"]
    assert fields(output["rows"][0])["sequence_length"]["value"]["value"] == 4
    assert set(fields(output["rows"][1])) == {"residue_map_row"}
    assert "alignment_sequence" not in canonical(output) and "native_symbols" not in canonical(output)
    assert output["calculation_id"] is None


def test_extraction_header_and_map_unknown_are_not_hidden_success():
    result = extracted(descriptor=False)
    request = select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "explicit", "positions_0based": [99]}}, ["descriptor", "residue_map_row"])
    output = projected(result, request)
    assert output["requested_count"] == output["returned_count"] == 2 and output["matched_count"] == 1
    assert fields(output["rows"][0])["descriptor"]["value"] is None
    assert output["rows"][1]["identity"]["request"] == {"kind": "sequence_position", "sequence_position_0based": 99}
    assert output["state"] == "unavailable"


def test_unmapped_actual_and_unknown_position_requests():
    result = comparison(b.make_sheet(pairs=[(0, 0), (1, 1), (2, 2)]))
    output = projected(result, select("correspondence", {"kind": "unmapped_positions", "structure_role": "fixed", "positions_0based": [3, 99]}, ["unmapped_position"]))
    assert fields(output["rows"][0])["unmapped_position"]["value"]["reason"] == "explicit_map_unmapped"
    assert output["rows"][1]["identity"]["request"] == {"kind": "unmapped_position", "structure_role": "fixed", "sequence_position_0based": 99}
    assert output["matched_count"] == 1


def test_inventory_mixed_row_kinds_and_explicit_window():
    _, parsed, _, _ = f.fixture_pdb()
    inventory = inspect_structure(parsed, inventory_selection={"blocks": {"kind": "all"}, "include": ["models", "chains", "residue_variants", "native_metadata"]})
    result = {"kind": "inspection", "inventory": inventory}
    request = select("structure_inventory", {"kind": "all_inventory_rows"}, ["model", "chain", "position", "native_metadata"], offset=1, limit=2)
    output = projected(result, request)
    assert [list(fields(row)) for row in output["rows"]] == [["chain"], ["position"]]
    expected_count = sum(len(inventory[k]) for k in ("models", "chains", "positions", "metadata"))
    assert output["requested_count"] == output["matched_count"] == expected_count
    assert output["returned_count"] == 2 and output["omitted_count"] == expected_count - 2
    absent = projected(result, select("structure_inventory", {"kind": "inventory_rows", "row_keys": ["absent"]}, ["model"]))
    assert absent["requested_count"] == absent["returned_count"] == 1 and absent["matched_count"] == 0
    unavailable = deepcopy(inventory)
    unavailable.update(state="unavailable", models=[], chains=[], positions=[], metadata=[])
    with pytest.raises(ValueError, match="^selected_field_unavailable$"):
        projected({"kind": "inspection", "inventory": unavailable}, request)


def test_coordinate_frames_and_precomputed_atoms_are_retained_without_transformation(monkeypatch):
    sheet = b.make_sheet()
    params = b.declared_parameters(sheet, translation=[0, 0, 2])
    params["coordinate_sets"] = [{"coordinate_set_id": "moved", "structure_role": "moving", "members": {"kind": "sequence_positions", "positions": [3, 1]}, "atom_scope": "selected_ca", "frame": "moving_in_fixed_frame"}]
    result = comparison(sheet, params)
    request = select("structure_coordinates", {"kind": "coordinate_set", "coordinate_set_id": "moved"}, ["xyz", "atom_identity"], offset=1, limit=1)
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        output = projected(result, request)
    assert output["coordinate_set"] == params["coordinate_sets"][0]
    assert fields(output["rows"][0])["xyz"]["value"]["value"] == [1.0, 0.0, 2.0]
    assert output["rows"][0]["identity"]["sequence_position_0based"] == 1
    assert (output["requested_count"], output["returned_count"], output["omitted_count"]) == (2, 1, 1)
    assert v.validate_protein_structure_projection_result(published(output, result))["coordinate_set"] == params["coordinate_sets"][0]


def test_unknown_coordinate_population_raises_without_fabricated_zero():
    with pytest.raises(ValueError, match="^selected_field_unavailable$"):
        projected(comparison(), select("structure_coordinates", {"kind": "coordinate_set", "coordinate_set_id": "not_calculated"}, ["xyz"]))


def test_supplied_partial_coordinate_table_keeps_source_state_and_issues():
    # Deliberately supplied partial-result fixture: the four retained atom rows
    # are complete records, without a claim that the original capture is full.
    sheet = b.make_sheet()
    params = f.fit_parameters()
    params["coordinate_sets"] = [{"coordinate_set_id": "retained_atoms", "structure_role": "fixed", "members": {"kind": "all_selected_chain"},
        "atom_scope": "selected_chain_all_atoms", "frame": "original"}]
    result = comparison(sheet, params)
    issue = {"stage": "capture", "code": "capture_incomplete", "structure_role": "fixed", "position_key": None, "atom_row_key": None,
        "correspondence_id": None, "field": "coordinate_set", "artifact_role": None}
    result["components"]["state"] = "partial"
    coordinate = result["components"]["coordinate_sets"][0]
    coordinate.update(state="partial", requested_position_count=None, issues=[issue])
    output = projected(result, select("structure_coordinates", {"kind": "coordinate_set", "coordinate_set_id": "retained_atoms"}, ["xyz"]))
    assert output["requested_count"] == output["matched_count"] == output["returned_count"] == 4
    assert output["state"] == "partial" and output["issues"] == [issue]
    assert all(fields(row)["xyz"]["value"]["state"] == "present" for row in output["rows"])
    assert v.validate_protein_structure_projection_result(published(output, result))["state"] == "partial"


def test_missing_ca_distance_retains_unavailable_reason_and_known_match_count():
    fixed = b.cif_case(b.TETRAHEDRON, missing=(3,))
    moving = b.cif_case(b.TETRAHEDRON, role="moving")
    sheet = b.make_sheet(fixed, moving)
    parameters = b.declared_parameters(sheet)
    parameters["missing_coordinate_policy"] = "use_available"
    result = comparison(sheet, parameters)
    output = projected(result, select("site_measurements", {"kind": "evaluation_requests", "request_indices_0based": [3]}, ["distance", "fixed_declared_residue", "availability_reason"]))
    values = fields(output["rows"][0])
    assert values["distance"]["value"] == {"value": None, "state": "unavailable", "reason": "ca_missing", "unit": "angstrom", "origin": "derived"}
    assert values["availability_reason"]["value"] == "ca_missing"
    assert values["fixed_declared_residue"]["value"]["label_seq_id"] == 4
    assert output["requested_count"] == output["matched_count"] == output["returned_count"] == 1


def test_no_implicit_header_for_map_only_extraction_and_unknown_full_population():
    result = extracted(descriptor=False)
    request = select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "explicit", "positions_0based": [2]}}, ["residue_map_row"])
    output = projected(result, request)
    assert output["requested_count"] == 1 and output["rows"][0]["identity"]["kind"] == "sequence_position"
    result["sequence"].update(sequence_length=None, sequence_available=False, alignment_sequence=None)
    with pytest.raises(ValueError, match="^selected_field_unavailable$"):
        projected(result, select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "all"}}, ["residue_map_row"]))


def test_explicit_extraction_header_text_and_descriptor_only_when_requested():
    result = extracted()
    output = projected(result, select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "all"}}, ["alignment_sequence", "native_symbols", "descriptor"]))
    assert output["requested_count"] == 1
    values = fields(output["rows"][0])
    assert values["alignment_sequence"]["value"] == "AGST"
    assert values["native_symbols"]["value"] == ["A", "G", "S", "T"]
    assert values["descriptor"]["value"] == result["descriptor"]


def test_unavailable_explicit_sequence_string_has_a_failure_reason():
    result = extracted(descriptor=False)
    result["sequence"]["residues"][0]["alignment_symbol"] = None
    result["sequence"].update(state="partial", sequence_available=False, alignment_sequence=None)
    output = projected(result, select("extracted_sequence", {"kind": "extracted_sequence", "residue_positions": {"kind": "all"}}, ["alignment_sequence"]))
    assert fields(output["rows"][0])["alignment_sequence"]["value"] is None
    assert output["rows"][0]["issues"][0]["code"] == "selected_field_unavailable"
    assert output["rows"][0]["issues"][0]["field"] == "sequence"
    assert output["state"] == "unavailable"
    assert output["requested_count"] == output["matched_count"] == output["returned_count"] == 1


def test_all_enumerated_aggregate_and_transform_cells_have_expected_shapes():
    result = comparison()
    aggregate = summary(result, *v.COUNT_FIELDS, *v.COVERAGE_FIELDS, *v.ALIGNMENT_FIELDS, *v.AGGREGATE_FIELDS)
    measured = fields(aggregate["rows"][0])
    assert len(measured) == 45
    assert measured["fixed_coordinate_count"]["value"]["value"] == 4
    assert measured["evaluation_excluded_count"]["value"]["value"] == 0
    assert measured["alignment_score"]["value"]["state"] == "not_applicable"
    transform = projected(result, select("transform", {"kind": "transform"}, ["rotation", "cross_covariance", *v.TRANSFORM_VECTOR_FIELDS, *v.TRANSFORM_NUMBER_FIELDS, "fit_member_ids", "numerical_parameters", "identifiability"]))
    assert fields(transform["rows"][0])["cross_covariance"]["value"]["value"] == [[0.75, -0.25, -0.25], [-0.25, 0.75, -0.25], [-0.25, -0.25, 0.75]]
    assert fields(transform["rows"][0])["reflection_correction_sign"]["value"]["value"] == 1


def test_native_uncertainty_zero_missing_and_semantics_remain_distinct():
    for raw, expected in (("0.00", 0.0), ("", None)):
        _, _, sequence, metadata = f.fixture_pdb(role="single", b=raw)
        result = {"kind": "extraction", "sequence": sequence, "metadata": metadata, "descriptor": None}
        atom = metadata["atom_uncertainty"][0]["atom_row_key"]
        output = projected(result, select("native_uncertainty", {"kind": "atom_uncertainty", "structure_role": "single", "atom_row_keys": [atom]}, ["b_factor_native", "plddt", "anisotropic_U_A2"]))
        value = fields(output["rows"][0])
        assert value["b_factor_native"]["value"]["value"] == expected
        assert value["b_factor_native"]["value"]["state"] == ("present" if expected == 0 else "missing")
        assert value["plddt"]["value"]["value"] is None
        assert len(value["anisotropic_U_A2"]["value"]) == 6
        assert value["b_factor_native"]["population"]["member_ids"] == [atom]


PAE = """
loop_
_ma_qa_metric.id
_ma_qa_metric.name
_ma_qa_metric.type
_ma_qa_metric.mode
_ma_qa_metric.software_group_id
p error PAE local-pairwise 1
loop_
_ma_qa_metric_local_pairwise.ordinal_id
_ma_qa_metric_local_pairwise.model_id
_ma_qa_metric_local_pairwise.label_asym_id_1
_ma_qa_metric_local_pairwise.label_seq_id_1
_ma_qa_metric_local_pairwise.label_comp_id_1
_ma_qa_metric_local_pairwise.label_asym_id_2
_ma_qa_metric_local_pairwise.label_seq_id_2
_ma_qa_metric_local_pairwise.label_comp_id_2
_ma_qa_metric_local_pairwise.metric_id
_ma_qa_metric_local_pairwise.metric_value
3 5 X 2 ALA X 7 SER p 3
4 5 X 7 SER X 2 ALA p 8
"""


def test_ordered_pae_preserves_actual_endpoints_native_addresses_and_definition(monkeypatch):
    _, _, seq, metadata = f.fixture_cif(role="single", extra=PAE)
    result = {"kind": "extraction", "sequence": seq, "metadata": metadata, "descriptor": None}
    keys = [r["row_key"] for r in metadata["qa_rows"]]
    request = select("native_uncertainty", {"kind": "qa_rows", "structure_role": "single", "row_keys": keys}, ["qa", "metric_definition"])
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        output = projected(result, request)
    qa = [fields(row)["qa"]["value"] for row in output["rows"]]
    assert [(row["endpoint_1"]["label_seq_id"], row["endpoint_2"]["label_seq_id"], row["value"]["value"]) for row in qa] == [(2, 7, 3.0), (7, 2, 8.0)]
    assert all(row["value"]["unit"] == "angstrom" and row["native_addresses"] for row in qa)
    assert fields(output["rows"][0])["metric_definition"]["value"]["meaning"] == "pae"


def test_selected_native_metadata_row_retains_original_native_type():
    _, _, seq, metadata = b.from_pdb(b"EXPDTA    X-RAY DIFFRACTION\n" + f.pdb_bytes(), "single")
    result = {"kind": "extraction", "sequence": seq, "metadata": metadata, "descriptor": None}
    metadata = result["metadata"]
    key = metadata["metadata_values"][0]["row_key"]
    output = projected(result, select("native_uncertainty", {"kind": "metadata_rows", "structure_role": "single", "row_keys": [key]}, ["metadata_value"]))
    assert fields(output["rows"][0])["metadata_value"]["value"] == metadata["metadata_values"][0]
    assert fields(output["rows"][0])["metadata_value"]["value"]["native_text"]["text"].strip() == "X-RAY DIFFRACTION"


def test_known_empty_population_differs_from_unknown_population():
    known = comparison(b.make_sheet(pairs=[]))
    request = select("site_measurements", {"kind": "all_evaluation_requests"}, ["distance"])
    empty = projected(known, request)
    assert empty["requested_count"] == empty["matched_count"] == empty["returned_count"] == empty["omitted_count"] == 0
    assert empty["rows"] == [] and empty["state"] == "complete"
    unknown = deepcopy(known)
    unknown["components"]["evaluation"]["selection"].update(requested_count=None, resolved_pair_count=None, available_candidate_count=None)
    with pytest.raises(ValueError, match="^selected_field_unavailable$"):
        projected(unknown, request)
    # The explicit request is known even while whole-population enumeration is not.
    explicit = projected(unknown, select("site_measurements", {"kind": "evaluation_requests", "request_indices_0based": [2]}, ["distance"]))
    assert explicit["requested_count"] == explicit["returned_count"] == 1 and explicit["matched_count"] == 0


@pytest.mark.parametrize("change", [
    lambda s: s["fields"].append("hidden_atoms"),
    lambda s: s["fields"].append(s["fields"][0]),
    lambda s: s.update(family="transform"),
    lambda s: s.update(extra="unrestricted"),
    lambda s: s.update(window={"offset_0based": True, "limit": 1}),
    lambda s: s.update(window={"offset_0based": 0, "limit": 0}),
    lambda s: s.update(fields=[]),
])
def test_closed_selection_rejects_wrong_fields_types_and_member_family(change):
    request = select("comparison_summary", {"kind": "comparison"}, ["fit_rmsd"])
    change(request)
    with pytest.raises(ValueError):
        v.validate_protein_structure_projection_selection(request)


@pytest.mark.parametrize("family,members,fields_", [
    ("correspondence", {"kind": "unmapped_positions", "structure_role": "fixed", "positions_0based": [1]}, ["correspondence_row"]),
    ("native_uncertainty", {"kind": "qa_rows", "structure_role": "fixed", "row_keys": ["x"]}, ["plddt"]),
    ("structure_coordinates", {"kind": "coordinate_set", "coordinate_set_id": "x"}, ["distance"]),
])
def test_contradictory_exact_member_field_combinations_reject(family, members, fields_):
    with pytest.raises(ValueError, match="invalid_schema"):
        v.validate_protein_structure_projection_selection(select(family, members, fields_))


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(returned_count=2),
    lambda x: x.update(matched_count=2),
    lambda x: x.update(matched_count=1.0),
    lambda x: x.update(projection_id="different"),
    lambda x: x["rows"][0]["values"][0].update(field="evaluation_rmsd"),
    lambda x: x["rows"][0]["values"][0]["value"].update(value=True),
    lambda x: x["rows"][0]["values"][0]["value"].update(value=float("nan")),
    lambda x: x["rows"][0]["values"][0]["value"].update(value=None),
    lambda x: x["rows"][0]["values"][0]["value"].update(value=4.0),
    lambda x: x["rows"][0]["values"][0]["value"].update(unit="angstrom"),
    lambda x: x["rows"][0]["values"][0].update(population=None),
    lambda x: x["rows"][0]["values"][0]["population"].update(denominator=2),
])
def test_rows_validator_rejects_type_cell_selection_and_count_relationship_changes(mutation):
    value = summary(comparison(), "mapped_pair_count")
    mutation(value)
    with pytest.raises(ValueError):
        v.validate_protein_structure_projection_rows(value)


def test_rows_validator_requires_requested_field_or_failure_and_exact_explicit_population():
    result = comparison()
    output = summary(result, "mapped_pair_count", "available_pair_count")
    output["rows"][0]["values"].pop()
    with pytest.raises(ValueError, match="selected_field_unavailable"):
        v.validate_protein_structure_projection_rows(output)
    output = projected(result, select("site_measurements", {"kind": "evaluation_requests", "request_indices_0based": [99]}, ["distance"]))
    output["state"] = "complete"
    with pytest.raises(ValueError, match="conflicting_identity"):
        v.validate_protein_structure_projection_rows(output)
    output["state"] = "unavailable"
    output["matched_count"] = 1
    with pytest.raises(ValueError, match="conflicting_identity"):
        v.validate_protein_structure_projection_rows(output)


def test_result_validators_detach_and_do_not_authenticate_fake_custody():
    result = comparison()
    rows = summary(result, "evaluation_rmsd")
    value = published(rows, result)
    validated = v.validate_protein_structure_projection_result(value)
    assert validated == value
    validated["custody"]["run_id"] = "detached"
    assert value["custody"]["run_id"] == "synthetic-run"
    bad = deepcopy(value)
    bad["custody"]["result_receipt_key"] = "not-a-matching-locator"
    with pytest.raises(ValueError, match="conflicting_identity"):
        v.validate_protein_structure_projection_result(bad)


def test_artifact_delivery_does_not_claim_unseen_numbers_or_publish_a_table(monkeypatch):
    result = comparison()
    request = select("comparison_summary", {"kind": "comparison"}, ["evaluation_rmsd"], delivery="artifact")
    with monkeypatch.context() as guard:
        forbid_projection_work(guard)
        rows = projected(result, request)
    assert "table_file" not in rows and rows["rows"]
    value = published(rows, result)
    assert value["delivery"]["kind"] == "artifact" and "rows" not in value["delivery"]
    assert "artifact_descriptor_not_numerical_delivery" in value["qualifications"]
    v.validate_protein_structure_projection_result(value)
    value["delivery"]["row_count"] += 1
    with pytest.raises(ValueError, match="conflicting_identity"):
        v.validate_protein_structure_projection_result(value)


def test_four_standalone_and_nested_schemas_validate_arbitrary_parent_fields_and_reject_mutations():
    result = comparison()
    rows = summary(result, "evaluation_rmsd")
    projection = published(rows, result)
    descriptor = extracted()["descriptor"]
    saved = {"version": "protein_structure_saved_sheet_v1", "custody": f.synthetic_custody(),
        "sheet_file": f.identity(canonical(result["sheet"]).encode(), "protein_structure_comparison_sheet_v1"),
        "original_components_file": projection["calculation"]["components_file"], "operation": "compare_protein_structures",
        "original_mode": "fit_then_evaluate_ca", "allowed_uses": ["recalculate", "select_projection"]}
    failure = {"version": "protein_structure_failure_return_v1", "custody": None, "projection_id": "absent",
        "issue": {"stage": "projection", "code": "selected_field_unavailable", "structure_role": None, "position_key": None,
            "atom_row_key": None, "correspondence_id": None, "field": "projection_members", "artifact_role": None}}
    records = dict(zip(v.protein_structure_fact_sources(), ([projection], [saved], [descriptor], [failure])))
    properties, payload = {}, {}
    for index, (source, value) in enumerate(records.items()):
        schema = v.protein_structure_fact_sources()[source]["report_schema"]
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
        properties["parent_selected_" + str(index)] = schema
        payload["parent_selected_" + str(index)] = value
    enclosing = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    validator = Draft202012Validator(enclosing)
    validator.validate(payload)
    bad = deepcopy(payload)
    bad["parent_selected_0"][0]["delivery"]["rows"][0]["values"][0]["value"] = "a narrative instead of a NumberCell"
    assert not validator.is_valid(bad)
    bad = deepcopy(payload)
    bad["parent_selected_0"][0]["delivery"]["rows"][0]["values"][0]["field"] = "all_coordinates"
    assert not validator.is_valid(bad)
    bad = deepcopy(payload)
    bad["parent_selected_2"][0]["reference_ref"] = "reference_not-a-real-shape"
    assert not validator.is_valid(bad)
    bad = deepcopy(payload)
    bad["parent_selected_3"][0]["issue"]["code"] = "invented_issue"
    assert not validator.is_valid(bad)
    assert v.validate_protein_structure_failure_return(failure) == failure


def test_two_distinct_source_documents_coexist_under_nested_oneof():
    sources = v.protein_structure_fact_sources()
    projection_schema = sources["execution_protein_structure_projections"]["report_schema"]
    sequence_schema = sources["execution_protein_structure_sequences"]["report_schema"]
    result = comparison()
    projection = published(summary(result, "evaluation_rmsd"), result)
    descriptor = extracted()["descriptor"]
    # Wrong outer definitions expose accidental resolution against the parent.
    parent = {"type": "object", "$defs": {"ProjectionResult": False, "StructureSequenceDescriptor": False},
        "properties": {"arbitrary_choice": {"oneOf": [projection_schema, sequence_schema]}},
        "required": ["arbitrary_choice"], "additionalProperties": False}
    validator = Draft202012Validator(parent)
    validator.validate({"arbitrary_choice": [projection]})
    validator.validate({"arbitrary_choice": [descriptor]})
    bad = deepcopy(descriptor)
    bad["sequence_length"] = "4"
    assert not validator.is_valid({"arbitrary_choice": [bad]})
    # Changed registered documents remain different even when their JSON Schema
    # accepts more values. Root owns rejection at exact-source registration.
    changed = deepcopy(projection_schema)
    changed["$defs"]["FileIdentity"]["additionalProperties"] = True
    assert canonical(changed) != canonical(projection_schema)


def test_input_digest_and_selected_side_mismatches_reject_without_recalculation():
    result = comparison()
    result["sheet"]["sequences"]["fixed"]["selection"]["zero_occupancy_policy"] = "include"
    with pytest.raises(ValueError, match="input_digest_mismatch"):
        summary(result, "evaluation_rmsd")
    result = extracted()
    with pytest.raises(ValueError, match="conflicting_identity"):
        projected(result, select("native_uncertainty", {"kind": "atom_uncertainty", "structure_role": "fixed", "atom_row_keys": ["pdb_line_2"]}, ["occupancy"]))
