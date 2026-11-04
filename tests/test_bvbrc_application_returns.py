"""Pure saved-value controls; fabricated metadata here is not Source custody.

No fake Store, producer, ToolOperation or successful host publication is used.
Genuine positive custody is exercised separately through the AppService host.
"""
from copy import deepcopy
import hashlib
import json
from types import MappingProxyType, SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_application_returns as returns
from gene_annotation_episode import bvbrc_annotation_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_annotation_contracts as contracts
from gene_annotation_episode import bvbrc_annotation_native as native
from gene_annotation_episode.execution_contracts import canonical
from test_bvbrc_annotation_bundle_adapter import arguments, selection


def saved_value_case(data=None):
    args = arguments(data=data, selections=[{"field": "literal/ordered", "selection": selection(ordinals=[0, 0])},
        {"field": "empty", "selection": selection(ordinals=[])}])
    result = adapter.consume_bundle(**args)
    source = "source_" + "f" * 24
    def content(value, character):
        data = canonical(value).encode(); digest = hashlib.sha256(data).hexdigest()
        return {"source_ref": "source_" + character * 24, "artifact_field": "artifact_ref",
            "artifact_ref": "artifact_" + digest, "sha256": digest, "byte_count": len(data)}
    selector = {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_projection",
        "requirements": [{"requirement_id": "native-genome", "role": "caller_selected_gto", "required": True,
            "declared_format": deepcopy(args["bundle"]["artifacts"][0]["declared_format"]),
            "producer_rule_evidence": None, "exact_object": None}],
        "adapter": {"adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
            "parameters": deepcopy(args["parameters"])}, "requested_schema": args["requested_form"],
        "supplied_metadata": [], "supplied_contents": [], "supplied_capabilities": []}
    stored = {key: deepcopy(result[key]) for key in ("adapter_id", "adapter_version", "status", "facts", "missing_requirements", "diagnostics")}
    stored.update(sheet_content=content(result["sheet"], "a"), components_content=content(result["components"], "b"))
    bundle_content = content(args["bundle"], "f")
    body = {"version": returns.RESULT_VERSION, "source_ref": source, "reference": source,
        "publication": {"bundle_content": bundle_content, "result_record_refs": [source], "adapter_result": stored},
        "publication_inputs": {"selector": selector, "adapter": selector["adapter"],
            "adapter_implementation_sha256": "a" * 64},
        "assignment": {"selector": selector}, "record_refs": [source], "bundle": args["bundle"]}
    return body, result["sheet"], result["components"]


def test_saved_projector_retains_exact_order_duplicate_occurrences_empty_context_and_encoded_field_identity(monkeypatch):
    body, sheet, components = saved_value_case(); original = deepcopy((body, sheet, components))
    def forbidden(*a, **k): raise AssertionError("saved return tried to parse/calculate/read native bytes")
    for owner, name in [(native, "_parse"), (adapter, "parse_annotation_artifact"),
            (adapter, "calculate_annotation_components"), (native, "calculate_sequence_composition_scores")]:
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = returns.project_application_facts(body, sheet=sheet, components=components)
    rows = result[returns.FACT_SOURCE]
    assert len(rows) == 2 and rows[0]["field"].endswith("/literal%2Fordered")
    assert [row["requested_ordinal"] for row in rows[0]["value"]["records"]] == [0, 0]
    assert rows[1]["value"]["records"] == []
    assert rows[1]["value"]["context"]["definitions"] == rows[0]["value"]["context"]["definitions"]
    assert (body, sheet, components) == original


@pytest.mark.parametrize("change", ["source", "bundle-source", "unlisted", "selector", "adapter", "pin",
    "sheet-bytes", "components-bytes", "task", "status", "stored-value"])
def test_saved_publication_metadata_does_not_replace_original_selection_or_content(change):
    body, sheet, components = saved_value_case()
    if change == "source": body["reference"] = "source_" + "0" * 24
    elif change == "bundle-source": body["publication"]["bundle_content"]["source_ref"] = "source_" + "0" * 24
    elif change == "unlisted": body["record_refs"] = []
    elif change == "selector": body["assignment"] = {"selector": {}}
    elif change == "adapter": body["publication_inputs"]["adapter"] = {}
    elif change == "pin": body["publication_inputs"]["adapter_implementation_sha256"] = "unknown"
    elif change == "sheet-bytes": sheet["analysis_id"] = "other"
    elif change == "components-bytes": components["analysis_id"] = "other"
    elif change == "task": body["bundle"]["original_task"]["task_id"] = "other"
    elif change == "status": body["publication"]["adapter_result"]["status"] = "partial"
    else: body["publication"]["adapter_result"]["facts"]["empty"]["records"] = [None]
    with pytest.raises(ValueError): returns.project_application_facts(body, sheet=sheet, components=components)


