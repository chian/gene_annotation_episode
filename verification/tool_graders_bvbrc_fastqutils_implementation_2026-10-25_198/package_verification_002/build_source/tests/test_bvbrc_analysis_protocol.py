"""Synthetic envelopes/source-derived shapes; the retained 403 is real HTTP.

No successful deployed AppService, Workspace or MinHash response was retained
by the native study.  These tests do not claim that such a call was executed.
"""

from copy import deepcopy
from pathlib import Path
import json
import socket

import pytest

from gene_annotation_episode.bvbrc_analysis_protocol import (
    RPC_METHODS, RPCValidationError, decode_rpc_response, parse_task_records,
    parse_workspace_records, prepare_rpc_request, validate_start_parameters,
)


STUDY = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24"
METHOD = "AppService.enumerate_apps"
UUID_A = "11111111-1111-4111-8111-111111111111"
UUID_B = "22222222-2222-4222-8222-222222222222"


def metadata(name="input.fa", *, parent="/alice/work/", uid=UUID_A, kind="contigs", size=0, shock=""):
    return [name, kind, parent, "2026-10-24T12:34:56Z", uid, "alice", size,
            {"zero": "0", "unknown": None}, {"is_folder": int(kind == "folder")}, "w", "n", shock]


def decode(document, **changes):
    args = {"method": METHOD, "request_id": "corr-1", "http_status": 200}
    args.update(changes)
    return decode_rpc_response(json.dumps(document).encode(), **args)


def codes(result):
    return {d["code"] for d in result["diagnostics"]}


REQUESTS = [
    ("AppService.enumerate_apps", []),
    ("AppService.start_app2", ["Homology", {"x": [0, "0", None, False]}, {}]),
    ("AppService.query_tasks", [["00123", 0, "123"]]),
    ("Workspace.ls", [{"paths": ["/alice/work/"], "fullHierachicalOutput": 1,
                       "recursive": 0, "query": {"size": {"$gte": 0}}}]),
    ("Workspace.get", [{"objects": ["/alice/work/input.fa"], "metadata_only": 0, "adminmode": 0}]),
    ("Workspace.get_download_url", [{"objects": ["/alice/work/input.fa"]}]),
    ("Workspace.create", [{"objects": [["/alice/work/input.fa", "contigs", None, None]],
                           "createUploadNodes": 1, "overwrite": 0}]),
    ("Minhash.compute_genome_distance_for_genome2", ["83333.1", 0, 1.0, 0, 1, 0, 1, 0]),
    ("Minhash.compute_genome_distance_for_fasta2", ["/alice/work/input.fa", 0.01, 0.1, 10, 0, 1, 0, 1]),
]


@pytest.mark.parametrize("method,params", REQUESTS)
def test_exact_native_method_order_and_detached_operands(method, params):
    before = deepcopy(params)
    result = prepare_rpc_request(method, params, request_id=0)
    assert result == {"version": "1.1", "method": method, "params": before, "id": 0}
    assert result["params"] is not params
    assert params == before
    assert json.dumps(result["params"]) == json.dumps(params)


def test_exactly_nine_rpc_primitives_no_hidden_workflow():
    assert set(RPC_METHODS) == {method for method, _ in REQUESTS}
    with pytest.raises(RPCValidationError) as error:
        prepare_rpc_request("AppService.submit_workflow", [], request_id="x")
    assert error.value.code == "unsupported_rpc_method"
    assert error.value.diagnostics[0] == {"code": "unsupported_rpc_method", "path": "$.method"}


