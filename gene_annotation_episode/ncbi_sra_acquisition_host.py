"""Host custody for one ordinary, explicitly advertised SRA file GET.

The existing Workflow supplies the actual action and metadata reader. Native
XML is read only for a fresh preparation; saved authentication reads metadata
and sealed private controls, never the advertisement or downloaded entity.
"""
from copy import deepcopy
import hashlib
import json
import math

from . import ncbi_sra_acquisition as sra
from .acquisition import SourceSnapshot
from .communication import plain
from .domain import ContractError, canonical, identity
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .molecular_measurement_tools import authenticate_molecular_invocation
from .molecular_sequence_input_contracts import input_record_digest
from .native_file_capture import NativeFileCaptureError, _metadata, retained_native_file
from .native_flux_balance_storage import read_bytes


TOOL = sra.TOOL
PREPARED_VERSION = "ncbi_sra_file_prepared_v1"
EVIDENCE_VERSION = "ncbi_sra_file_receipt_evidence_v1"


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _closed(value, names, code):
    _require(type(value) is dict and set(value) == set(names.split()), code)


def _same(left, right):
    return canonical(left) == canonical(right)


def _authority(registry, arguments, authority, operation_key):
    _require(type(authority) is tuple and len(authority) == 2
        and isinstance(authority[0], BindingContext) and callable(authority[1]), "sra_file_input_not_received")
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments,
        plain(authority[0].scope), operation_key)
    _require(authority[0] is context and authority[1] is reader, "sra_file_input_not_received")
    return context, reader


def _invocation(context, operation_key):
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(suffix.isdecimal() and str(int(suffix)) == suffix, "sra_file_input_not_received")
    return dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=input_record_digest(plain(context.request)),
        assignment_sha256=input_record_digest(plain(context.assignment)), scope=plain(context.scope))


def _input(registry, arguments, context, reader, operation_key):
    """Use the actual metadata owner and original action cutoff before bytes."""
    file = arguments["advertisement_file"]
    reference = file["artifact_ref"]
    try:
        item = reader(context, reference, "artifact", file_format=file["format"])
    except ValueError as error:
        raise ContractError("sra_file_input_not_received") from error
    _closed(item, "receiver scope inheritance_manifest witness file artifact_record byte_verification",
        "sra_file_input_identity_conflict")
    metadata = _metadata(registry.store, reference)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    expected_receiver = dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)),
        assignment_sha256=input_record_digest(plain(context.assignment)))
    witness = item["witness"]
    _closed(witness, "reference namespace record record_sha256 record_revision source_version",
        "sra_file_input_identity_conflict")
    _require(_same(item["receiver"], expected_receiver)
        and _same(item["scope"], registry.store.validate_scope(plain(context.scope)))
        and _same(item["inheritance_manifest"], manifest)
        and _same(plain(context.request)["message"].get("knowledge_inheritance"), manifest)
        and _same(item["file"], file) and _same(item["artifact_record"], metadata)
        and item["byte_verification"] == "unavailable"
        and witness["reference"] == reference and witness["namespace"] == "artifact"
        and _same(witness["record"], metadata)
        and witness["record_sha256"] == input_record_digest(metadata)
        and witness["record_revision"] is None and witness["source_version"] is None,
        "sra_file_input_identity_conflict")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="sra_file_")
    records.authenticate(context)
    try:
        admission = records.file_admission_before(context, reference, "artifact", reference,
            _invocation(context, operation_key)["decision_index"])
    except ValueError as error:
        raise ContractError("sra_file_input_not_received") from error
    return dict(metadata=deepcopy(item), admission=admission)


def _prepared(value, arguments, invocation, input):
    _closed(value, "version arguments invocation input selection", "sra_file_saved_outcome_conflict")
    _require(value["version"] == PREPARED_VERSION and _same(value["arguments"], arguments)
        and _same(value["invocation"], invocation) and _same(value["input"], input),
        "sra_file_saved_outcome_conflict")
    sra.validate_sra_file_selection(value["selection"], arguments=arguments)
    return deepcopy(value)