@pytest.mark.parametrize("change", ["float-count", "bool-ordinal", "null-alias", "wrong-field", "extra-row-key"])
def test_whole_typed_row_validator_is_strict_without_interpreting_native_reference_looking_data(change):
    body, sheet, components = saved_value_case()
    rows = returns.project_application_facts(body, sheet=sheet, components=components)[returns.FACT_SOURCE]
    row = rows[0]
    if change == "float-count": row["value"]["record_accounting"]["returned_occurrences"] = 2.0
    elif change == "bool-ordinal": row["value"]["records"][0]["requested_ordinal"] = False
    elif change == "null-alias": row["value"]["records"][0]["value"] = {"kind": "null", "value": None}
    elif change == "wrong-field": row["field"] = "bvbrc_application_field:other/field"
    else: row["nested_source_ref"] = "source_" + "a" * 24
    with pytest.raises(ValueError): returns.validate_application_rows(rows)


def test_fact_factory_preserves_local_native_definitions_and_only_top_source_has_reference_meaning():
    factory = returns.application_fact_sources()[returns.FACT_SOURCE]
    schema = factory["report_schema"]
    Draft202012Validator.check_schema(schema)
    # The existing VCF return also contributes its native recursive definitions.
    assert len(schema["$defs"]) == 98
    fields = schema["items"]["properties"]
    assert fields["source_ref"]["x-reference-namespace"] == "execution_result"
    assert fields["field"]["format"] == "identifier"
    assert "x-reference-namespace" not in json.dumps(fields["value"])
    body, sheet, components = saved_value_case()
    rows = returns.project_application_facts(body, sheet=sheet, components=components)[returns.FACT_SOURCE]
    Draft202012Validator(schema).validate(rows)
    assert returns.validate_application_rows(rows) == rows


def test_invalid_adapter_without_saved_scientific_values_returns_no_invented_fact_source():
    body, sheet, components = saved_value_case()
    saved = body["publication"]["adapter_result"]
    saved.update(status="invalid", facts={}, sheet_content=None, components_content=None)
    assert returns.project_application_facts(body, sheet=None, components=None) == {returns.FACT_SOURCE: []}


def return_schema():
    return {"type": "object", "additionalProperties": False, "properties": {
        "observations": returns.application_fact_sources()[returns.FACT_SOURCE]["report_schema"]},
        "required": ["observations"]}


def test_actual_runtime_form_compiler_and_receiver_resolve_only_declared_top_references():
    from gene_annotation_episode.runtime import _compile_form
    from gene_annotation_episode.communication import validate_form
    from test_bvbrc_annotation_native import gto
    data = gto()
    data["features"][0]["source_ref"] = "source_" + "9" * 24
    data["features"][0]["artifact_ref"] = "artifact_" + "8" * 64
    body, sheet, components = saved_value_case(data)
    rows = returns.project_application_facts(body, sheet=sheet, components=components)[returns.FACT_SOURCE]
    schema = _compile_form(json.dumps(return_schema()), extra_sources=returns.application_fact_sources())
    resolved = []
    def resolver(reference, namespace):
        resolved.append((reference, namespace))
        return (namespace == "execution_result" and reference == body["source_ref"] or
            namespace == returns.IDENTIFIER_NAMESPACE and any(reference == row["field"] for row in rows))
    payload = {"observations": rows}
    assert validate_form(payload, schema, resolver) == payload
    assert set(resolved) == {(row[key], namespace) for row in rows
        for key, namespace in (("source_ref", "execution_result"), ("field", returns.IDENTIFIER_NAMESPACE))}
    with pytest.raises(ValueError):
        validate_form(payload, schema, lambda *_: False)


@pytest.mark.parametrize("change", ["nested-reference", "definition", "extra-field", "source-type"])
def test_registered_schema_identity_cannot_be_widened_at_runtime(change):
    from gene_annotation_episode.runtime import _compile_form
    schema = return_schema(); field = schema["properties"]["observations"]
    if change == "nested-reference":
        field["items"]["properties"]["value"]["oneOf"][0]["properties"]["context"] = {
            "type": "string", "format": "reference", "x-reference-namespace": "artifact"}
    elif change == "definition":
        field["$defs"]["AnnotationJSON0"] = {}
    elif change == "extra-field":
        field["items"]["additionalProperties"] = True
    else:
        field["type"] = ["array", "null"]
    with pytest.raises(ValueError):
        _compile_form(json.dumps(schema), extra_sources=returns.application_fact_sources())