@pytest.mark.parametrize("method,params,code", [
    ([], [], "unsupported_rpc_method"),
    (METHOD, {}, "expected_array"),
    (METHOD, [None], "wrong_parameter_arity"),
    ("AppService.start_app2", ["Homology", {}, []], "expected_object"),
    ("AppService.query_tasks", [[True]], "invalid_task_id"),
    ("AppService.query_tasks", [["123x"]], "invalid_task_id"),
    ("Workspace.ls", [{"paths": ["/alice/work"], "limit": 10}], "unknown_workspace_option"),
    ("Workspace.ls", [{"paths": ["/alice/work"], "fullHierarchicalOutput": 1}], "unknown_workspace_option"),
    ("Workspace.get", [{"objects": ["/alice/work/a"], "metadata_only": True}], "expected_integer_boolean"),
    ("Workspace.get", [{"objects": ["/alice/work/a"], "metadata_only": "0"}], "expected_integer_boolean"),
    ("Workspace.get_download_url", [{"objects": ["https://example.org/a"]}], "invalid_workspace_reference"),
    ("Workspace.create", [{"objects": [["/alice/work/a"]]}], "invalid_creation_tuple"),
    ("Workspace.create", [{"objects": [["/alice/work/a", "contigs", []]]}], "expected_object"),
    ("Minhash.compute_genome_distance_for_fasta2", [">x\nACGT", 0.1, 0.1, 10, 1, 1, 1, 0], "invalid_minhash_input"),
    ("Minhash.compute_genome_distance_for_fasta2", ["local.fa", 0.1, 0.1, 10, 1, 1, 1, 0], "invalid_minhash_input"),
    ("Minhash.compute_genome_distance_for_genome2", ["83333.1", True, 0.1, 10, 1, 1, 1, 0], "invalid_minhash_threshold"),
    ("Minhash.compute_genome_distance_for_genome2", ["83333.1", 0.1, 0.1, 10.0, 1, 1, 1, 0], "invalid_max_hits"),
])
def test_invalid_request_operands_are_diagnosed_without_coercion(method, params, code):
    before = deepcopy(params)
    with pytest.raises(RPCValidationError) as error:
        prepare_rpc_request(method, params, request_id="x")
    assert code in {d["code"] for d in error.value.diagnostics}
    assert params == before


def test_start_parameters_share_real_fields_and_preserve_original_values():
    params = {"parent_id": "0", "workspace": "", "base_url": "https://example.org",
              "container_id": "image", "user_metadata": "", "reservation": "r",
              "data_container_id": "data", "disable_preflight": 0,
              "preflight_data": {"cpu": 0, "policy_data": {}, "unknown": None},
              "constraint": "x", "user_override": "alice"}
    assert validate_start_parameters(params) == []
    assert prepare_rpc_request("AppService.start_app2", ["Homology", {}, params], request_id="x")["params"][2] == params
    for field, value, expected in [("parent_id", 0, "expected_string"),
                                   ("disable_preflight", False, "expected_integer"),
                                   ("preflight_data", [], "expected_object"),
                                   ("request_key", "key", "unknown_start_parameter")]:
        assert {"code": expected, "path": "$.start_parameters." + field} in validate_start_parameters({field: value})


def test_create_source_defined_optional_fields_and_link_name_difference():
    objects = [["/alice/work/new", "Directory"],
               ["/alice/work/input.fa", "contigs", {}, None, "1729771200"],
               ["/alice/work/native.json", "json", None, {"x": [0, None]}]]
    options = {"objects": objects, "permission": "r", "setowner": None,
               "createUploadNodes": 0, "downloadFromLinks": 1, "downloadLinks": 0,
               "overwrite": 0, "adminmode": 0}
    assert prepare_rpc_request("Workspace.create", [options], request_id=None)["params"] == [options]
    options["downloadLinks"] = 1
    with pytest.raises(RPCValidationError) as error:
        prepare_rpc_request("Workspace.create", [options], request_id="x")
    assert {"code": "declared_but_unused_native_option", "path": "$.params[0].downloadLinks"} in error.value.diagnostics


@pytest.mark.parametrize("version", [{"version": "1.1"}, {"jsonrpc": "2.0"}])
@pytest.mark.parametrize("value", [None, 0, "0", [], {"native": [0, "0", None, False]}])
def test_rpc_single_result_original_types_and_complete_envelope(version, value):
    document = {**version, "id": "corr-1", "result": [value], "native_extension": {"a": 1}}
    result = decode(document)
    assert result == {"status": "ok", "value": value, "native": document, "diagnostics": []}


@pytest.mark.parametrize("document,code", [
    ({"version": "1.1", "id": "wrong", "result": [[]]}, "response_id_mismatch"),
    ({"version": "1.1", "result": [[]]}, "missing_response_id"),
    ({"version": "1.1", "id": "corr-1", "result": []}, "wrong_result_arity"),
    ({"version": "1.1", "id": "corr-1", "result": [1, 2]}, "wrong_result_arity"),
    ({"version": "1.1", "id": "corr-1", "result": {}}, "wrong_result_arity"),
    ({"version": "1.1", "id": "corr-1"}, "missing_result_or_error"),
    ({"id": "corr-1", "result": [[]]}, "missing_rpc_version"),
    ({"version": "2.0", "id": "corr-1", "result": [[]]}, "unsupported_or_ambiguous_rpc_version"),
    ({"version": "1.1", "jsonrpc": "2.0", "id": "corr-1", "result": [[]]}, "unsupported_or_ambiguous_rpc_version"),
    ({"jsonrpc": "2.0", "id": "corr-1", "result": [[]], "error": None}, "ambiguous_result_error"),
    ({"version": "1.1", "id": "corr-1", "result": [[]], "error": {}}, "ambiguous_result_error"),
    ({"jsonrpc": "2.0", "id": "corr-1", "error": "bad"}, "invalid_rpc_error"),
    ({"version": "1.1", "id": "corr-1", "result": [[]], "method": "Workspace.ls"}, "response_method_mismatch"),
    ([], "invalid_rpc_envelope"),
])
def test_rpc_invalid_envelope_never_has_successful_value(document, code):
    result = decode(document)
    assert result["status"] == "invalid" and result["value"] is None
    assert result["native"] == document
    assert code in codes(result)


