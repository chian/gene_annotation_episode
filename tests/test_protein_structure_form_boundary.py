"""Exact native facts through real form expansion; no receipt-authority claim."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode import communication as boundary
from gene_annotation_episode.episode_contract_information import (
    ContractInformationError, expand_fact_form, validate_saved_fact_form,
)
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.protein_structure_contracts import issue
from gene_annotation_episode.protein_structure_result_views import (
    protein_structure_fact_sources, project_protein_structure_results,
)
from gene_annotation_episode.schema_information_text import schema_fingerprint
_helpers = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
identity = _helpers.identity
sequence_descriptor = _helpers.sequence_descriptor
synthetic_custody = _helpers.synthetic_custody

FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"
PREFIX = "execution_protein_structure_"
FIELDS = {"the_comparison": PREFIX + "projections", "reuse_later": PREFIX + "saved_sheets",
    "selected_sequence": PREFIX + "sequences", "unavailable": PREFIX + "failures"}


def object_form(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def expanded(*, neighbor=False):
    sources = protein_structure_fact_sources()
    properties = {field: {"$ref": "episode-fact:" + source} for field, source in FIELDS.items()}
    if neighbor:
        properties["target"] = {"type": "string", "format": "reference", "x-reference-namespace": "subject"}
    submitted = json.dumps(object_form(properties))
    result = expand_fact_form(submitted, child_role="results", facts_by_role={"results": sources},
        permitted_child_roles=["results"])
    assert validate_saved_fact_form(child_role="results", submitted_schema_json=submitted,
        expanded_schema=result["expanded_schema"], declaration=result["declaration"]) == result["expanded_schema"]
    return sources, submitted, result


@pytest.fixture(scope="module")
def native_facts():
    native = json.loads((FIXTURES / "held_out.json").read_bytes())
    sheet = native["sheet"]
    components = sheet["native_baseline"]
    selection = {"projection_id": "requested_comparison", "family": "comparison_summary",
        "members": {"kind": "comparison"}, "fields": ["evaluation_rmsd", "evaluation_used_count"],
        "window": None, "delivery_kind": "values"}
    rows = project_protein_structure_results({"kind": "comparison", "sheet": sheet,
        "components": components}, selection=[selection])[0]
    calculation = {"calculation_id": rows["calculation_id"],
        "input_numerical_sha256": components["input_numerical_sha256"],
        "components_file": identity(canonical(components).encode(), "protein_structure_components_v1")}
    projection = {key: deepcopy(value) for key, value in rows.items() if key not in ("rows", "calculation_id")}
    projection.update(version="protein_structure_projection_v1", custody=synthetic_custody(),
        calculation=calculation, delivery={"kind": "values", "rows": deepcopy(rows["rows"])})
    saved = {"version": "protein_structure_saved_sheet_v1", "custody": synthetic_custody(),
        "sheet_file": identity(canonical(sheet).encode(), "protein_structure_comparison_sheet_v1"),
        "original_components_file": calculation["components_file"], "operation": "compare_protein_structures",
        "original_mode": sheet["scientific_mode"], "allowed_uses": ["recalculate", "select_projection", "use_transform"]}
    sequence = sequence_descriptor(json.loads((FIXTURES / "extract.json").read_bytes())["sequence"])
    failure = {"version": "protein_structure_failure_return_v1", "custody": None, "projection_id": "requested_missing",
        "issue": issue("selected_field_unavailable", stage="projection", field="projection_fields")}
    return dict(zip(FIELDS.values(), ([projection], [saved], [sequence], [failure])))


def form(native_facts, *, neighbor=False):
    sources, submitted, result = expanded(neighbor=neighbor)
    schema = result["expanded_schema"]
    interpretations = {"target": "subject:target"} if neighbor else {}
    payload = boundary.form_with_facts(interpretations, schema, native_facts)
    resolver = boundary.reference_resolver({"subject": ["subject:target"]})
    assert boundary.validate_form(payload, schema, resolver) == payload
    return schema, payload


def test_four_exact_source_resources_expand_and_retain_original_fingerprints(native_facts, tmp_path):
    sources, submitted, result = expanded()
    schema = result["expanded_schema"]
    ids = set()
    for declaration in result["declaration"]["fact_references"]:
        source, field = declaration["source"], declaration["field"]
        original = sources[source]["report_schema"]
        assert "x-source" not in original
        assert declaration["source_had_x_source"] is False
        assert declaration["schema_sha256"] == schema_fingerprint(original)
        assert schema["properties"][field] == {**original, "x-source": source}
        ids.add(original["$id"])
    assert len(ids) == 4
    payload = boundary.form_with_facts({}, schema, native_facts)
    assert boundary.validate_form(payload, schema) == payload
    # Preserve an actual admitted example, separate from its deliberately
    # changed copy below. The schema/identities are host data, not prompt text.
    (tmp_path / "filled-form.json").write_text(json.dumps({
        "submitted_schema_json": submitted, "declaration": result["declaration"],
        "form": payload}, indent=2, allow_nan=False) + "\n")
    assert boundary.interpretation_schema(schema) == object_form({})
    assert boundary.generation_schema(boundary.interpretation_schema(schema)) == object_form({})
    assert len(json.loads(submitted)["properties"]) == 4
    payload["the_comparison"][0]["returned_count"] = 70
    assert native_facts[PREFIX + "projections"][0]["returned_count"] == 1


@pytest.mark.parametrize("source", list(FIELDS.values()))
def test_each_source_can_be_selected_alone_with_an_arbitrary_parent_field(native_facts, source):
    submitted = json.dumps(object_form({"answer_for_parent": {"$ref": "episode-fact:" + source}}))
    result = expand_fact_form(submitted, child_role="results", facts_by_role={"results": protein_structure_fact_sources()},
        permitted_child_roles=["results"])
    payload = boundary.form_with_facts({}, result["expanded_schema"], {source: native_facts[source]})
    assert boundary.validate_form(payload, result["expanded_schema"]) == payload
    assert set(payload) == {"answer_for_parent"}


@pytest.mark.parametrize("value", [1.0, True, -1, "1"])
def test_projection_counts_keep_integer_meaning(native_facts, value):
    schema, payload = form(native_facts)
    payload["the_comparison"][0]["returned_count"] = value
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form(payload, schema)


@pytest.mark.parametrize("field", ["reuse_later", "selected_sequence"])
def test_descriptor_file_length_is_an_integer_count(native_facts, field):
    schema, payload = form(native_facts)
    file_key = "sheet_file" if field == "reuse_later" else "sequence_file"
    length = payload[field][0][file_key]["byte_length"]
    payload[field][0][file_key]["byte_length"] = float(length)
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form(payload, schema)


@pytest.mark.parametrize("change", ["count_relationship", "cell_relationship", "unit", "numerator", "extra_field", "custody"])
def test_selected_value_relationships_are_checked_beyond_json_shape(native_facts, change):
    schema, payload = form(native_facts)
    projection = payload["the_comparison"][0]
    values = projection["delivery"]["rows"][0]["values"]
    if change == "count_relationship": projection["returned_count"] = 2
    elif change == "cell_relationship": values[0]["value"]["state"] = "unavailable"
    elif change == "unit": values[0]["value"]["unit"] = "fraction"
    elif change == "numerator": values[1]["population"]["numerator"] = 99
    elif change == "extra_field": projection["narrative"] = "unrequested text"
    else: projection["custody"]["result_operation_key"] = "different_operation"
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form(payload, schema)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_selected_measurements_are_rejected(native_facts, value):
    schema, payload = form(native_facts)
    payload["the_comparison"][0]["delivery"]["rows"][0]["values"][0]["value"]["value"] = value
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form(payload, schema)
    assert error.value.diagnostic["code"] == "nonfinite_number"


@pytest.mark.parametrize("change", ["source", "unknown_source", "schema_id", "definition", "array", "annotation", "remote_ref"])
def test_registered_source_contract_cannot_be_widened_or_substituted(change):
    _, _, result = expanded()
    schema = result["expanded_schema"]
    field = schema["properties"]["the_comparison"]
    if change == "source": field["x-source"] = PREFIX + "sequences"
    elif change == "unknown_source": field["x-source"] = PREFIX + "made_up"
    elif change == "schema_id": field["$id"] += ":changed"
    elif change == "definition": field["$defs"]["Count"] = {"type": "number"}
    elif change == "array": field["minItems"] = 0
    elif change == "annotation": field["description"] = "different contract"
    else: field["items"] = {"$ref": "https://example.invalid/remote-schema"}
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(schema)


@pytest.mark.parametrize("container", ["object", "array"])
def test_source_contract_only_applies_to_a_whole_top_level_field(container):
    _, _, result = expanded()
    native = result["expanded_schema"]["properties"]["the_comparison"]
    wrapper = object_form({"nested": native}) if container == "object" else {"type": "array", "items": native}
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(object_form({"wrapper": wrapper}))


@pytest.mark.parametrize("change", ["missing", "extra", "wrong_array", "wrong_row"])
def test_enclosing_parent_requirements_still_apply(native_facts, change):
    schema, payload = form(native_facts)
    if change == "missing": del payload["the_comparison"]
    elif change == "extra": payload["unrequested"] = 10
    elif change == "wrong_array": payload["unavailable"] = {}
    else: payload["unavailable"] = [payload["reuse_later"][0]]
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form(payload, schema)


def test_neighbor_reference_is_resolved_at_each_call_without_caching_authority(native_facts):
    schema, payload = form(native_facts, neighbor=True)
    calls, allowed = [], True
    def resolver(reference, namespace):
        calls.append((reference, namespace))
        return allowed and (reference, namespace) == ("subject:target", "subject")
    assert boundary.validate_form(payload, schema, resolver) == payload
    assert calls == [("subject:target", "subject")]
    allowed = False
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form(payload, schema, resolver)
    assert error.value.diagnostic["code"] == "unknown_reference"
    assert error.value.diagnostic["field"] == "report.target"
    # The native custody identifiers are pattern fields. Their original receipt
    # authority belongs to the result/return consumers, not this shape check.
    assert calls == [("subject:target", "subject")] * 2


def test_changed_saved_relationship_is_rejected_without_current_catalog():
    _, submitted, result = expanded()
    declaration = deepcopy(result["declaration"])
    declaration["fact_references"][0]["source_had_x_source"] = True
    with pytest.raises(ContractInformationError, match="saved_fact_source_schema_mismatch"):
        validate_saved_fact_form(child_role="results", submitted_schema_json=submitted,
            expanded_schema=result["expanded_schema"], declaration=declaration)


def test_model_interpretations_cannot_supply_recorded_protein_values(native_facts):
    schema, payload = form(native_facts)
    with pytest.raises(boundary.ReportBoundaryError, match="non-recorded fields"):
        boundary.form_with_facts(payload, schema, native_facts)