def test_selected_value_display_preserves_native_keys_and_values_under_frozen_context():
    from gene_annotation_episode.scientific_process_prompt import _execution_presentation_values
    from test_bvbrc_annotation_native import gto
    data = gto()
    data["features"][0].update(source_ref="source_" + "9" * 24,
        output_path="/literal/native/output", request_sha256="a" * 64,
        native_object={"task_id": "literal-native-task", "artifact_ref": "artifact_" + "8" * 64})
    body, sheet, components = saved_value_case(data)
    rows = returns.project_application_facts(body, sheet=sheet, components=components)[returns.FACT_SOURCE]
    original = deepcopy(rows)
    def frozen(value):
        if isinstance(value, dict):
            return MappingProxyType({key: frozen(child) for key, child in value.items()})
        return tuple(map(frozen, value)) if isinstance(value, list) else value
    display = _execution_presentation_values(frozen({returns.FACT_SOURCE: rows}))[returns.FACT_SOURCE]
    assert display[0]["field"] == "literal/ordered"
    assert "source_ref" not in display[0]
    for before, after in zip(rows, display, strict=True):
        assert after["value"]["records"] == before["value"]["records"]
        assert after["value"]["record_accounting"] == before["value"]["record_accounting"]
        context = after["value"]["context"]
        assert "original_task" not in context and "content" not in context
        assert "observed_task_id" not in context["native_task_identity"]
        assert context["native_task_identity"]["state"] == before["value"]["context"]["native_task_identity"]["state"]
    assert rows == original


@pytest.mark.parametrize("accession,origin,version,stop", [
    ("application_artifact_bundle_" + "a" * 64, "tool", "bvbrc_appservice_bundle_data_v1", True),
    ("artifact_bundle_" + "a" * 64, "tool", "bvbrc_appservice_bundle_data_v1", False),
    ("application_artifact_bundle_" + "a" * 64, "user", "bvbrc_appservice_bundle_data_v1", False),
    ("application_artifact_bundle_" + "a" * 64, "tool", "other-version", False),
    ("application_artifact_bundle_" + "a" * 63, "tool", "bvbrc_appservice_bundle_data_v1", False),
])
def test_receipt_metadata_policy_stops_only_new_bound_application_source(accession, origin, version, stop):
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    # Metadata-only engineering control: this mints no Source, receipt or grant.
    record = {"record_type": "source", "provider": "episode.bvbrc_appservice_bundle_data",
        "origin": origin, "version": version, "accession": accession}
    projection = SimpleNamespace(store=SimpleNamespace(_refs=lambda value: ["private-dependency-sentinel"]))
    assert EpisodeReceipts.forward_references(projection, record) == ([] if stop else ["private-dependency-sentinel"])


@pytest.mark.parametrize("references", [[], ["engineered-new-partial"]])
def test_newer_partial_application_does_not_borrow_older_completion(references):
    from gene_annotation_episode.bvbrc_appservice_publication import AppServicePublications
    context = SimpleNamespace(assignment={"selector": {"adapter": {
        "adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION}}},
        scope={}, episode_id="engineered-results")
    reads = []
    def read(reference, *args, **kwargs):
        reads.append(reference)
        assert reference == "engineered-new-partial"
        return {"publication": {"completion_proof": None}}
    projection = SimpleNamespace(host=SimpleNamespace(custody=SimpleNamespace(authenticate=lambda *a, **k: None)),
        api=SimpleNamespace(_own_outcomes=lambda context: [(0, {"result": {
            "publication_ref": "engineered-old-publication", "result_record_refs": ["engineered-old-complete"]}}),
            (1, {"result": {"publication_ref": "engineered-new-publication", "result_record_refs": references}})]), read=read)
    assert AppServicePublications.completion(projection, context) is None
    assert reads == references


def test_installed_annotation_adapter_requires_its_actual_implementation_pin():
    from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
    row = {"adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
        "implementation_sha256": adapter.implementation_sha256()}
    assert bind_adapters([row])[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)] == (adapter, row["implementation_sha256"])
    row["implementation_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="appservice_adapter_implementation_conflict"):
        bind_adapters([row])