def test_rpc_11_null_error_and_exact_numeric_correlation():
    assert decode({"version": "1.1", "id": "corr-1", "result": [[]], "error": None})["status"] == "ok"
    for request_id in (0, None, "0", 0.0):
        document = {"version": "1.1", "id": request_id, "result": [0]}
        assert decode(document, request_id=request_id)["status"] == "ok"
    assert "response_id_mismatch" in codes(decode({"version": "1.1", "id": "0", "result": [[]]}, request_id=0))
    assert "response_id_mismatch" in codes(decode({"version": "1.1", "id": False, "result": [[]]}, request_id=0))


def test_rpc_error_object_and_http_error_remain_distinct():
    error = {"code": -32603, "message": "failed", "data": {"phase": "native"},
             "error": ["native detail"], "extension": 0}
    document = {"jsonrpc": "2.0", "id": "corr-1", "error": error}
    result = decode(document, http_status=500)
    assert result["native"]["error"] == error
    assert {"http_error", "native_rpc_error"} <= codes(result)
    apparent_success = decode({"version": "1.1", "id": "corr-1", "result": [[]]}, http_status=403)
    assert apparent_success["status"] == "invalid" and apparent_success["value"] is None


@pytest.mark.parametrize("content,code", [(None, "missing_response"), (b"", "missing_response"),
    (b"<html>error</html>", "invalid_json"), (b"\xff", "invalid_json"),
    ({"result": [[]]}, "invalid_content_type"), (b'{"result":[NaN]}', "invalid_json"),
    (b'{"result":[1e10000]}', "unrepresentable_json_number"),
    (b'{"result":[1e-10000]}', "unrepresentable_json_number")])
def test_missing_or_non_json_responses(content, code):
    result = decode_rpc_response(content, method=METHOD, request_id="x", http_status=200)
    assert result["status"] == "invalid" and result["native"] is None and result["value"] is None
    assert code in codes(result)


def test_ambiguous_duplicate_rpc_members_are_not_accepted():
    content = b'{"version":"1.1","id":"wrong","id":"corr-1","result":[[]]}'
    result = decode_rpc_response(content, method=METHOD, request_id="corr-1", http_status=200)
    assert result["status"] == "invalid" and "duplicate_json_member" in codes(result)
    nested = b'{"version":"1.1","id":"corr-1","result":[{"1":{"id":1,"id":2}}]}'
    result = decode_rpc_response(nested, method=METHOD, request_id="corr-1", http_status=200)
    assert {"code": "duplicate_json_member", "path": '$["result"][0]["1"]["id"]'} in result["diagnostics"]


def test_retained_actual_403_is_http_failure_not_native_rpc_failure():
    content = (STUDY / "observations/enumerate_apps.response.bin").read_bytes()
    result = decode_rpc_response(content, method=METHOD, request_id="source-study", http_status=403)
    assert result["status"] == "invalid" and result["native"] is None
    assert {"http_error", "invalid_json"} <= codes(result)
    assert "native_rpc_error" not in codes(result)
    assert b"<html" in content.lower()


def test_start_receipt_is_not_rewritten_as_status_query():
    native = {"id": 7301, "application_id": "Homology", "state_code": "Q",
              "params": '{"query":"x","zero":0}', "req_runtime": 259200,
              "output_path": "/alice/work", "output_file": "out", "owner": "alice"}
    result = parse_task_records(native, operation="start_app2")
    row = result["records"][0]
    assert result["status"] == "ok" and row["task_id"] == 7301
    assert row["state_field"] == "state_code" and row["native_state"] == "Q"
    assert row["parameters_field"] == "params" and row["parameters"] == native["params"]
    assert row["native_record"] == native and result["native"] == native
    assert all(row[field] is None for field in ("submit_time", "start_time", "completed_time", "elapsed_time", "storage_location"))
    assert "queue_duration" not in row and "annotation_score" not in row


