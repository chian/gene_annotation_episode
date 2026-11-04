"""Engineered BioMart acquisition confirmations; no live HTTP or biology."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import ensembl_acquisition as native
from gene_annotation_episode import ensembl_acquisition_host as host
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
import test_ensembl_acquisition as captures


def forbidden(*args, **kwargs):
    raise AssertionError("BioMart confirmation attempted HTTP or native work")


def capture(operation="gene_homologies", raw=None, **changes):
    raw = ({"registry": captures.REGISTRY_XML, "datasets": captures.DATASETS_TSV,
        "configuration": captures.configuration(), "gene_homologies": captures.table(captures.row())}[operation]
        if raw is None else raw)
    return captures.snapshot(captures.arguments(operation), raw, **changes)


def value(snapshot):
    return native.ensembl_value(snapshot, arguments=snapshot.request,
        artifact_ref="artifact_" + hashlib.sha256(snapshot.content).hexdigest(), evidence=captures.evidence())


def receipt(snapshot):
    return native.ensembl_receipt(value(snapshot), source_ref=captures.RESULT)


def failed(code):
    return native.failed_ensembl_receipt("ensembl_" + code, source_ref=captures.RESULT)


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        yield store, ToolRegistry(store)


def publish(registry, snapshot, *, selected=None, prepared=None):
    selected = snapshot.request if selected is None else selected
    prepared = host.prepare_ensembl_request(registry, selected) if prepared is None else prepared
    token = registry._publications.set([])
    try:
        return host.publish_ensembl_request(registry, selected, snapshot, prepared=prepared)
    finally:
        registry._publications.reset(token)


def test_common_confirmation_schema_and_no_response_never_invent_refs(publisher, monkeypatch):
    store, registry = publisher
    monkeypatch.setattr(store, "artifact", forbidden)
    monkeypatch.setattr(registry, "_source", forbidden)
    assert native.ensembl_receipt_schema() == acquisition_receipt_schema(failure_codes=native.ENSEMBL_FAILURE_CODES)
    result = native.failed_ensembl_receipt("data_acquisition_failed")
    assert result == dict(acquired=False, source_ref=None, data_ref=None, failure_code="data_acquisition_failed")
    assert native.validate_ensembl_receipt(result) == result
    assert native.validate_ensembl_receipt(result) is not result and list(store.list("source")) == []
    assert Draft202012Validator(native.ensembl_receipt_schema()).is_valid(result)
    with pytest.raises(ContractError, match="ensembl_receipt_invalid"):
        native.failed_ensembl_receipt("arbitrary unretained error text")


@pytest.mark.parametrize("change", [{"acquired": 1}, {"source_ref": None}, {"data_ref": None},
    {"data_ref": captures.RESULT}, {"source_ref": captures.RESULT + "\n"}, {"extra": None},
    {"failure_code": "data_acquisition_failed"}, {"acquired": False, "failure_code": "data_acquisition_failed"}])
def test_closed_receipts_reject_type_reference_and_confirmation_contradictions(change):
    valid = dict(acquired=True, source_ref=captures.RESULT, data_ref="artifact_" + "a" * 64, failure_code=None)
    with pytest.raises(ContractError, match="ensembl_receipt_invalid"):
        native.validate_ensembl_receipt({**valid, **change})


@pytest.mark.parametrize("operation", native.OPERATIONS)
def test_source_free_content_and_supplied_source_wrapper_preserve_literal_legacy_payload(operation):
    snapshot = capture(operation)
    private = value(snapshot)
    legacy = native.ensembl_result(snapshot, arguments=snapshot.request, source_ref=captures.RESULT,
        artifact_ref=private["raw_artifact_ref"], evidence=captures.evidence())
    assert private["version"] == native.VALUE_VERSION and "source_ref" not in private
    assert "source_ref" not in native.ensembl_value_schema()["properties"]
    assert native.ensembl_result_from_value(private, source_ref=captures.RESULT,
        evidence=captures.evidence()) == legacy
    assert legacy == {**{key: child for key, child in private.items() if key != "observed_transfer"},
        "version": native.VERSION, "source_ref": captures.RESULT}
    assert native.validate_ensembl_result(legacy, evidence=captures.evidence()) == legacy
    before = deepcopy(private)
    legacy["requested"]["max_bytes"] = 1
    assert private == before
    assert native.ensembl_receipt(private, source_ref=captures.RESULT) == dict(acquired=True,
        source_ref=captures.RESULT, data_ref=private["raw_artifact_ref"], failure_code=None)


@pytest.mark.parametrize("field,raw,response_key", [("declared_body_bytes", False, "declared_body_bytes"),
    ("declared_body_bytes", -1, "declared_body_bytes"), ("declared_body_bytes", "0", "declared_body_bytes"),
    ("body_capture_failure", False, "capture_failure"), ("body_capture_failure", 0, "capture_failure")])
def test_malformed_optional_transfer_is_private_literal_and_legacy_normalized(field, raw, response_key):
    snapshot = capture(**{field: raw})
    private = value(snapshot)
    expected = captures.result()
    expected["response"][response_key] = None
    assert native.ensembl_result(snapshot, arguments=snapshot.request, source_ref=captures.RESULT,
        artifact_ref=private["raw_artifact_ref"], evidence=captures.evidence()) == expected
    assert private["observed_transfer"][field] == raw and type(private["observed_transfer"][field]) is type(raw)
    assert native.ensembl_receipt(private, source_ref=captures.RESULT) == failed("transport_metadata_unavailable")


@pytest.mark.parametrize("field,raw", [("declared_body_bytes", float("nan")), ("body_capture_failure", b"bad")])
def test_python_only_optional_metadata_keeps_old_pure_normalization_without_inventing_source(field, raw):
    snapshot = capture(**{field: raw})
    artifact = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    legacy = native.ensembl_result(snapshot, arguments=snapshot.request, source_ref=captures.RESULT,
        artifact_ref=artifact, evidence=captures.evidence())
    expected = captures.result()
    expected["response"]["declared_body_bytes" if field == "declared_body_bytes" else "capture_failure"] = None
    assert legacy == expected
    with pytest.raises(ValueError):
        native.ensembl_value(snapshot, arguments=snapshot.request, artifact_ref=artifact, evidence=captures.evidence())


@pytest.mark.parametrize("changes,code", [({"status": None}, "transport_metadata_unavailable"),
    ({"status": True}, "transport_metadata_unavailable"), ({"status": 404}, "http_not_success"),
    ({"status": 302}, "http_redirect"), ({"body_complete": False}, "response_incomplete"),
    ({"body_complete": None}, "response_incomplete"), ({"retained_body_bytes": False}, "transport_metadata_unavailable"),
    ({"retained_body_bytes": 0}, "transport_count_conflict"), ({"observed_body_bytes": None}, "transport_metadata_unavailable"),
    ({"observed_body_bytes": 0}, "transport_count_conflict"), ({"declared_body_bytes": 0}, "transport_count_conflict"),
    ({"response_byte_limit": 1}, "transport_count_conflict"), ({"body_capture_failure": "interrupted"}, "response_capture_failure")])
def test_native_complete_stamp_cannot_override_transport_failure(changes, code):
    private = value(capture(**changes))
    assert private["native_completion"] == "reported_complete"
    assert native.ensembl_receipt(private, source_ref=captures.RESULT) == failed(code)


def test_absent_content_length_and_mime_only_qualification_do_not_destroy_authentic_selected_data():
    private = value(capture(declared_body_bytes=None, headers={"content-type": "application/octet-stream"}))
    assert private["response"]["declared_body_bytes"] is None
    assert private["issues"] == [{"code": "content_type_mismatch", "pointer": "/response/content_type"}]
    assert native.ensembl_receipt(private, source_ref=captures.RESULT)["acquired"] is True


@pytest.mark.parametrize("raw,code", [(b"\xff", "invalid_native_utf8"),
    (b"Query ERROR: original diagnostic", "native_error_response"), (b"", "native_response_empty"),
    (captures.table(captures.row(), stamp=False), "native_completion_missing"),
    (captures.table(captures.row()) + b"[success]\n", "native_completion_conflict"),
    (captures.table(captures.row()) + b"late\trow\n", "native_data_after_completion"),
    (captures.table(captures.row()[:-1]), "native_column_arity_conflict"),
    (captures.table(captures.row(source="UNSELECTED")), "native_source_id_not_requested"),
    (captures.table(captures.row(start="0")), "native_coordinate_invalid")])
def test_native_query_errors_and_invalid_rows_never_confirm_correct_data(raw, code):
    assert receipt(capture(raw=raw)) == failed(code)


def test_empty_completed_mapping_and_blank_target_duplicate_rows_keep_distinct_populations():
    empty = value(capture(raw=captures.table()))
    assert empty["retained_row_count"] == 0 and empty["native_completion"] == "reported_complete"
    assert native.ensembl_receipt(empty, source_ref=captures.RESULT)["acquired"]
    blank = [captures.GENE, "13", "1", "10", "-1"] + [""] * 8
    first = captures.row(); first[10] = "1e-9999"
    rows = [first, first, captures.row(target="ENSMUSG00000000001"), blank]
    raw = captures.table(*rows).replace(b"\n", b"\r\n")
    private = value(capture(raw=raw))
    assert private["native_text"].encode() == raw
    assert [line["cells"] for line in private["tsv_lines"] if line["role"] == "row"] == rows
    assert private["requested_id_count"] == 1 and private["retained_row_count"] == 4
    assert private["matching_population_count"] is None and private["population_coverage"] == "selected_response_only"
    assert private["coordinate_convention"] == "native_one_based_inclusive"
    assert [column["denominator"] for column in private["columns"]][10:12] == ["target_sequence", "query_sequence"]
    assert native.ensembl_receipt(private, source_ref=captures.RESULT)["acquired"]


def test_repeated_requested_ids_do_not_require_fabricated_repeated_native_rows():
    selected = captures.arguments("gene_homologies", gene_ids=[captures.GENE, captures.GENE, "UNKNOWN_ID"])
    snapshot = captures.snapshot(selected, captures.table(captures.row()))
    private = value(snapshot)
    assert private["requested_id_count"] == 3 and private["retained_row_count"] == 1
    assert native.ensembl_receipt(private, source_ref=captures.RESULT)["acquired"]


@pytest.mark.parametrize("damage", ["source", "version", "rows", "row_count_bool", "target_dataset", "column",
    "denominator", "discovery", "missing_context", "transfer"])
def test_private_value_rejects_crossfield_tampering_without_external_identity_claim(damage):
    private = value(capture())
    if damage == "source": private["source_ref"] = captures.RESULT
    elif damage == "version": private["version"] = native.VERSION
    elif damage == "rows": private["tsv_lines"][1]["cells"][0] = "OTHER"
    elif damage == "row_count_bool": private["retained_row_count"] = True
    elif damage == "target_dataset": private["dataset_contexts"][1]["dataset"] = captures.SOURCE_DATASET
    elif damage == "column": private["columns"][0]["attribute"] = "ensembl_gene_id"
    elif damage == "denominator": private["columns"][10]["denominator"] = "query_sequence"
    elif damage == "discovery": private["discovery_evidence"].pop(0)
    elif damage == "missing_context": private["dataset_contexts"].pop()
    else: private["observed_transfer"]["declared_body_bytes"] = 0
    with pytest.raises(ValueError): native.validate_ensembl_value(private)


def test_retained_value_confirmation_needs_no_original_snapshot_or_invented_discovery_authority(monkeypatch):
    private = value(capture())
    expected = native.ensembl_receipt(private, source_ref=captures.RESULT)
    legacy = native.ensembl_result_from_value(private, source_ref=captures.RESULT)
    monkeypatch.setattr(native, "validate_ensembl_discovery", forbidden)
    monkeypatch.setattr(native, "_snapshot_response", forbidden)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    assert native.ensembl_receipt(private, source_ref=captures.RESULT) == expected
    assert native.ensembl_result_from_value(private, source_ref=captures.RESULT) == legacy
    assert native.validate_ensembl_value(private) == private


def test_optional_supplied_discovery_still_must_match_actual_configuration_evidence():
    private = value(capture())
    evidence = captures.evidence()
    captures.replace_evidence(evidence, captures.SOURCE_CONFIG,
        captures.configuration(attributes=[name for name in captures.ATTRIBUTES if name != "mmusculus_homolog_perc_id"]))
    with pytest.raises(ValueError): native.validate_ensembl_value(private, evidence=evidence)


def test_direct_publisher_keeps_original_selection_then_private_value_before_real_source(publisher, monkeypatch):
    store, registry = publisher
    snapshot = capture("registry")
    original = registry._source
    def source_after_value(*args, **kwargs):
        selection_ref, private_ref = kwargs["auxiliary_artifact_refs"]
        assert json.loads(store.get_artifact(selection_ref)) == dict(version=host.SELECTION_VERSION,
            arguments=snapshot.request, direct_source_refs=[], sources=[])
        assert native.validate_ensembl_value(json.loads(store.get_artifact(private_ref))) == value(snapshot)
        return original(*args, **kwargs)
    monkeypatch.setattr(registry, "_source", source_after_value)
    result, refs = publish(registry, snapshot)
    saved = store.get(result["source_ref"])
    assert result == dict(acquired=True, source_ref=saved["id"], data_ref=saved["artifact_ref"], failure_code=None)
    assert refs == [saved["id"], saved["artifact_ref"]]
    assert saved["provider"] == "ensembl" and saved["version"] is saved["accession"] is None
    assert saved["parent_source_refs"] == [] and store.get_artifact(saved["artifact_ref"]) == snapshot.content
    assert json.loads(store.get_artifact(saved["request_ref"])) == dict(request=snapshot.request, transport=snapshot.transport)
    assert {saved["request_ref"], *saved["auxiliary_artifact_refs"]}.isdisjoint(refs)
    assert list(store.list("reference")) == []
    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


@pytest.mark.parametrize("damage", ["service", "url", "request", "wire", "redirects"])
def test_sealed_but_contradictory_capture_keeps_literal_source_and_second_failure_witness(publisher, damage):
    store, registry = publisher
    snapshot = capture("registry"); selected = deepcopy(snapshot.request)
    if damage == "service": snapshot = replace(snapshot, service="literal-other-service")
    elif damage == "url": snapshot = replace(snapshot, url="https://example.org/actual-unselected")
    elif damage == "request": snapshot = replace(snapshot, request={**selected, "max_bytes": 1})
    elif damage == "wire": snapshot.transport["request"]["url"] += "&unselected=1"
    else: snapshot.transport["request_policy"]["automatic_redirects"] = True
    result, refs = publish(registry, snapshot, selected=selected)
    saved = store.get(result["source_ref"])
    assert result["acquired"] is False and result["data_ref"] is None and refs == [saved["id"]]
    assert saved["uri"] == snapshot.url and saved["parent_source_refs"] == []
    assert store.get_artifact(saved["artifact_ref"]) == snapshot.content
    assert json.loads(store.get_artifact(saved["request_ref"])) == dict(request=snapshot.request, transport=snapshot.transport)
    assert len(saved["auxiliary_artifact_refs"]) == 2
    witness = json.loads(store.get_artifact(saved["auxiliary_artifact_refs"][1]))
    assert witness == dict(version=host.FAILURE_WITNESS_VERSION, observed_snapshot_service=snapshot.service,
        observed_snapshot_url=snapshot.url, failure_code=result["failure_code"])


def test_failed_prepared_revalidation_retains_no_fictitious_selection_or_parent_links(publisher):
    store, registry = publisher
    snapshot = capture("registry")
    prepared = host.prepare_ensembl_request(registry, snapshot.request)
    prepared["selection"]["sources"] = [{"invented": True}]
    result, refs = publish(registry, snapshot, prepared=prepared)
    saved = store.get(result["source_ref"])
    assert not result["acquired"] and result["data_ref"] is None and refs == [saved["id"]]
    assert "parent_source_refs" not in saved and len(saved["auxiliary_artifact_refs"]) == 1
    assert json.loads(store.get_artifact(saved["auxiliary_artifact_refs"][0])) == dict(
        version=host.FAILURE_WITNESS_VERSION, observed_snapshot_service=snapshot.service,
        observed_snapshot_url=snapshot.url, failure_code=result["failure_code"])
    assert store.get_artifact(saved["artifact_ref"]) == snapshot.content


@pytest.mark.parametrize("raw,changes", [(b"<MartRegistry", {}), (b"\xff", {}),
    (captures.REGISTRY_XML, {"status": 403}), (captures.REGISTRY_XML, {"body_complete": False}),
    (captures.REGISTRY_XML, {"declared_body_bytes": False})])
def test_failed_captured_representation_retains_data_privately_but_confirms_source_only(publisher, raw, changes):
    store, registry = publisher
    snapshot = capture("registry", raw, **changes)
    result, refs = publish(registry, snapshot)
    saved = store.get(result["source_ref"])
    assert not result["acquired"] and result["data_ref"] is None and refs == [saved["id"]]
    assert store.get_artifact(saved["artifact_ref"]) == raw
    private = json.loads(store.get_artifact(saved["auxiliary_artifact_refs"][1]))
    assert native.validate_ensembl_value(private) == value(snapshot)


def test_result_and_value_schema_copies_are_detached_and_legacy_view_is_unchanged():
    legacy = captures.result()
    assert native.ensembl_outcome_view({"result": legacy})["result"]["version"] == native.MODEL_VIEW_VERSION
    private = value(capture())
    assert native.ensembl_outcome_view({"result": native.ensembl_receipt(private,
        source_ref=captures.RESULT)}) is None
    schema = native.ensembl_value_schema(); Draft202012Validator.check_schema(schema)
    schema["properties"]["version"] = {}
    assert native.ensembl_value_schema()["properties"]["version"] == {"const": native.VALUE_VERSION}