def prepare_sra_file(registry, arguments, *, authority, operation_key):
    context, reader = _authority(registry, arguments, authority, operation_key)
    arguments = sra.validate_sra_file_arguments(arguments)
    invocation = _invocation(context, operation_key)
    input = _input(registry, arguments, context, reader, operation_key)
    try:
        raw = read_bytes(retained_native_file(registry.store, arguments["advertisement_file"]))
    except (NativeFileCaptureError, OSError, ValueError) as error:
        code = "sra_file_input_identity_conflict" if getattr(error, "code", None) == "retained_artifact_mismatch" else "sra_file_input_bytes_unavailable"
        raise ContractError(code) from error
    selection = sra.resolve_sra_file_selection(raw, arguments=arguments)
    return _prepared(dict(version=PREPARED_VERSION, arguments=arguments, invocation=invocation,
        input=input, selection=selection), arguments, invocation, input)


def _scalar(value):
    return (value is None or type(value) in (str, bool, int)
        or type(value) is float and math.isfinite(value))


def _evidence(value, *, arguments, invocation, input):
    _closed(value, "version prepared evidence", "sra_file_saved_outcome_conflict")
    _require(value["version"] == EVIDENCE_VERSION, "sra_file_saved_outcome_conflict")
    prepared = _prepared(value["prepared"], arguments, invocation, input)
    evidence = value["evidence"]
    _require(type(evidence) is dict, "sra_file_saved_outcome_conflict")
    if evidence.get("kind") == "value":
        _closed(evidence, "kind value", "sra_file_saved_outcome_conflict")
        native = sra.validate_sra_file_value(evidence["value"])
        _require(_same(native["requested"], arguments) and _same(native["selection"], prepared["selection"]),
            "sra_file_saved_outcome_conflict")
    else:
        _closed(evidence, "kind code observed_snapshot_service observed_snapshot_url", "sra_file_saved_outcome_conflict")
        _require(evidence["kind"] == "failure" and evidence["code"] == "sra_file_value_invalid"
            and _scalar(evidence["observed_snapshot_service"])
            and (evidence["observed_snapshot_url"] is None or type(evidence["observed_snapshot_url"]) is str),
            "sra_file_saved_outcome_conflict")
    canonical(value)
    return deepcopy(value)


def publish_sra_file_request(registry, arguments, snapshot, *, prepared):
    _require(type(prepared) is dict and type(prepared.get("invocation")) is dict,
        "sra_file_saved_outcome_conflict")
    operation_key = prepared["invocation"].get("operation_key")
    active = registry._current_invocation.get()
    _require(type(active) is tuple and len(active) == 5, "sra_file_input_not_received")
    context, reader = _authority(registry, arguments, (active[0], active[1]), operation_key)
    arguments = sra.validate_sra_file_arguments(arguments)
    invocation = _invocation(context, operation_key)
    input = _input(registry, arguments, context, reader, operation_key)
    prepared = _prepared(prepared, arguments, invocation, input)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "sra_file_value_invalid")
    artifact_ref = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    try:
        value = sra.sra_file_value(snapshot, arguments=arguments, selection=prepared["selection"], artifact_ref=artifact_ref)
    except ValueError:
        evidence = dict(kind="failure", code="sra_file_value_invalid",
            observed_snapshot_service=deepcopy(snapshot.service), observed_snapshot_url=deepcopy(snapshot.url))
    else:
        evidence = dict(kind="value", value=value)
    envelope = _evidence(dict(version=EVIDENCE_VERSION, prepared=prepared, evidence=evidence),
        arguments=arguments, invocation=invocation, input=input)
    witness = registry.store.artifact(canonical(envelope), "application/json")
    source = registry._source(TOOL, None, snapshot=snapshot, accession=None, software_version=None,
        parent_source_refs=[], auxiliary_artifact_refs=[witness])
    receipt = (sra.sra_file_receipt(envelope["evidence"]["value"], source_ref=source["id"])
        if envelope["evidence"]["kind"] == "value" else
        sra.failed_sra_file_receipt(envelope["evidence"]["code"], source_ref=source["id"]))
    return receipt, [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]


def _control(store, reference):
    try:
        metadata = _metadata(store, reference)
        raw = store.get_artifact(reference)
    except OSError as error:
        raise ContractError("sra_file_saved_outcome_conflict") from error
    _require(type(raw) is bytes and len(raw) == metadata["size"]
        and hashlib.sha256(raw).hexdigest() == metadata["sha256"], "sra_file_saved_outcome_conflict")
    try:
        value = json.loads(raw)
        _require(raw == canonical(value).encode(), "sra_file_saved_outcome_conflict")
    except (ValueError, TypeError, UnicodeError, OverflowError) as error:
        raise ContractError("sra_file_saved_outcome_conflict") from error
    return value