def test_task_query_preserves_native_time_strings_unknown_states_and_null():
    task = {"id": "7301", "app": "Homology", "status": "future-native-state",
            "parameters": {"zero": 0, "text": "0", "null": None}, "submit_time": "2026-10-24 12:00:00",
            "start_time": "", "completed_time": None, "elapsed_time": "", "storage_location": "active"}
    result = parse_task_records({"7301": task}, operation="query_tasks", requested_task_ids=[7301])
    row = result["records"][0]
    assert result["status"] == "ok" and row["native_state"] == "future-native-state"
    assert row["start_time"] == "" and row["completed_time"] is None
    assert row["submit_time"] == "2026-10-24 12:00:00" and row["elapsed_time"] == ""
    assert row["parameters"] == task["parameters"]


def test_task_partial_neighbors_missing_and_wrong_ids():
    native = {"7301": {"id": 7301, "app": "Homology", "status": "completed", "elapsed_time": "00:02:03"},
              "7302": "not a task", "7303": {"id": 7304, "status": "queued"}}
    result = parse_task_records(native, operation="query_tasks", requested_task_ids=["7301", "7302", "7303"])
    assert result["status"] == "partial" and len(result["records"]) == 3
    assert result["records"][0]["status"] == "ok" and result["records"][0]["elapsed_time"] == "00:02:03"
    assert result["records"][1]["native_record"] == "not a task"
    assert {"invalid_task_record", "task_map_id_mismatch", "unrequested_task_id", "requested_task_not_returned"} <= codes(result)
    assert {"code": "invalid_task_record", "path": '$["7302"]'} in result["diagnostics"]
    assert result["native"] == native


def test_missing_task_is_unknown_and_empty_query_is_not_a_completion():
    assert parse_task_records({}, operation="query_tasks")["status"] == "ok"
    missing = parse_task_records({}, operation="query_tasks", requested_task_ids=["7301"])
    assert missing["status"] == "invalid" and missing["records"] == []
    assert codes(missing) == {"requested_task_not_returned"}
    malformed = parse_task_records({"id": False, "elapsed_time": 0}, operation="start_app2")
    assert malformed["records"][0]["elapsed_time"] is None
    assert malformed["records"][0]["native_record"]["elapsed_time"] == 0


def test_workspace_metadata_12_13_and_hierarchical_parent_path():
    good = metadata(parent="/alice/work")
    error = metadata("bad.fa", uid=UUID_B) + ["object failure"]
    result = parse_workspace_records({"/alice/work": [good, error]}, operation="ls", requested_paths=["/alice/work/"])
    assert result["status"] == "partial"
    row = result["records"][0]
    assert row["native_metadata"] == good and row["parent_path"] == "/alice/work"
    assert row["object_path"] == "/alice/work/input.fa"
    assert row["listing_path"] == "/alice/work" and row["request_indices"] == [0]
    assert row["size"] == 0 and row["error"] is None
    assert result["records"][1]["error"] == "object failure"
    assert {"code": "native_object_error", "path": '$["/alice/work"][1][12]'} in result["diagnostics"]


def test_workspace_short_and_wrong_type_tuples_do_not_drop_neighbors():
    rows = [metadata(), ["partial", "contigs"], "bad"]
    result = parse_workspace_records(rows, operation="create")
    assert result["status"] == "partial" and len(result["records"]) == 3
    assert result["records"][0]["object_id"] == UUID_A
    assert result["records"][1]["name"] == "partial" and result["records"][1]["size"] is None
    assert result["records"][2]["native_record"] == "bad"
    assert {"code": "invalid_metadata_arity", "path": "$[1]"} in result["diagnostics"]
    wrong = metadata(size="0")
    malformed = parse_workspace_records([wrong], operation="create")
    assert malformed["records"][0]["size"] is None and malformed["native"][0][6] == "0"


def test_unordered_create_ancestors_and_duplicate_requested_paths():
    rows = [metadata("new", kind="folder", uid=UUID_B),
            metadata(parent="/alice/work/new/"), metadata("second.fa", uid="33333333-3333-4333-8333-333333333333")]
    paths = ["/alice/work/second.fa", "/alice/work/new/input.fa", "/alice/work/new/input.fa"]
    result = parse_workspace_records(rows, operation="create", requested_paths=paths)
    assert result["status"] == "ok"
    assert [row["request_indices"] for row in result["records"]] == [[], [1, 2], [0]]
    assert result["records"][0]["requested_path"] is None
    assert result["records"][1]["request_index"] is None
    assert result["records"][2]["requested_path"] == paths[0]
    assert result["native"] == rows


