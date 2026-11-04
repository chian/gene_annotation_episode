"""Ordinary supplied arsenic calculations with actual action and File custody.

The existing calibrated-signal reader and calculator own scientific meanings.
The common owned worker owns dispatch. This module creates no child episode,
instrument run, calibration fit, chemical assignment or reference permission.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from . import arsenic_speciation_result_contracts as contracts
from . import calibrated_signal_contracts as core
from . import calibrated_signal_sheet as inputs
from . import molecular_sequence_result_contracts as stored
from . import native_lifecycle
from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .materials import source_window_selection
from .molecular_measurement_tools import (
    MolecularOperationUnpublished, _publication_bytes, _recorded_molecular_action_details,
    _recorded_molecular_producer_details, authenticate_molecular_invocation, retain_molecular_publication,
)
from .molecular_sequence_input_contracts import (
    decode_molecular_sequence_input, input_record_digest, validate_molecular_sequence_received_input,
)
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import _identity, _metadata
from .reference_edit_outcome_tools import _context, _invocation


TOOL = contracts.TOOL
WORKER_OPERATION = "arsenic_speciation"
REQUEST_VERSION = "ordinary_arsenic_speciation_calculation_request_v1"
RESULT_VERSION = "ordinary_arsenic_speciation_calculation_result_v1"
INTENT_VERSION = "ordinary_arsenic_speciation_intent_v1"
CONTROL_VERSION = "ordinary_arsenic_speciation_publication_v1"


def _require(condition, code):
    if not condition:
        raise ContractError("arsenic_speciation_" + code)


def _closed(value, names):
    _require(type(value) is dict and set(value) == set(names.split()), "closed_shape_required")


def _same(left, right):
    return canonical(left) == canonical(right)


def arsenic_speciation_tool_contract():
    return dict(resources="local", invocation_route=dict(kind="direct"), input_schema=deepcopy(contracts.ARGUMENT_SCHEMA),
        description=("Calculate explicitly selected sample/species results from an explicitly received calibrated-signal "
            "JSON Sheet using supplied retention times, calibration, dilution, units and quantity bases. Retain ambiguous "
            "associations, censoring, separate populations and unpropagated uncertainty. Alternatively calculate a new "
            "selection from a retained result Sheet, read the original controlled values, or inspect the complete supplied "
            "input Sheet and original result selection without calculation or additional File grants. This "
            "ordinary tool neither operates HPLC-ICP-MS nor supplies experimental calibration or chemical-identity proof."))


def validate_arsenic_speciation_worker_request(value):
    value = core.copy_json(value)
    _closed(value, "version input_file sheet selection")
    _require(value["version"] == REQUEST_VERSION, "worker_request_required")
    file = _identity(value["input_file"])
    _require(file["format"] == "json", "json_file_required")
    sheet = core.validate_calibrated_signal_sheet(value["sheet"])
    core.validate_calibrated_signal_selection(value["selection"], sheet)
    return value


def validate_arsenic_speciation_worker_result(value, *, request=None):
    value = core.copy_json(value)
    _closed(value, "version request sheet components calculation failures error")
    _require(value["version"] == RESULT_VERSION, "worker_result_required")
    selected = validate_arsenic_speciation_worker_request(value["request"])
    _require(request is None or _same(selected, request), "worker_request_conflict")
    _require(_same(core.validate_calibrated_signal_sheet(value["sheet"]), selected["sheet"]), "worker_sheet_conflict")
    calculation = value["calculation"]
    _closed(calculation, "state call_count native_invocation")
    _require(calculation["native_invocation"] == "not_requested", "native_not_requested")
    if value["components"] is not None:
        components = core.validate_calibrated_signal_components_shape(value["components"])
        _require(_same(components["sheet"], value["sheet"]) and _same(components["selection"], selected["selection"])
            and calculation == dict(state="completed", call_count=1, native_invocation="not_requested")
            and type(calculation["call_count"]) is int and value["error"] is None, "worker_components_conflict")
    else:
        _require(calculation == dict(state="calculation_failed", call_count=None, native_invocation="not_requested"),
            "worker_calculation_conflict")
        _closed(value["error"], "exception_type message")
        _require(all(type(item) is str for item in value["error"].values()), "worker_error_invalid")
    _require(type(value["failures"]) is list, "worker_failures_invalid")
    for issue in value["failures"]:
        stored.validate_supplied_failure(issue)
        _require(issue["version"] == "molecular_sequence_supplied_failure_v1", "private_failure_required")
    return value


def run_arsenic_speciation_tool_request(request):
    """Store-free: one existing calculator call, with no source or File reads."""
    from .calibrated_signal_calculations import calculate_calibrated_signal_components
    request = validate_arsenic_speciation_worker_request(request)
    sheet = request["sheet"]
    components, error, failures = None, None, []
    try:
        components = calculate_calibrated_signal_components(sheet, selection=request["selection"])
    except Exception as problem:
        # A raised call has no retained return observation. Do not infer zero
        # or completion from the request, intent, or output-file existence.
        calculation = dict(state="calculation_failed", call_count=None, native_invocation="not_requested")
        failures.append(stored.supplied_failure("calculation_failed", "calculation", role="sheet"))
        error = dict(exception_type=type(problem).__module__ + "." + type(problem).__name__, message=str(problem))
    else:
        calculation = dict(state="completed", call_count=1, native_invocation="not_requested")
    return validate_arsenic_speciation_worker_result(dict(version=RESULT_VERSION, request=request, sheet=sheet,
        components=components, calculation=calculation, failures=failures, error=error), request=request)


def _file(registry, file):
    file = _identity(file)
    metadata = _metadata(registry.store, file["artifact_ref"])
    _require((metadata["sha256"], metadata["size"]) == (file["sha256"], file["size_bytes"]), "file_identity_conflict")
    return file


def _source_admission(registry, context, reader, reference, cutoff):
    received = reader(context, reference, "source", source_metadata_only=True)
    _require(received.get("failure") is None and received.get("selection") == dict(reference=reference, namespace="source"),
        "source_not_received")
    return EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="arsenic_speciation_").source_admission_before(
        context, reference, cutoff)


def _cutoff(registry, context):
    active = registry._current_invocation.get()
    if active is not None and active[0] is context:
        return _invocation(context, active[4])["decision_index"]
    return registry.store.db.execute("SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions "
        "WHERE run_id=? AND episode_id=?", (context.run_id, context.episode_id)).fetchone()[0]


def _input_admission(registry, context, selected, cutoff):
    record = registry.store.get(selected["reference"])
    _require(record.get("record_type") == selected["namespace"], "input_namespace_conflict")
    if selected["namespace"] == "source":
        immutable_record(record)
        artifact, representation, _ = source_window_selection(record, "original")
        _require(representation == "original", "original_file_required")
    else:
        artifact = selected["reference"]
    _metadata(registry.store, artifact)
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="arsenic_speciation_")
    records.authenticate(context)
    return artifact, records.file_admission_before(context, selected["reference"], selected["namespace"], artifact, cutoff)


def _check_received(registry, context, evidence, selected, cutoff):
    evidence = inputs.validate_calibrated_signal_input_read(evidence)
    received = validate_molecular_sequence_received_input(evidence["received_input"])
    _require(received["selection"] == selected and received["input"] is not None, "input_not_received")
    item = received["input"]
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="arsenic_speciation_")
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    _require(item["receiver"] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(item["scope"], registry.store.validate_scope(plain(context.scope)))
        and _same(item["inheritance_manifest"], manifest)
        and _same(plain(context.request)["message"].get("knowledge_inheritance"), manifest)
        and _same(item["witness"]["record"], registry.store.get(selected["reference"]))
        and records._received_before(context.episode_id, selected["reference"], cutoff)
        and records._received_before(context.episode_id, item["file"]["artifact_ref"], cutoff), "input_admission_conflict")
    _require(_file(registry, item["file"])["format"] == "json", "json_file_required")
    return evidence


def _roles(sheet):
    return {name: "empty" if type(sheet[name]) is list and not sheet[name] else "present" for name in contracts.INPUT_ROLES}


def _input_bytes(input):
    """Bind embedded decoded observations to the complete admitted File bytes.

    Hex retains even malformed UTF-8 without replacing it. This private witness
    permits recovery and retained authentication without reopening that input.
    """
    file = _identity(input["file"])
    encoded = input["raw_hex"]
    _require(encoded is None or type(encoded) is str and re.fullmatch(r"(?:[0-9a-f]{2})*", encoded) is not None,
        "input_bytes_conflict")
    received = None if input["evidence"] is None else inputs.validate_calibrated_signal_input_read(
        input["evidence"])["received_input"]["input"]
    if received is not None and received["byte_verification"] != "verified":
        _require(encoded is None and input["sheet"] is None, "input_bytes_conflict")
        return
    _require(encoded is not None, "input_bytes_required")
    raw = bytes.fromhex(encoded)
    _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"],
        "input_bytes_conflict")
    decoded = decode_molecular_sequence_input(raw, tag_key="version")
    if received is not None:
        _require(received["file"] == file and _same(decoded, received["content"]), "input_decode_conflict")
    else:
        _require(decoded["state"] == "decoded" and decoded["failure"] is None
            and _same(core.validate_calibrated_signal_sheet(decoded["value"]), input["sheet"]), "saved_sheet_conflict")


def _authenticate_input(registry, context, arguments, invocation, input, *, seen=()):
    """Authenticate the same sealed input before dispatch, retention and replay."""
    _input_bytes(input)
    cutoff = invocation["decision_index"]
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="arsenic_speciation_")
    if arguments["mode"] == "calculate":
        evidence = _check_received(registry, context, input["evidence"], arguments["input"], cutoff)
        artifact, admission = _input_admission(registry, context, arguments["input"], cutoff)
        _require(_same(admission, input["admission"]) and input["protected_input_artifact_refs"] == [artifact]
            and input["file"] == evidence["received_input"]["input"]["file"]
            and _same(input["sheet"], evidence["sheet"]) and input["input_state"] == evidence["state"]
            and input["role_states"] == {name: item["state"] for name, item in evidence["roles"].items()}
            and input["original_source"] is None, "input_control_conflict")
        admission = (records.source_admission_before(context, arguments["input"]["reference"], cutoff)
            if arguments["input"]["namespace"] == "source" else None)
        _require(_same(admission, input["source_admission"]), "source_admission_conflict")
    else:
        original = input["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(original["source_ref"] == arguments["result_ref"]
            and digest(registry.store.get(original["source_ref"])) == original["record_sha256"], "original_source_conflict")
        admission = records.source_admission_before(context, original["source_ref"], cutoff)
        parent = _control(registry, _metadata_publication(registry, original["source_ref"]), seen)
        _require(_same(admission, input["source_admission"]) and input["file"] == parent["files"]["sheet"]["file"]
            and input["protected_input_artifact_refs"] == parent["protected_input_artifact_refs"]
            and _same(input["sheet"], parent["intent"]["input"]["sheet"])
            and input["raw_hex"] == parent["intent"]["input"]["raw_hex"]
            and input["evidence"] is input["admission"] is None and input["input_state"] == "complete"
            and input["role_states"] == _roles(input["sheet"]), "saved_sheet_conflict")
    return input


def _fresh_input(registry, context, reader, arguments, invocation):
    selected, cutoff = arguments["input"], invocation["decision_index"]
    source_admission = (_source_admission(registry, context, reader, selected["reference"], cutoff)
        if selected["namespace"] == "source" else None)
    artifact, admission = _input_admission(registry, context, selected, cutoff)
    evidence = inputs.read_calibrated_signal_inputs(selected["reference"], namespace=selected["namespace"],
        read_input=lambda reference, namespace: reader(context, reference, namespace, tag_key="version"))
    evidence = _check_received(registry, context, evidence, selected, cutoff)
    _require(evidence["received_input"]["input"]["file"]["artifact_ref"] == artifact, "input_identity_conflict")
    received = evidence["received_input"]["input"]
    raw = (_publication_bytes(registry.store, artifact) if received["byte_verification"] == "verified" else None)
    return dict(evidence=evidence, admission=admission, source_admission=source_admission,
        original_source=None, file=received["file"], raw_hex=None if raw is None else raw.hex(), sheet=evidence["sheet"],
        input_state=evidence["state"], role_states={name: item["state"] for name, item in evidence["roles"].items()},
        protected_input_artifact_refs=[artifact])


def _scientific_request(arguments, input):
    if input["sheet"] is None:
        return None, dict(state="input_unavailable", call_count=0, native_invocation="not_requested")
    try:
        core.validate_calibrated_signal_selection(arguments["selection"], input["sheet"])
    except ValueError:
        return None, dict(state="selection_invalid", call_count=0, native_invocation="not_requested")
    request = validate_arsenic_speciation_worker_request(dict(version=REQUEST_VERSION, input_file=input["file"],
        sheet=input["sheet"], selection=arguments["selection"]))
    return request, dict(state="not_started", call_count=0, native_invocation="not_requested")


def _validate_intent(value):
    value = core.copy_json(value)
    _closed(value, "version arguments invocation policy input request calculation")
    arguments = contracts.validate_ordinary_arsenic_arguments(value["arguments"])
    _require(value["version"] == INTENT_VERSION and arguments["mode"] not in ("read_stored", "read_inputs")
        and _same(LocalJobPolicy(**value["policy"]).to_dict(), value["policy"]), "intent_conflict")
    _closed(value["input"], "evidence admission source_admission original_source file raw_hex sheet input_state role_states protected_input_artifact_refs")
    _identity(value["input"]["file"])
    _input_bytes(value["input"])
    request, calculation = _scientific_request(arguments, value["input"])
    _require(_same(request, value["request"]) and _same(calculation, value["calculation"]), "intent_request_conflict")
    return value


def _worker_control(value, intent):
    _closed(value, "selection handle observation native_request native_request_raw result result_hex")
    selected, handle, observation = value["selection"], value["handle"], value["observation"]
    _closed(selected, "version command cwd environment policy request python implementation_files")
    directory = Path(selected["cwd"])
    key = intent["invocation"]["operation_key"]
    _require(directory.is_absolute() and str(directory) == selected["cwd"] and ".." not in directory.parts
        and directory.parts[-4:] == ("cache", "molecular-measurements", digest(key), "worker"), "worker_directory_conflict")
    command = [selected["python"]["path"], "-m", "gene_annotation_episode.sequence_worker",
        str(directory / "worker-request.json"), str(directory / "worker-result.json")]
    _require(selected["version"] == "ordinary_molecular_execution_v1" and selected["command"] == handle["command"] == command
        and selected["cwd"] == handle["cwd"] and handle["stdout"] == str(directory / "stdout")
        and handle["stderr"] == str(directory / "stderr")
        and _same(selected["request"], dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"])))
        and _same(selected["policy"], intent["policy"]) and _same(handle["metadata"]["policy"], intent["policy"])
        and _same(observation["metadata"]["policy"], intent["policy"])
        and observation["terminal"] is True and observation["quiescent"] is True, "worker_control_conflict")
    paths = handle["paths"]
    _require(all(type(path) is str and Path(path).parent == directory for path in paths.values()), "worker_handle_conflict")
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
        validate_arsenic_speciation_worker_result(value["result"], request=intent["request"])
    return value


def _dispatch(registry, intent, directory):
    path = directory / "execution-selection.json"
    if path.exists():
        selected = decode_json(path.read_bytes())
        _require(selected["version"] == "ordinary_molecular_execution_v1"
            and selected["cwd"] == str(directory) and _same(selected["policy"], intent["policy"])
            and _same(selected["request"], dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"])))
            and selected["command"] == [selected["python"]["path"], "-m", "gene_annotation_episode.sequence_worker",
                str(directory / "worker-request.json"), str(directory / "worker-result.json")], "original_worker_selection_conflict")
    else:
        _require(_same(registry.local_job_policy.to_dict(), intent["policy"]), "original_unstarted_policy_conflict")


def _worker_record(work, intent, directory):
    _require(Path(work.output_path) == directory / "worker-result.json", "worker_output_conflict")
    handle = native_lifecycle.NativeJobHandle(directory / "native-handle.json")
    observation = native_lifecycle.status(handle)
    if not (observation["terminal"] and observation["quiescent"]):
        raise MolecularOperationUnpublished("arsenic_speciation_worker_attempt_unconfirmed")
    _require(_same({key: value for key, value in work.metadata.items() if key != "molecular_failure"}, observation["metadata"]),
        "worker_metadata_conflict")
    body = handle.read()
    with _regular(body["paths"]["request"]) as stream: raw = stream.read()
    result, encoded = None, None
    if Path(work.output_path).is_file():
        with _regular(work.output_path) as stream: content = stream.read()
        encoded = content.hex()
        try: result = validate_arsenic_speciation_worker_result(decode_json(content), request=intent["request"])
        except (ValueError, TypeError, KeyError): pass
    with _regular(directory / "worker-request.json") as stream:
        _require(_same(decode_json(stream.read()), dict(operation=WORKER_OPERATION, arguments=dict(request=intent["request"]))),
            "worker_request_conflict")
    return _worker_control(dict(selection=decode_json((directory / "execution-selection.json").read_bytes()),
        handle=body, observation=observation, native_request=decode_json(raw), native_request_raw=raw.decode(),
        result=result, result_hex=encoded), intent)


def _retained(file):
    return dict(state="retained_undeclared", file=file, declared=None,
        observed_identity={name: file[name] for name in ("sha256", "size_bytes")}, failure=None)


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool" and source.get("provider") == TOOL
        and source.get("version") == contracts.SOURCE_VERSION and "operand_refs" not in source, "producer_required")
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = contracts.validate_ordinary_arsenic_arguments(producer["arguments"])
    public = contracts.validate_ordinary_arsenic_return(producer["outcome"]["result"])
    _require(arguments["mode"] in ("calculate", "calculate_saved") and public["source_ref"] == source_ref
        and public["selection"] == arguments["selection"] and producer["outcome"]["record_refs"] == [source_ref], "publication_conflict")
    parents = ([arguments["result_ref"]] if arguments["mode"] == "calculate_saved" else
        [arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else [])
    _require(source.get("parent_source_refs") == parents, "parent_sources_conflict")
    return dict(source=source, producer=producer, public=public)


def _control(registry, publication, seen=()):
    source, producer = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = (*seen, source["id"])
    control = decode_json(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, "version intent worker files packet_ref protected_input_artifact_refs")
    intent = _validate_intent(control["intent"])
    _require(control["version"] == CONTROL_VERSION and control["packet_ref"] == source["artifact_ref"]
        and _same(intent["arguments"], producer["arguments"]) and _same(intent["invocation"], producer["invocation"]),
        "publication_control_conflict")
    invocation, arguments, input = intent["invocation"], intent["arguments"], intent["input"]
    context = _context(registry.store, invocation)
    _authenticate_input(registry, context, arguments, invocation, input, seen=seen)
    if control["worker"] is not None: _worker_control(control["worker"], intent)
    _closed(control["files"], "sheet components")
    for role, state in control["files"].items():
        stored.validate_file_state(state)
        if state["file"] is not None: _file(registry, state["file"])
    _require(control["protected_input_artifact_refs"] == input["protected_input_artifact_refs"], "protected_inputs_conflict")
    expected = [control["files"][role]["file"]["artifact_ref"] for role in contracts.FILE_ROLES
        if control["files"][role]["file"] is not None
        and control["files"][role]["file"]["artifact_ref"] not in control["protected_input_artifact_refs"]]
    _require(source.get("auxiliary_artifact_refs") == list(dict.fromkeys(expected)), "private_files_conflict")
    component_file = control["files"]["components"]["file"]
    result = None if control["worker"] is None else control["worker"]["result"]
    calculation = (intent["calculation"] if intent["request"] is None else
        dict(state="worker_uncertain", call_count=None, native_invocation="not_requested")
        if result is None else result["calculation"])
    components = None
    if component_file is not None:
        _require(result is not None and result["components"] is not None, "components_producer_conflict")
        raw = canonical(result["components"]).encode()
        _require(component_file["sha256"] == hashlib.sha256(raw).hexdigest()
            and component_file["size_bytes"] == len(raw), "components_identity_conflict")
        components = result["components"]
    sheet_file = control["files"]["sheet"]["file"]
    _require(sheet_file is None or sheet_file == input["file"], "sheet_identity_conflict")
    packet = contracts.ordinary_arsenic_packet(arguments=arguments, input_state=input["input_state"],
        role_states=input["role_states"], components=components, calculation=calculation,
        file_states={role: state["state"] for role, state in control["files"].items()}, failures=publication["public"]["failures"])
    _require(_same(packet, {key: item for key, item in publication["public"].items() if key != "source_ref"}), "packet_control_conflict")
    if result is not None:
        _require(all(stored.supplied_failure_view(issue) in packet["failures"] for issue in result["failures"]),
            "worker_failure_conflict")
    return control


def read_arsenic_speciation_publication(registry, context, reader, source_ref, *, require_sheet=False,
        before_decision_index=None, recovery_operation_key=None):
    with registry.store.read_snapshot():
        records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="arsenic_speciation_")
        records.authenticate(context)
        publication = _metadata_publication(registry, source_ref,
            recovery_context=context if recovery_operation_key else None, recovery_operation_key=recovery_operation_key)
        invocation = publication["producer"]["invocation"]
        own = recovery_operation_key == invocation["operation_key"] and (context.run_id, context.episode_id) == (
            invocation["run_id"], invocation["episode_id"])
        if before_decision_index is None: before_decision_index = _cutoff(registry, context)
        admission = None if own else _source_admission(registry, context, reader, source_ref, before_decision_index)
        packet = contracts.validate_ordinary_arsenic_packet(decode_json(_publication_bytes(registry.store, publication["source"]["artifact_ref"])))
        _require(_same(contracts.project_ordinary_arsenic_return(packet, source_ref), publication["public"]), "public_packet_conflict")
        publication.update(packet=packet, source_admission=admission, control=None, sheet=None, sheet_raw_hex=None,
            stored=deepcopy(publication["public"]), admission_kind="source_only")
        if require_sheet:
            control = _control(registry, publication)
            file = control["files"]["sheet"]["file"]
            _require(file is not None, "saved_sheet_unavailable")
            raw = _publication_bytes(registry.store, file["artifact_ref"])
            sheet = core.validate_calibrated_signal_sheet(decode_json(raw))
            _require(_same(sheet, control["intent"]["input"]["sheet"])
                and raw.hex() == control["intent"]["input"]["raw_hex"], "saved_sheet_conflict")
            publication.update(control=control, sheet=sheet, sheet_raw_hex=raw.hex())
        return publication


def read_arsenic_speciation_inputs(registry, context, reader, source_ref, *, before_decision_index=None):
    """Inspect the authenticated stored input, never the original input File.

    The existing control binds its complete byte witness, decoded Sheet and
    original producer. Public Source admission authorizes this finite view,
    not access to the control, File, worker or arbitrary nested provenance.
    """
    with registry.store.read_snapshot():
        publication = read_arsenic_speciation_publication(registry, context, reader, source_ref,
            before_decision_index=before_decision_index)
        control = _control(registry, publication)
        input = control["intent"]["input"]
        return contracts.ordinary_arsenic_input_view(source_ref=source_ref,
            result_selection=publication["public"]["selection"], input_state=input["input_state"],
            role_states=input["role_states"], sheet=input["sheet"])


def _retain_arsenic_speciation_publication(registry, prepared):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    intent, worker = _validate_intent(prepared["intent"]), prepared["worker"]
    input = intent["input"]
    _authenticate_input(registry, _context(registry.store, intent["invocation"]), intent["arguments"],
        intent["invocation"], input)
    missing_state = "not_requested" if intent["request"] is None else "producer_unavailable"
    files = {role: stored.empty_file_state(missing_state) for role in contracts.FILE_ROLES}
    received = None if input["evidence"] is None else input["evidence"]["received_input"]["input"]
    if received is None or received["byte_verification"] == "verified": files["sheet"] = _retained(_file(registry, input["file"]))
    else: files["sheet"] = stored.empty_file_state("identity_conflict" if received["byte_verification"] == "identity_conflict" else "unavailable")
    components, failures, calculation = None, [], intent["calculation"]
    if intent["request"] is None:
        failures.append(stored.supplied_failure("selection_invalid" if calculation["state"] == "selection_invalid" else "input_invalid", "load", role="sheet"))
    elif worker is None or worker["result"] is None:
        calculation = dict(state="worker_uncertain", call_count=None, native_invocation="not_requested")
        failures.append(stored.supplied_failure("worker_uncertain", "worker"))
    else:
        result = validate_arsenic_speciation_worker_result(worker["result"], request=intent["request"])
        calculation, failures = result["calculation"], deepcopy(result["failures"])
        if result["components"] is not None:
            try:
                reference = registry.store.artifact(canonical(result["components"]), "application/json")
                metadata = _metadata(registry.store, reference)
                file = dict(artifact_ref=reference, sha256=metadata["sha256"], size_bytes=metadata["size"], format="json")
                files["components"] = _retained(file)
                components = result["components"]
            except (OSError, ValueError):
                files["components"] = stored.empty_file_state("retention_failed")
                failures.append(stored.supplied_failure("retention_failed", "capture", role="components"))
    if worker is not None and worker["observation"]["metadata"].get("native_returncode") != 0:
        failures.append(stored.supplied_failure("worker_failed", "worker"))
    packet = contracts.ordinary_arsenic_packet(arguments=intent["arguments"], input_state=input["input_state"],
        role_states=input["role_states"], components=components, calculation=calculation,
        file_states={role: item["state"] for role, item in files.items()}, failures=failures)
    packet_ref = registry.store.artifact(canonical(packet), "application/json")
    protected = input["protected_input_artifact_refs"]
    control = dict(version=CONTROL_VERSION, intent=intent, worker=worker, files=files,
        packet_ref=packet_ref, protected_input_artifact_refs=protected)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    arguments = intent["arguments"]
    parents = ([arguments["result_ref"]] if arguments["mode"] == "calculate_saved" else
        [arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else [])
    auxiliaries = list(dict.fromkeys(item["file"]["artifact_ref"] for item in files.values()
        if item["file"] is not None and item["file"]["artifact_ref"] not in protected))
    source = registry.store.put("source", dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=contracts.SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=parents, auxiliary_artifact_refs=auxiliaries), origin="tool")
    return dict(source=source, public=contracts.project_ordinary_arsenic_return(packet, source["id"]), control=control)


def _outcome(arguments, key, public):
    partial = public["sheet"] is None if arguments["mode"] == "read_inputs" else public["values"] is None or bool(public["failures"])
    return dict(status="partial" if partial else "completed", operation_ref=identity("operation", dict(
        key=key, name=TOOL, arguments=arguments)), record_refs=[public["source_ref"]],
        changed_record_refs=[] if arguments["mode"] in ("read_stored", "read_inputs") else [public["source_ref"]], result=public,
        feedback=None if not partial else dict(category="representation", code="arsenic_speciation_partial", source_ref=public["source_ref"]))


def read_arsenic_speciation_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = contracts.validate_ordinary_arsenic_arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial"), "action_result_unavailable")
    if arguments["mode"] == "read_inputs":
        public = contracts.validate_ordinary_arsenic_input_view(outcome["result"])
        _require(outcome["record_refs"] == [public["source_ref"]]
            and outcome["changed_record_refs"] == [] and arguments["result_ref"] == public["source_ref"], "action_source_conflict")
        expected = read_arsenic_speciation_inputs(registry, context, reader, public["source_ref"],
            before_decision_index=details["invocation"]["decision_index"])
        _require(_same(expected, public), "action_result_conflict")
        return public
    public = contracts.validate_ordinary_arsenic_return(outcome["result"])
    _require(outcome["record_refs"] == [public["source_ref"]], "action_source_conflict")
    publication = read_arsenic_speciation_publication(registry, context, reader, public["source_ref"],
        recovery_operation_key=operation_key if arguments["mode"] != "read_stored" else None,
        before_decision_index=details["invocation"]["decision_index"])
    if arguments["mode"] == "read_stored": _require(arguments["result_ref"] == public["source_ref"], "action_source_conflict")
    else: _require(publication["producer"]["invocation"]["operation_key"] == operation_key, "action_source_conflict")
    _require(_same(publication["public"], public), "action_result_conflict")
    return public


async def execute_arsenic_speciation_tool(registry, arguments, *, scope, operation_key, authority):
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry and owner.run_id == context.run_id, "execution_owner_conflict")
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / "cache" / "molecular-measurements" / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed", "partial"):
                _require(_same(read_arsenic_speciation_action_result(registry, context, arguments, operation_key, reader=reader),
                    outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("invalid", "unavailable", "failed")
                    and outcome.get("result") is None and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        pending = False
        try:
            arguments = contracts.validate_ordinary_arsenic_arguments(arguments)
            if arguments["mode"] == "read_inputs":
                public = read_arsenic_speciation_inputs(registry, context, reader, arguments["result_ref"],
                    before_decision_index=invocation["decision_index"])
            elif arguments["mode"] == "read_stored":
                public = read_arsenic_speciation_publication(registry, context, reader, arguments["result_ref"],
                    before_decision_index=invocation["decision_index"])["public"]
            else:
                intent_path = directory / "arsenic-speciation-intent.json"
                pending = intent_path.exists()
                if pending:
                    intent = _validate_intent(decode_json(intent_path.read_bytes()))
                    _require(_same(intent["arguments"], arguments) and _same(intent["invocation"], invocation), "original_intent_conflict")
                else:
                    if arguments["mode"] == "calculate": input = _fresh_input(registry, context, reader, arguments, invocation)
                    else:
                        publication = read_arsenic_speciation_publication(registry, context, reader, arguments["result_ref"],
                            require_sheet=True, before_decision_index=invocation["decision_index"])
                        input = dict(evidence=None, admission=None, source_admission=publication["source_admission"],
                            original_source=dict(source_ref=arguments["result_ref"], record_sha256=digest(publication["source"])),
                            file=publication["control"]["files"]["sheet"]["file"], raw_hex=publication["sheet_raw_hex"],
                            sheet=publication["sheet"], input_state="complete",
                            role_states=_roles(publication["sheet"]), protected_input_artifact_refs=publication["control"]["protected_input_artifact_refs"])
                    request, calculation = _scientific_request(arguments, input)
                    intent = _validate_intent(dict(version=INTENT_VERSION, arguments=arguments, invocation=invocation,
                        policy=registry.local_job_policy.to_dict(), input=input, request=request, calculation=calculation))
                    _authenticate_input(registry, context, arguments, invocation, intent["input"])
                    _immutable(intent_path, intent)
                _authenticate_input(registry, context, arguments, invocation, intent["input"])
                pending = True
                worker = None
                if intent["request"] is not None:
                    selected = _directory(directory / "worker")
                    selected.mkdir(mode=0o700, exist_ok=True)
                    _dispatch(registry, intent, selected)
                    work = await registry._sequence_worker_async(WORKER_OPERATION, dict(request=intent["request"]),
                        directory=selected, owned_directory=selected)
                    authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                    worker = _worker_record(work, intent, selected)
                with registry.store.transaction():
                    public = retain_molecular_publication(registry, dict(intent=intent, worker=worker), tool_name=TOOL)["public"]
                    outcome = _outcome(arguments, operation_key, public)
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
                raise MolecularOperationUnpublished("arsenic_speciation_original_action_unpublished") from error
            with registry.store.transaction():
                message = str(error)
                code = message if re.fullmatch(r"[a-z][a-z0-9_]*", message) else "arsenic_speciation_input_invalid"
                diagnostic = registry.store.artifact(canonical(dict(version="arsenic_speciation_diagnostic_v1",
                    exception_type=type(error).__module__ + "." + type(error).__name__, message=message)), "application/json")
                outcome = dict(status="unavailable" if isinstance(error, OSError) or code.endswith("_unavailable") else "invalid",
                    operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)), record_refs=[],
                    changed_record_refs=[], result=None, feedback=dict(category="arguments_or_reference", code=code, diagnostic_ref=diagnostic))
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ["TOOL", "WORKER_OPERATION", "REQUEST_VERSION", "RESULT_VERSION", "arsenic_speciation_tool_contract",
    "execute_arsenic_speciation_tool", "run_arsenic_speciation_tool_request", "validate_arsenic_speciation_worker_request",
    "validate_arsenic_speciation_worker_result", "read_arsenic_speciation_publication",
    "read_arsenic_speciation_action_result", "read_arsenic_speciation_inputs", "_retain_arsenic_speciation_publication"]
