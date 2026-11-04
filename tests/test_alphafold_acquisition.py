"""Engineered snapshots for the pure AlphaFold contract; no HTTP or archive claim."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode import alphafold_acquisition as af


SOURCE = "source_" + "a" * 24
FILE_SOURCE = "source_" + "b" * 24
PDB = "https://alphafold.ebi.ac.uk/files/AF-CALLER-F7-model_v99.pdb"
CIF = "https://alphafold.ebi.ac.uk/files/AF-CALLER-F7-model_v99.cif"


def _snapshot(raw, arguments, url, *, status=200, complete=True):
    return SourceSnapshot(af.SERVICE, url, deepcopy(arguments), "2026-10-31T00:00:00Z", raw,
        "application/octet-stream", dict(status=status, headers={"content-type": "application/json"},
            body_complete=complete, retained_body_bytes=len(raw), observed_body_bytes=len(raw),
            declared_body_bytes=len(raw), response_byte_limit=arguments["max_bytes"],
            request={"method": "GET", "url": url}))


def _artifact(raw):
    return "artifact_" + hashlib.sha256(raw).hexdigest()


def _prediction(raw=b'[{"uninterpreted":0}]', **options):
    arguments = dict(identifier="CALLER-literal_7", max_bytes=4096)
    snapshot = _snapshot(raw, arguments, af.alphafold_prediction_url(arguments["identifier"]), **options)
    result = af.alphafold_prediction_result(snapshot, arguments=arguments, source_ref=SOURCE,
        artifact_ref=_artifact(raw))
    return snapshot, arguments, result


def _file(*, file_format="pdb_3x_text", raw=b"unparsed structure\x00", status=200, complete=True):
    url = PDB if file_format == "pdb_3x_text" else CIF
    metadata_raw = json.dumps([{"arbitrary_file_key": url}]).encode()
    arguments = dict(metadata_source_ref=SOURCE, url_pointer="/0/arbitrary_file_key",
        file_format=file_format, max_bytes=4096)
    selected = af.resolve_alphafold_file_selection(metadata_raw, arguments=arguments)
    snapshot = _snapshot(raw, arguments, selected["url"], status=status, complete=complete)
    result = af.alphafold_file_result(snapshot, arguments=arguments, association=selected["association"],
        source_ref=FILE_SOURCE, artifact_ref=_artifact(raw))
    return snapshot, arguments, selected, result


@pytest.mark.parametrize("change", [
    {"identifier": ""}, {"identifier": "../P12345"}, {"identifier": "P12345/F1"},
    {"identifier": "P12345%2fF1"}, {"identifier": "P12345?x"}, {"identifier": "P12345\n"},
    {"identifier": "Ｐ12345"}, {"identifier": False}, {"identifier": 12345},
    {"max_bytes": True}, {"max_bytes": 1.0}, {"max_bytes": 0}, {"max_bytes": -1},
    {"endpoint": "summary"},
])
def test_prediction_arguments_are_explicit_single_literal_segment(change):
    arguments = dict(identifier="P12345", max_bytes=4096)
    arguments.update(change)
    with pytest.raises(ValueError):
        af.validate_alphafold_prediction_arguments(arguments)


def test_prediction_path_preserves_case_dashes_and_underscores_without_aliasing():
    arguments = dict(identifier="caller-Isoform_2", max_bytes=1)
    assert af.validate_alphafold_prediction_arguments(arguments) == arguments
    assert af.alphafold_prediction_url(arguments["identifier"]) == af.PREDICTION_ROOT + "caller-Isoform_2"
    assert "F1" not in af.alphafold_prediction_url(arguments["identifier"])


@pytest.mark.parametrize("change", [
    {"metadata_source_ref": "artifact_" + "a" * 64}, {"metadata_source_ref": None},
    {"url_pointer": "0/file"}, {"url_pointer": "/~2"}, {"url_pointer": "/bad~"},
    {"url_pointer": False}, {"file_format": "pdb"}, {"max_bytes": False},
    {"max_bytes": 1.0}, {"max_bytes": 0}, {"url": PDB},
])
def test_file_arguments_reject_inferred_url_and_malformed_selected_operands(change):
    arguments = dict(metadata_source_ref=SOURCE, url_pointer="/0/file", file_format="pdb_3x_text", max_bytes=4096)
    arguments.update(change)
    with pytest.raises(ValueError):
        af.validate_alphafold_file_arguments(arguments)


def test_native_json_keeps_all_literal_fields_models_nulls_zeros_and_order():
    native = [{"accession_like": "DIFFERENT", "version_like": "not-interpreted", "sequence_like": "M?",
        "confidence_like": [0, None, False], "files": {"x": CIF}},
        {"accession_like": None, "unknown": {"arbitrary": [1, {"nested": "yes"}]}}]
    raw = ("  " + json.dumps(native, ensure_ascii=False) + "\n").encode()
    snapshot, arguments, result = _prediction(raw)
    assert result["native_json"] == native and result["parse_state"] == "array"
    assert result["requested"] == arguments and result["issues"] == []
    assert result["raw_artifact_ref"] == _artifact(raw) and snapshot.content == raw
    assert set(result) == {"version", "source_ref", "raw_artifact_ref", "requested", "response",
        "parse_state", "native_json", "issues"}
    result["native_json"][0]["confidence_like"].append(999)
    assert json.loads(snapshot.content) == native
    assert arguments == snapshot.request


@pytest.mark.parametrize("raw,state,native", [
    (b'{}', "object", {}), (b'[]', "array", []), (b'null', "native_null", None),
    (b'0', "scalar", 0), (b'false', "scalar", False), (b'"literal"', "scalar", "literal"),
    (b'{', "decode_failed", None), (b'{"x":0,"x":1}', "decode_failed", None),
    (b'{"x":NaN}', "decode_failed", None), (b'{"x":1e9999}', "decode_failed", None),
    (b'{"x":"\\ud800"}', "decode_failed", None), (b'{"\\ud800":0}', "decode_failed", None),
    (b'\xff', "decode_failed", None),
])
def test_native_json_parse_states_do_not_turn_null_into_decode_failure(raw, state, native):
    _, _, result = _prediction(raw)
    assert result["parse_state"] == state and result["native_json"] == native
    assert result["issues"] == ([dict(code="invalid_native_json", pointer="/native_json")]
        if state == "decode_failed" else [])


@pytest.mark.parametrize("pointer", ["/1/a~1b/~0file", "/0/a~1b/~0file"])
def test_exact_pointer_selects_advertised_model_without_first_model_or_version_default(pointer):
    native = [{"a/b": {"~file": PDB.replace("F7", "F8")}}, {"a/b": {"~file": PDB}}]
    raw = json.dumps(native).encode()
    arguments = dict(metadata_source_ref=SOURCE, url_pointer=pointer, file_format="pdb_3x_text", max_bytes=4096)
    selected = af.resolve_alphafold_file_selection(raw, arguments=arguments)
    expected = native[int(pointer[1])]["a/b"]["~file"]
    assert selected["url"] == expected
    assert selected["association"] == dict(version="alphafold_advertised_file_association_v1",
        metadata_source_ref=SOURCE, metadata_artifact_ref=_artifact(raw), url_pointer=pointer,
        advertised_url=expected, file_format="pdb_3x_text")
    assert raw == json.dumps(native).encode()


@pytest.mark.parametrize("pointer", ["/2/file", "/01/file", "/-1/file", "/-/file", "/0/missing", "/0/file/extra"])
def test_pointer_does_not_guess_missing_keys_or_noncanonical_array_indices(pointer):
    arguments = dict(metadata_source_ref=SOURCE, url_pointer=pointer, file_format="pdb_3x_text", max_bytes=4096)
    with pytest.raises(ValueError, match="alphafold_url_pointer_unresolved"):
        af.resolve_alphafold_file_selection(json.dumps([{"file": PDB}]).encode(), arguments=arguments)


def test_root_and_empty_key_pointers_are_literal_rfc6901_choices():
    arguments = dict(metadata_source_ref=SOURCE, url_pointer="", file_format="pdb_3x_text", max_bytes=4096)
    assert af.resolve_alphafold_file_selection(json.dumps(PDB).encode(), arguments=arguments)["url"] == PDB
    arguments["url_pointer"] = "/"
    assert af.resolve_alphafold_file_selection(json.dumps({"": PDB}).encode(), arguments=arguments)["url"] == PDB


@pytest.mark.parametrize("url", [
    "http://alphafold.ebi.ac.uk/files/model.pdb", "https://evil.test/files/model.pdb",
    "https://alphafold.ebi.ac.uk.evil.test/files/model.pdb", "https://user@alphafold.ebi.ac.uk/files/model.pdb",
    "https://alphafold.ebi.ac.uk:444/files/model.pdb", "https://alphafold.ebi.ac.uk/api/model.pdb",
    "https://alphafold.ebi.ac.uk/files/sub/model.pdb", "https://alphafold.ebi.ac.uk/files/model.cif",
    "https://alphafold.ebi.ac.uk/files/model.pdb#fragment", "https://alphafold.ebi.ac.uk/files/model%2epdb",
    "https://alphafold.ebi.ac.uk/files/../model.pdb", "https://alphafold.ebi.ac.uk/files/model.pdb\n",
    "https://alphafold.ebi.ac.uk\\evil.test/files/model.pdb", None, 0,
])
def test_selected_file_must_be_matching_official_https_advertised_file(url):
    arguments = dict(metadata_source_ref=SOURCE, url_pointer="/file", file_format="pdb_3x_text", max_bytes=4096)
    with pytest.raises(ValueError):
        af.resolve_alphafold_file_selection(json.dumps({"file": url}).encode(), arguments=arguments)


@pytest.mark.parametrize("raw", [b'{"file":"a","file":"b"}', b'{', b'NaN', b'"\\ud800"'])
def test_invalid_metadata_bytes_never_produce_a_selection(raw):
    arguments = dict(metadata_source_ref=SOURCE, url_pointer="/file", file_format="pdb_3x_text", max_bytes=4096)
    with pytest.raises(ValueError):
        af.resolve_alphafold_file_selection(raw, arguments=arguments)


@pytest.mark.parametrize("file_format", list(af.FILE_FORMATS))
def test_file_identity_is_selected_processing_not_parsed_native_identity(file_format):
    snapshot, arguments, selected, result = _file(file_format=file_format)
    assert result["file"] == dict(artifact_ref=_artifact(snapshot.content), sha256=snapshot.sha256,
        byte_length=len(snapshot.content), format=file_format)
    assert result["observed_identity"] == dict(native_model_id=None, state="not_parsed")
    assert result["association"] == selected["association"] and result["requested"] == arguments
    assert result["response"]["content_type"] == "application/json" and result["issues"] == []
    result["association"]["url_pointer"] = "/changed"
    assert selected["association"]["url_pointer"] == arguments["url_pointer"]


@pytest.mark.parametrize("kind,status,complete", [("prediction", 404, True), ("file", 403, True),
    ("prediction", 200, False), ("file", 200, False)])
def test_actual_http_failure_and_partial_capture_are_not_success_or_missing_entity(kind, status, complete):
    result = (_prediction(b'null', status=status, complete=complete)[2] if kind == "prediction" else
        _file(raw=b"provider error bytes", status=status, complete=complete)[3])
    assert result["response"]["http_status"] == status and result["response"]["body_complete"] is complete
    assert ("http_not_success" in [row["code"] for row in result["issues"]]) is (status != 200)
    assert ("response_incomplete" in [row["code"] for row in result["issues"]]) is (not complete)


@pytest.mark.parametrize("field,value,output", [("status", True, "http_status"),
    ("status", 200.0, "http_status"), ("body_complete", 1, "body_complete"),
    ("declared_body_bytes", False, "declared_body_bytes"),
    ("observed_body_bytes", -1, "observed_body_bytes")])
def test_transport_unknowns_do_not_become_native_zero_or_verified_types(field, value, output):
    snapshot, arguments, _ = _prediction()
    changed = replace(snapshot, transport={**snapshot.transport, field: value})
    result = af.alphafold_prediction_result(changed, arguments=arguments, source_ref=SOURCE,
        artifact_ref=_artifact(snapshot.content))
    assert result["response"][output] is None
    assert dict(code="transport_metadata_unavailable", pointer="/response/" + output) in result["issues"]
    assert changed.transport[field] == value


@pytest.mark.parametrize("change", [
    {"service": "rcsb_pdb"}, {"url": "https://alphafold.ebi.ac.uk/api/prediction/OTHER"},
    {"request": {"identifier": "OTHER", "max_bytes": 4096}},
    {"request": {"identifier": "CALLER-literal_7", "max_bytes": 4096.0}},
])
def test_snapshot_service_url_and_original_public_arguments_are_bound(change):
    snapshot, arguments, _ = _prediction()
    with pytest.raises(ValueError):
        af.alphafold_prediction_result(replace(snapshot, **change), arguments=arguments, source_ref=SOURCE,
            artifact_ref=_artifact(snapshot.content))


def test_snapshot_actual_request_and_raw_content_hash_cannot_be_substituted():
    snapshot, arguments, _ = _prediction()
    changed = replace(snapshot, transport={**snapshot.transport, "request": {"method": "POST", "url": snapshot.url}})
    with pytest.raises(ValueError, match="alphafold_snapshot_request_conflict"):
        af.alphafold_prediction_result(changed, arguments=arguments, source_ref=SOURCE,
            artifact_ref=_artifact(snapshot.content))
    with pytest.raises(ValueError, match="alphafold_artifact_identity_conflict"):
        af.alphafold_prediction_result(snapshot, arguments=arguments, source_ref=SOURCE,
            artifact_ref="artifact_" + "f" * 64)


def test_snapshot_content_cannot_exceed_the_original_selected_byte_limit():
    snapshot, arguments, _ = _prediction()
    arguments["max_bytes"] = 1
    changed = replace(snapshot, request=deepcopy(arguments))
    with pytest.raises(ValueError, match="alphafold_snapshot_byte_limit_conflict"):
        af.alphafold_prediction_result(changed, arguments=arguments, source_ref=SOURCE,
            artifact_ref=_artifact(snapshot.content))


@pytest.mark.parametrize("field,value", [("artifact_ref", "artifact_" + "f" * 64),
    ("sha256", "f" * 64), ("byte_length", 0), ("format", "pdbx_mmcif_text")])
def test_file_identity_hash_length_and_format_remain_joined(field, value):
    result = _file()[3]
    result["file"][field] = value
    with pytest.raises(ValueError):
        af.validate_alphafold_file_result(result)


@pytest.mark.parametrize("field,value", [("metadata_source_ref", FILE_SOURCE), ("url_pointer", "/other"),
    ("file_format", "pdbx_mmcif_text"), ("advertised_url", CIF), ("extra", None)])
def test_file_association_cannot_disagree_with_requested_meaning(field, value):
    _, _, _, result = _file()
    result["association"][field] = value
    with pytest.raises(ValueError):
        af.validate_alphafold_file_result(result)


@pytest.mark.parametrize("kind,field,value", [
    ("prediction", "parse_state", "object"), ("prediction", "source_ref", "source_not_real"),
    ("prediction", "native_json", {"nonfinite": float("inf")}), ("prediction", "extra", None),
    ("file", "observed_identity", {"native_model_id": "AF-invented", "state": "not_parsed"}),
    ("file", "extra", None),
])
def test_external_closed_dto_rejects_forged_shapes_or_parse_claims(kind, field, value):
    result = _prediction()[2] if kind == "prediction" else _file()[3]
    result[field] = value
    with pytest.raises(ValueError):
        (af.validate_alphafold_prediction_result if kind == "prediction" else af.validate_alphafold_file_result)(result)


@pytest.mark.parametrize("reference", [SOURCE + "\n", SOURCE + "\r\n",
    "source_" + "a" * 23, "source_" + "a" * 65, "artifact_" + "a" * 64])
def test_source_references_require_exact_namespace_and_existing_id_range(reference):
    prediction = _prediction()[2]
    _, arguments, selected, file = _file()
    for validate, value in [
        (af.validate_alphafold_prediction_result, {**prediction, "source_ref": reference}),
        (af.validate_alphafold_file_arguments, {**arguments, "metadata_source_ref": reference}),
        (af.validate_alphafold_file_association, {**selected["association"], "metadata_source_ref": reference}),
        (af.validate_alphafold_file_result, {**file, "source_ref": reference}),
    ]:
        with pytest.raises(ValueError):
            validate(value)


@pytest.mark.parametrize("reference", ["artifact_" + "a" * 64 + "\n", "artifact_" + "a" * 64 + "\r\n",
    "artifact_" + "a" * 63, "artifact_" + "a" * 65, SOURCE])
def test_metadata_artifact_references_require_exact_namespace_and_digest_length(reference):
    prediction = _prediction()[2]
    association = _file()[2]["association"]
    for validate, value in [
        (af.validate_alphafold_prediction_result, {**prediction, "raw_artifact_ref": reference}),
        (af.validate_alphafold_file_association, {**association, "metadata_artifact_ref": reference}),
    ]:
        with pytest.raises(ValueError):
            validate(value)


@pytest.mark.parametrize("width", [24, 64])
def test_exact_source_reference_guards_preserve_both_existing_id_bounds(width):
    reference = "source_" + "a" * width
    prediction = _prediction()[2]
    _, arguments, selected, file = _file()
    arguments = {**arguments, "metadata_source_ref": reference}
    association = {**selected["association"], "metadata_source_ref": reference}
    assert af.validate_alphafold_prediction_result({**prediction, "source_ref": reference})["source_ref"] == reference
    assert af.validate_alphafold_file_arguments(arguments) == arguments
    assert af.validate_alphafold_file_association(association, arguments=arguments) == association
    assert af.validate_alphafold_file_result({**file, "source_ref": reference,
        "requested": arguments, "association": association})["source_ref"] == reference


@pytest.mark.parametrize("kind", ["prediction", "file"])
def test_closed_result_status_count_and_issue_joins_cannot_be_forged(kind):
    original = _prediction()[2] if kind == "prediction" else _file()[3]
    validate = af.validate_alphafold_prediction_result if kind == "prediction" else af.validate_alphafold_file_result
    variants = []
    changed = deepcopy(original); changed["response"]["http_status"] = 404; variants.append(changed)
    changed = deepcopy(original); changed["response"]["body_complete"] = False; variants.append(changed)
    changed = deepcopy(original); changed["response"]["retained_bytes"] = True; variants.append(changed)
    changed = deepcopy(original); changed["response"]["retained_bytes"] = 4097; variants.append(changed)
    changed = deepcopy(original); changed["issues"] = [dict(code="http_not_success", pointer="/response/http_status")]; variants.append(changed)
    changed = deepcopy(original); changed["issues"] = [dict(code="invalid_native_json", pointer="/native_json")]; variants.append(changed)
    for changed in variants:
        with pytest.raises(ValueError):
            validate(changed)


@pytest.mark.parametrize("kind", ["prediction", "file"])
def test_schema_is_closed_and_owns_recursive_native_json_when_embedded(kind):
    result = _prediction(b'[{"nested":[null,0,{"keep":false}]}]')[2] if kind == "prediction" else _file()[3]
    schema = af.ALPHAFOLD_PREDICTION_RESULT_SCHEMA if kind == "prediction" else af.ALPHAFOLD_FILE_RESULT_SCHEMA
    parent = dict(type="object", properties={"selected": schema}, required=["selected"], additionalProperties=False,
        **{"$defs": {"NativeJSON": {"type": "null"}}})
    Draft202012Validator.check_schema(parent)
    assert Draft202012Validator(parent).is_valid({"selected": result})
    result["extra"] = None
    assert not Draft202012Validator(parent).is_valid({"selected": result})