def test_create_ambiguous_same_path_and_omitted_object_remain_qualified():
    rows = [metadata(), metadata(uid=UUID_B)]
    result = parse_workspace_records(rows, operation="create", requested_paths=["/alice/work/input.fa"])
    assert result["status"] == "invalid" and "ambiguous_created_object" in codes(result)
    missing = parse_workspace_records([], operation="create", requested_paths=["/alice/work/existing-folder"])
    assert missing["status"] == "invalid" and codes(missing) == {"requested_object_not_returned"}
    assert "native_object_error" not in codes(missing)


def test_get_preserves_positions_missing_data_empty_data_and_shock_url():
    shock = "https://shock.example.org/node/44444444-4444-4444-8444-444444444444"
    rows = [[metadata()], [metadata("empty.txt", uid=UUID_B), ""],
            [metadata("remote.fa", shock=shock), shock]]
    paths = ["/alice/work/input.fa", "/alice/work/empty.txt", "/alice/work/remote.fa"]
    result = parse_workspace_records(rows, operation="get", requested_paths=paths)
    assert result["status"] == "ok"
    assert [row["request_index"] for row in result["records"]] == [0, 1, 2]
    assert [row["content_kind"] for row in result["records"]] == ["not_returned", "inline_text", "shock_url"]
    assert result["records"][0]["content"] is None and result["records"][1]["content"] == ""
    assert result["records"][2]["content"] == shock and result["records"][2]["shock_url"] == shock
    assert "file_bytes" not in result["records"][2]


def test_get_checks_path_uuid_and_cardinality_without_reordering():
    wrong = parse_workspace_records([[metadata("other.fa")]], operation="get", requested_paths=["/alice/work/input.fa", "/alice/work/missing.fa"])
    assert {"response_count_mismatch", "requested_object_path_mismatch", "requested_object_not_returned"} <= codes(wrong)
    assert wrong["records"][0]["object_path"] == "/alice/work/other.fa"
    by_uuid = parse_workspace_records([[metadata()]], operation="get", requested_paths=[UUID_A.upper()])
    assert by_uuid["status"] == "ok"
    unknown_ws = parse_workspace_records([[metadata()]], operation="get", requested_paths=["/_uuid/" + UUID_B + "/input.fa"])
    assert "workspace_uuid_mapping_unavailable" in codes(unknown_ws)


def test_download_urls_keep_native_null_and_indexed_invalid_values():
    url = "https://workspace.example.org/download/key/input.fa"
    result = parse_workspace_records([url, None, 0], operation="get_download_url", requested_paths=["/a/w/a", "/a/w/b", "/a/w/c"])
    assert result["status"] == "partial" and len(result["records"]) == 3
    assert result["records"][1]["download_url"] is None and result["records"][1]["status"] == "ok"
    assert result["records"][2]["native_record"] == 0
    assert {"code": "invalid_download_url", "path": "$[2]"} in result["diagnostics"]
    assert "expires_at" not in result["records"][0]


def test_listing_missing_empty_directories_does_not_invent_missing_pages():
    result = parse_workspace_records({}, operation="ls", requested_paths=["/alice/work/empty"])
    assert result == {"status": "ok", "records": [], "native": {}, "diagnostics": []}


def test_minhash_is_a_single_synchronous_native_value_not_a_task():
    raw = (STUDY / "sources/Mash/test/ref/genomes.dist").read_text().splitlines()[0].split("\t")
    # Upstream Mash values in an explicitly synthetic BV-BRC envelope.  The
    # synthetic reference ID does not turn this into a native BV-BRC result.
    value = [["83333.1", *raw[2:5]], ["83333.1", 0, "0", "0/0"]]
    result = decode({"version": "1.1", "id": "corr-1", "result": [value]}, method="Minhash.compute_genome_distance_for_genome2")
    assert result["status"] == "ok" and result["value"] == value
    assert result["value"][0][-1] == "41/1000"
    assert "task_id" not in result


def test_pure_functions_perform_no_network_or_mutation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network operation in pure protocol")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    for method, params in REQUESTS:
        prepare_rpc_request(method, params, request_id="x")
    value = [[metadata(), "ACGT"]]
    before = deepcopy(value)
    parsed = parse_workspace_records(value, operation="get", requested_paths=["/alice/work/input.fa"])
    parsed["records"][0]["native_record"][0][0] = "changed"
    assert value == before
    parse_task_records({"id": 1}, operation="start_app2")
    assert decode({"version": "1.1", "id": "corr-1", "result": [[]]})["status"] == "ok"
