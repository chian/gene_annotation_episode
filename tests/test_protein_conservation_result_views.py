"""Pure engineered DTO/formatter controls; no native or custody proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from gene_annotation_episode import protein_conservation_result_contracts as contracts
from gene_annotation_episode import protein_conservation_result_views as views
from gene_annotation_episode import scientific_process_prompt as prompt
from gene_annotation_episode import phylogeny_calculators, phylogeny_formats
from gene_annotation_episode import phylogeny_calculation_contracts as numerical_contracts
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.molecular_result_facts import (
    merge_molecular_facts, requested_molecular_fact_fields, validate_frozen_molecular_return,
    validate_molecular_fact,
)
from gene_annotation_episode.rna_structure_comparison_receiver_prompt import render_rna_comparison_receiver_prompt
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from test_protein_conservation_result_contracts import FIXTURE, FIXTURE_SHA256, SOURCE, build


@pytest.fixture
def supplied():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    assert value["provenance"]["actual_native_execution"] is False
    assert value["provenance"]["producer_authenticated"] is False
    return value


def returned(supplied, *, selection=None):
    selected = build(supplied, **({} if selection is None else {"selection": selection}))
    return contracts.project_conservation_return(selected, source_ref=SOURCE)


def form_schema():
    return {"type": "object", "properties": {"conservation":
        contracts.conservation_fact_sources()[contracts.FACT_SOURCE]["report_schema"]},
        "required": ["conservation"], "additionalProperties": False}


def forbid_science(monkeypatch, *, io=False):
    def denied(*args, **kwargs):
        raise AssertionError("presentation or typed validation attempted unselected work")
    monkeypatch.setattr(phylogeny_formats, "parse_aligned_fasta", denied)
    monkeypatch.setattr(phylogeny_calculators, "literal_site_conservation", denied)
    monkeypatch.setattr(phylogeny_calculators, "alignment_components", denied)
    monkeypatch.setattr(numerical_contracts, "ratio", denied)
    monkeypatch.setattr(numerical_contracts, "quantity", denied)
    monkeypatch.setattr(contracts, "conservation_public_value", denied)
    if io:
        monkeypatch.setattr(Path, "open", denied)


def test_formatter_copies_literal_native_and_derived_values_without_io_or_science(supplied, monkeypatch):
    packet = returned(supplied)
    before = deepcopy(packet)
    forbid_science(monkeypatch, io=True)
    text = views.render_protein_conservation_result(packet)
    assert views.select_protein_conservation_values(packet) == packet
    assert packet == before
    for literal in (SOURCE, '"C-"', '"A-"', '"cA"', "0.6666666666666666", "0.67",
            "strict_greater_than", "unrounded_binary64_ratio", "binary64_fixed_2_ties_to_even",
            "Denominator operand", "predicted correspondence", "not functional confidence"):
        assert literal in text
    for private in (supplied["alignment"]["alignment_id"], supplied["alignment"]["artifact"]["raw_artifact_ref"],
            supplied["alignment"]["artifact"]["source_ref"], supplied["alignment"]["artifact"]["sha256"],
            supplied["input_record"]["file"]["artifact_ref"], supplied["input_record"]["file"]["sha256"]):
        assert private not in text


def test_empty_views_keep_scientific_context_and_distinct_population_accounting(supplied, monkeypatch):
    selection = deepcopy(supplied["selection"])
    selection["native_rows"]["row_indices"] = []
    selection["sites"]["columns_0based"] = []
    packet = returned(supplied, selection=selection)
    forbid_science(monkeypatch)
    text = views.render_protein_conservation_result(packet)
    for phrase in ("member_count", "site_count", "supplied_three_rows", "Native return code",
            "Output capture extent", "Parser status", "Population completeness", "unknown",
            "Original input header occurrences", "Denominator operand", "case-distinct characters", "[]"):
        assert phrase in text
    assert '"available"' in text
    assert packet["context"]["member_count"]["value"] == 3
    assert packet["accounting"]["native_rows"]["returned_record_count"] == 0


def test_known_native_rows_remain_visible_when_full_scientific_population_is_unknown(supplied):
    supplied["alignment"]["rows"][2]["sequence"] = "c"
    supplied["alignment"].update(completeness="partial", observed_column_count=None)
    supplied["population_request"] = dict(kind="all_output_rows_and_columns",
        label="retained rows with unresolved full columns", completeness="partial")
    supplied.update(population=None, components=None)
    supplied["native_execution"]["parser_status"] = "partial"
    packet = returned(supplied)
    text = views.render_protein_conservation_result(packet)
    assert '"c"' in text and "output_column_dimension_unresolved" in text
    assert '"member_count" | null | null' in text
    assert packet["context"]["member_count"] is None
    assert packet["accounting"]["native_rows"]["retained_record_count"] == 3
    assert packet["accounting"]["sites"]["retained_record_count"] is None


def test_native_headers_that_resemble_tracking_data_remain_literal(supplied, monkeypatch):
    header = "source_" + "9" * 24 + " slot evidence entries library /opaque/scientific/header"
    supplied["alignment"]["rows"][2].update(raw_header=header, member_label=header.split()[0])
    supplied["input_record"]["records"][2]["header"] = header
    packet = returned(supplied)
    forbid_science(monkeypatch)
    for text in (views.render_protein_conservation_result(packet), prompt._values(prompt._information(packet)),
            prompt._lookup({"status": "completed", "record_refs": [SOURCE], "result": packet})):
        assert header in text
        assert supplied["alignment"]["artifact"]["source_ref"] not in text
    assert prompt._information(packet) == packet


def test_declared_issue_provenance_is_hidden_without_stripping_native_fields(supplied):
    private = "artifact_" + "8" * 64
    supplied["issues"] = [dict(code="native_output_qualified", phase="native_capture", path="/private/host/path",
        severity="qualification", evidence_refs=[private])]
    text = views.render_protein_conservation_result(returned(supplied))
    assert "native_output_qualified" in text and "native_capture" in text
    assert "retained diagnostic evidence" in text
    assert private not in text and "/private/host/path" not in text


@pytest.mark.parametrize("kind", ["unknown_version", "malformed", "row_shape_only", "invalid_source"])
def test_selector_never_infers_valid_result_from_partial_or_unrelated_shapes(supplied, kind):
    packet = returned(supplied)
    if kind == "unknown_version":
        packet["version"] = "ordinary_protein_conservation_values_v99"
    elif kind == "malformed":
        packet["native_rows"][0]["row_index"] = 99
    elif kind == "row_shape_only":
        packet = {"native_rows": packet["native_rows"], "sites": packet["sites"]}
    else:
        packet["source_ref"] = "not-a-Source"
    assert views.select_protein_conservation_values(packet) is None
    with pytest.raises(ValueError):
        views.render_protein_conservation_result(packet)


def test_source_free_primary_value_and_immutable_mapping_are_presentable_without_inventing_source(supplied):
    value = build(supplied)
    shown = views.select_protein_conservation_values(MappingProxyType(value))
    assert shown == value and "source_ref" not in shown
    text = views.render_protein_conservation_result(value)
    assert "Callable result Source" in text and "null" in text
    assert SOURCE not in text


def test_fact_registration_merges_exact_source_and_full_ordered_selection(supplied, monkeypatch):
    full = returned(supplied)
    selection = deepcopy(supplied["selection"])
    selection["native_rows"]["row_indices"] = [2, 0]
    selection["sites"]["columns_0based"] = []
    page = returned(supplied, selection=selection)
    empty_selection = deepcopy(selection)
    empty_selection["native_rows"]["row_indices"] = []
    empty = returned(supplied, selection=empty_selection)
    forbid_science(monkeypatch)
    groups = merge_molecular_facts([full, page], [deepcopy(full), empty], fact_source=contracts.FACT_SOURCE)
    assert groups == [full, page, empty]
    assert validate_molecular_fact(full, fact_source=contracts.FACT_SOURCE) == full
    changed = deepcopy(full)
    changed["context"]["native_execution"]["reported_version"] = "different supplied self-report"
    with pytest.raises(ValueError, match="facts_source_conflict"):
        merge_molecular_facts([full], [changed], fact_source=contracts.FACT_SOURCE)


def test_exact_registered_fact_schema_and_semantics_visit_only_outer_source(supplied, monkeypatch):
    from gene_annotation_episode.runtime import _compile_form
    packet = returned(supplied)
    schema = form_schema()
    forbid_science(monkeypatch)
    seen = []
    def resolver(reference, namespace):
        seen.append((reference, namespace))
        return reference == SOURCE and namespace == "source"
    assert validate_closed_schema(schema) == schema
    assert _compile_form(json.dumps(schema), contracts.conservation_fact_sources()) == schema
    assert validate_form({"conservation": [packet]}, schema, resolver) == {"conservation": [packet]}
    assert seen == [(SOURCE, "source")]
    with pytest.raises(ReportBoundaryError):
        validate_form({"conservation": [packet]}, schema,
            lambda reference, namespace: reference == supplied["alignment"]["artifact"]["source_ref"])
    assert requested_molecular_fact_fields(schema, fact_source=contracts.FACT_SOURCE) == ["conservation"]
    # This method is a pure form-reference projection; no Episode/Source owner
    # is fabricated or claimed by this direct metadata-only call.
    assert ScientificProcessEpisodes.received_form_references(None, None,
        {"conservation": [packet]}, schema, None) == [SOURCE]


@pytest.mark.parametrize("change", ["unit", "open", "nested"])
def test_unregistered_schema_variants_do_not_gain_native_string_or_reference_exceptions(change):
    schema = form_schema()
    if change == "unit":
        node = schema["properties"]["conservation"]["$defs"]["Site"]["properties"]["majority_fraction"]
        node["properties"]["unit"] = {"const": "confidence"}
    elif change == "open":
        schema["properties"]["conservation"]["$defs"]["Return"]["additionalProperties"] = True
    else:
        schema["properties"] = {"nested": {"type": "object", "properties": schema["properties"],
            "required": ["conservation"], "additionalProperties": False}}
        schema["required"] = ["nested"]
    with pytest.raises(ValueError):
        validate_closed_schema(schema)


@pytest.mark.parametrize("change", ["boolean_index", "native_sequence", "quantity_unit", "missing_source"])
def test_typed_and_frozen_forms_cannot_change_retained_native_or_calculated_values(supplied, change):
    packet = returned(supplied)
    form = {"conservation": [deepcopy(packet)]}
    changed = form["conservation"][0]
    if change == "boolean_index":
        changed["native_rows"][0]["row_index"] = False
    elif change == "native_sequence":
        changed["native_rows"][2]["sequence"] = "c-"
    elif change == "quantity_unit":
        changed["context"]["member_count"]["unit"] = "rows per input file"
    else:
        changed.pop("source_ref")
    with pytest.raises(ValueError):
        validate_frozen_molecular_return(form, form_schema(), [packet], fact_source=contracts.FACT_SOURCE)


def test_engineered_receiver_keeps_supplied_question_and_value_tables_in_task_and_steering(supplied, monkeypatch):
    packet = returned(supplied)
    question = "Supplied parent question: inspect the selected native correspondence and literal conservation."
    instructions = "Supplied unchanged receiver instruction text."
    state = {"goal": {"objective": question}, "scope": {}, "scientific_process": {}, "working_state": {},
        "requested_form": form_schema(), "available_report_facts": contracts.conservation_fact_sources(),
        "last_local_outcome": {"status": "completed", "record_refs": [SOURCE], "result": packet}}
    forbid_science(monkeypatch)
    wire = render_rna_comparison_receiver_prompt(state, instructions)
    assert wire.startswith("TASK\n") and "STEERING" in wire
    assert question in wire and instructions in wire
    assert "Selected native alignment rows" in wire and "Denominator operand" in wire
    assert SOURCE in wire and supplied["alignment"]["artifact"]["raw_artifact_ref"] not in wire
    assert supplied["alignment"]["artifact"]["source_ref"] not in wire
    assert prompt.has_molecular_receiver_context(state) is True
