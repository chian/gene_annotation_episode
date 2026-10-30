"""Pure artifact construction from C4b-decoded synthetic native responses.

No live calls, scientific measurements, host custody, publication persistence or
complete episode communication are claimed by these component tests.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_appservice_bundle_values import (
    build_acquisition_value, build_artifact_bundle,
)
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.execution_contracts import digest
from test_api_bvbrc_appservice import (
    FORMAT, PREFIX, OBJECT_UUID, association, bound, common_receipt, content_binding,
    harness, metadata, original_request, original_task, prepare, resolved_object, result_selector,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure artifact construction attempted network access")
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


def selector(two=False):
    result = result_selector()
    if two:
        result["requirements"].append({**deepcopy(result["requirements"][0]),
                                      "requirement_id": "r2", "role": "sidecar"})
    return result


def fixture(h, *, number=1, selected=None, requirement_ids=None, role="native_output",
            content=b"abcdef", byte_range=None, status=200, headers=None,
            complete=True, metadata_size=6, prior=(), request=None,
            supplied_evidence=(), support_refs=(), task_association=None,
            object_number=None, metadata_receipt_ref=None, native_uuid=False,
            url="https://fixture.invalid/exact-download"):
    """All identifiers here are explicit synthetic host-supplied bindings."""
    request = original_request() if request is None else deepcopy(request)
    selected = selector() if selected is None else deepcopy(selected)
    requirement_ids = ["r1"] if requirement_ids is None else requirement_ids
    object_number = number if object_number is None else object_number
    path = "/synthetic/work/" + str(object_number) + "/same-name.json"
    uuid = OBJECT_UUID if object_number == 1 else f"{object_number:08x}-1111-1111-1111-111111111111"
    selected_object = {"kind": "receipt_row", "receipt_ref": metadata_receipt_ref or f"metadata_{object_number}", "row_pointer": "/result/0/0"}
    assoc = {**association(path), "output_uuid": uuid, "kind": "task_result_manifest",
             "evidence_ref": "source_manifest", "pointer": f"/output_files/{object_number - 1}"}
    if task_association is not None:
        assoc.update(deepcopy(task_association))
    obj = resolved_object(selected_object, row=metadata(path, uuid=uuid, type="txt", size=metadata_size), association=assoc)
    obj["object"]["metadata_receipt_ref"] = selected_object["receipt_ref"]
    if native_uuid:
        obj["native_reference"] = uuid.upper()
    if metadata_size is None:
        obj["metadata"] = None
    capability = {"kind": "acquired", "receipt_ref": f"capability_{number}", "input_index": 0}
    entry = {"input_index": 0, "object_selection": selected_object, "object": obj["object"],
        "task_association": assoc, "url": url, "issued_observed_at": "2026-10-24T12:00:00+00:00",
        "expires_at": None, "expiry_evidence": None}
    declared = selected["requirements"][0]["declared_format"]
    args = {"capability": capability, "object": selected_object, "byte_range": byte_range,
            "requirement_ids": requirement_ids, "role": role, "declared_format": deepcopy(declared)}
    bindings = bound(request, "download", args, original_task=original_task(request), object=obj,
                     capability={"selection": capability, "entry": entry})
    bindings.update(original_handoff_ref="original_handoff", capability=capability)
    operation = prepare(h, "download", args, bindings, selector=selected, request=request)
    if headers is None:
        headers = {"Content-Length": str(len(content))}
    snapshot = SourceSnapshot("bvbrc_analysis", url,
        {"kind": "download", "url": url, "requested_byte_range": deepcopy(byte_range)},
        f"2026-10-24T12:00:{number:02d}+00:00", content, "application/octet-stream",
        {"status": status, "body_complete": complete, "received_body_bytes": len(content),
         "effective_url": url, "automatic_redirects": False, "headers": deepcopy(headers),
         "request": {"method": "GET", "url": url}})
    event = h.service.decode(operation, snapshot)
    binding = {"source_ref": f"source_download_{number}", "content": {
        **content_binding(content), "source_ref": f"source_download_{number}"},
        "retrieved_at": snapshot.retrieved_at, "media_type": snapshot.media_type,
        "transport": deepcopy(snapshot.transport), "selected_operands": {
            key: deepcopy(operation[key]) for key in
            ("operation", "request_sha256", "arguments_sha256", "native_operands")}}
    common = common_receipt(request, "download", args, status=event["facts"].get("parse_status", "failed"))
    common.update(purpose="acquisition", receipt_ref=f"provisional_common_{number}", snapshot=deepcopy(binding))
    common["origin"].update(episode_id="results", operation_key=f"synthetic-run:results:{number}")
    publication = {"version": "bvbrc_appservice_publication_inputs_v1", "request": deepcopy(request),
        "selector": deepcopy(selected), "original_handoff_ref": "original_handoff",
        "current_operation": {"name": PREFIX + "download", "arguments": deepcopy(args)},
        "current_snapshot": deepcopy(binding), "prior_acquisition_receipt_refs": list(prior),
        "support_receipt_refs": list(support_refs), "supplied_evidence": deepcopy(list(supplied_evidence)),
        "adapter": deepcopy(selected["adapter"]),
        "adapter_implementation_sha256": None if selected["adapter"] is None else "a" * 64}
    validate_contract("PublicationInputs", publication)
    return {"prepared": operation, "event": event, "snapshot": snapshot, "common_receipt": common,
            "publication_inputs": publication, "acquisition_receipt_ref": f"acquisition_{number}"}


def acquisition(case):
    result = build_acquisition_value(**case)
    assert set(result) == {"contract", "value", "diagnostics"}
    validate_contract(result["contract"], result["value"])
    for row in result["diagnostics"]:
        validate_contract("Diagnostic", row)
    return result


def dependency(case, result=None):
    result = acquisition(case) if result is None else result
    assert result["contract"] == "AcquisitionReceipt"
    return {"receipt_ref": case["acquisition_receipt_ref"], "receipt": result["value"]}


def bundle(case, acquisitions=None, *, queries=(), inputs=None):
    return build_artifact_bundle(case["publication_inputs"],
        original_task=case["prepared"]["bound_inputs"]["resolved"]["original_task"],
        acquisitions=[dependency(case)] if acquisitions is None else acquisitions,
        input_bindings=case["publication_inputs"]["request"]["input_bindings"] if inputs is None else inputs,
        query_bindings=list(queries))


def codes(result):
    return {row["code"] for row in result["diagnostics"]}


def refreeze(case):
    """Adversarial shape-valid binding; never a new authenticated host record."""
    operation = case["prepared"]
    native = operation["native_operands"]
    operation["request_sha256"] = operation["bound_inputs"]["request_sha256"] = digest(native["request"])
    operation["arguments_sha256"] = operation["bound_inputs"]["selected_argument_sha256"] = digest(native["arguments"])
    frozen = {key: deepcopy(operation[key]) for key in
              ("operation", "request_sha256", "arguments_sha256", "native_operands")}
    case["common_receipt"]["snapshot"]["selected_operands"] = deepcopy(frozen)
    case["common_receipt"]["origin"]["arguments_sha256"] = operation["arguments_sha256"]
    publication = case["publication_inputs"]
    publication.update(request=deepcopy(native["request"]), selector=deepcopy(native["selector"]),
        current_operation={"name": operation["operation"], "arguments": deepcopy(native["arguments"])},
        current_snapshot=deepcopy(case["common_receipt"]["snapshot"]))


def test_exact_host_bindings_and_unknown_producer_identity_are_preserved(harness):
    case = fixture(harness)
    before = deepcopy(case)
    result = acquisition(case)
    value, source = result["value"], case["common_receipt"]["snapshot"]
    assert value["publication_ref"] is None and value["publication_inputs_sha256"] == digest(case["publication_inputs"])
    assert value["artifact"]["byte_count"] == 6
    assert value["artifact"]["sha256"] == hashlib.sha256(b"abcdef").hexdigest()
    assert value["artifact"]["source_ref"] == source["source_ref"]
    assert value["artifact"]["raw_artifact_ref"] == source["content"]["artifact_ref"]
    assert value["artifact"]["transfer"]["receipt_ref"] == "acquisition_1"
    assert value["artifact"]["task_association"]["byte_version_status"] == "unknown"
    assert value["artifact"]["declared_format"] == FORMAT
    assert "output_version_unproven" in codes(result)
    assert bundle(case)["status"] == "ok"
    assert case == before and harness.client.calls == []


def test_200_ignores_range_without_truncation_or_relabeling(harness):
    case = fixture(harness, byte_range=[2, 4])
    result = acquisition(case)
    assert result["value"]["snapshot"]["transport"]["status"] == 200
    assert result["value"]["artifact"]["transfer"] == {"receipt_ref": "acquisition_1",
        "body_complete": True, "requested_range": [2, 4], "observed_range": None,
        "total_size": 6, "object_complete": "yes"}
    assert result["value"]["artifact"]["byte_count"] == 6
    assert "range_ignored" in codes(result) and bundle(case)["status"] == "ok"


def test_exact_uuid_reference_preserves_service_accepted_uuid_spelling(harness):
    case = fixture(harness, object_number=10, native_uuid=True)
    assert acquisition(case)["contract"] == "AcquisitionReceipt"
    assert case["prepared"]["bound_inputs"]["resolved"]["object"]["native_reference"].startswith("0000000A")


@pytest.mark.parametrize("content,complete,expected_status", [(b"cd", False, "partial"), (b"cde", True, "ok")])
def test_206_body_and_object_completeness_remain_separate(harness, content, complete, expected_status):
    case = fixture(harness, content=content, byte_range=[2, 4], status=206, complete=complete,
                   headers={"Content-Length": "3", "Content-Range": "bytes 2-4/6"})
    value = acquisition(case)["value"]
    assert value["status"] == expected_status
    transfer = value["artifact"]["transfer"]
    assert transfer["body_complete"] is complete and transfer["object_complete"] == "no"
    assert transfer["observed_range"] == {"start": 2, "end_inclusive": 4, "total_size": 6}
    assert value["artifact"]["byte_count"] == len(content)
    assembled = bundle(case)
    assert assembled["status"] == "partial"
    assert assembled["missing_requirements"][0]["reason_code"] == "download_incomplete"


def test_short_body_retained_after_transport_failure_is_not_zero(harness):
    case = fixture(harness, content=b"abc", complete=False, headers={"Content-Length": "6"})
    result = acquisition(case)
    assert result["contract"] == "AcquisitionReceipt"
    assert result["value"]["status"] == "partial" and result["value"]["artifact"]["byte_count"] == 3
    assert result["value"]["failure"]["code"] == "download_incomplete"
    assert bundle(case)["status"] == "partial"


def test_empty_complete_missing_and_empty_incomplete_are_distinct(harness):
    empty = fixture(harness, content=b"", metadata_size=0)
    assert acquisition(empty)["value"]["status"] == "ok"
    assert bundle(empty)["status"] == "ok" and bundle(empty)["artifacts"][0]["byte_count"] == 0
    missing = bundle(empty, [])
    assert missing["status"] == "partial" and missing["artifacts"] == []
    assert missing["missing_requirements"] == [{"requirement_id": "r1", "kind": "output_bytes", "role": "native_output",
        "source_refs": [], "reason_code": "output_bytes_missing"}]
    incomplete = fixture(harness, content=b"", complete=False, metadata_size=6, headers={"Content-Length": "6"})
    assert acquisition(incomplete)["value"]["status"] == "invalid"
    assert bundle(incomplete)["status"] == "invalid"


def test_http_failure_retains_response_but_is_not_usable_artifact(harness):
    case = fixture(harness, content=b"denied", status=403)
    result = acquisition(case)
    assert result["value"]["status"] == "failed" and result["value"]["artifact"]["byte_count"] == 6
    assert result["value"]["failure"]["code"] == "capability_http_error"
    result = bundle(case)
    assert result["status"] == "failed" and result["artifacts"] == []
    assert result["acquisition_receipt_refs"] == ["acquisition_1"]
    assert result["missing_requirements"][0]["reason_code"] == "download_failed"


@pytest.mark.parametrize("status,content,complete", [(403, b"denied", True), (200, b"", False)])
def test_failure_of_one_output_does_not_relabel_an_unacquired_requirement(harness, status, content, complete):
    case = fixture(harness, selected=selector(two=True), status=status, content=content, complete=complete,
                   headers={"Content-Length": "6"})
    result = bundle(case)
    assert result["status"] == "partial"
    assert result["missing_requirements"][1]["reason_code"] == "output_bytes_missing"
    assert result["missing_requirements"][0]["reason_code"] == ("download_failed" if status == 403 else "download_invalid")


def test_unknown_complete_object_size_is_not_inferred_from_received_count(harness):
    case = fixture(harness, metadata_size=None, headers={})
    value = acquisition(case)["value"]
    assert value["artifact"]["transfer"]["total_size"] is None
    assert value["artifact"]["transfer"]["object_complete"] == "unknown"
    assert bundle(case)["missing_requirements"][0]["reason_code"] == "object_completeness_unproven"


def test_impossible_range_projection_falls_back_to_retained_common_receipt(harness):
    case = fixture(harness, content=b"cdef", byte_range=[2, 4], status=206,
        headers={"Content-Length": "4", "Content-Range": "bytes 2-4/6"})
    result = acquisition(case)
    assert result["contract"] == "CommonReceipt" and result["value"]["status"] == "invalid"
    assert result["value"]["snapshot"] == case["common_receipt"]["snapshot"]
    assert "range_byte_count_conflict" in codes(result)


def test_absent_snapshot_keeps_specific_failure_without_artifact(harness):
    case = fixture(harness)
    case.update(snapshot=None, publication_inputs=None)
    case["common_receipt"].update(snapshot=None, status="failed")
    case["event"].update(state="failed", failure_code="capability_unavailable")
    case["event"]["facts"].update(failure=None)
    result = acquisition(case)
    assert result["contract"] == "CommonReceipt" and result["value"]["status"] == "failed"
    assert "capability_unavailable" in codes(result) and "artifact" not in result["value"]


@pytest.mark.parametrize("mutate,code", [
    (lambda c: c["publication_inputs"].update(original_handoff_ref="other_handoff"), "original_task_mismatch"),
    (lambda c: c["prepared"]["bound_inputs"]["resolved"]["original_task"].update(task_id="other-task"), "original_task_mismatch"),
    (lambda c: c["prepared"]["bound_inputs"]["resolved"]["object"]["selection"].update(receipt_ref="wrong-object"), "workspace_target_conflict"),
    (lambda c: c["publication_inputs"]["selector"]["requirements"][0].update(role="invented-role"), "publication_dependency_conflict"),
    (lambda c: c["publication_inputs"]["current_operation"]["arguments"].update(byte_range=[1, 2]), "publication_operation_conflict"),
    (lambda c: c["common_receipt"]["snapshot"]["content"].update(sha256="f" * 64), "snapshot_binding_conflict"),
    (lambda c: c["event"]["facts"]["projection"].update(byte_count=0), "appservice_event_projection_conflict"),
])
def test_conflicting_selected_relationships_keep_common_receipt(harness, mutate, code):
    case = fixture(harness)
    mutate(case)
    result = acquisition(case)
    assert result["contract"] == "CommonReceipt" and code in codes(result)
    assert result["value"]["snapshot"] == case["common_receipt"]["snapshot"]


@pytest.mark.parametrize("field,value", [("role", "sidecar"), ("declared_format", {**FORMAT, "format": "other"}),
    ("exact_object", {"kind": "receipt_row", "receipt_ref": "other-metadata", "row_pointer": "/result/0/0"})])
def test_every_requirement_is_rechecked_without_first_requirement_choice(harness, field, value):
    selected = selector()
    selected["requirements"].append({**deepcopy(selected["requirements"][0]), "requirement_id": "r2"})
    case = fixture(harness, selected=selected, requirement_ids=["r1", "r2"])
    case["prepared"]["native_operands"]["selector"]["requirements"][1][field] = value
    refreeze(case)
    result = acquisition(case)
    assert result["contract"] == "CommonReceipt" and "publication_requirement_conflict" in codes(result)


def test_producer_and_transformation_evidence_must_be_exact_frozen_values(harness):
    evidence = {"content": content_binding(b"source rule"), "pointer": "/rule"}
    selected = selector()
    selected["requirements"][0]["producer_rule_evidence"] = evidence
    selected["requirements"][0]["declared_format"].update(producer_source_ref=evidence["content"]["source_ref"],
                                                        transformation_evidence=[evidence])
    case = fixture(harness, selected=selected, supplied_evidence=[evidence])
    assert acquisition(case)["contract"] == "AcquisitionReceipt"
    case["publication_inputs"]["supplied_evidence"][0]["pointer"] = "/different_rule"
    result = acquisition(case)
    assert result["contract"] == "CommonReceipt" and "publication_evidence_missing" in codes(result)


def test_producer_reference_can_be_a_retained_source_without_support_receipt(harness):
    selected = selector()
    selected["requirements"][0]["declared_format"]["producer_source_ref"] = "actual_source_rule"
    case = fixture(harness, selected=selected, support_refs=["actual_source_rule"])
    assert acquisition(case)["contract"] == "AcquisitionReceipt"
    case["publication_inputs"]["support_receipt_refs"] = []
    assert "publication_producer_source_missing" in codes(acquisition(case))


@pytest.mark.parametrize("kind", ["unverified_original_path", "task_info_folder_member"])
def test_weak_association_is_preserved_without_universal_completion_gate(harness, kind):
    case = fixture(harness, task_association={"kind": kind, "byte_version_status": "current_bytes_observed"})
    result = bundle(case)
    assert result["status"] == "ok" and "output_association_unproven" in codes(result)
    assert result["artifacts"][0]["task_association"]["kind"] == kind
    assert result["artifacts"][0]["task_association"]["byte_version_status"] == "current_bytes_observed"


def test_producer_byte_version_is_copied_only_with_supplied_evidence(harness):
    evidence = {"content": content_binding(b"actual producer digest fixture"), "pointer": "/sha256"}
    case = fixture(harness, task_association={"byte_version_status": "producer_bytes_bound", "version_evidence": [evidence]},
        supplied_evidence=[evidence])
    result = bundle(case)
    assert result["artifacts"][0]["task_association"]["version_evidence"] == [evidence]
    assert "output_version_unproven" not in codes(result)


def test_two_required_outputs_publish_partial_then_usable_without_rewriting_prior(harness):
    selected = selector(two=True)
    first = fixture(harness, selected=selected)
    dep1 = dependency(first)
    before = deepcopy(dep1)
    one = bundle(first, [dep1])
    assert one["status"] == "partial" and [row["requirement_id"] for row in one["missing_requirements"]] == ["r2"]
    second = fixture(harness, selected=selected, number=2, requirement_ids=["r2"], role="sidecar", prior=[dep1["receipt_ref"]])
    two = bundle(second, [dep1, dependency(second)])
    assert two["status"] == "ok" and two["missing_requirements"] == []
    assert [row["role"] for row in two["artifacts"]] == ["native_output", "sidecar"]
    assert two["acquisition_receipt_refs"] == ["acquisition_1", "acquisition_2"]
    assert dep1 == before and one["status"] == "partial"
    assert dep1["receipt"]["publication_inputs_sha256"] != digest(second["publication_inputs"])


def test_projection_endpoint_gets_only_artifact_status_not_scientific_completion(harness):
    selected = selector()
    selected.update(endpoint="requested_projection", adapter={"adapter_id": "fixture_missing_science",
        "adapter_version": "1", "parameters": {"threshold": 5}}, requested_schema={"type": "object",
        "properties": {"query_count": {"type": "integer"}}, "required": ["query_count"], "additionalProperties": False})
    case = fixture(harness, selected=selected)
    result = bundle(case)
    assert result["status"] == "ok"
    assert not {"query_count", "projection", "practical_complete", "completion", "usable_projection"}.intersection(result)
    assert result["requested_selector_sha256"] == digest(selected)


def test_support_download_and_unselected_artifacts_cannot_satisfy_requirements(harness):
    selected = selector(two=True)
    support = fixture(harness, selected=selected, requirement_ids=[], role="support_manifest")
    dep1 = dependency(support)
    assert bundle(support)["artifacts"] == []
    assert len(bundle(support)["missing_requirements"]) == 2
    second = fixture(harness, selected=selected, number=2, requirement_ids=["r2"], role="sidecar", prior=[dep1["receipt_ref"]])
    result = bundle(second, [dep1, dependency(second)])
    assert [row["role"] for row in result["artifacts"]] == ["sidecar"]
    assert [row["requirement_id"] for row in result["missing_requirements"]] == ["r1"]
    assert result["acquisition_receipt_refs"] == ["acquisition_1", "acquisition_2"]
    assert "unselected_artifact_retained" in codes(result)
    with pytest.raises(ContractValidationError):
        bundle(second, [{"receipt_ref": "support", "receipt": support["common_receipt"]}, dependency(second)])


def test_repeated_reference_and_distinct_receipts_for_duplicate_bytes_are_retained(harness):
    first = fixture(harness)
    dep1 = dependency(first)
    duplicate = bundle(first, [dep1, deepcopy(dep1)])
    assert duplicate["acquisition_receipt_refs"] == ["acquisition_1"]
    assert len(duplicate["artifacts"]) == 2 and "duplicate_acquisition_receipt" in codes(duplicate)
    second = fixture(harness, number=2, object_number=1, metadata_receipt_ref="fresh_metadata_receipt", prior=["acquisition_1"])
    result = bundle(second, [dep1, dependency(second)])
    assert len(result["artifacts"]) == 2 and result["acquisition_receipt_refs"] == ["acquisition_1", "acquisition_2"]
    assert result["artifacts"][0]["workspace_object"]["metadata_receipt_ref"] != result["artifacts"][1]["workspace_object"]["metadata_receipt_ref"]
    assert "duplicate_artifact_representation" in codes(result)
    assert not any("independent" in key for key in result)


@pytest.mark.parametrize("kind", ["missing_prior", "unselected_prior", "changed_bytes", "changed_task", "changed_selector",
                                  "changed_current_dependencies", "reordered", "same_ref_different_value"])
def test_changed_dependencies_are_rejected(harness, kind):
    first = fixture(harness)
    prior = dependency(first)
    second = fixture(harness, number=2, prior=[prior["receipt_ref"]])
    current = dependency(second)
    deps = [prior, current]
    if kind == "missing_prior":
        deps.pop(0)
    elif kind == "unselected_prior":
        second["publication_inputs"]["prior_acquisition_receipt_refs"] = []
    elif kind == "changed_bytes":
        prior["receipt"]["artifact"]["sha256"] = "0" * 64
    elif kind == "changed_task":
        prior["receipt"]["artifact"]["task_association"]["task_id"] = "other-task"
    elif kind == "changed_selector":
        prior["receipt"]["snapshot"]["selected_operands"]["native_operands"]["selector"]["requirements"][0]["role"] = "other-role"
    elif kind == "changed_current_dependencies":
        second["publication_inputs"]["support_receipt_refs"] = ["later-inserted-source"]
    elif kind == "reordered":
        deps.reverse()
    else:
        other = deepcopy(prior)
        other["receipt"]["publication_ref"] = "changed-publication"
        deps.insert(1, other)
    with pytest.raises(ContractValidationError):
        bundle(second, deps)


def test_query_and_metadata_bindings_are_explicit_original_values(harness):
    request = original_request()
    content = content_binding(b">q\nACGT\n")
    evidence = {"content": content, "pointer": "/members/0"}
    input_binding = {"binding_id": "query", "parameter_pointer": "/input_fasta_file", "kind": "retained_bytes",
        "content": content, "workspace_path": "/original/query.fa", "inline_value": None, "link_evidence": None,
        "members": [{"member_id": "member1", "member_pointer": "/members/0", "length": 4,
            "molecule": "dna", "sequence_sha256": hashlib.sha256(b"ACGT").hexdigest(), "evidence": evidence}]}
    request["input_bindings"] = [input_binding]
    request["parameters"]["input_fasta_file"] = "/original/query.fa"
    selected = selector()
    selected["supplied_metadata"] = [evidence]
    case = fixture(harness, request=request, selected=selected, supplied_evidence=[evidence])
    raw = dependency(case)
    query = {"input_binding_id": "query", "input_source_ref": content["source_ref"], "input_member_id": "member1",
        "input_member_pointer": "/members/0", "length": 4, "molecule": "dna", "sequence_sha256": input_binding["members"][0]["sequence_sha256"],
        "raw_source_ref": raw["receipt"]["artifact"]["source_ref"], "raw_report_ordinal": 0,
        "query_id": "observed_q", "query_title": "observed title", "transformation_evidence": []}
    empty = bundle(case, [raw])
    assert empty["query_bindings"] == []
    result = bundle(case, [raw], queries=[query])
    assert result["query_bindings"] == [query] and result["supplied_scientific_metadata"] == [evidence]
    query["input_member_id"] = "inferred-from-title"
    with pytest.raises(ContractValidationError, match="query_member_missing"):
        bundle(case, [raw], queries=[query])
    changed = deepcopy(input_binding)
    changed["members"][0]["length"] = 5
    with pytest.raises(ContractValidationError, match="publication_input_bindings_conflict"):
        bundle(case, [raw], inputs=[changed])


def test_outputs_reconstruct_from_saved_json_without_network_or_hidden_state(harness, monkeypatch):
    first = fixture(harness, selected=selector(two=True))
    dep1 = dependency(first)
    second = fixture(harness, selected=selector(two=True), number=2, requirement_ids=["r2"], role="sidecar", prior=["acquisition_1"])
    dep2 = dependency(second)
    original = bundle(second, [dep1, dep2])
    saved = json.loads(json.dumps({"publication_inputs": second["publication_inputs"],
        "original_task": original["original_task"], "acquisitions": [dep1, dep2],
        "input_bindings": [], "query_bindings": []}))
    def forbidden(*args, **kwargs):
        pytest.fail("pure bundle construction attempted Store access")
    monkeypatch.setattr(harness.store, "get", forbidden)
    monkeypatch.setattr(harness.store, "get_artifact", forbidden)
    assert build_artifact_bundle(**saved) == original
    assert harness.client.calls == []
