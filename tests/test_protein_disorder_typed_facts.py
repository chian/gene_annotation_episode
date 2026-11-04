"""Pure typed-boundary controls over the retained231 supplied-data fixture.

Lexical Source identifiers below exercise schemas and reference projection;
they do not create Sources, receipts, workers or scientific execution proof.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode import protein_disorder_measurements as core
from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.molecular_result_facts import (
    merge_molecular_facts, molecular_fact_sources, requested_molecular_fact_fields,
    requested_molecular_fact_sources, validate_frozen_molecular_return,
    validate_molecular_fact,
)
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from test_protein_disorder_result_contracts import SOURCE, prepared, request


FACT = contracts.FACT_SOURCE


def _forbidden(*args, **kwargs):
    raise AssertionError("typed disorder boundary attempted scientific work")


@pytest.fixture(autouse=True)
def no_scientific_recalculation(monkeypatch):
    for name in ("build_disorder_sheet", "calculate_disorder_components", "_response", "_csv"):
        monkeypatch.setattr(core, name, _forbidden)


def _schema():
    return dict(type="object", additionalProperties=False, properties={
        "measurements": contracts.ordinary_disorder_fact_sources()[FACT]["report_schema"]},
        required=["measurements"])


def _view(*, rows=None):
    if rows is None:
        rows = [request("summary", ["source_parsed_row_count", "descriptive_mean_score", "disordered_percentage"]),
            request("residue", ["source_intervals"], row_ordinal=0)]
    arguments, sheet, components = prepared(rows=rows)
    packet = contracts.ordinary_disorder_packet(arguments=arguments, sheet=sheet, components=components)
    return contracts.project_ordinary_disorder_return(packet, SOURCE)


def test_registered_complete_fact_schema_is_requested_and_inserted_literally():
    schema, value = _schema(), _view()
    assert validate_closed_schema(schema) == schema
    assert molecular_fact_sources()[FACT] == contracts.ordinary_disorder_fact_sources()[FACT]
    assert requested_molecular_fact_sources(schema) == (FACT,)
    assert requested_molecular_fact_fields(schema, fact_source=FACT) == ["measurements"]
    form = form_with_facts({}, schema, {FACT: [value]})
    seen = []
    validate_form(form, schema, lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert form == {"measurements": [value]}
    assert seen == [(SOURCE, "source")]
    assert value["values"]["context"]["summary"]["scientific_service_execution_verified"] is False


@pytest.mark.parametrize("change", [
    lambda node: node.update(minItems=1),
    lambda node: node["items"]["properties"]["source_ref"].update(**{"x-reference-namespace": "artifact"}),
    lambda node: node["$defs"].update(unselected={"type": "string"}),
])
def test_complete_registered_schema_cannot_be_modified(change):
    schema = _schema()
    change(schema["properties"]["measurements"])
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic["code"] == "invalid_schema"


def test_registered_fact_cannot_be_nested_below_a_report_field():
    schema = _schema()
    schema["properties"]["measurements"] = dict(type="object", additionalProperties=False,
        properties={"nested": schema["properties"]["measurements"]}, required=["nested"])
    with pytest.raises(ReportBoundaryError, match="whole top-level fields"):
        validate_closed_schema(schema)


@pytest.mark.parametrize("change", [
    lambda value: value["values"]["rows"][0].update(value=True),
    lambda value: value["values"]["rows"][1].update(value=.9),
    lambda value: value["values"]["rows"][1]["operands"][1].update(value=999),
    lambda value: value["values"]["rows"][1].update(unit="function_confidence"),
    lambda value: value["values"]["data_identity"].update(sheet_canonical_sha256="not-a-digest"),
    lambda value: value["values"]["context"]["summary"].update(scientific_service_execution_verified=True),
])
def test_real_form_boundary_rejects_changed_types_values_operands_and_attestation(change):
    value, resolved = _view(), []
    change(value)
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"measurements": [value]}, _schema(),
            lambda *args: resolved.append(args) or True)
    assert caught.value.diagnostic["field"] == "measurements"
    assert resolved == []
    with pytest.raises(ContractError, match="protein_disorder_return_invalid"):
        validate_molecular_fact(value, fact_source=FACT)


@pytest.mark.parametrize("wrong", [None, {}, "not an array"])
def test_real_form_boundary_requires_an_array_of_complete_groups(wrong):
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"measurements": wrong}, _schema(), lambda *args: True)
    assert caught.value.diagnostic["code"] == "protein_disorder_return_array_required"


def test_validated_schema_cache_never_supplies_source_authority():
    form, schema = {"measurements": [_view()]}, _schema()
    validate_form(form, schema, lambda reference, namespace: reference == SOURCE and namespace == "source")
    denied = []
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(form, schema, lambda reference, namespace: denied.append((reference, namespace)) or False)
    assert caught.value.diagnostic["code"] == "unknown_reference"
    assert denied == [(SOURCE, "source")]


def test_opaque_mapping_and_input_references_survive_without_becoming_file_grants():
    value = _view(rows=[])
    artifact = "artifact_" + "b" * 64
    nested_source = "source_" + "c" * 24
    literal = ["invalid supplied mapping", {"subject_ref": nested_source, "artifact_ref": artifact,
        "slot": "thought_pattern", "evidence": {"retained": True}, "entries": [], "library": "literal"}]
    context = value["values"]["context"]
    context["input"]["input_ref"] = artifact
    context["input"]["input_mapping"] = deepcopy(literal)
    context["mapping"] = dict(supplied=deepcopy(literal), available=False, reason="invalid_supplied_mapping")
    original, seen = deepcopy(value), []
    validate_form({"measurements": [value]}, _schema(),
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert value == original
    assert seen == [(SOURCE, "source")]
    # This is the real pure reference-projection hook, not a runtime grant.
    projected = ScientificProcessEpisodes.received_form_references(
        SimpleNamespace(), None, {"measurements": [value]}, _schema(), "pure-projection")
    assert projected == [SOURCE]
    assert artifact not in projected and nested_source not in projected


def test_groups_deduplicate_complete_copies_but_keep_distinct_selections_of_one_source():
    first = _view()
    second = _view(rows=[request("summary", ["unique_input_coverage"])])
    original = deepcopy((first, second))
    merged = merge_molecular_facts([first], [deepcopy(first), second], fact_source=FACT)
    assert merged == [first, second]
    assert (first, second) == original
    merged[0]["values"]["context"]["input"]["input_ref"] = "literal mutation"
    assert (first, second) == original


def test_conflicting_complete_copies_of_the_same_source_and_selection_are_rejected():
    first = _view()
    changed = deepcopy(first)
    changed["values"]["context"]["input"]["input_ref"] = "opaque different supplied input"
    assert validate_molecular_fact(changed, fact_source=FACT) == changed
    with pytest.raises(ContractError, match="protein_disorder_facts_source_conflict"):
        merge_molecular_facts([first], [changed], fact_source=FACT)


def test_frozen_comparison_and_scientific_hook_use_the_same_literal_complete_group():
    value, schema = _view(), _schema()
    frozen, form = [deepcopy(value)], {"measurements": [deepcopy(value)]}
    validate_frozen_molecular_return(form, schema, frozen, fact_source=FACT)
    pure_services = SimpleNamespace(molecular_frozen_facts=lambda context, *, fact_source: deepcopy(frozen))
    # Invoke only the finite pure check; this object claims no runtime owner.
    ScientificProcessEpisodes._validate_molecular_report(SimpleNamespace(services=pure_services), None, form, schema)
    form["measurements"][0]["values"]["context"]["input"]["input_ref"] = "changed opaque provenance"
    with pytest.raises(ReportBoundaryError) as caught:
        validate_frozen_molecular_return(form, schema, frozen, fact_source=FACT)
    assert caught.value.diagnostic["code"] == "protein_disorder_frozen_source_mismatch"
    assert frozen == [value]


def test_scientific_hook_reports_unavailable_frozen_disorder_facts_without_a_key_error():
    pure_services = SimpleNamespace(molecular_frozen_facts=lambda context, *, fact_source: None)
    with pytest.raises(ReportBoundaryError) as caught:
        ScientificProcessEpisodes._validate_molecular_report(SimpleNamespace(services=pure_services), None,
            {"measurements": [_view()]}, _schema())
    assert caught.value.diagnostic["field"] == "measurements"
    assert caught.value.diagnostic["code"] == "protein_disorder_facts_not_frozen"
