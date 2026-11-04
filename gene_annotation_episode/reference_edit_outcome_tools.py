"""Ordinary retained reference/edit analysis, without a native worker.

Only actual selected actions and admitted records may supply the pure kernel.
Public Source bytes contain the public value packet; raw captures and input
strings remain in private custody. Reading a Source never grants its Files.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from . import reference_edit_outcomes as core
from .alignment_site_native import (
    _selected_reference_alignment_authority, immutable_record, original_mappings,
    read_selected_reference_alignment, source_descriptor,
)
from .communication import plain
from .domain import ContractError, identity, obj
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .molecular_sequence_input_contracts import (
    SUBJECT_NAMESPACES, input_record_digest, validate_molecular_sequence_received_source,
    validate_molecular_sequence_received_subject,
)
from .native_file_capture import _metadata
from .molecular_measurement_tools import (
    _publication_bytes, _recorded_molecular_action_details, _recorded_molecular_producer_details,
    authenticate_molecular_invocation, retain_molecular_publication,
)
from .tool_grading_artifacts import MEDIA_TYPE, retain_tool_grading, source_tool_grading_entries


TOOL = "analyze_cas9_mutation_outcomes"
RESULT_VERSION = "ordinary_reference_edit_outcome_result_v1"
SOURCE_VERSION = RESULT_VERSION
PACKET_VERSION = "ordinary_reference_edit_outcome_packet_v1"
CONTROL_VERSION = "ordinary_reference_edit_outcome_publication_v1"
_REQUEST_KEYS = ("population", "gap_bins", "guide_comparisons", "template_comparisons")
_CONTROL_KEYS = ("version arguments invocation request admission_invocation alignments comparisons source_admission "
    "original_source envelope_ref public_packet_ref grading_ref native_call_state calculator_id implementation")


def _require(condition, code):
    if not condition: raise ContractError("reference_edit_outcome_" + code)


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "closed_fields_required")


def _request(arguments):
    return core._request(dict(version=core.REQUEST_VERSION, **{key: arguments[key] for key in _REQUEST_KEYS}))


def _arguments(arguments):
    arguments = core._json(arguments)
    _require(type(arguments) is dict, "arguments_invalid")
    mode = arguments.get("mode")
    if mode == "analyze":
        _closed(arguments, "mode population gap_bins guide_comparisons template_comparisons")
        _request(arguments)
    else:
        _require(mode in ("read_stored", "calculate_saved"), "mode_invalid")
        _closed(arguments, "mode result_ref" if mode == "read_stored" else "mode result_ref gap_bins")
        _require(type(arguments["result_ref"]) is str and core._SOURCE.fullmatch(arguments["result_ref"]) is not None,
            "source_required")
        if mode == "calculate_saved":
            # Only the existing pure parameter grammar is evaluated here.
            core._request(dict(version=core.REQUEST_VERSION, population=[], gap_bins=arguments["gap_bins"],
                guide_comparisons=[], template_comparisons=[]))
    return arguments


def reference_edit_outcome_tool_contract():
    """One direct callable; saved modes need no original native deployment."""
    reference = dict(type="string", minLength=1)
    pair = obj(dict(reference_ref=reference, edited_ref=reference,
        alignment_ref=dict(type=["string", "null"], minLength=1), group_label=dict(type=["string", "null"])))
    guide = obj(dict(**deepcopy(core._COMPARISON_SELECTION), guide_ref=reference, reference_interval=deepcopy(core._INTERVAL)))
    template = obj(dict(**deepcopy(core._COMPARISON_SELECTION), template_ref=reference,
        edited_interval=deepcopy(core._INTERVAL), reference_interval=core._nullable(deepcopy(core._INTERVAL))))
    selected = dict(type="string", pattern=r"^source_[a-f0-9]{24,64}$")
    schema = dict(anyOf=[obj(dict(mode=dict(type="string", const="analyze"), population=dict(type="array", items=pair),
        gap_bins=deepcopy(core._BINS), guide_comparisons=dict(type="array", items=guide), template_comparisons=dict(type="array", items=template))),
        obj(dict(mode=dict(type="string", const="read_stored"), result_ref=selected)),
        obj(dict(mode=dict(type="string", const="calculate_saved"), result_ref=selected, gap_bins=deepcopy(core._BINS)))])
    return dict(resources="local", invocation_route=dict(kind="direct"), input_schema=schema,
        description="Analyze explicitly paired reference and edited nucleotide sequences through selected retained alignments.",
        instructions=("Preserve the assigned question and supplied population. analyze reads actual selected retained alignment observations; "
            "null alignment_ref means not selected, not failed or unchanged. Keep original order, duplicate occurrences, native models, "
            "partial geometry, zero, missing values, units and both declared/classified denominators. Guide placements and template windows "
            "are explicitly supplied literal comparisons; do not infer cleavage, HDR, NHEJ or biological success. "
            "No alignment, acquisition or native worker is requested. read_stored returns the original Source's complete literal group. "
            "calculate_saved preserves frozen observations, pairing and placements, applies explicit gap_bins and publishes a distinct derived "
            "Source; historical values remain unchanged. Only the result Source is delivered; provenance identities grant no input or private Files."))


def reference_edit_outcome_fact_sources():
    """The exact public group; only its result Source is a semantic reference."""
    return {"reference_edit_outcomes": dict(type="array",
        meaning=("Recorded reference/edited nucleotide outcome groups, preserving ordered submitted occurrences, selected native "
            "correspondence, observed edit types, explicit gap bins, supplied guide/template comparisons, units, missingness "
            "and declared versus classified populations; these values do not infer repair mechanisms."),
        report_schema=dict(type="array", items=deepcopy(core.RETURN_SCHEMA), **{"x-source": "reference_edit_outcomes"}))}


def _invocation(context, operation_key):
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(suffix.isdecimal() and str(int(suffix)) == suffix, "action_key_invalid")
    return dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=digest(plain(context.request)), scope=plain(context.scope))


def _context(store, invocation):
    _closed(invocation, "run_id episode_id operation_key decision_index request_sha256 scope")
    _require(type(invocation["decision_index"]) is int and invocation["decision_index"] >= 0, "invocation_conflict")
    records = EpisodeReturnRecords(store, invocation["run_id"], failure_prefix="reference_edit_outcome_")
    context = records.context(invocation["episode_id"])
    _require(canonical(_invocation(context, invocation["operation_key"])) == canonical(invocation), "invocation_conflict")
    return context


def _frozen_admission(store, context, received, reference, namespace, cutoff):
    validate = validate_molecular_sequence_received_source if namespace == "source" else validate_molecular_sequence_received_subject
    received = validate(received)
    _require(received["failure"] is None and received["selection"] == dict(reference=reference, namespace=namespace), "input_not_received")
    item = received["input"]
    records = EpisodeReturnRecords(store, context.run_id, failure_prefix="reference_edit_outcome_")
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(store.db, context.run_id, context.episode_id)
    _require(item["receiver"] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and canonical(item["scope"]) == canonical(store.validate_scope(plain(context.scope)))
        and canonical(item["inheritance_manifest"]) == canonical(manifest)
        and canonical(plain(context.request)["message"].get("knowledge_inheritance")) == canonical(manifest)
        and canonical(item["witness"]["record"]) == canonical(store.get(reference))
        and records._received_before(context.episode_id, reference, cutoff), "input_admission_conflict")
    return received


def _admit(store, reader, context, reference, namespace, cutoff):
    _require(callable(reader), "input_reader_required")
    received = reader(context, reference, namespace, **{
        "source_metadata_only" if namespace == "source" else "subject_metadata_only": True})
    return _frozen_admission(store, context, received, reference, namespace, cutoff)


def _comparison_models(request):
    models = {}
    for name in ("guide_comparisons", "template_comparisons"):
        for selected in request[name]:
            pair = request["population"][selected["pair_ordinal"]]
            refs = [selected["guide_ref"], pair["reference_ref"]] if name == "guide_comparisons" else [selected["template_ref"], pair["edited_ref"]]
            if name == "template_comparisons" and selected["reference_interval"] is not None: refs.append(pair["reference_ref"])
            for reference in refs: models.setdefault(reference, set()).add(selected["molecule"])
    return models


def _comparison_admissions(registry, context, reader, request, cutoff):
    result = []
    for reference in core._comparison_refs(request):
        namespace = registry.store.get(reference)["record_type"]
        _require(namespace in SUBJECT_NAMESPACES, "sequence_subject_required")
        result.append(_admit(registry.store, reader, context, reference, namespace, cutoff))
    return result


def _literal_inputs(registry, context, request, admissions):
    sequences, witnesses, models = [], [], _comparison_models(request)
    for admission in admissions:
        reference = admission["selection"]["reference"]
        failure = None
        try:
            registry._check_sequence_operand(reference, plain(context.scope))
            try:
                sequence = registry._sequence(reference)
            except ContractError as error:
                if str(error) != "explicit_sequence_model_required": raise
                _require(len(models[reference]) == 1, "sequence_model_conflict")
                sequence = registry._sequence(reference, molecule_model=next(iter(models[reference])))
        except OSError:
            sequence, failure = None, "sequence_bytes_unavailable"
        except ContractError as error:
            if str(error) != "referenced_record_has_no_sequence": raise
            sequence, failure = None, "sequence_not_available"
        _require(sequence is None or type(sequence) is str, "sequence_capture_invalid")
        sequences.append(dict(subject_ref=reference, sequence=sequence))
        witnesses.append(dict(admission=admission, sequence_sha256=None if sequence is None else hashlib.sha256(sequence.encode("utf-8")).hexdigest(),
            failure_code=failure))
    return dict(sequences=sequences), witnesses


def _prepare_analyze(registry, context, reader, arguments, invocation):
    request, cutoff = _request(arguments), invocation["decision_index"]
    authorities = [None if pair["alignment_ref"] is None else _selected_reference_alignment_authority(
        registry.store, context, pair["alignment_ref"], before_decision_index=cutoff) for pair in request["population"]]
    for pair, selected in zip(request["population"], authorities):
        if selected is not None:
            _require(selected["operands"]["query"]["subject_ref"] == pair["edited_ref"]
                and selected["operands"]["reference"]["subject_ref"] == pair["reference_ref"], "selected_pair_conflict")
    admitted = _comparison_admissions(registry, context, reader, request, cutoff)
    captures = [None if pair["alignment_ref"] is None else read_selected_reference_alignment(registry.store, context,
        pair["alignment_ref"], before_decision_index=cutoff) for pair in request["population"]]
    comparisons, witnesses = _literal_inputs(registry, context, request, admitted)
    sheet = core.populate_reference_edit_outcome_sheet(request, alignment_inputs=captures, comparison_inputs=comparisons)
    components = core.calculate_reference_edit_outcome_components(sheet)
    return dict(arguments=arguments, invocation=invocation, request=request,
        stored=dict(version=RESULT_VERSION, request=request, sheet=sheet, components=components), admission_invocation=invocation,
        alignments=[dict(pair_ordinal=i, admission=selected["admission"], capture_sha256=digest(captures[i]))
            for i, selected in enumerate(authorities) if selected is not None], comparisons=witnesses,
        source_admission=None, original_source=None)


def _packet(public):
    return dict(version=PACKET_VERSION, value={key: deepcopy(value) for key, value in public.items() if key not in ("version", "source_ref")})


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == TOOL and source.get("version") == RESULT_VERSION and "operand_refs" not in source,
        "producer_required")
    details = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = _arguments(details["arguments"])
    public = core.validate_reference_edit_outcome_return(details["outcome"]["result"])
    _require(public["source_ref"] == source_ref and details["outcome"]["record_refs"] == [source_ref], "publication_conflict")
    parents = (list(dict.fromkeys(pair["source_ref"] for pair in public["pairs"] if pair["source_ref"] is not None))
        if arguments["mode"] == "analyze" else [arguments["result_ref"]])
    _require(source.get("parent_source_refs") == parents, "parent_sources_conflict")
    references = source.get("auxiliary_artifact_refs")
    _require(type(references) is list and len(references) == 2 and len(set(references)) == 2, "private_files_conflict")
    metadata = [_metadata(registry.store, reference) for reference in references]
    _require(metadata[0]["media_type"] == "application/json" and metadata[1]["media_type"] == MEDIA_TYPE,
        "private_files_conflict")
    _metadata(registry.store, source["request_ref"])
    packet = json.loads(_publication_bytes(registry.store, source["artifact_ref"]))
    _require(canonical(packet) == canonical(_packet(public)), "public_packet_conflict")
    return dict(source=source, producer=details, public=public, packet=packet,
        envelope_ref=references[0], grading_ref=references[1])


def _request_from_public(public, gap_bins):
    return core._request(dict(version=core.REQUEST_VERSION, gap_bins=deepcopy(gap_bins),
        population=[{key: pair[key] for key in ("reference_ref", "edited_ref", "alignment_ref", "group_label")} for pair in public["pairs"]],
        guide_comparisons=[{key: row[key] for key in ("pair_ordinal", "guide_ref", "reference_interval", "orientation", "molecule")}
            for row in public["guide_comparisons"]],
        template_comparisons=[{key: row[key] for key in ("pair_ordinal", "template_ref", "edited_interval", "reference_interval", "orientation", "molecule")}
            for row in public["template_comparisons"]]))


def _control(registry, publication, seen):
    source, details = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = {*seen, source["id"]}
    control = json.loads(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, _CONTROL_KEYS)
    _require(control["version"] == CONTROL_VERSION and control["native_call_state"] == "not_requested"
        and control["calculator_id"] == core.COMPONENT_VERSION and type(control["implementation"]) is dict
        and canonical(control["arguments"]) == canonical(details["arguments"])
        and canonical(control["invocation"]) == canonical(details["invocation"])
        and control["public_packet_ref"] == source["artifact_ref"] and control["envelope_ref"] == publication["envelope_ref"]
        and control["grading_ref"] == publication["grading_ref"], "control_conflict")
    _require(set(control["implementation"]) == {"reference_edit_outcome_tools.py", "reference_edit_outcomes.py"}
        and all(type(pin) is dict and set(pin) == {"sha256", "size_bytes"}
            and type(pin["sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", pin["sha256"])
            and type(pin["size_bytes"]) is int and pin["size_bytes"] > 0
            for pin in control["implementation"].values()), "implementation_conflict")
    request = core._request(control["request"])
    _require(canonical(request) == canonical(_request_from_public(publication["public"], publication["public"]["gap_bins"])), "request_conflict")
    producer_context = _context(registry.store, control["invocation"])
    if control["arguments"]["mode"] == "analyze":
        _require(control["original_source"] is control["source_admission"] is None
            and canonical(control["admission_invocation"]) == canonical(control["invocation"])
            and canonical(request) == canonical(_request(control["arguments"])), "control_conflict")
    else:
        original = control["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(original["source_ref"] == control["arguments"]["result_ref"], "original_source_conflict")
        parent = _metadata_publication(registry, original["source_ref"])
        _require(original["record_sha256"] == digest(parent["source"]), "original_source_conflict")
        _frozen_admission(registry.store, producer_context, control["source_admission"], original["source_ref"], "source",
            control["invocation"]["decision_index"])
        previous = _control(registry, parent, seen)
        _require(canonical(request) == canonical({**previous["request"], "gap_bins": control["arguments"]["gap_bins"]})
            and all(canonical(control[key]) == canonical(previous[key]) for key in ("admission_invocation", "alignments", "comparisons")),
            "saved_observations_conflict")
    admission_context = _context(registry.store, control["admission_invocation"])
    _require(type(control["alignments"]) is list, "admission_conflict")
    selected = [(i, pair) for i, pair in enumerate(request["population"]) if pair["alignment_ref"] is not None]
    _require(len(selected) == len(control["alignments"]), "admission_conflict")
    for (ordinal, pair), witness in zip(selected, control["alignments"]):
        _closed(witness, "pair_ordinal admission capture_sha256")
        authority = _selected_reference_alignment_authority(registry.store, admission_context, pair["alignment_ref"],
            before_decision_index=control["admission_invocation"]["decision_index"])
        _require(type(witness["pair_ordinal"]) is int and witness["pair_ordinal"] == ordinal
            and type(witness["capture_sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", witness["capture_sha256"])
            and canonical(witness["admission"]) == canonical(authority["admission"])
            and authority["operands"]["query"]["subject_ref"] == pair["edited_ref"]
            and authority["operands"]["reference"]["subject_ref"] == pair["reference_ref"], "admission_conflict")
    _require(type(control["comparisons"]) is list and len(control["comparisons"]) == len(core._comparison_refs(request)), "admission_conflict")
    for reference, witness in zip(core._comparison_refs(request), control["comparisons"]):
        _closed(witness, "admission sequence_sha256 failure_code")
        _require((witness["sequence_sha256"] is None and witness["failure_code"] in
                ("sequence_bytes_unavailable", "sequence_not_available"))
            or (type(witness["sequence_sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", witness["sequence_sha256"])
                and witness["failure_code"] is None), "admission_conflict")
        namespace = witness["admission"]["selection"]["namespace"]
        _require(namespace in SUBJECT_NAMESPACES, "admission_conflict")
        _frozen_admission(registry.store, admission_context, witness["admission"], reference, namespace,
            control["admission_invocation"]["decision_index"])
    return control


def _read_reference_edit_outcome_publication(registry, context, reader, source_ref, *,
        require_envelope=False, recovery_operation_key=None, before_decision_index=None):
    _require(type(require_envelope) is bool, "read_mode_invalid")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="reference_edit_outcome_")
    records.authenticate(context)
    publication = _metadata_publication(registry, source_ref, recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication["producer"]["invocation"]
    own = recovery_operation_key is not None and recovery_operation_key == invocation["operation_key"] and (
        context.run_id, context.episode_id) == (invocation["run_id"], invocation["episode_id"])
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    _require(type(cutoff) is int and cutoff >= 0, "receipt_cutoff_invalid")
    admission = None if own else _admit(registry.store, reader, context, source_ref, "source", cutoff)
    publication.update(received_input=admission, control=None, stored=None)
    if not require_envelope: return publication
    control = _control(registry, publication, set())
    stored = core._json(json.loads(_publication_bytes(registry.store, publication["envelope_ref"])))
    _closed(stored, "version request sheet components")
    _require(type(stored["sheet"]) is dict and type(stored["components"]) is dict, "stored_envelope_conflict")
    _require(stored["version"] == RESULT_VERSION and canonical(stored["request"]) == canonical(control["request"])
        and stored["sheet"].get("version") == core.SHEET_VERSION and stored["components"].get("version") == core.COMPONENT_VERSION
        and canonical(stored["sheet"]["request"]) == canonical(stored["request"])
        and canonical(stored["components"]["request"]) == canonical(stored["request"])
        and canonical(core._public(stored["components"])) == canonical(publication["packet"]["value"])
        and all(canonical(stored["sheet"][key]) == canonical(stored["components"][key]) for key in
            ("status", "pairs", "guide_comparisons", "template_comparisons", "issue_codes")), "stored_envelope_conflict")
    captures = stored["sheet"]["alignment_inputs"]
    _require(type(captures) is list and len(captures) == len(control["request"]["population"]), "stored_capture_conflict")
    witnesses = {row["pair_ordinal"]: row for row in control["alignments"]}
    for i, (pair, capture) in enumerate(zip(control["request"]["population"], captures)):
        if pair["alignment_ref"] is None:
            _require(capture is None, "stored_capture_conflict"); continue
        witness = witnesses[i]
        authority = _selected_reference_alignment_authority(registry.store, _context(registry.store, control["admission_invocation"]),
            pair["alignment_ref"], before_decision_index=control["admission_invocation"]["decision_index"])
        _require(digest(capture) == witness["capture_sha256"] and capture["operands"] == authority["operands"]
            and capture["source"] == source_descriptor(registry.store, authority["source"], authority["alignment"])
            and canonical(capture["original_mappings"]) == canonical(original_mappings(registry.store, authority["operands"])),
            "stored_capture_conflict")
    _, values = core._sequences(stored["sheet"]["comparison_inputs"], control["request"])
    for reference, witness in zip(core._comparison_refs(control["request"]), control["comparisons"]):
        value = values[reference]
        _require(witness["sequence_sha256"] == (None if value is None else hashlib.sha256(value.encode("utf-8")).hexdigest())
            and (witness["failure_code"] in ("sequence_bytes_unavailable", "sequence_not_available") if value is None
                else witness["failure_code"] is None), "stored_capture_conflict")
    _publication_bytes(registry.store, publication["grading_ref"])
    entries = source_tool_grading_entries(registry.store, source_ref)
    _require(len(entries) == 1 and entries[0]["artifact_ref"] == publication["grading_ref"]
        and canonical(entries[0]["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"])), "grading_conflict")
    publication.update(control=control, stored=stored)
    return publication


def _current_cutoff(registry, context):
    invocation = registry._current_invocation.get()
    if invocation is not None and invocation[0] is context:
        return _invocation(context, invocation[4])["decision_index"]
    # A completed owner/facts read uses only already committed semantic receipts.
    row = registry.store.db.execute("SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions WHERE run_id=? AND episode_id=?",
        (context.run_id, context.episode_id)).fetchone()
    return row[0]


def read_reference_edit_outcome_publication(registry, context, reader, source_ref, *,
        require_envelope=False, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_reference_edit_outcome_publication(registry, context, reader, source_ref,
            require_envelope=require_envelope, recovery_operation_key=recovery_operation_key)


def read_retained_reference_edit_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    """Return the literal original DTO without reopening private observations."""
    return read_reference_edit_outcome_publication(registry, context, reader, source_ref,
        recovery_operation_key=recovery_operation_key)["public"]


def _prepare_saved(registry, context, reader, arguments, invocation):
    publication = read_reference_edit_outcome_publication(registry, context, reader, arguments["result_ref"],
        require_envelope=arguments["mode"] == "calculate_saved")
    if arguments["mode"] == "read_stored": return dict(public=publication["public"])
    previous, control = publication["stored"], publication["control"]
    request = {**deepcopy(previous["request"]), "gap_bins": deepcopy(arguments["gap_bins"])}
    sheet = core.populate_reference_edit_outcome_sheet(request, alignment_inputs=previous["sheet"]["alignment_inputs"],
        comparison_inputs=previous["sheet"]["comparison_inputs"])
    components = core.calculate_reference_edit_outcome_components(sheet)
    return dict(arguments=arguments, invocation=invocation, request=request,
        stored=dict(version=RESULT_VERSION, request=request, sheet=sheet, components=components),
        admission_invocation=control["admission_invocation"], alignments=control["alignments"], comparisons=control["comparisons"],
        source_admission=publication["received_input"], original_source=dict(source_ref=publication["source"]["id"], record_sha256=digest(publication["source"])))


def _retain_reference_edit_outcome_publication(registry, prepared):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    stored = prepared["stored"]
    envelope_ref = registry.store.artifact(canonical(stored), "application/json")
    packet = dict(version=PACKET_VERSION, value=core._public(stored["components"]))
    packet_ref = registry.store.artifact(canonical(packet), "application/json")
    grading_ref = retain_tool_grading(registry.store, provider=TOOL, native_artifact_ref=packet_ref,
        grading=dict(sheet=stored["sheet"], scores=stored["components"]))
    paths = [Path(__file__), Path(core.__file__)]
    implementation = {path.name: dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size_bytes=path.stat().st_size) for path in paths}
    control = dict(version=CONTROL_VERSION, **{key: deepcopy(prepared[key]) for key in
        ("arguments", "invocation", "request", "admission_invocation", "alignments", "comparisons", "source_admission", "original_source")},
        envelope_ref=envelope_ref, public_packet_ref=packet_ref, grading_ref=grading_ref,
        native_call_state="not_requested", calculator_id=core.COMPONENT_VERSION, implementation=implementation)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    parents = (list(dict.fromkeys(capture["source"]["source_ref"] for capture in stored["sheet"]["alignment_inputs"] if capture is not None))
        if prepared["arguments"]["mode"] == "analyze" else [prepared["arguments"]["result_ref"]])
    source = registry.store.put("source", dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref, text_ref=None,
        request_ref=control_ref, version=RESULT_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=parents, auxiliary_artifact_refs=[envelope_ref, grading_ref]), origin="tool")
    public = core.project_reference_edit_outcome_return(stored["components"], source_ref=source["id"])
    return dict(source=source, public=public, stored=stored, control=control)


def read_reference_edit_outcome_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial") and type(outcome.get("result")) is dict, "action_result_unavailable")
    public = core.validate_reference_edit_outcome_return(outcome["result"])
    _require(outcome.get("record_refs") == [public["source_ref"]], "action_source_conflict")
    with registry.store.read_snapshot():
        publication = _read_reference_edit_outcome_publication(registry, context, reader, public["source_ref"],
            recovery_operation_key=operation_key if arguments["mode"] != "read_stored" else None,
            before_decision_index=details["invocation"]["decision_index"])
    _require(canonical(publication["public"]) == canonical(public), "action_source_conflict")
    if arguments["mode"] == "read_stored":
        _require(arguments["result_ref"] == public["source_ref"], "action_source_conflict")
    else:
        _require(publication["producer"]["invocation"]["operation_key"] == operation_key, "action_source_conflict")
    return public


def execute_reference_edit_outcome(registry, arguments, *, scope, operation_key, authority):
    """One atomic committed derivation; no physical-call-count claim or await."""
    arguments = core._json(arguments)
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
                _require(canonical(read_reference_edit_outcome_action_result(registry, context, arguments, operation_key, reader=reader))
                    == canonical(outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("invalid", "unavailable", "failed") and outcome.get("result") is None
                    and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        try:
            with registry.store.transaction():
                arguments = _arguments(arguments)
                prepared = (_prepare_analyze(registry, context, reader, arguments, invocation) if arguments["mode"] == "analyze"
                    else _prepare_saved(registry, context, reader, arguments, invocation))
                public = (prepared["public"] if arguments["mode"] == "read_stored" else
                    retain_molecular_publication(registry, prepared, tool_name=TOOL)["public"])
                outcome = dict(status="completed" if public["status"] == "complete" else "partial",
                    operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
                    record_refs=[public["source_ref"]], changed_record_refs=[] if arguments["mode"] == "read_stored" else [public["source_ref"]],
                    result=public, feedback=None if public["status"] == "complete" else dict(category="representation",
                        code="reference_edit_outcome_partial", source_ref=public["source_ref"]))
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
        except Exception as error:
            text = str(error)
            code = text if re.fullmatch(r"[a-z][a-z0-9_]*", text) else "reference_edit_outcome_input_invalid"
            diagnostic = registry.store.artifact(canonical(dict(version="reference_edit_outcome_diagnostic_v1",
                exception_type=type(error).__module__ + "." + type(error).__name__, exception_message=text)), "application/json")
            outcome = dict(status="unavailable" if isinstance(error, OSError) or code.endswith("_unavailable") else
                "invalid" if isinstance(error, (ContractError, ValueError, KeyError, TypeError)) else "failed",
                operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
                record_refs=[], changed_record_refs=[], result=None,
                feedback=dict(category="arguments_or_reference", code=code, diagnostic_ref=diagnostic))
            registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
        return outcome


__all__ = ["TOOL", "SOURCE_VERSION", "reference_edit_outcome_tool_contract", "reference_edit_outcome_fact_sources",
    "execute_reference_edit_outcome", "read_retained_reference_edit_publication",
    "read_reference_edit_outcome_publication", "read_reference_edit_outcome_action_result"]
