"""Reader-only protocol tests; synthetic EMDB operands, no HTTP or publication authority."""
from dataclasses import replace
import hashlib
import json
import pytest
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode import emdb_acquisition as emdb


# These are engineering EMDB-shaped JSON operands, not a retained live reply or
# an assertion that arbitrary native fields have a particular scientific unit.
NATIVE = {"emdb_id": "EMD-8117", "map": {"unknown_unit_object": {"valueOf_": 0, "units": "literal-unit"}},
    "sample": {"macromolecule_list": {"macromolecule": [{"macromolecule_id": 2}, {"macromolecule_id": 1}]}},
    "structure_determination_list": {"structure_determination": [
        {"method": "first-literal", "image_processing": [{"final_reconstruction": {"resolution": None}}]},
        {"method": "second-literal", "image_processing": [{"final_reconstruction": {
            "resolution": {"valueOf_": 2.8, "units": "A"}}}]}]},
    "crossreferences": {"pdb_list": {"pdb_reference": [{"pdb_id": "5irx", "relationship": {"in_frame": "FULLOVERLAP"}}]},
        "emdb_list": {"emdb_reference": [{"emdb_id": "EMD-8118", "relationship": {"other": "other EM volume"}}]},
        "citation_list": {"literal_uninterpreted": "retained native text"}},
    "unknown_column": [None, 0, False, [], {}]}


def snapshot(raw=None, *, native=NATIVE, max_bytes=4096):
    raw = json.dumps(native, ensure_ascii=False, separators=(",", ":")).encode() if raw is None else raw
    args = {"entry_id": "EMD-8117", "max_bytes": max_bytes}
    url = emdb.emdb_entry_url(args["entry_id"])
    return SourceSnapshot(emdb.SERVICE, url, args, "2026-10-31T00:00:00+00:00", raw,
        "application/json", {"status": 200, "body_complete": True,
            "headers": {"content-type": "application/json"}, "observed_body_bytes": len(raw),
            "declared_body_bytes": len(raw), "retained_body_bytes": len(raw),
            "response_byte_limit": max_bytes, "request": {"method": "GET", "url": url},
            "request_policy": {"automatic_redirects": False, "timeout_seconds": 3}})


def project(value):
    return emdb.emdb_entry_result(value, arguments={"entry_id": "EMD-8117", "max_bytes": value.request["max_bytes"]},
        source_ref="source_" + "a" * 24, artifact_ref="artifact_" + hashlib.sha256(value.content).hexdigest())


def test_full_native_arrays_associations_units_null_zero_and_unknown_columns_survive():
    original = snapshot()
    result = project(original)
    assert result["native_json"] == NATIVE and result["issues"] == []
    assert result["requested"] == {"entry_id": "EMD-8117", "max_bytes": 4096}
    assert len(result["native_json"]["structure_determination_list"]["structure_determination"]) == 2
    assert result["native_json"]["unknown_column"] == [None, 0, False, [], {}]
    result["native_json"]["unknown_column"].append("detached")
    assert json.loads(original.content) == NATIVE
    assert emdb.emdb_entry_url("EMD-0008117").endswith("/EMD-0008117")


@pytest.mark.parametrize("native,code", [({}, "native_entry_id_missing"),
    ({"emdb_id": None}, "native_entry_id_null"), ({"emdb_id": False}, "native_entry_id_invalid"),
    ({"emdb_id": "EMD-8118"}, "native_entry_id_differs_from_request")])
def test_native_identity_is_literal_and_never_filled_from_request(native, code):
    result = project(snapshot(native=native))
    assert result["native_json"] == native
    assert result["issues"] == [{"code": code, "pointer": "/emdb_id"}]


@pytest.mark.parametrize("raw,state", [(b'{"emdb_id":1,"emdb_id":2}', "decode_failed"),
    (b'{"emdb_id":NaN}', "decode_failed"), (b'{"x":Infinity}', "decode_failed"),
    (b'{"x":"\\ud800"}', "decode_failed"), (b'\xff', "decode_failed"),
    (b'null', "non_object"), (b'[0,null,false]', "non_object")])
def test_invalid_json_and_nonobjects_remain_distinct_retained_response_states(raw, state):
    result = project(snapshot(raw))
    assert result["parse_state"] == state
    assert result["native_json"] == (None if state == "decode_failed" else json.loads(raw))
    assert result["response"]["retained_bytes"] == len(raw)
    assert result["issues"][0]["pointer"] == ""


@pytest.mark.parametrize("changed", [{"service": "rcsb_pdb"}, {"url": "https://example.invalid/EMD-8117"},
    {"request": {"entry_id": "EMD-8118", "max_bytes": 4096}},
    {"request": {"entry_id": "EMD-8117", "max_bytes": 4096, "fields": []}}])
def test_response_cannot_be_rebound_to_another_selected_operand(changed):
    with pytest.raises(ValueError):
        project(replace(snapshot(), **changed))


def test_original_artifact_digest_and_external_dto_states_are_checked():
    original = snapshot()
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        emdb.emdb_entry_result(original, arguments=original.request,
            source_ref="source_" + "a" * 24, artifact_ref="artifact_" + "0" * 64)
    result = project(original)
    for key, altered in (("parse_state", "decode_failed"), ("source_ref", result["source_ref"] + "\n"),
            ("raw_artifact_ref", result["raw_artifact_ref"] + "\n")):
        with pytest.raises(ValueError):
            emdb.validate_emdb_entry_result({**result, key: altered})


@pytest.mark.parametrize('policy', [None, {}, {'automatic_redirects': 0}, {'automatic_redirects': True}],
    ids=['missing-policy', 'missing-redirect', 'integer-redirect', 'enabled-redirect'])
def test_absence_does_not_relax_original_no_redirect_authentication(policy):
    capture = snapshot()
    capture.transport['request_policy'] = policy
    with pytest.raises(ValueError, match='transport_policy_conflict'):
        project(capture)


@pytest.mark.parametrize('change,code', [('status', 'emdb_http_not_success'),
    ('body_complete', 'emdb_response_incomplete'), ('identity', 'emdb_native_entry_id_differs_from_request')])
def test_failed_reader_receipts_never_expose_acquired_data(change, code):
    capture = snapshot(native={'emdb_id': 'EMD-8118'}) if change == 'identity' else snapshot()
    capture.transport['request_policy'].pop('timeout_seconds')
    if change == 'status':
        capture.transport['status'] = 500
    if change == 'body_complete':
        capture.transport['body_complete'] = False
    value = project(capture)
    assert value['raw_artifact_ref'] == 'artifact_' + hashlib.sha256(capture.content).hexdigest()
    assert emdb.emdb_entry_receipt(value) == {
        'acquired': False, 'source_ref': value['source_ref'], 'data_ref': None, 'failure_code': code}
