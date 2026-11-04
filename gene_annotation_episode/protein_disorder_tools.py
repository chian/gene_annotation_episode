"""Ordinary disorder API work and authenticated stored-result selection.

The existing supplied-data owner alone parses and calculates disorder values.
One owned worker may send one selected POST. Its HTTP observations authenticate
transport, never the service's scientific implementation or model calibration.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlencode

from . import protein_disorder_measurements as core
from . import protein_disorder_result_contracts as contracts
from . import molecular_sequence_result_contracts as stored
from . import native_lifecycle
from .acquisition import AcquisitionError, PublicClients
from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, identity
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import (
    MolecularOperationUnpublished, _publication_bytes, _recorded_molecular_action_details,
    _recorded_molecular_producer_details, authenticate_molecular_invocation, retain_molecular_publication,
)
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import _identity, _metadata
from .reference_edit_outcome_tools import _context, _invocation


TOOL = contracts.TOOL
WORKER_OPERATION = "protein_disorder"
REQUEST_VERSION = "ordinary_protein_disorder_worker_request_v1"
RESULT_VERSION = "ordinary_protein_disorder_worker_result_v1"
TRANSPORT_VERSION = "ordinary_protein_disorder_transport_v1"
INTENT_VERSION = "ordinary_protein_disorder_intent_v1"
CONTROL_VERSION = "ordinary_protein_disorder_publication_v1"
_ROLES = ("native_response", "transport", "sheet", "components")


def _require(condition, code):
    if not condition:
        raise ContractError("protein_disorder_" + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "closed_shape_required")


def _copy(value):
    return stored.copy_json(value)


def _same(left, right):
    return canonical(left) == canonical(right)


def _json_value(value):
    """Preserve the JSON meaning of observed HTTP header pairs, including order."""
    return json.loads(json.dumps(value, allow_nan=False))


def protein_disorder_tool_contract():
    return dict(resources="api", invocation_route=dict(kind="direct"),
        input_schema=contracts.protein_disorder_result_schema("Arguments"),
        description=("Request one IUPred2A long-mode disorder response for the explicitly supplied protein string, "
            "retaining original characters and ASCII-letter cleaning with its original case. Select stored residue, "
            "region and summary fields with their separate row and input populations. Alternatively calculate the "
            "retained original Sheet again or read selected retained values without an API request. Scores are "
            "dimensionless predictor outputs, not function correctness probabilities. Observed HTTP transfer does "
            "not authenticate scientific service execution; missing responses and native logs remain unavailable."))


def _input(sheet):
    _require(type(sheet) is dict and sheet.get("schema") == core.SHEET_SCHEMA
        and type(sheet.get("inputs")) is dict, "sheet_required")
    return {key: deepcopy(sheet["inputs"][key]) for key in
        ("protein_sequence", "threshold", "input_ref", "input_mapping")}


def _post(arguments, timeout_seconds):
    _require(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
        and timeout_seconds > 0, "http_timeout_required")
    form = dict(seq="".join(character for character in arguments["protein_sequence"] if character in core._ASCII),
        iupred2="long", anchor2="no")
    body = urlencode(form).encode("ascii")
    return dict(method="POST", url=contracts.ENDPOINT, form=form, body_hex=body.hex(),
        body_sha256=hashlib.sha256(body).hexdigest(), body_size_bytes=len(body),
        max_bytes=arguments["max_bytes"], timeout_seconds=timeout_seconds,
        follow_redirects=False, content_type="application/x-www-form-urlencoded")


def _request(arguments, invocation, directory, *, sheet=None, timeout_seconds=None):
    arguments = contracts.validate_ordinary_disorder_arguments(arguments)
    _require(arguments["mode"] != "read_stored", "worker_mode_invalid")
    original = (dict(protein_sequence=arguments["protein_sequence"], threshold=arguments["threshold"],
        input_ref=None, input_mapping=None) if arguments["mode"] == "predict" else _input(sheet))
    return validate_disorder_worker_request(dict(version=REQUEST_VERSION, arguments=arguments,
        invocation=deepcopy(invocation), directory=str(directory), input=original,
        post=_post(arguments, timeout_seconds) if arguments["mode"] == "predict" else None,
        sheet=deepcopy(sheet)))


def validate_disorder_worker_request(value):
    value = _copy(value)
    _closed(value, "version arguments invocation directory input post sheet")
    _require(value["version"] == REQUEST_VERSION, "worker_request_required")
    arguments = contracts.validate_ordinary_disorder_arguments(value["arguments"])
    _require(arguments["mode"] in ("predict", "calculate_saved"), "worker_mode_invalid")
    invocation = value["invocation"]
    _closed(invocation, "run_id episode_id operation_key decision_index request_sha256 scope")
    index = invocation["decision_index"]
    _require(type(index) is int and index >= 0
        and all(type(invocation[key]) is str and invocation[key] for key in ("run_id", "episode_id"))
        and invocation["operation_key"] == f'{invocation["run_id"]}:{invocation["episode_id"]}:{index}'
        and type(invocation["request_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", invocation["request_sha256"]) is not None
        and type(invocation["scope"]) is dict, "invocation_conflict")
    _require(type(value["directory"]) is str, "worker_directory_conflict")
    directory = Path(value["directory"])
    _require(directory.is_absolute() and str(directory) == value["directory"] and ".." not in directory.parts
        and directory.parts[-4:] == ("cache", "molecular-measurements", digest(invocation["operation_key"]), "worker"),
        "worker_directory_conflict")
    _closed(value["input"], "protein_sequence threshold input_ref input_mapping")
    if arguments["mode"] == "predict":
        _require(value["sheet"] is None and _same(value["input"], dict(protein_sequence=arguments["protein_sequence"],
            threshold=arguments["threshold"], input_ref=None, input_mapping=None)), "inline_input_conflict")
        _closed(value["post"], "method url form body_hex body_sha256 body_size_bytes max_bytes timeout_seconds follow_redirects content_type")
        _require(_same(value["post"], _post(arguments, value["post"]["timeout_seconds"])), "post_request_conflict")
    else:
        _require(value["post"] is None and _same(value["input"], _input(value["sheet"])), "saved_sheet_conflict")
    return value


def _validate_transport(value, request):
    value = _copy(value)
    _closed(value, "version state post snapshot response_hex decode_state response_text failure")
    _require(value["version"] == TRANSPORT_VERSION and _same(value["post"], request["post"]), "transport_request_conflict")
    if request["post"] is None:
        _require(value == dict(version=TRANSPORT_VERSION, state="not_requested", post=None,
            snapshot=None, response_hex=None, decode_state="missing", response_text=None, failure=None),
            "saved_transport_conflict")
        return value
    if value["failure"] is not None:
        _closed(value["failure"], "code phase exception_type message")
        _require(all(type(value["failure"][key]) is str for key in ("code", "exception_type", "message"))
            and (value["failure"]["phase"] is None or type(value["failure"]["phase"]) is str), "transport_failure_invalid")
    if value["snapshot"] is None:
        _require(value["state"] == "request_failed" and value["failure"] is not None
            and value["response_hex"] is value["response_text"] is None and value["decode_state"] == "missing",
            "transport_missing_conflict")
        return value
    _require(value["state"] == "response_received" and type(value["response_hex"]) is str
        and re.fullmatch(r"(?:[0-9a-f]{2})*", value["response_hex"]) is not None, "response_bytes_required")
    snapshot, post = value["snapshot"], request["post"]
    _closed(snapshot, "service url request retrieved_at media_type transport")
    raw = bytes.fromhex(value["response_hex"])
    _require(len(raw) <= post["max_bytes"] and snapshot["service"] == "iupred2a"
        and snapshot["url"] == contracts.ENDPOINT and snapshot["request"] == {}
        and type(snapshot["retrieved_at"]) is str and type(snapshot["media_type"]) is str,
        "response_identity_conflict")
    transport = snapshot["transport"]
    _require(type(transport) is dict and type(transport.get("request")) is dict, "http_request_required")
    observed = transport["request"]
    headers = observed.get("headers")
    _require(type(headers) is dict and all(type(key) is str and type(child) is str for key, child in headers.items()),
        "http_request_headers_required")
    content_types = [child for key, child in headers.items() if key.lower() == "content-type"]
    _require(observed.get("method") == "POST" and observed.get("url") == post["url"]
        and observed.get("body_sha256") == post["body_sha256"]
        and observed.get("body_base64") == base64.b64encode(bytes.fromhex(post["body_hex"])).decode("ascii")
        and content_types == [post["content_type"]]
        and _same(transport.get("request_policy"), dict(timeout_seconds=post["timeout_seconds"], automatic_redirects=False)),
        "http_request_conflict")
    count = len(raw)
    retained, observed_count, limit = (transport.get(key) for key in
        ("retained_body_bytes", "observed_body_bytes", "response_byte_limit"))
    _require(type(retained) is int and retained == count and type(observed_count) is int and observed_count >= count
        and type(limit) is int and limit == post["max_bytes"]
        and (transport.get("body_complete") is not True or observed_count == count), "http_capture_count_conflict")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        _require(value["decode_state"] == "invalid_utf8" and value["response_text"] is None, "response_decode_conflict")
    else:
        _require(value["decode_state"] == "decoded" and value["response_text"] == text, "response_decode_conflict")
    return value


def _native_outcome(transport):
    if transport["response_text"] is None or transport["snapshot"] is None:
        return "failed"
    observed = transport["snapshot"]["transport"]
    status = observed.get("status")
    if type(status) is not int or not 200 <= status < 300:
        return "failed"
    count = len(bytes.fromhex(transport["response_hex"]))
    declared = observed.get("declared_body_bytes")
    return ("completed" if observed.get("body_complete") is True
        and type(observed.get("retained_body_bytes")) is int and observed["retained_body_bytes"] == count
        and type(observed.get("observed_body_bytes")) is int and observed["observed_body_bytes"] == count
        and (declared is None or type(declared) is int and declared == count)
        and type(observed.get("response_byte_limit")) is int
        and observed["response_byte_limit"] == transport["post"]["max_bytes"]
        and observed.get("body_capture_failure") is None else "partial")


def _write_bytes(path, raw):
    try:
        descriptor = path.open("xb")
    except FileExistsError:
        with _regular(path) as stream:
            _require(stream.read() == raw, "immutable_bytes_conflict")
    else:
        with descriptor as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())


def _perform_post(request):
    """Seal the one actual response before any predictor-output interpretation."""
    post, directory = request["post"], Path(request["directory"])
    if post is None:
        return _validate_transport(dict(version=TRANSPORT_VERSION, state="not_requested", post=None,
            snapshot=None, response_hex=None, decode_state="missing", response_text=None, failure=None), request)
    marker = directory / "post-started.json"
    _require(not marker.exists(), "post_already_attempted")
    _immutable(marker, dict(invocation=request["invocation"], post=post))
    snapshot, failure = None, None
    try:
        snapshot = PublicClients(ncbi_email=None)._http("iupred2a", post["url"], {}, "text/plain",
            body=bytes.fromhex(post["body_hex"]), content_type=post["content_type"],
            max_bytes=post["max_bytes"], timeout_seconds=post["timeout_seconds"], follow_redirects=False)
    except Exception as error:
        snapshot = getattr(error, "snapshot", None)
        failure = dict(code=error.code if isinstance(error, AcquisitionError) else "provider_request_failed",
            phase=getattr(error, "phase", None), exception_type=type(error).__module__ + "." + type(error).__name__,
            message=str(error))
    native = None if snapshot is None else snapshot.content
    if native is not None:
        _require(type(native) is bytes, "response_bytes_required")
        _write_bytes(directory / "native-response.bin", native)
    value = dict(version=TRANSPORT_VERSION, state="request_failed" if snapshot is None else "response_received",
        post=post, snapshot=None if snapshot is None else _json_value({key: child for key, child in asdict(snapshot).items()
            if key != "content"}), response_hex=None if native is None else native.hex(),
        decode_state="missing", response_text=None, failure=failure)
    if native is not None:
        try:
            value["response_text"] = native.decode("utf-8")
            value["decode_state"] = "decoded"
        except UnicodeError:
            value["decode_state"] = "invalid_utf8"
    _immutable(directory / "transport-seal.json", value)
    return _validate_transport(value, request)


def run_disorder_tool_request(request):
    """Store-free: one POST at most and one unchanged calculator invocation."""
    request = validate_disorder_worker_request(request)
    transport = _perform_post(request)
    sheet, components, error = request["sheet"], None, None
    calculation = dict(state="not_requested", call_count=0)
    try:
        if request["post"] is not None:
            sheet = core.build_disorder_sheet(None, **request["input"], native_response=transport["response_text"],
                native_log=None, native_outcome=_native_outcome(transport))
        calculation = dict(state="failed", call_count=1)
        components = core.calculate_disorder_components(sheet)
        calculation = dict(state="completed", call_count=1)
    except Exception as problem:
        calculation = dict(state="failed", call_count=calculation["call_count"])
        error = dict(exception_type=type(problem).__module__ + "." + type(problem).__name__, message=str(problem))
    return validate_disorder_worker_result(dict(version=RESULT_VERSION, request=request, transport=transport,
        sheet=sheet, components=components, calculation=calculation, error=error), request=request)


def validate_disorder_worker_result(value, *, request=None):
    value = _copy(value)
    _closed(value, "version request transport sheet components calculation error")
    _require(value["version"] == RESULT_VERSION, "worker_result_required")
    selected = validate_disorder_worker_request(value["request"])
    _require(request is None or _same(selected, request), "worker_request_conflict")
    transport = _validate_transport(value["transport"], selected)
    if value["sheet"] is not None:
        _require(_same(_input(value["sheet"]), selected["input"]), "worker_input_conflict")
        if selected["post"] is None:
            _require(_same(value["sheet"], selected["sheet"]), "worker_sheet_conflict")
        else:
            inputs = value["sheet"]["inputs"]
            _require(inputs["native_csv"] is inputs["native_log"] is None
                and inputs["native_response"] == transport["response_text"]
                and inputs["native_outcome"] == _native_outcome(transport), "worker_native_conflict")
    _closed(value["calculation"], "state call_count")
    if value["components"] is not None:
        _require(value["calculation"] == dict(state="completed", call_count=1)
            and type(value["calculation"]["call_count"]) is int and value["error"] is None, "calculation_conflict")
        contracts.ordinary_disorder_packet(arguments=selected["arguments"], sheet=value["sheet"], components=value["components"])
    else:
        _require(value["calculation"]["state"] == "failed" and (value["calculation"]["call_count"] is None
            or type(value["calculation"]["call_count"]) is int and value["calculation"]["call_count"] in (0, 1)),
            "calculation_conflict")
        _closed(value["error"], "exception_type message")
        _require(all(type(child) is str for child in value["error"].values()), "worker_error_invalid")
    return value


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store, value["artifact_ref"])
    _require((metadata["sha256"], metadata["size"]) == (value["sha256"], value["size_bytes"]), "file_identity_conflict")
    return value


def _source_admission(registry, context, reader, reference, cutoff):
    item = reader(context, reference, "source", source_metadata_only=True)
    _require(item.get("failure") is None and item.get("selection") == dict(reference=reference, namespace="source"),
        "source_not_received")
    return EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_disorder_").source_admission_before(
        context, reference, cutoff)


def _cutoff(registry, context):
    active = registry._current_invocation.get()
    if active is not None and active[0] is context:
        return _invocation(context, active[4])["decision_index"]
    return registry.store.db.execute("SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions "
        "WHERE run_id=? AND episode_id=?", (context.run_id, context.episode_id)).fetchone()[0]


def _validate_intent(value):
    value = _copy(value)
    _closed(value, "version arguments invocation policy request source_admission original_source")
    _require(value["version"] == INTENT_VERSION, "intent_required")
    arguments = contracts.validate_ordinary_disorder_arguments(value["arguments"])
    request = validate_disorder_worker_request(value["request"])
    _require(arguments["mode"] != "read_stored" and _same(arguments, request["arguments"])
        and _same(value["invocation"], request["invocation"])
        and _same(LocalJobPolicy(**value["policy"]).to_dict(), value["policy"]), "intent_request_conflict")
    if arguments["mode"] == "predict":
        _require(value["source_admission"] is value["original_source"] is None, "inline_source_conflict")
    else:
        original = value["original_source"]
        _closed(original, "source_ref record_sha256 sheet_file")
        _require(original["source_ref"] == arguments["result_ref"]
            and type(original["record_sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", original["record_sha256"]) is not None,
            "original_source_conflict")
        _identity(original["sheet_file"])
        _require(type(value["source_admission"]) is dict, "source_admission_required")
    return value


def _dispatch(registry, intent, directory):
    path = directory / "execution-selection.json"
    if any((directory / name).exists() for name in ("post-started.json", "transport-seal.json", "native-response.bin")):
        _require((directory / "native-handle.json").is_file(), "original_worker_handle_missing")
    if path.exists():
        selected = decode_json(path.read_bytes())
        _require(selected["version"] == "ordinary_molecular_execution_v1" and selected["cwd"] == str(directory)
            and _same(selected["policy"], intent["policy"])
            and _same(selected["request"], dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"])))
            and selected["command"] == [selected["python"]["path"], "-m", "gene_annotation_episode.sequence_worker",
                str(directory / "worker-request.json"), str(directory / "worker-result.json")], "original_worker_selection_conflict")
    else:
        _require(_same(registry.local_job_policy.to_dict(), intent["policy"]), "original_unstarted_policy_conflict")


def _worker_control(value, intent):
    value = _copy(value)
    _closed(value, "selection handle observation native_request native_request_raw result result_hex")
    selected, handle, observation = value["selection"], value["handle"], value["observation"]
    _closed(selected, "version command cwd environment policy request python implementation_files")
    directory = Path(intent["request"]["directory"])
    command = [selected["python"]["path"], "-m", "gene_annotation_episode.sequence_worker",
        str(directory / "worker-request.json"), str(directory / "worker-result.json")]
    _require(selected["version"] == "ordinary_molecular_execution_v1" and selected["command"] == handle["command"] == command
        and selected["cwd"] == handle["cwd"] == str(directory)
        and handle["stdout"] == str(directory / "stdout") and handle["stderr"] == str(directory / "stderr")
        and _same(selected["request"], dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"])))
        and _same(selected["policy"], intent["policy"]) and _same(handle["metadata"]["policy"], intent["policy"])
        and _same(observation["metadata"]["policy"], intent["policy"])
        and observation["terminal"] is True and observation["quiescent"] is True, "worker_control_conflict")
    paths = handle["paths"]
    _require(type(paths) is dict and all(type(path) is str and Path(path).parent == directory for path in paths.values()),
        "worker_handle_conflict")
    raw = value["native_request_raw"]
    _require(type(raw) is str and hashlib.sha256(raw.encode()).hexdigest() == handle["request_sha256"]
        and _same(decode_json(raw.encode()), value["native_request"])
        and _same(value["native_request"], dict(command=command, cwd=str(directory), file_bytes=intent["policy"]["scratch_bytes"],
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None,
            env=selected["environment"])), "worker_handle_conflict")
    encoded = value["result_hex"]
    _require(encoded is None or type(encoded) is str and re.fullmatch(r"(?:[0-9a-f]{2})*", encoded) is not None,
        "worker_result_bytes_conflict")
    if value["result"] is not None:
        _require(encoded is not None and _same(decode_json(bytes.fromhex(encoded)), value["result"]), "worker_result_bytes_conflict")
        validate_disorder_worker_result(value["result"], request=intent["request"])
    return value


def _worker_record(work, intent, directory):
    _require(Path(work.output_path) == directory / "worker-result.json", "worker_output_conflict")
    handle = native_lifecycle.NativeJobHandle(directory / "native-handle.json")
    observation = native_lifecycle.status(handle)
    if not (observation["terminal"] and observation["quiescent"]):
        raise MolecularOperationUnpublished("protein_disorder_worker_attempt_unconfirmed")
    _post_completion_gate(directory, intent["request"])
    _require(_same({key: child for key, child in work.metadata.items() if key != "molecular_failure"}, observation["metadata"]),
        "worker_metadata_conflict")
    body = handle.read()
    with _regular(body["paths"]["request"]) as stream:
        raw = stream.read()
    result, encoded = None, None
    if Path(work.output_path).is_file():
        with _regular(work.output_path) as stream:
            content = stream.read()
        encoded = content.hex()
        try:
            result = validate_disorder_worker_result(decode_json(content), request=intent["request"])
        except (ValueError, TypeError, KeyError):
            pass
    with _regular(directory / "worker-request.json") as stream:
        _require(_same(decode_json(stream.read()), dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"]))),
            "worker_request_conflict")
    if result is not None and result["transport"]["post"] is not None:
        with _regular(directory / "post-started.json") as stream:
            _require(_same(decode_json(stream.read()), dict(invocation=intent["invocation"], post=intent["request"]["post"])),
                "post_reservation_conflict")
        with _regular(directory / "transport-seal.json") as stream:
            _require(_same(decode_json(stream.read()), result["transport"]), "transport_seal_conflict")
        if result["transport"]["response_hex"] is not None:
            with _regular(directory / "native-response.bin") as stream:
                _require(stream.read().hex() == result["transport"]["response_hex"], "response_bytes_conflict")
    return _worker_control(dict(selection=decode_json((directory / "execution-selection.json").read_bytes()),
        handle=body, observation=observation, native_request=decode_json(raw), native_request_raw=raw.decode(),
        result=result, result_hex=encoded), intent)


def _post_completion_gate(directory, request):
    """A terminal worker does not establish the outcome of an unsealed POST."""
    marker = directory / "post-started.json"
    if request["post"] is not None and marker.exists():
        with _regular(marker) as stream:
            _require(_same(decode_json(stream.read()), dict(invocation=request["invocation"], post=request["post"])),
                "post_reservation_conflict")
        if not (directory / "transport-seal.json").is_file():
            raise MolecularOperationUnpublished("protein_disorder_post_outcome_unconfirmed")


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool" and source.get("provider") == TOOL
        and source.get("version") == contracts.SOURCE_VERSION and "operand_refs" not in source, "producer_required")
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = contracts.validate_ordinary_disorder_arguments(producer["arguments"])
    public = contracts.validate_ordinary_disorder_return(producer["outcome"]["result"])
    _require(arguments["mode"] in ("predict", "calculate_saved") and public["source_ref"] == source_ref
        and public["selection"] == arguments["selection"] and producer["outcome"]["record_refs"] == [source_ref]
        and producer["outcome"]["changed_record_refs"] == [source_ref], "publication_conflict")
    _require(source.get("parent_source_refs") == ([arguments["result_ref"]] if arguments["mode"] == "calculate_saved" else []),
        "parent_sources_conflict")
    return dict(source=source, producer=producer, public=public)


def _saved_input(registry, intent, *, seen=()):
    if intent["arguments"]["mode"] == "predict":
        return
    invocation, original = intent["invocation"], intent["original_source"]
    context = _context(registry.store, invocation)
    _require(digest(registry.store.get(original["source_ref"])) == original["record_sha256"], "original_source_conflict")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_disorder_")
    _require(_same(records.source_admission_before(context, original["source_ref"], invocation["decision_index"]),
        intent["source_admission"]), "source_admission_conflict")
    parent = _control(registry, _metadata_publication(registry, original["source_ref"]), seen)
    file = parent["files"]["sheet"]["file"]
    _require(file is not None and original["sheet_file"] == file, "saved_sheet_identity_conflict")
    sheet = parent["worker"]["result"]["sheet"]
    _require(_same(intent["request"]["sheet"], sheet), "saved_sheet_conflict")


def _control(registry, publication, seen=()):
    source, producer = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = (*seen, source["id"])
    control = decode_json(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, "version intent worker files packet_ref")
    intent = _validate_intent(control["intent"])
    _require(control["version"] == CONTROL_VERSION and control["packet_ref"] == source["artifact_ref"]
        and _same(intent["arguments"], producer["arguments"])
        and _same(intent["invocation"], producer["invocation"]), "publication_control_conflict")
    _saved_input(registry, intent, seen=seen)
    worker = _worker_control(control["worker"], intent)
    result = worker["result"]
    _require(result is not None and result["components"] is not None, "publication_result_unavailable")
    _closed(control["files"], "native_response transport sheet components")
    native = result["transport"]
    contents = dict(native_response=None if native["response_hex"] is None else bytes.fromhex(native["response_hex"]),
        transport=None if intent["arguments"]["mode"] == "calculate_saved" else canonical(native).encode(),
        sheet=canonical(result["sheet"]).encode(), components=canonical(result["components"]).encode())
    for role, state in control["files"].items():
        stored.validate_file_state(state)
        raw = contents[role]
        if raw is None:
            _require(state == stored.empty_file_state("not_requested" if intent["arguments"]["mode"] == "calculate_saved"
                else "producer_unavailable"), "file_state_conflict")
        else:
            file = _file(registry, state["file"])
            _require(state["state"] == "retained_undeclared"
                and file["format"] == ("bytes" if role == "native_response" else "json")
                and state["declared"] is state["failure"] is None
                and file["sha256"] == hashlib.sha256(raw).hexdigest() and file["size_bytes"] == len(raw), "file_bytes_conflict")
    expected = list(dict.fromkeys(control["files"][role]["file"]["artifact_ref"] for role in _ROLES
        if control["files"][role]["file"] is not None))
    _require(source.get("auxiliary_artifact_refs") == expected, "private_files_conflict")
    packet = contracts.ordinary_disorder_packet(arguments=intent["arguments"], sheet=result["sheet"], components=result["components"])
    _require(_same(packet, {key: child for key, child in publication["public"].items() if key != "source_ref"}),
        "packet_control_conflict")
    return control


def read_protein_disorder_publication(registry, context, reader, source_ref, *, require_sheet=False,
        require_numeric=False, before_decision_index=None, recovery_operation_key=None):
    with registry.store.read_snapshot():
        EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_disorder_").authenticate(context)
        publication = _metadata_publication(registry, source_ref,
            recovery_context=context if recovery_operation_key else None, recovery_operation_key=recovery_operation_key)
        invocation = publication["producer"]["invocation"]
        own = recovery_operation_key == invocation["operation_key"] and (context.run_id, context.episode_id) == (
            invocation["run_id"], invocation["episode_id"])
        admission = None if own else _source_admission(registry, context, reader, source_ref,
            _cutoff(registry, context) if before_decision_index is None else before_decision_index)
        packet = contracts.validate_ordinary_disorder_packet(decode_json(_publication_bytes(registry.store,
            publication["source"]["artifact_ref"])))
        _require(_same(contracts.project_ordinary_disorder_return(packet, source_ref), publication["public"]), "public_packet_conflict")
        publication.update(packet=packet, stored=publication["public"], admission_kind="source_only", source_admission=admission,
            control=None, sheet=None, components=None)
        if require_sheet or require_numeric:
            control = _control(registry, publication)
            result = control["worker"]["result"]
            sheet = decode_json(_publication_bytes(registry.store, control["files"]["sheet"]["file"]["artifact_ref"]))
            _require(_same(sheet, result["sheet"]), "saved_sheet_conflict")
            components = None
            if require_numeric:
                components = decode_json(_publication_bytes(registry.store, control["files"]["components"]["file"]["artifact_ref"]))
                _require(_same(components, result["components"]), "saved_components_conflict")
                contracts.ordinary_disorder_packet(arguments=publication["producer"]["arguments"], sheet=sheet, components=components)
            publication.update(control=control, sheet=sheet, components=components)
        return publication


def _read_selected(publication, arguments):
    if publication["public"]["selection"] == arguments["selection"]:
        return publication["public"]
    packet = contracts.ordinary_disorder_packet(arguments=arguments,
        sheet=publication["sheet"], components=publication["components"])
    return contracts.project_ordinary_disorder_return(packet, publication["source"]["id"])


def _retained(registry, raw, *, format, media_type):
    reference = registry.store.artifact(raw, media_type)
    metadata = _metadata(registry.store, reference)
    file = dict(artifact_ref=reference, sha256=metadata["sha256"], size_bytes=metadata["size"], format=format)
    return dict(state="retained_undeclared", file=file, declared=None,
        observed_identity=dict(sha256=file["sha256"], size_bytes=file["size_bytes"]), failure=None)


def _retain_protein_disorder_publication(registry, prepared):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    intent = _validate_intent(prepared["intent"])
    _saved_input(registry, intent)
    worker = _worker_control(prepared["worker"], intent)
    result = worker["result"]
    _require(result is not None and result["components"] is not None, "publication_result_unavailable")
    transport = result["transport"]
    state = "not_requested" if intent["arguments"]["mode"] == "calculate_saved" else "producer_unavailable"
    files = dict(native_response=stored.empty_file_state(state), transport=stored.empty_file_state(state),
        sheet=_retained(registry, canonical(result["sheet"]).encode(), format="json", media_type="application/json"),
        components=_retained(registry, canonical(result["components"]).encode(), format="json", media_type="application/json"))
    if intent["arguments"]["mode"] == "predict":
        files["transport"] = _retained(registry, canonical(transport).encode(), format="json", media_type="application/json")
        if transport["response_hex"] is not None:
            files["native_response"] = _retained(registry, bytes.fromhex(transport["response_hex"]), format="bytes",
                media_type=transport["snapshot"]["media_type"])
    packet = contracts.ordinary_disorder_packet(arguments=intent["arguments"], sheet=result["sheet"], components=result["components"])
    packet_ref = registry.store.artifact(canonical(packet), "application/json")
    control = dict(version=CONTROL_VERSION, intent=intent, worker=worker, files=files, packet_ref=packet_ref)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    auxiliaries = list(dict.fromkeys(files[role]["file"]["artifact_ref"] for role in _ROLES if files[role]["file"] is not None))
    source = registry.store.put("source", dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=contracts.SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[intent["arguments"]["result_ref"]] if intent["arguments"]["mode"] == "calculate_saved" else [],
        auxiliary_artifact_refs=auxiliaries), origin="tool")
    return dict(source=source, public=contracts.project_ordinary_disorder_return(packet, source["id"]), control=control)


def _outcome(arguments, key, public):
    partial = public["values"]["context"]["status"] != "complete" or any(
        row["value_state"] in ("path_missing", "invalid_type") for row in public["values"]["rows"])
    return dict(status="partial" if partial else "completed", operation_ref=identity("operation", dict(
        key=key, name=TOOL, arguments=arguments)), record_refs=[public["source_ref"]],
        changed_record_refs=[] if arguments["mode"] == "read_stored" else [public["source_ref"]], result=public,
        feedback=None if not partial else dict(category="representation", code="protein_disorder_partial", source_ref=public["source_ref"]))


def read_protein_disorder_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = contracts.validate_ordinary_disorder_arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial"), "action_result_unavailable")
    public = contracts.validate_ordinary_disorder_return(outcome["result"])
    _require(outcome["record_refs"] == [public["source_ref"]], "action_source_conflict")
    publication = read_protein_disorder_publication(registry, context, reader, public["source_ref"],
        before_decision_index=details["invocation"]["decision_index"],
        recovery_operation_key=operation_key if arguments["mode"] != "read_stored" else None)
    if arguments["mode"] == "read_stored":
        _require(arguments["result_ref"] == public["source_ref"] and outcome["changed_record_refs"] == [], "action_source_conflict")
        if publication["public"]["selection"] != arguments["selection"]:
            publication = read_protein_disorder_publication(registry, context, reader, public["source_ref"],
                require_numeric=True, before_decision_index=details["invocation"]["decision_index"])
        expected = _read_selected(publication, arguments)
    else:
        _require(publication["producer"]["invocation"]["operation_key"] == operation_key, "action_source_conflict")
        expected = publication["public"]
    _require(_same(expected, public), "action_result_conflict")
    return public


async def execute_protein_disorder_tool(registry, arguments, *, scope, operation_key, authority):
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / "cache" / "molecular-measurements" / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed", "partial"):
                _require(_same(read_protein_disorder_action_result(registry, context, arguments, operation_key, reader=reader),
                    outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("invalid", "unavailable", "failed") and outcome.get("result") is None
                    and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        pending = False
        try:
            arguments = contracts.validate_ordinary_disorder_arguments(arguments)
            if arguments["mode"] == "read_stored":
                publication = read_protein_disorder_publication(registry, context, reader, arguments["result_ref"],
                    before_decision_index=invocation["decision_index"])
                if publication["public"]["selection"] != arguments["selection"]:
                    publication = read_protein_disorder_publication(registry, context, reader, arguments["result_ref"],
                        require_numeric=True, before_decision_index=invocation["decision_index"])
                public = _read_selected(publication, arguments)
            else:
                intent_path = directory / "protein-disorder-intent.json"
                pending = intent_path.exists()
                selected = _directory(directory / "worker")
                if pending:
                    intent = _validate_intent(decode_json(intent_path.read_bytes()))
                    _require(_same(intent["arguments"], arguments) and _same(intent["invocation"], invocation)
                        and intent["request"]["directory"] == str(selected), "original_intent_conflict")
                else:
                    publication = (None if arguments["mode"] == "predict" else read_protein_disorder_publication(
                        registry, context, reader, arguments["result_ref"], require_sheet=True,
                        before_decision_index=invocation["decision_index"]))
                    request = _request(arguments, invocation, selected,
                        sheet=None if publication is None else publication["sheet"],
                        timeout_seconds=registry.clients.timeout if publication is None else None)
                    original = (None if publication is None else dict(source_ref=arguments["result_ref"],
                        record_sha256=digest(publication["source"]), sheet_file=publication["control"]["files"]["sheet"]["file"]))
                    intent = _validate_intent(dict(version=INTENT_VERSION, arguments=arguments, invocation=invocation,
                        policy=registry.local_job_policy.to_dict(), request=request,
                        source_admission=None if publication is None else publication["source_admission"], original_source=original))
                    _saved_input(registry, intent)
                    _immutable(intent_path, intent)
                _saved_input(registry, intent)
                pending = True
                selected.mkdir(mode=0o700, exist_ok=True)
                _dispatch(registry, intent, selected)
                work = await registry._sequence_worker_async(WORKER_OPERATION, dict(request=intent["request"]),
                    directory=selected, owned_directory=selected)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                worker = _worker_record(work, intent, selected)
                with registry.store.transaction():
                    if worker["result"] is None or worker["result"]["components"] is None:
                        diagnostic = registry.store.artifact(canonical(dict(version="protein_disorder_worker_failure_v1",
                            intent=intent, worker=worker)), "application/json")
                        outcome = dict(status="failed", operation_ref=identity("operation", dict(
                            key=operation_key, name=TOOL, arguments=arguments)), record_refs=[], changed_record_refs=[], result=None,
                            feedback=dict(category="execution", code="protein_disorder_worker_failed", diagnostic_ref=diagnostic))
                    else:
                        public = retain_molecular_publication(registry, dict(intent=intent, worker=worker), tool_name=TOOL)["public"]
                        outcome = _outcome(arguments, operation_key, public)
                        if worker["observation"]["metadata"].get("native_returncode") != 0:
                            outcome.update(status="partial", feedback=dict(category="execution",
                                code="protein_disorder_worker_partial", source_ref=public["source_ref"]))
                    registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                return outcome
            with registry.store.transaction():
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if pending:
                raise MolecularOperationUnpublished("protein_disorder_original_action_unpublished") from error
            with registry.store.transaction():
                code = str(error)
                code = code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "protein_disorder_input_invalid"
                diagnostic = registry.store.artifact(canonical(dict(version="protein_disorder_diagnostic_v1",
                    exception_type=type(error).__module__ + "." + type(error).__name__, message=str(error))), "application/json")
                outcome = dict(status="unavailable" if isinstance(error, OSError) else "invalid",
                    operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
                    record_refs=[], changed_record_refs=[], result=None,
                    feedback=dict(category="arguments_or_reference", code=code, diagnostic_ref=diagnostic))
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ["TOOL", "WORKER_OPERATION", "REQUEST_VERSION", "RESULT_VERSION", "TRANSPORT_VERSION", "INTENT_VERSION",
    "CONTROL_VERSION", "protein_disorder_tool_contract", "validate_disorder_worker_request", "run_disorder_tool_request",
    "validate_disorder_worker_result", "execute_protein_disorder_tool", "read_protein_disorder_publication",
    "read_protein_disorder_action_result", "_retain_protein_disorder_publication"]