def _source(store, reference):
    value = store.get(reference)
    _require(value.get("record_type") == "source" and value.get("origin") == "external"
        and value.get("provider") == TOOL and value.get("version") is value.get("accession") is None
        and value.get("parent_source_refs") == [] and type(value.get("auxiliary_artifact_refs")) is list
        and len(value["auxiliary_artifact_refs"]) == 1, "sra_file_saved_outcome_conflict")
    payload = {key: child for key, child in value.items() if key not in {"id", "record_type", "origin"}}
    _require(value.get("id") == reference == identity("source", dict(origin=value["origin"], record=payload)),
        "sra_file_saved_outcome_conflict")
    return value


def _without_pending(value):
    _require(type(value) is dict, "sra_file_saved_outcome_conflict")
    return {key: child for key, child in value.items() if key != "pending_work_after_action"}


def _operation(registry, arguments, context, operation_key, outcome):
    row = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
    _require(row is not None and row["name"] == TOOL and row["arguments"] == canonical(arguments)
        and row["scope"] == canonical(plain(context.scope))
        and row["id"] == identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
        "sra_file_saved_outcome_conflict")
    saved = json.loads(row["result"])
    _require(_same(saved, outcome) and saved.get("operation_ref") == row["id"], "sra_file_saved_outcome_conflict")
    index = _invocation(context, operation_key)["decision_index"]
    action = registry.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (context.run_id, context.episode_id, index)).fetchone()
    _require(action is not None and _same(json.loads(action["action"]), dict(kind="tool", tool=TOOL, arguments=arguments))
        and (action["result"] is None or _same(_without_pending(json.loads(action["result"])), saved)),
        "sra_file_saved_outcome_conflict")
    return saved


def authenticate_saved_sra_file(registry, arguments, *, authority, operation_key, outcome):
    context, reader = _authority(registry, arguments, authority, operation_key)
    arguments = sra.validate_sra_file_arguments(arguments)
    # Current metadata and original temporal authority precede private controls.
    input = _input(registry, arguments, context, reader, operation_key)
    invocation = _invocation(context, operation_key)
    saved = _operation(registry, arguments, context, operation_key, outcome)
    receipt = sra.validate_sra_file_receipt(saved["result"])
    reference = receipt["source_ref"]
    if reference is None:
        _require(not receipt["acquired"] and saved.get("status") in {"invalid", "failed", "unavailable", "partial"}
            and saved.get("record_refs") == [], "sra_file_saved_outcome_conflict")
        return
    source = _source(registry.store, reference)
    envelope = _evidence(_control(registry.store, source["auxiliary_artifact_refs"][0]),
        arguments=arguments, invocation=invocation, input=input)
    control = _control(registry.store, source["request_ref"])
    _closed(control, "request transport", "sra_file_saved_outcome_conflict")
    metadata = _metadata(registry.store, source["artifact_ref"])
    evidence = envelope["evidence"]
    if evidence["kind"] == "value":
        value = evidence["value"]
        _require(value["observed"]["url"] == source["uri"]
            and _same(value["observed"]["request"], control["request"])
            and _same(value["observed"]["transport"], control["transport"])
            and value["raw_file"]["artifact_ref"] == metadata["id"]
            and value["raw_file"]["sha256"] == metadata["sha256"]
            and value["raw_file"]["size_bytes"] == metadata["size"], "sra_file_saved_outcome_conflict")
        actual = sra.sra_file_receipt(value, source_ref=reference)
    else:
        _require(evidence["observed_snapshot_url"] == source["uri"], "sra_file_saved_outcome_conflict")
        actual = sra.failed_sra_file_receipt(evidence["code"], source_ref=reference)
    incomplete = (not receipt["acquired"] and receipt["failure_code"] == "data_acquisition_publication_incomplete"
        and saved.get("status") == "partial" and (saved.get("feedback") or {}).get("code") == receipt["failure_code"])
    _require((incomplete or (_same(actual, receipt)
        and saved.get("status") == ("completed" if receipt["acquired"] else "partial")))
        and saved.get("record_refs") == [reference, *([source["artifact_ref"]] if receipt["acquired"] else [])],
        "sra_file_saved_outcome_conflict")


__all__ = ["TOOL", "PREPARED_VERSION", "EVIDENCE_VERSION", "prepare_sra_file",
    "publish_sra_file_request", "authenticate_saved_sra_file"]
