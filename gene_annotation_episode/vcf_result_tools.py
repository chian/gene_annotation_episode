"""Atomic ordinary derivation over an explicitly received VCF result.

The shared input owner supplies File authority; the pure VCF owner supplies
all parsing and calculation. Delivering the result Source grants no inputs,
private sheets or native-caller capability.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from . import vcf_result_measurements as core
from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, identity, obj
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .materials import source_window_selection
from .molecular_measurement_tools import (
    _publication_bytes, _recorded_molecular_action_details, _recorded_molecular_producer_details,
    authenticate_molecular_invocation, retain_molecular_publication,
)
from .molecular_sequence_input_contracts import (
    input_record_digest, validate_molecular_sequence_received_file,
)
from .native_file_capture import _metadata
from .tool_grading_artifacts import retain_tool_grading


TOOL = "result.variants.vcf"
SOURCE_VERSION = "ordinary_vcf_result_v1"
CONTROL_VERSION = "ordinary_vcf_publication_v1"
PACKET_VERSION = "ordinary_vcf_public_packet_v1"
FACT_SOURCE = "vcf_result_outcomes"
CALCULATOR_ID = "vcf_result_measurements.calculate_vcf_components"
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_ARTIFACT = re.compile(r"artifact_[a-f0-9]{64}\Z")
_CONTROL_KEYS = ("version arguments invocation admission_invocation received_input file_admission source_admission "
    "original_source sheet_ref components_ref public_packet_ref grading_ref native_call_state calculator_id implementation")


def _require(condition, code):
    if not condition:
        raise ContractError("vcf_result_" + code)


def _copy(value):
    return json.loads(canonical(value))


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "closed_fields_required")


def _arguments(arguments):
    arguments = _copy(arguments)
    _require(type(arguments) is dict, "arguments_invalid")
    mode = arguments.get("mode")
    if mode == "analyze":
        _closed(arguments, "mode namespace reference max_bytes capture_state original_size_bytes selection")
        namespace, reference = arguments["namespace"], arguments["reference"]
        _require(namespace in ("source", "artifact") and type(reference) is str
            and (_SOURCE if namespace == "source" else _ARTIFACT).fullmatch(reference) is not None,
            "input_selection_invalid")
        _require(type(arguments["max_bytes"]) is int and arguments["max_bytes"] >= 0, "max_bytes_invalid")
        _require(arguments["capture_state"] in ("complete", "truncated", "unknown")
            and (arguments["original_size_bytes"] is None or type(arguments["original_size_bytes"]) is int
                and arguments["original_size_bytes"] >= 0), "capture_invalid")
        arguments["selection"] = core.validate_vcf_selection(arguments["selection"], sheet=None)
    else:
        _require(mode in ("read_stored", "calculate_saved"), "mode_invalid")
        _closed(arguments, "mode result_ref" if mode == "read_stored" else "mode result_ref selection")
        _require(type(arguments["result_ref"]) is str and _SOURCE.fullmatch(arguments["result_ref"]) is not None,
            "source_required")
        if mode == "calculate_saved":
            arguments["selection"] = core.validate_vcf_selection(arguments["selection"], sheet=None)
    return arguments


def vcf_result_tool_contract():
    source = dict(type="string", pattern=r"^source_[a-f0-9]{24,64}$")
    selection = core.vcf_result_schema("Selection")
    selected = {"$ref": selection["$ref"]}
    schema = {"$schema": selection["$schema"], "$defs": selection["$defs"], "anyOf": [
        obj(dict(mode=dict(type="string", const="analyze"), namespace=dict(enum=["source", "artifact"]),
            reference=dict(type="string", minLength=1), max_bytes=dict(type="integer", minimum=0),
            capture_state=dict(enum=["complete", "truncated", "unknown"]),
            original_size_bytes=dict(type=["integer", "null"], minimum=0), selection=deepcopy(selected))),
        obj(dict(mode=dict(type="string", const="read_stored"), result_ref=deepcopy(source))),
        obj(dict(mode=dict(type="string", const="calculate_saved"), result_ref=deepcopy(source),
            selection=deepcopy(selected))),
    ]}
    return dict(resources="local", invocation_route=dict(kind="direct"), input_schema=schema,
        description="Inspect an explicitly received VCF result and return selected native fields, associations and qualified populations.",
        instructions=("Use the supplied VCF File and explicit selection to answer the assigned scientific question. "
            "analyze preserves original bytes, header declarations, ordered records, alleles and samples. Caller capture_state "
            "and original_size_bytes describe input extent, not native execution success. max_bytes bounds the complete "
            "received File; oversize input is rejected rather than silently truncated. Preserve FILTER dot versus PASS, "
            "declared cardinalities, missing tokens and native genotypes. Do not infer reference build, normal sample, "
            "caller execution, functional annotation or clinical interpretation. This operation does not run Mutect2, LUMPY, "
            "filtering or annotation software. read_stored returns the original literal public group. calculate_saved applies "
            "explicit selection to the authenticated sheet and publishes a distinct derived Source without reading or parsing "
            "the original File. Row windows affect returned rows, not selected population denominators. Only the result Source "
            "is delivered; nested input identities are provenance and grant no File access."))


def vcf_result_fact_sources():
    schema = core.vcf_result_schema("Return")
    report = {"$schema": schema["$schema"], "$defs": schema["$defs"], "type": "array",
        "items": {"$ref": schema["$ref"]}, "x-source": FACT_SOURCE}
    report["$id"] = "urn:gene-annotation:vcf-result-return:" + digest(report)
    return {FACT_SOURCE: dict(type="array",
        meaning=("Selected retained VCF fields, original associations, record/allele/sample populations and capture qualifications. "
            "Supplied-result analysis does not establish execution or success of a variant caller or annotation pipeline."),
        report_schema=report)}


def _invocation(context, operation_key):
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(suffix.isdecimal() and str(int(suffix)) == suffix, "action_key_invalid")
    return dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=digest(plain(context.request)), scope=plain(context.scope))


def _context(registry, invocation):
    _closed(invocation, "run_id episode_id operation_key decision_index request_sha256 scope")
    _require(type(invocation["decision_index"]) is int and invocation["decision_index"] >= 0, "invocation_conflict")
    records = EpisodeReturnRecords(registry.store, invocation["run_id"], failure_prefix="vcf_result_")
    context = records.context(invocation["episode_id"])
    _require(canonical(_invocation(context, invocation["operation_key"])) == canonical(invocation), "invocation_conflict")
    return context


def _cutoff(registry, context):
    active = registry._current_invocation.get()
    if active is not None and active[0] is context:
        return _invocation(context, active[4])["decision_index"]
    return registry.store.db.execute("SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions "
        "WHERE run_id=? AND episode_id=?", (context.run_id, context.episode_id)).fetchone()[0]


def _source_admission(registry, context, reader, source_ref, cutoff):
    _require(callable(reader), "input_reader_required")
    admitted = reader(context, source_ref, "source", source_metadata_only=True)
    _require(type(admitted) is dict and admitted.get("failure") is None
        and admitted.get("selection") == dict(reference=source_ref, namespace="source"), "source_not_received")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="vcf_result_")
    records.authenticate(context)
    return records.source_admission_before(context, source_ref, cutoff)


def _received_file(registry, context, received):
    received = validate_molecular_sequence_received_file(received)
    if received["failure"] is not None:
        _require(False, received["failure"]["code"])
    _require(received["input"] is not None, "file_not_received")
    item, selected = received["input"], received["selection"]
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    record = registry.store.get(selected["reference"])
    _require(item["byte_verification"] == "verified" and item["receiver"] == dict(run_id=context.run_id,
        episode_id=context.episode_id, request_sha256=input_record_digest(plain(context.request)),
        assignment_sha256=input_record_digest(plain(context.assignment)))
        and canonical(item["scope"]) == canonical(registry.store.validate_scope(plain(context.scope)))
        and canonical(item["inheritance_manifest"]) == canonical(manifest)
        and canonical(plain(context.request)["message"].get("knowledge_inheritance")) == canonical(manifest)
        and canonical(item["witness"]["record"]) == canonical(record)
        and item["witness"]["record_sha256"] == input_record_digest(record), "input_admission_conflict")
    return received


def _prepare_analyze(registry, context, reader, arguments, invocation):
    reference, namespace = arguments["reference"], arguments["namespace"]
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="vcf_result_")
    records.authenticate(context)
    if namespace == "source":
        _source_admission(registry, context, reader, reference, invocation["decision_index"])
        artifact_ref, representation, _ = source_window_selection(registry.store.get(reference), "original")
        _require(representation == "original" and type(artifact_ref) is str, "original_file_required")
    else:
        artifact_ref = reference
    # Timing authority precedes even the input reader's streamed verification.
    admission = records.file_admission_before(context, reference, namespace, artifact_ref, invocation["decision_index"])
    metadata = _metadata(registry.store, artifact_ref)
    _require(metadata["size"] <= arguments["max_bytes"], "input_exceeds_max_bytes")
    received, path = reader(context, reference, namespace, file_format="vcf")
    received = _received_file(registry, context, received)
    file = received["input"]["file"]
    _require(path is not None and received["selection"] == dict(reference=reference, namespace=namespace)
        and file == dict(artifact_ref=artifact_ref, sha256=metadata["sha256"], size_bytes=metadata["size"], format="vcf"),
        "input_identity_conflict")
    with Path(path).open("rb") as handle:
        content = handle.read(file["size_bytes"] + 1)
    _require(len(content) == file["size_bytes"] and hashlib.sha256(content).hexdigest() == file["sha256"], "input_identity_conflict")
    capture = dict(state=arguments["capture_state"], byte_start_0based=0,
        byte_end_0based_exclusive=len(content), original_size_bytes=arguments["original_size_bytes"])
    sheet = core.parse_vcf_sheet(dict(input_id=reference, retained_file=file,
        original_file=file if arguments["capture_state"] == "complete" else None,
        source_ref=reference if namespace == "source" else None, content=content, capture=capture))
    selection = core.validate_vcf_selection(arguments["selection"], sheet=sheet)
    return dict(arguments=arguments, invocation=invocation, admission_invocation=invocation,
        received_input=received, file_admission=admission, source_admission=None, original_source=None,
        sheet=sheet, components=core.calculate_vcf_components(sheet, selection))


def _packet(public):
    return dict(version=PACKET_VERSION, value=deepcopy(public["value"]))


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None, read_packet=True):
    _require(type(read_packet) is bool, "read_mode_invalid")
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == TOOL and source.get("version") == SOURCE_VERSION and "operand_refs" not in source,
        "producer_required")
    details = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = _arguments(details["arguments"])
    public = core.validate_vcf_return(details["outcome"]["result"])
    _require(public["source_ref"] == source_ref and details["outcome"]["record_refs"] == [source_ref], "publication_conflict")
    _require(arguments["mode"] in ("analyze", "calculate_saved")
        and canonical(public["value"]["selection"]) == canonical(arguments["selection"]), "selection_conflict")
    parents = ([arguments["reference"]] if arguments["mode"] == "analyze" and arguments["namespace"] == "source" else
        [] if arguments["mode"] == "analyze" else [arguments["result_ref"]])
    _require(source.get("parent_source_refs") == parents, "parent_sources_conflict")
    references = source.get("auxiliary_artifact_refs")
    _require(type(references) is list and len(references) == 3 and len(set(references)) == 3
        and all(type(ref) is str and _ARTIFACT.fullmatch(ref) for ref in references), "private_files_conflict")
    # Literal reads authenticate only the public packet. Missing private body
    # siblings cannot erase independently retained public values.
    packet = None
    if read_packet:
        packet = json.loads(_publication_bytes(registry.store, source["artifact_ref"]))
        _require(canonical(packet) == canonical(_packet(public)), "public_packet_conflict")
    return dict(source=source, producer=details, public=public, packet=packet,
        sheet_ref=references[0], components_ref=references[1], grading_ref=references[2])


def _control(registry, publication, seen):
    source, details = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = {*seen, source["id"]}
    control = json.loads(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, _CONTROL_KEYS)
    _require(control["version"] == CONTROL_VERSION and control["native_call_state"] == "not_requested"
        and control["calculator_id"] == CALCULATOR_ID
        and canonical(control["arguments"]) == canonical(details["arguments"])
        and canonical(control["invocation"]) == canonical(details["invocation"])
        and control["public_packet_ref"] == source["artifact_ref"]
        and all(control[key] == publication[key] for key in ("sheet_ref", "components_ref", "grading_ref")), "control_conflict")
    _require(type(control["implementation"]) is dict and set(control["implementation"]) == {
        "vcf_result_tools.py", "vcf_result_measurements.py"} and all(type(pin) is dict and set(pin) == {"sha256", "size_bytes"}
        and type(pin["sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", pin["sha256"])
        and type(pin["size_bytes"]) is int and pin["size_bytes"] > 0 for pin in control["implementation"].values()),
        "implementation_conflict")
    context = _context(registry, control["invocation"])
    arguments = _arguments(control["arguments"])
    if arguments["mode"] == "analyze":
        _require(control["source_admission"] is control["original_source"] is None
            and canonical(control["admission_invocation"]) == canonical(control["invocation"]), "control_conflict")
        received = _received_file(registry, context, control["received_input"])
        selected, file = received["selection"], received["input"]["file"]
        _require(selected == dict(reference=arguments["reference"], namespace=arguments["namespace"])
            and file["format"] == "vcf" and file["size_bytes"] <= arguments["max_bytes"], "input_admission_conflict")
        records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="vcf_result_")
        admitted = records.file_admission_before(context, selected["reference"], selected["namespace"],
            file["artifact_ref"], control["invocation"]["decision_index"])
        _require(canonical(admitted) == canonical(control["file_admission"]), "input_admission_conflict")
        descriptor = dict(input_id=arguments["reference"], retained_file=file,
            original_file=file if arguments["capture_state"] == "complete" else None,
            source_ref=arguments["reference"] if arguments["namespace"] == "source" else None,
            capture=dict(state=arguments["capture_state"], byte_start_0based=0,
                byte_end_0based_exclusive=file["size_bytes"], original_size_bytes=arguments["original_size_bytes"]))
        _require(canonical(publication["public"]["value"]["input"]) == canonical(descriptor), "input_descriptor_conflict")
    else:
        original = control["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(original["source_ref"] == arguments["result_ref"], "original_source_conflict")
        records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="vcf_result_")
        admitted = records.source_admission_before(context, original["source_ref"], control["invocation"]["decision_index"])
        _require(canonical(admitted) == canonical(control["source_admission"]), "source_admission_conflict")
        parent = _metadata_publication(registry, original["source_ref"])
        _require(original["record_sha256"] == digest(parent["source"]), "original_source_conflict")
        previous = _control(registry, parent, seen)
        _require(all(canonical(control[key]) == canonical(previous[key]) for key in
            ("admission_invocation", "received_input", "file_admission", "sheet_ref")), "saved_observations_conflict")
        _require(canonical(publication["public"]["value"]["input"]) == canonical(parent["public"]["value"]["input"]),
            "saved_observations_conflict")
    return control


def _read_vcf_result_publication(registry, context, reader, source_ref, *, require_sheet=False,
        recovery_operation_key=None, before_decision_index=None):
    _require(type(require_sheet) is bool, "read_mode_invalid")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="vcf_result_")
    records.authenticate(context)
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key, read_packet=False)
    invocation = publication["producer"]["invocation"]
    own = recovery_operation_key == invocation["operation_key"] and (context.run_id, context.episode_id) == (
        invocation["run_id"], invocation["episode_id"])
    cutoff = _cutoff(registry, context) if before_decision_index is None else before_decision_index
    admission = None if own else _source_admission(registry, context, reader, source_ref, cutoff)
    packet = json.loads(_publication_bytes(registry.store, publication["source"]["artifact_ref"]))
    _require(canonical(packet) == canonical(_packet(publication["public"])), "public_packet_conflict")
    publication.update(source_admission=admission, packet=packet, control=None, sheet=None)
    if not require_sheet:
        return publication
    control = _control(registry, publication, set())
    sheet = core.validate_vcf_sheet(json.loads(_publication_bytes(registry.store, control["sheet_ref"])))
    _require(canonical(sheet["input"]) == canonical(publication["public"]["value"]["input"]), "sheet_input_conflict")
    publication.update(control=control, sheet=sheet)
    return publication


def read_vcf_result_publication(registry, context, reader, source_ref, *, require_sheet=False, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_vcf_result_publication(registry, context, reader, source_ref,
            require_sheet=require_sheet, recovery_operation_key=recovery_operation_key)


def read_retained_vcf_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    publication = read_vcf_result_publication(registry, context, reader, source_ref,
        recovery_operation_key=recovery_operation_key)
    return {**publication, "stored": publication["public"]}


def _prepare_saved(registry, context, reader, arguments, invocation):
    publication = read_vcf_result_publication(registry, context, reader, arguments["result_ref"],
        require_sheet=arguments["mode"] == "calculate_saved")
    if arguments["mode"] == "read_stored":
        return dict(public=publication["public"])
    sheet, control = publication["sheet"], publication["control"]
    selection = core.validate_vcf_selection(arguments["selection"], sheet=sheet)
    return dict(arguments=arguments, invocation=invocation, sheet=sheet,
        components=core.calculate_vcf_components(sheet, selection),
        **{key: deepcopy(control[key]) for key in ("admission_invocation", "received_input", "file_admission")},
        source_admission=publication["source_admission"], original_source=dict(source_ref=publication["source"]["id"],
            record_sha256=digest(publication["source"])))


def _retain_vcf_result_publication(registry, prepared):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    sheet = core.validate_vcf_sheet(prepared["sheet"])
    components = core.validate_vcf_components(prepared["components"])
    _require(components["sheet_sha256"] == core._hash(sheet)
        and canonical(components["value"]["input"]) == canonical(sheet["input"])
        and canonical(components["value"]["selection"]) == canonical(prepared["arguments"]["selection"]),
        "components_input_conflict")
    sheet_ref = registry.store.artifact(canonical(sheet), "application/json")
    components_ref = registry.store.artifact(canonical(components), "application/json")
    packet_ref = registry.store.artifact(canonical(dict(version=PACKET_VERSION, value=components["value"])), "application/json")
    grading_ref = retain_tool_grading(registry.store, provider=TOOL, native_artifact_ref=packet_ref,
        grading=dict(sheet=sheet, scores=components))
    implementation = {path.name: dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size_bytes=path.stat().st_size)
        for path in (Path(__file__), Path(core.__file__))}
    control = dict(version=CONTROL_VERSION, **{key: deepcopy(prepared[key]) for key in
        ("arguments", "invocation", "admission_invocation", "received_input", "file_admission", "source_admission", "original_source")},
        sheet_ref=sheet_ref, components_ref=components_ref, public_packet_ref=packet_ref, grading_ref=grading_ref,
        native_call_state="not_requested", calculator_id=CALCULATOR_ID, implementation=implementation)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    arguments = prepared["arguments"]
    parents = ([arguments["reference"]] if arguments["mode"] == "analyze" and arguments["namespace"] == "source" else
        [] if arguments["mode"] == "analyze" else [arguments["result_ref"]])
    source = registry.store.put("source", dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=parents, auxiliary_artifact_refs=[sheet_ref, components_ref, grading_ref]), origin="tool")
    return dict(source=source, public=core.project_vcf_return(components, source_ref=source["id"]),
        sheet=sheet, components=components, control=control)


def read_vcf_result_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial") and type(outcome.get("result")) is dict,
        "action_result_unavailable")
    public = core.validate_vcf_return(outcome["result"])
    _require(outcome.get("record_refs") == [public["source_ref"]], "action_source_conflict")
    with registry.store.read_snapshot():
        publication = _read_vcf_result_publication(registry, context, reader, public["source_ref"],
            recovery_operation_key=operation_key if arguments["mode"] != "read_stored" else None,
            before_decision_index=details["invocation"]["decision_index"])
    _require(canonical(publication["public"]) == canonical(public), "action_source_conflict")
    if arguments["mode"] == "read_stored":
        _require(arguments["result_ref"] == public["source_ref"], "action_source_conflict")
    else:
        _require(publication["producer"]["invocation"]["operation_key"] == operation_key, "action_source_conflict")
    return public


def execute_vcf_result(registry, arguments, *, scope, operation_key, authority):
    """Authenticate and commit one derivation; no worker or caller execution."""
    arguments = _copy(arguments)
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    invocation = _invocation(context, operation_key)
    with registry.store.transaction():
        saved = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        if saved is not None:
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed", "partial"):
                _require(canonical(read_vcf_result_action_result(registry, context, arguments, operation_key, reader=reader))
                    == canonical(outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("invalid", "unavailable", "failed") and outcome.get("result") is None
                    and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        try:
            with registry.store.transaction():
                arguments = _arguments(arguments)
                prepared = (_prepare_analyze(registry, context, reader, arguments, invocation) if arguments["mode"] == "analyze" else
                    _prepare_saved(registry, context, reader, arguments, invocation))
                public = (prepared["public"] if arguments["mode"] == "read_stored" else
                    retain_molecular_publication(registry, prepared, tool_name=TOOL)["public"])
                value = public["value"]
                partial = (bool(value["issues"]) or value["input"]["capture"]["state"] != "complete"
                    or not value["population"]["record_population_complete"])
                outcome = dict(status="partial" if partial else "completed", operation_ref=identity("operation", dict(
                    key=operation_key, name=TOOL, arguments=arguments)), record_refs=[public["source_ref"]],
                    changed_record_refs=[] if arguments["mode"] == "read_stored" else [public["source_ref"]], result=public,
                    feedback=None if not partial else dict(category="representation", code="vcf_result_partial", source_ref=public["source_ref"]))
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
        except Exception as error:
            text = str(error)
            code = text if re.fullmatch(r"[a-z][a-z0-9_]*", text) else "vcf_result_input_invalid"
            diagnostic = registry.store.artifact(canonical(dict(version="vcf_result_diagnostic_v1",
                exception_type=type(error).__module__ + "." + type(error).__name__, exception_message=text)), "application/json")
            outcome = dict(status="unavailable" if isinstance(error, OSError) or code.endswith("_unavailable") else
                "invalid" if isinstance(error, (ContractError, ValueError, KeyError, TypeError)) else "failed",
                operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)), record_refs=[],
                changed_record_refs=[], result=None, feedback=dict(category="arguments_or_reference", code=code, diagnostic_ref=diagnostic))
            registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
        return outcome


__all__ = ["TOOL", "SOURCE_VERSION", "CONTROL_VERSION", "PACKET_VERSION", "FACT_SOURCE",
    "vcf_result_tool_contract", "vcf_result_fact_sources", "execute_vcf_result", "read_vcf_result_publication",
    "read_retained_vcf_publication", "read_vcf_result_action_result"]
