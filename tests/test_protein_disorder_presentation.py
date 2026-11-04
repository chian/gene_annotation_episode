"""SCI presentation over retained231 values, without predictor or custody claims.

The existing fixture contains engineered upstream-wrapper outputs. Source
constants here exercise controlled DTO/metadata presentation only; no Source,
receipt, invocation, service response or scientific binding is manufactured.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode import protein_disorder_measurements as core
from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode import scientific_process_prompt as prompt
from gene_annotation_episode.domain import identity
from test_protein_disorder_result_contracts import SOURCE, packet, request


def returned(*, case="ordinary", rows=None):
    return contracts.project_ordinary_disorder_return(packet(case=case, rows=rows), SOURCE)


def forbid_work(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("disorder presentation attempted byte access or numerical work")
    for name in ("build_disorder_sheet", "calculate_disorder_components", "_response", "_csv", "_source_arithmetic"):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("pathlib.Path.read_bytes", forbidden)
    monkeypatch.setattr("pathlib.Path.read_text", forbidden)
    return forbidden


@pytest.mark.parametrize("port", ["values", "lookup", "steering"])
def test_real_sci_presentation_paths_keep_ordered_cells_operands_and_full_qualifications(port, monkeypatch):
    value = returned(rows=[request("summary", ["disordered_percentage", "descriptive_mean_score", "unique_input_coverage"]),
        request("residue", ["score_token", "score_value", "native_threshold_comparison"], row_ordinal=3),
        request("region", ["start_1based", "end_1based", "member_row_ordinals"], region_ordinal=0)])
    before = deepcopy(value)
    outcome = dict(status="completed", result=value, record_refs=[SOURCE], changed_record_refs=[SOURCE])
    forbid_work(monkeypatch)
    if port == "values":
        text = prompt._values(value)
    elif port == "lookup":
        text = prompt._lookup(outcome)
    else:
        text = prompt._steering({"last_local_outcome": outcome}, [])
    assert "Selected molecular result 1" in text and "predict_protein_disorder_regions" in text
    fields = ["disordered_percentage", "descriptive_mean_score", "unique_input_coverage",
        "score_token", "score_value", "native_threshold_comparison", "start_1based", "end_1based", "member_row_ordinals"]
    positions = [text.index("| values.rows[" + str(index) + "].field | " + name + " |")
        for index, name in enumerate(fields)]
    assert positions == sorted(positions)
    assert "| values.rows[0].value | 75.0 |" in text or "| values.rows[0].value | 75 |" in text
    assert "| values.rows[0].operands[0].value | 3 |" in text
    assert "| values.rows[0].operands[1].value | 4 |" in text
    assert "| values.rows[1].unit | dimensionless_predictor_score |" in text
    assert "| values.rows[3].value | .9 |" in text
    assert "| values.rows[4].value | 0.9 |" in text
    assert "| values.rows[5].value | true |" in text
    assert "| values.rows[8].value[0] | 0 |" in text
    assert "| values.rows[8].value[1] | 1 |" in text
    for name, definition in value["values"]["context"]["definitions"].items():
        assert "| values.context.definitions." + name + " | " + prompt._cell(definition) + " |" in text
    assert "| values.context.summary.scientific_service_execution_verified | false |" in text
    assert SOURCE in text
    for digest in value["values"]["data_identity"].values():
        if isinstance(digest, str) and len(digest) == 64:
            assert digest not in text
    for key in ("module_sha256", "callable_sha256"):
        assert value["values"]["context"]["source_profile"][key] not in text
    assert value == before


@pytest.mark.parametrize("case", ["ordinary", "empty", "null_input"])
def test_empty_selection_keeps_global_context_populations_definitions_and_missingness(case, monkeypatch):
    value = returned(case=case)
    before = deepcopy(value)
    forbid_work(monkeypatch)
    text = prompt._lookup(dict(status="partial", result=value, record_refs=[SOURCE]))
    assert "| values.rows | empty array |" in text
    for name in ("source_parsed_row_count", "descriptive_mean_denominator_rows",
            "unique_usable_input_position_count", "input_coverage_denominator_symbols"):
        expected = prompt._scalar(value["values"]["context"]["summary"][name])
        assert "| values.context.summary." + name + " | " + expected + " |" in text
    assert "| values.context.parameters.threshold | " in text
    assert "| values.context.definitions.uncertainty | " in text
    assert "| values.context.source_equivalent.stage | " in text
    assert value == before


def test_nonfinite_native_score_token_and_null_value_render_as_distinct_literal_cells(monkeypatch):
    value = returned(case="nonfinite",
        rows=[request("residue", ["score_token", "score_kind", "score_value"], row_ordinal=0)])
    forbid_work(monkeypatch)
    text = prompt._values(value)
    assert "| values.rows[0].value | NaN |" in text
    assert "| values.rows[1].value | nan |" in text
    assert "| values.rows[2].value | null |" in text
    assert "| values.rows[2].value_state | stored_null |" in text
    assert "| values.rows[2].unit | dimensionless_predictor_score |" in text


def test_declared_mapping_addresses_get_stable_roles_without_changing_coordinates_or_opaque_data(monkeypatch):
    value = returned(rows=[request("residue", ["source_intervals"], row_ordinal=0)])
    context = value["values"]["context"]
    input_ref, subject_ref = "source_" + "b" * 24, "artifact_" + "c" * 64
    context["input"]["input_ref"] = input_ref
    for mapping in (context["input"]["input_mapping"], context["mapping"]["supplied"]):
        mapping["path"][0]["subject_ref"] = subject_ref
    row = value["values"]["rows"][0]
    row["value"][0]["subject_ref"] = subject_ref
    row["scientific_qualifiers"]["value"]["cells"]["source_intervals"][0]["subject_ref"] = subject_ref
    contracts.validate_ordinary_disorder_return(value)
    before = deepcopy(value)
    forbid_work(monkeypatch)
    text = prompt._values(value)
    assert input_ref not in text and subject_ref not in text
    assert "Retained input provenance" in text and "Supplied mapping subject 1" in text
    assert "Supplied mapping subject 2" not in text
    assert "| values.context.mapping.supplied.path[0].start | 100 |" in text
    assert "| values.context.mapping.supplied.path[0].end | 108 |" in text
    assert "| values.context.mapping.supplied.path[0].unit | aa |" in text
    assert "| values.context.mapping.supplied.path[0].strand | + |" in text
    assert "| values.rows[0].value[0].start | 101 |" in text
    assert "| values.rows[0].value[0].end | 102 |" in text
    assert value == before


def test_complete_packet_protects_opaque_supplied_data_from_instruction_provenance_rewriting(monkeypatch):
    value = returned()
    literal = ["unusable supplied mapping", {"slot": "thought_pattern", "evidence": "retained literal evidence",
        "option_ref": "literal option", "entry": {"entries": ["original"], "library": "retained literal library"},
        "content_role": "tool_and_resource_instructions_not_scientific_evidence", "section_sha256": "literal annotation"}]
    context = value["values"]["context"]
    context["input"]["input_mapping"] = deepcopy(literal)
    context["mapping"] = dict(supplied=deepcopy(literal), available=False, reason="invalid_supplied_mapping")
    contracts.validate_ordinary_disorder_return(value)
    before = deepcopy(value)
    forbid_work(monkeypatch)
    assert prompt._information(value) == value
    text = prompt._lookup(dict(status="partial", result=value, record_refs=[SOURCE]))
    for preserved in ("retained literal evidence", "literal option", "retained literal library", "literal annotation"):
        assert preserved in text
    assert "| values.context.mapping.available | false |" in text
    assert "| values.context.mapping.reason | invalid_supplied_mapping |" in text
    assert value == before


def test_full_packet_deduplication_keeps_source_and_ordered_selection_separate():
    value = returned(rows=[request("summary", ["disordered_percentage"])])
    other_source = {**deepcopy(value), "source_ref": "source_" + "d" * 24}
    other_selection = returned(rows=[request("summary", ["descriptive_mean_score"])])
    original = [value, deepcopy(value), other_source, other_selection]
    shown, packets = prompt._selected_molecular_view(original)
    assert shown == ["Selected molecular result 1", "Selected molecular result 1",
        "Selected molecular result 2", "Selected molecular result 3"]
    assert packets == [value, other_source, other_selection]
    assert original == [value, value, other_source, other_selection]


def test_actual_source_record_shape_keeps_callable_sources_and_hides_only_private_artifact_addresses():
    parent = "source_" + "e" * 24
    body = dict(provider=contracts.TOOL, accession=None, uri=None,
        artifact_ref="artifact_" + "1" * 64, text_ref=None, request_ref="artifact_" + "2" * 64,
        version=contracts.SOURCE_VERSION, retrieved_at="2026-11-02T12:00:00+00:00",
        parent_source_refs=[parent], auxiliary_artifact_refs=["artifact_" + "3" * 64])
    source = dict(id=identity("source", dict(origin="tool", record=body)), record_type="source", origin="tool", **body)
    before = deepcopy(source)
    shown = prompt._information(source)
    assert shown == dict(source_ref=source["id"], operation=contracts.TOOL, origin="tool", accession=None, uri=None,
        parent_source_refs=[parent], recorded_file_associations=dict(selected_values="recorded",
            verification_control="recorded", text=None, auxiliary=["recorded"]))
    text = prompt._lookup(dict(status="completed", result=source))
    assert source["id"] in text and parent in text
    assert "artifact_" not in text and body["version"] not in text and body["retrieved_at"] not in text
    assert source == before


@pytest.mark.parametrize("problem", ["version", "unit"])
def test_unknown_or_malformed_packet_keeps_existing_literal_fallback(problem):
    value = returned(rows=[request("summary", ["disordered_percentage"])])
    if problem == "version":
        value["version"] = "unknown_protein_disorder_values_v9"
    else:
        value["values"]["rows"][0]["unit"] = "function_confidence"
    before = deepcopy(value)
    assert prompt._selected_molecular_packet(value) is None
    shown, packets = prompt._selected_molecular_view(value)
    assert shown == value and packets == []
    assert "Selected molecular result" not in prompt._values(value)
    assert value == before


def test_registered_exact_disorder_fact_schema_selects_the_existing_molecular_receiver():
    facts = contracts.ordinary_disorder_fact_sources()
    schema = facts[contracts.FACT_SOURCE]
    assert prompt.has_molecular_receiver_context({"available_report_facts": {contracts.FACT_SOURCE: schema}})
    malformed = deepcopy(schema)
    malformed["report_schema"]["items"]["properties"]["source_ref"]["pattern"] = "^artifact_"
    assert not prompt.has_molecular_receiver_context({"available_report_facts": {contracts.FACT_SOURCE: malformed}})
