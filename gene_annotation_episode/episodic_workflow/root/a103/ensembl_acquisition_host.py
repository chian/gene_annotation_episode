"""Join explicit BioMart requests to existing Source, action and receipt owners.

Only direct selected Sources require receiver admission. Their authenticated
producer-owned parent links allow private verification of retained discovery
evidence; this never grants ancestor Sources, raw Files or control artifacts.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import re

from . import ensembl_acquisition as ensembl
from .acquisition import SourceSnapshot
from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .waiting import validate_pending


SELECTION_VERSION = "ensembl_discovery_selection_v1"
FAILURE_WITNESS_VERSION = "ensembl_acquisition_failure_witness_v1"


def _require(condition, code="ensembl_discovery_custody_conflict"):
    if not condition:
        raise ContractError(code)


def _same(left, right):
    return canonical(left) == canonical(right)


def _digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _artifact(store, reference):
    value = store.get(reference)
    _require(value.get("record_type") == "artifact" and value.get("id") == reference
        and type(value.get("sha256")) is str and re.fullmatch(r"[a-f0-9]{64}", value["sha256"]) is not None
        and reference == "artifact_" + value["sha256"] and type(value.get("size")) is int and value["size"] >= 0,
        "ensembl_artifact_identity_conflict")
    return value


def _bytes(store, reference):
    metadata = _artifact(store, reference)
    raw = store.get_artifact(reference)
    _require(type(raw) is bytes and len(raw) == metadata["size"]
        and hashlib.sha256(raw).hexdigest() == metadata["sha256"], "ensembl_artifact_identity_conflict")
    return raw


def _control(store, reference):
    raw = _bytes(store, reference)
    try:
        value = json.loads(raw)
        _require(raw == canonical(value).encode(), "ensembl_control_invalid")
    except (ValueError, UnicodeError, TypeError, OverflowError) as error:
        raise ContractError("ensembl_control_invalid") from error
    return value


def _source(store, reference):
    source = store.get(reference)
    _require(source.get("record_type") == "source" and source.get("id") == reference
        and source.get("origin") == "external" and source.get("provider") == "ensembl"
        and source.get("version") is None and source.get("accession") is None,
        "ensembl_source_invalid")
    payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    _require(identity("source", {"origin": "external", "record": payload}) == reference,
        "ensembl_source_identity_conflict")
    return source


def _admitted(registry, arguments, authority):
    direct = ensembl.ensembl_discovery_refs(arguments)
    if not direct:
        return None, {}
    _require(type(authority) is tuple and len(authority) == 2 and callable(authority[1]),
        "ensembl_received_input_authority_required")
    context, reader = authority
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="ensembl_").authenticate(context)
    sources = {}
    for reference in direct:
        value = reader(context, reference, "source", source_metadata_only=True)
        _require(type(value) is dict and value.get("failure") is None and value.get("input") is not None,
            "ensembl_source_not_received")
        source = _source(registry.store, reference)
        _require(_same(value["input"]["witness"]["record"], source), "ensembl_source_identity_conflict")
        sources[reference] = source
    return context, sources


def _without_pending(value):
    value = deepcopy(value)
    if "pending_work_after_action" in value:
        validate_pending(value.pop("pending_work_after_action"))
    return value


def _is_receipt(value):
    return type(value) is dict and set(value) == {"acquired", "source_ref", "data_ref", "failure_code"}


def _receipt_refs(value):
    value = ensembl.validate_ensembl_receipt(value)
    return ([] if value["source_ref"] is None else [value["source_ref"],
        *([value["data_ref"]] if value["acquired"] else [])])


def _operation(registry, source_ref, *, expected=None, allow_pending=False, current_context=None):
    query = ("SELECT * FROM tool_operations WHERE name=? AND EXISTS("
        "SELECT 1 FROM json_each(result,'$.record_refs') published WHERE published.value=?)")
    params = [ensembl.TOOL, source_ref]
    if expected is not None:
        query += " AND id=? AND operation_key=?"
        params += [expected["operation_ref"], expected["operation_key"]]
    rows = registry.store.db.execute(query, params).fetchall()
    _require(len(rows) == 1, "ensembl_original_operation_conflict")
    row = rows[0]
    arguments, outcome = json.loads(row["arguments"]), json.loads(row["result"])
    _require(type(outcome) is dict and row["arguments"] == canonical(arguments)
        and row["result"] == canonical(outcome), "ensembl_original_operation_conflict")
    arguments = ensembl.validate_ensembl_arguments(arguments)
    _require(row["id"] == identity("operation", {"key": row["operation_key"], "name": ensembl.TOOL,
        "arguments": arguments}) and outcome.get("operation_ref") == row["id"]
        and outcome.get("status") in {"completed", "partial", "failed"}
        and outcome.get("record_refs") == (_receipt_refs(outcome["result"])
            if _is_receipt(outcome.get("result")) else [source_ref]), "ensembl_original_operation_conflict")
    if _is_receipt(outcome.get("result")):
        _require(outcome["result"]["source_ref"] == source_ref and outcome["status"] == (
            "completed" if outcome["result"]["acquired"] else "partial"), "ensembl_original_operation_conflict")
    operation = {"operation_key": row["operation_key"], "operation_ref": row["id"]}
    tables = {value[0] for value in registry.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    actions = ([] if "runtime_actions" not in tables else registry.store.db.execute(
        "SELECT * FROM runtime_actions WHERE ?=run_id||':'||episode_id||':'||decision_index",
        (row["operation_key"],)).fetchall())
    _require(len(actions) <= 1 and (actions or arguments["operation"] == "registry"),
        "ensembl_original_action_required")
    if actions:
        action = actions[0]
        producer = EpisodeReturnRecords(registry.store, action["run_id"], failure_prefix="ensembl_").context(action["episode_id"])
        _require(row["scope"] == canonical(plain(producer.scope))
            and _same(json.loads(action["action"]), {"kind": "tool", "tool": ensembl.TOOL,
                "arguments": arguments}), "ensembl_original_action_conflict")
        if action["result"] is None:
            _require(allow_pending and (arguments["operation"] == "registry" or current_context is not None
                and current_context.run_id == producer.run_id and current_context.episode_id == producer.episode_id),
                "ensembl_original_action_incomplete")
        else:
            _require(_same(_without_pending(json.loads(action["result"])), outcome),
                "ensembl_original_action_conflict")
    return operation, arguments, outcome


def _selection(arguments, entries):
    return {"version": SELECTION_VERSION, "arguments": deepcopy(arguments),
        "direct_source_refs": ensembl.ensembl_discovery_refs(arguments), "sources": deepcopy(entries)}


def _entry(source, operation, outcome):
    return {"source_ref": source["id"], "source_record_sha256": _digest(source),
        "raw_artifact_ref": source["artifact_ref"], "request_ref": source["request_ref"],
        **operation, "operation_result_sha256": _digest(outcome)}


def _entries(value):
    fields = {"source_ref", "source_record_sha256", "raw_artifact_ref", "request_ref",
        "operation_key", "operation_ref", "operation_result_sha256"}
    _require(type(value) is list, "ensembl_selection_conflict")
    for row in value:
        _require(type(row) is dict and set(row) == fields and all(type(child) is str for child in row.values())
            and re.fullmatch(r"source_[a-f0-9]{24,64}", row["source_ref"]) is not None
            and all(re.fullmatch(r"artifact_[a-f0-9]{64}", row[key]) is not None
                for key in ("raw_artifact_ref", "request_ref"))
            and all(re.fullmatch(r"[a-f0-9]{64}", row[key]) is not None
                for key in ("source_record_sha256", "operation_result_sha256"))
            and bool(row["operation_key"]) and re.fullmatch(r"operation_[a-f0-9]{24,64}", row["operation_ref"]) is not None,
            "ensembl_selection_conflict")
    return value


def _lineage(registry, arguments, *, admitted=None, read_entities, expected_entries=None):
    """Authenticate sealed parents before privately opening their controls.

    Replay reconstructs only originally complete UTF8 discovery captures from
    the original controlled DTO. This verifies retained identities and never
    asserts that a native entity File was read again or remains available.
    """
    evidence, entries, loaded, visiting = {}, [], {}, set()
    expected = None if expected_entries is None else {row["source_ref"]: row for row in _entries(expected_entries)}
    if expected is not None:
        _require(len(expected) == len(expected_entries), "ensembl_selection_conflict")
    def load(reference):
        if reference in loaded:
            return loaded[reference]
        _require(reference not in visiting, "ensembl_source_lineage_cycle")
        visiting.add(reference)
        source = _source(registry.store, reference)
        if admitted is not None and reference in admitted:
            _require(_same(source, admitted[reference]), "ensembl_source_identity_conflict")
        previous = None if expected is None else expected.get(reference)
        _require(expected is None or previous is not None, "ensembl_selection_conflict")
        operation, selected, outcome = _operation(registry, reference, expected=previous)
        direct = ensembl.ensembl_discovery_refs(selected)
        _require(selected["operation"] != "gene_homologies" and source.get("parent_source_refs") == direct
            and outcome["status"] == "completed", "ensembl_discovery_producer_invalid")
        receipt = outcome.get("result") if _is_receipt(outcome.get("result")) else None
        auxiliary = source.get("auxiliary_artifact_refs")
        if receipt is None:
            value = outcome.get("result")
            validate_schema(value, ensembl.ensembl_result_schema())
            _require(value["source_ref"] == reference, "ensembl_discovery_producer_invalid")
        else:
            ensembl.validate_ensembl_receipt(receipt)
            _require(receipt["acquired"] and receipt["source_ref"] == reference
                and receipt["data_ref"] == source["artifact_ref"] and type(auxiliary) is list
                and len(auxiliary) == 2, "ensembl_discovery_producer_invalid")
            value = _control(registry.store, auxiliary[1])
            validate_schema(value, ensembl.ensembl_value_schema())
        _require(value["requested"] == selected
            and value["raw_artifact_ref"] == source["artifact_ref"] and value["native_response_state"] == "data"
            and value["representation_state"] == "complete" and not value["issues"]
            and value["response"]["body_complete"] is True and type(value["native_text"]) is str,
            "ensembl_discovery_response_not_complete")
        for parent in direct:
            load(parent)
        parent_refs = {row["source_ref"] for row in value["discovery_evidence"]}
        expected_parent_entries = [row for row in entries if row["source_ref"] in parent_refs]
        _require(type(auxiliary) is list and len(auxiliary) == (1 if receipt is None else 2)
            and _same(_control(registry.store, auxiliary[0]), _selection(selected, expected_parent_entries)),
            "ensembl_source_lineage_selection_conflict")
        control = _control(registry.store, source["request_ref"])
        _require(type(control) is dict and set(control) == {"request", "transport"}
            and _same(control["request"], selected), "ensembl_source_request_conflict")
        metadata = _artifact(registry.store, source["artifact_ref"])
        raw = _bytes(registry.store, source["artifact_ref"]) if read_entities else value["native_text"].encode("utf-8")
        _require(len(raw) == metadata["size"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"],
            "ensembl_artifact_identity_conflict")
        snapshot = SourceSnapshot("ensembl", source["uri"], selected, source["retrieved_at"], raw,
            ensembl.ensembl_request_spec(selected)["media_type"], control["transport"])
        actual = ensembl.ensembl_result(snapshot, arguments=selected, source_ref=reference,
            artifact_ref=source["artifact_ref"], evidence=evidence)
        expected_value = value if receipt is None else ensembl.ensembl_result_from_value(
            value, source_ref=reference, evidence=evidence)
        _require(_same(actual, expected_value) and (receipt is None or
            _same(ensembl.ensembl_receipt(value, source_ref=reference), receipt)),
            "ensembl_discovery_saved_result_conflict")
        entry = _entry(source, operation, outcome)
        _require(previous is None or _same(previous, entry), "ensembl_selection_conflict")
        entries.append(entry)
        evidence[reference] = {"snapshot": snapshot, "artifact_ref": source["artifact_ref"]}
        loaded[reference] = source
        visiting.remove(reference)
        return source
    for reference in ensembl.ensembl_discovery_refs(arguments):
        load(reference)
    _require(expected is None or set(expected) == set(loaded), "ensembl_selection_conflict")
    ensembl.validate_ensembl_discovery(arguments, evidence=evidence)
    return evidence, _selection(arguments, entries)


def prepare_ensembl_request(registry, arguments, *, authority=None):
    arguments = ensembl.validate_ensembl_arguments(arguments)
    with registry.store.read_snapshot():
        _, admitted = _admitted(registry, arguments, authority)
        evidence, selection = _lineage(registry, arguments, admitted=admitted, read_entities=True)
    return {"arguments": arguments, "evidence": evidence, "selection": selection,
        "evidence_basis": "verified_retained_entity_bytes"}


def _prepared(registry, arguments, prepared):
    _require(type(prepared) is dict and set(prepared) == {"arguments", "evidence", "selection", "evidence_basis"}
        and _same(prepared["arguments"], arguments) and prepared["evidence_basis"] == "verified_retained_entity_bytes",
        "ensembl_prepared_request_conflict")
    selection = prepared["selection"]
    _require(type(selection) is dict and set(selection) == {"version", "arguments", "direct_source_refs", "sources"}
        and selection["version"] == SELECTION_VERSION and _same(selection["arguments"], arguments)
        and selection["direct_source_refs"] == ensembl.ensembl_discovery_refs(arguments)
        and type(selection["sources"]) is list, "ensembl_selection_conflict")
    evidence, actual = _lineage(registry, arguments, read_entities=False, expected_entries=selection["sources"])
    _require(_same(actual, selection) and type(prepared["evidence"]) is dict
        and set(prepared["evidence"]) == set(evidence), "ensembl_prepared_request_conflict")
    for reference, item in evidence.items():
        previous = prepared["evidence"][reference]
        _require(type(previous) is dict and set(previous) == {"snapshot", "artifact_ref"}
            and previous["artifact_ref"] == item["artifact_ref"] and isinstance(previous["snapshot"], SourceSnapshot),
            "ensembl_prepared_request_conflict")
        left, right = previous["snapshot"], item["snapshot"]
        _require(left.content == right.content and all(getattr(left, key) == getattr(right, key)
            for key in ("service", "url", "retrieved_at", "media_type"))
            and _same(left.request, right.request) and _same(left.transport, right.transport),
            "ensembl_prepared_request_conflict")
    return evidence, actual


def _finite_failure(error):
    code = str(error)
    return code if code in ensembl.ENSEMBL_FAILURE_CODES else "data_acquisition_publication_incomplete"


def _failure_witness(snapshot, code):
    return {"version": FAILURE_WITNESS_VERSION, "observed_snapshot_service": snapshot.service,
        "observed_snapshot_url": snapshot.url, "failure_code": code}


def _validate_failure_witness(value, source, receipt):
    _require(type(value) is dict and set(value) == {"version", "observed_snapshot_service",
        "observed_snapshot_url", "failure_code"} and value["version"] == FAILURE_WITNESS_VERSION
        and type(value["observed_snapshot_service"]) is str and type(value["observed_snapshot_url"]) is str
        and value["observed_snapshot_url"] == source["uri"]
        and value["failure_code"] in ensembl.ENSEMBL_FAILURE_CODES
        and not receipt["acquired"] and receipt["source_ref"] == source["id"]
        and receipt["failure_code"] == value["failure_code"], "ensembl_failure_witness_invalid")


def publish_ensembl_request(registry, arguments, snapshot, *, prepared):
    arguments = ensembl.validate_ensembl_arguments(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        "ensembl_snapshot_invalid")
    try:
        evidence, selection = _prepared(registry, arguments, prepared)
    except (ContractError, ValueError, KeyError, TypeError) as error:
        # An unsealed response has no invented selection or parent links.
        code = _finite_failure(error)
        witness = registry.store.artifact(canonical(_failure_witness(snapshot, code)), "application/json")
        source = registry._source("ensembl", None, snapshot=snapshot, accession=None,
            auxiliary_artifact_refs=[witness])
        return ensembl.failed_ensembl_receipt(code, source_ref=source["id"]), [source["id"]]
    witness = registry.store.artifact(canonical(selection), "application/json")
    artifact_ref = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    try:
        value = ensembl.ensembl_value(snapshot, arguments=arguments, artifact_ref=artifact_ref, evidence=evidence)
    except ValueError as error:
        code, value = _finite_failure(error), None
        retained = _failure_witness(snapshot, code)
    else:
        retained = value
    private_ref = registry.store.artifact(canonical(retained), "application/json")
    captured = replace(snapshot, url=value["response"]["request_url"]) if value is not None else snapshot
    source = registry._source("ensembl", None, snapshot=captured, accession=None,
        parent_source_refs=ensembl.ensembl_discovery_refs(arguments), auxiliary_artifact_refs=[witness, private_ref])
    _require(source["artifact_ref"] == artifact_ref, "ensembl_artifact_identity_conflict")
    receipt = (ensembl.failed_ensembl_receipt(code, source_ref=source["id"]) if value is None else
        ensembl.ensembl_receipt(value, source_ref=source["id"]))
    return receipt, _receipt_refs(receipt)


def _authenticate_saved_receipt(registry, arguments, source, receipt, *, admitted):
    """Recheck actual metadata/controls; never reopen cached entity bytes."""
    auxiliary = source.get("auxiliary_artifact_refs")
    _require(type(auxiliary) is list and len(auxiliary) in (1, 2), "ensembl_saved_source_conflict")
    control = _control(registry.store, source["request_ref"])
    _require(type(control) is dict and set(control) == {"request", "transport"}, "ensembl_source_request_conflict")
    value = _control(registry.store, auxiliary[-1])
    if len(auxiliary) == 1:
        _require("parent_source_refs" not in source, "ensembl_saved_source_conflict")
        _validate_failure_witness(value, source, receipt)
        _artifact(registry.store, source["artifact_ref"])
        return
    _require(source.get("parent_source_refs") == ensembl.ensembl_discovery_refs(arguments),
        "ensembl_saved_source_conflict")
    selection = _control(registry.store, auxiliary[0])
    _require(type(selection) is dict and set(selection) == {"version", "arguments", "direct_source_refs", "sources"}
        and selection["version"] == SELECTION_VERSION and _same(selection["arguments"], arguments)
        and selection["direct_source_refs"] == ensembl.ensembl_discovery_refs(arguments), "ensembl_selection_conflict")
    evidence, actual = _lineage(registry, arguments, admitted=admitted, read_entities=False,
        expected_entries=selection["sources"])
    _require(_same(actual, selection), "ensembl_selection_conflict")
    metadata = _artifact(registry.store, source["artifact_ref"])
    if type(value) is dict and value.get("version") == FAILURE_WITNESS_VERSION:
        _validate_failure_witness(value, source, receipt)
        return
    value = ensembl.validate_ensembl_value(value, evidence=evidence)
    _require(_same(value["requested"], arguments) and _same(control["request"], arguments)
        and value["raw_artifact_ref"] == source["artifact_ref"]
        and value["response"]["retained_bytes"] == metadata["size"]
        and _same(value["observed_transfer"], {key: control["transport"].get(key) for key in
            ("declared_body_bytes", "body_capture_failure")})
        and _same(ensembl.ensembl_receipt(value, source_ref=source["id"]), receipt),
        "ensembl_saved_receipt_conflict")
    if value["native_text"] is not None:
        raw = value["native_text"].encode("utf-8")
        _require(len(raw) == metadata["size"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"],
            "ensembl_artifact_identity_conflict")
        snapshot = SourceSnapshot("ensembl", source["uri"], arguments, source["retrieved_at"], raw,
            ensembl.ensembl_request_spec(arguments)["media_type"], control["transport"])
        _require(_same(ensembl.ensembl_value(snapshot, arguments=arguments,
            artifact_ref=source["artifact_ref"], evidence=evidence), value), "ensembl_saved_result_conflict")
    else:
        _require(value["decode_error"] == "invalid_native_utf8" and _same(value["response"],
            _saved_response(control["transport"], arguments, metadata["size"])), "ensembl_saved_response_conflict")


def authenticate_saved_ensembl_request(registry, arguments, *, authority=None, outcome):
    arguments = ensembl.validate_ensembl_arguments(arguments)
    with registry.store.read_snapshot():
        context, admitted = _admitted(registry, arguments, authority)
        value = outcome.get("result")
        receipt = ensembl.validate_ensembl_receipt(value) if _is_receipt(value) else None
        if receipt is not None and receipt["source_ref"] is None:
            _require(not receipt["acquired"] and outcome.get("record_refs") == []
                and outcome.get("status") in {"invalid", "unavailable", "failed"}, "ensembl_saved_outcome_conflict")
            return
        if value is None:
            _require(outcome.get("status") in {"invalid", "unavailable", "failed"}, "ensembl_saved_outcome_conflict")
            return
        refs = outcome.get("record_refs")
        _require(type(refs) is list and refs == (_receipt_refs(receipt) if receipt is not None else refs)
            and len(refs) == (2 if receipt is not None and receipt["acquired"] else 1), "ensembl_saved_outcome_conflict")
        source = _source(registry.store, refs[0])
        current_key = registry._current_invocation.get()
        expected = ({"operation_ref": outcome["operation_ref"], "operation_key": current_key[4]}
            if current_key is not None else None)
        _, selected, original = _operation(registry, source["id"], expected=expected,
            allow_pending=True, current_context=context)
        _require(_same(selected, arguments) and _same(original, outcome), "ensembl_saved_outcome_conflict")
        if receipt is not None:
            _require(receipt["source_ref"] == source["id"] and (not receipt["acquired"]
                or receipt["data_ref"] == source["artifact_ref"]), "ensembl_saved_receipt_conflict")
            _authenticate_saved_receipt(registry, arguments, source, receipt, admitted=admitted)
            return
        # A Source-only publication failure is durable custody, never a valid
        # parsed discovery response or an admission for its private artifacts.
        if value == {"retained_record_refs": [source["id"]]}:
            _require(outcome["status"] == "partial", "ensembl_saved_outcome_conflict")
            return
        validate_schema(value, ensembl.ensembl_result_schema())
        auxiliary = source.get("auxiliary_artifact_refs")
        _require(source.get("parent_source_refs") == ensembl.ensembl_discovery_refs(arguments)
            and type(auxiliary) is list and len(auxiliary) == 1, "ensembl_saved_source_conflict")
        selection = _control(registry.store, auxiliary[0])
        _require(type(selection) is dict and set(selection) == {"version", "arguments", "direct_source_refs", "sources"}
            and selection["version"] == SELECTION_VERSION and _same(selection["arguments"], arguments)
            and selection["direct_source_refs"] == ensembl.ensembl_discovery_refs(arguments),
            "ensembl_selection_conflict")
        evidence, actual = _lineage(registry, arguments, admitted=admitted, read_entities=False,
            expected_entries=selection["sources"])
        _require(_same(actual, selection) and value["source_ref"] == source["id"]
            and value["raw_artifact_ref"] == source["artifact_ref"], "ensembl_saved_source_conflict")
        control = _control(registry.store, source["request_ref"])
        _require(type(control) is dict and set(control) == {"request", "transport"}
            and _same(control["request"], arguments), "ensembl_source_request_conflict")
        metadata = _artifact(registry.store, source["artifact_ref"])
        if value["native_text"] is not None:
            raw = value["native_text"].encode("utf-8")
            _require(len(raw) == metadata["size"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"],
                "ensembl_artifact_identity_conflict")
            retained = SourceSnapshot("ensembl", source["uri"], arguments, source["retrieved_at"], raw,
                ensembl.ensembl_request_spec(arguments)["media_type"], control["transport"])
            actual_value = ensembl.ensembl_result(retained, arguments=arguments,
                source_ref=source["id"], artifact_ref=source["artifact_ref"], evidence=evidence)
            _require(_same(actual_value, value), "ensembl_saved_result_conflict")
        else:
            # Invalid UTF8 has no text reconstruction. Preserve this explicit
            # unavailable representation; do not invent a fresh entity read.
            ensembl.validate_ensembl_result(value, evidence=evidence)
            _require(value["decode_error"] == "invalid_native_utf8"
                and value["response"]["retained_bytes"] == metadata["size"], "ensembl_saved_result_conflict")
            _require(_same(value["response"], _saved_response(control["transport"], arguments, metadata["size"])),
                "ensembl_saved_response_conflict")


def _saved_response(transport, arguments, retained_bytes):
    """Project original control metadata without claiming another entity read."""
    _require(type(transport) is dict, "ensembl_saved_response_conflict")
    spec = ensembl.ensembl_request_spec(arguments)
    request, policy = transport.get("request"), transport.get("request_policy")
    _require(type(request) is dict and type(policy) is dict, "ensembl_saved_response_conflict")
    def observed(key, kind, minimum=None, maximum=None):
        value = transport.get(key)
        return value if type(value) is kind and (minimum is None or value >= minimum) and (
            maximum is None or value <= maximum) else None
    headers = transport.get("headers")
    def header(name):
        value = headers.get(name) if type(headers) is dict else None
        return value if type(value) is str else None
    return {"request_url": request.get("url"), "request_method": request.get("method"),
        "request_body_sha256": request.get("body_sha256"), "media_type": spec["media_type"],
        "http_status": observed("status", int, 100, 599), "content_type": header("content-type"),
        "body_complete": observed("body_complete", bool), "retained_bytes": retained_bytes,
        "reported_retained_bytes": observed("retained_body_bytes", int, 0),
        "observed_body_bytes": observed("observed_body_bytes", int, 0),
        "declared_body_bytes": observed("declared_body_bytes", int, 0),
        "response_byte_limit": observed("response_byte_limit", int, 0),
        "capture_failure": observed("body_capture_failure", str), "retry_after": header("retry-after"),
        "timeout_seconds": policy.get("timeout_seconds"), "automatic_redirects": policy.get("automatic_redirects")}


__all__ = ["prepare_ensembl_request", "publish_ensembl_request", "authenticate_saved_ensembl_request"]
