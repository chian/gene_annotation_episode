"""Authenticated Source-only custody for ordinary conservation results.

The execution owner owns admissions, the original native handle and capture.
This module validates their retained joins and copies selected saved values.
It never parses native bytes, calculates quantities or grants a private File.
"""
from datetime import datetime, timezone
import re

from .alignment_site_native import immutable_record
from .domain import ContractError
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import (
    _publication_bytes, _recorded_molecular_action_details, _recorded_molecular_producer_details,
    authenticate_molecular_invocation,
)
from .native_file_capture import capture_native_file
from .native_flux_balance_storage import decode_json
from . import protein_conservation_result_contracts as contracts
from . import protein_conservation_result_worker as result_worker
from .phylogeny_format_contracts import validate_alignment_document
from .phylogeny_calculation_contracts import alignment_population, validate_literal_site_conservation_components
from .reference_edit_outcome_tools import _admit, _context, _current_cutoff, _frozen_admission, _invocation


TOOL = contracts.TOOL
SOURCE_VERSION = contracts.SOURCE_VERSION
CONTROL_VERSION = "ordinary_protein_conservation_publication_v1"
CAPTURE_VERSION = "ordinary_protein_conservation_native_capture_v1"
_CONTROL_FIELDS = ("version arguments invocation capture_source alignment_file context_file population_file "
    "components_file value_file input_artifact_refs source_admission source_decision_admission "
    "original_source policy selected_resource worker")
_PREPARED_FIELDS = ("capture_source alignment_file context_file input_artifact_refs source_admission "
    "source_decision_admission original_source policy selected_resource")
_FILE_FIELDS = {"alignment_file": result_worker.ALIGNMENT_FORMAT,
    "context_file": result_worker.CONTEXT_VERSION, "population_file": result_worker.POPULATION_FORMAT,
    "components_file": result_worker.COMPONENTS_FORMAT, "value_file": contracts.PACKET_VERSION}


def _ports():
    # The execution owner imports publication ports only when executing them.
    from . import protein_conservation_tools
    return protein_conservation_tools


def _require(condition, code):
    if not condition:
        raise ContractError("protein_conservation_" + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "fields_invalid")


def _same(first, second):
    return canonical(first) == canonical(second)


def _input_refs(value):
    _require(type(value) is list and all(type(item) is str and
        re.fullmatch(r"artifact_[0-9a-f]{64}", item) is not None for item in value)
        and len(value) == len(set(value)), "input_files_conflict")
    return value


def _checked_file(registry, value, format, *, nullable=False):
    if value is None:
        _require(nullable, "document_missing")
        return None
    file = _ports()._file(registry, value)
    _require(file["format"] == format, "document_format_conflict")
    return file


def _file_values(registry, control):
    files = {key: _checked_file(registry, control[key], format,
        nullable=key in {"alignment_file", "population_file", "components_file"})
        for key, format in _FILE_FIELDS.items()}
    _require((files["population_file"] is None) == (files["components_file"] is None)
        and (files["alignment_file"] is not None or files["population_file"] is None),
        "document_presence_conflict")
    return files


def _document(registry, file):
    return None if file is None else decode_json(_publication_bytes(registry.store, file["artifact_ref"]))


def _declaration(key, file):
    if file is None:
        return None
    name, format = result_worker._FILES[key]
    _require(file["format"] == format, "document_format_conflict")
    return dict(relative_path=name, format=format, sha256=file["sha256"], size_bytes=file["size_bytes"])


def _worker_result(arguments, files):
    return dict(version=result_worker.OUTPUT_VERSION,
        mode="parse" if arguments["mode"] == "run_native" else "calculate_saved",
        alignment=None if arguments["mode"] == "calculate_saved" else _declaration("alignment", files["alignment_file"]),
        population=_declaration("population", files["population_file"]),
        components=_declaration("components", files["components_file"]),
        context=_declaration("context", files["context_file"]), value=_declaration("value", files["value_file"]))


def _private_files(capture, files, excluded):
    references = [capture["artifact_ref"], capture["request_ref"], *capture.get("auxiliary_artifact_refs", [])]
    references.extend(file["artifact_ref"] for name in
        ("alignment_file", "context_file", "population_file", "components_file")
        if (file := files[name]) is not None)
    return [reference for reference in dict.fromkeys(references) if reference not in excluded]


def _capture(registry, descriptor):
    _closed(descriptor, "source_ref record_sha256")
    capture = registry.store.get(descriptor["source_ref"])
    immutable_record(capture)
    _require(capture.get("record_type") == "source" and capture.get("origin") == "tool"
        and capture.get("provider") == TOOL and capture.get("version") == CAPTURE_VERSION
        and digest(capture) == descriptor["record_sha256"] and "operand_refs" not in capture,
        "capture_source_conflict")
    return capture


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == TOOL and source.get("version") == SOURCE_VERSION
        and source.get("accession") is source.get("uri") is source.get("text_ref") is None
        and "operand_refs" not in source, "producer_required")
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = contracts.validate_conservation_arguments(producer["arguments"])
    public = contracts.validate_conservation_return(producer["outcome"]["result"])
    _require(public["source_ref"] == source_ref and producer["outcome"]["record_refs"] == [source_ref]
        and arguments["mode"] in ("run_native", "calculate_saved")
        and _same(public["selection"], arguments["selection"])
        and _same(public["context"]["population_request"], arguments["population_request"]), "publication_conflict")
    parents = source.get("parent_source_refs")
    if arguments["mode"] == "run_native":
        _require(type(parents) is list and len(parents) == 1, "capture_source_conflict")
        capture = registry.store.get(parents[0])
        immutable_record(capture)
        _require(capture.get("record_type") == "source" and capture.get("origin") == "tool"
            and capture.get("provider") == TOOL and capture.get("version") == CAPTURE_VERSION
            and capture.get("accession") == producer["operation_ref"], "capture_source_conflict")
    else:
        _require(parents == [arguments["result_ref"]], "original_source_conflict")
    return dict(source=source, producer=producer, public=public, control=None,
        received_input=None, source_decision_admission=None)


def _documents(registry, files, arguments):
    context = result_worker._validate(_document(registry, files["context_file"]),
        result_worker._context_schema(), "saved_context_invalid")
    raw_alignment = _document(registry, files["alignment_file"])
    alignment = None if raw_alignment is None else validate_alignment_document(raw_alignment)
    _require(_same(context["alignment"], result_worker._metadata(alignment)), "alignment_metadata_conflict")
    result_worker._retained_extent(context, alignment)
    population = _document(registry, files["population_file"])
    components = _document(registry, files["components_file"])
    if population is not None:
        _require(alignment is not None, "population_alignment_conflict")
        alignment_population(population, alignment)
        _require(_same(population["evidence"], result_worker._evidence(context)), "population_evidence_conflict")
        components = validate_literal_site_conservation_components(components,
            alignment=alignment, population=population)
    value = contracts.conservation_public_value(alignment=alignment,
        population_request=arguments["population_request"], population=population, components=components,
        input_record=context["input"], native_execution=context["native_execution"],
        associations=context["row_associations"], selection=arguments["selection"], issues=context["issues"])
    supplied = contracts.validate_conservation_public_value(_document(registry, files["value_file"]))
    _require(_same(value, supplied), "saved_value_conflict")
    return dict(alignment=alignment, population=population, components=components, context=context, value=value)


def _saved_request(registry, arguments, files, *, store_root):
    return dict(version=result_worker.REQUEST_VERSION, mode="calculate_saved", input=None,
        alignment_file=None, native_execution=None, native_issues=None,
        saved=dict(alignment=None if files["alignment_file"] is None else dict(file=files["alignment_file"],
            path=_ports()._path(registry, files["alignment_file"], store_root=store_root)),
            context=dict(file=files["context_file"],
                path=_ports()._path(registry, files["context_file"], store_root=store_root))),
        population_request=arguments["population_request"], selection=arguments["selection"])


def _native_documents(documents, request, capture, arguments):
    original_input = documents["context"]["input"]
    _require(original_input is not None and _same(original_input["selection"], arguments["input"])
        and _same(original_input["file"], request["input"]["file"])
        and original_input["source_ref"] == request["input"]["source_ref"], "input_document_conflict")
    observed, native = documents["context"]["native_execution"], request["native_execution"]
    _require(_same({key: value for key, value in observed.items() if key != "parser_status"},
        {key: value for key, value in native.items() if key != "parser_status"})
        and _same(documents["context"]["issues"][:len(request["native_issues"])], request["native_issues"]),
        "native_document_conflict")
    captured = request["alignment_file"]
    _require((captured is None) == (observed["parser_status"] == "not_parsed"), "native_parser_conflict")
    if documents["alignment"] is not None:
        artifact = documents["alignment"]["artifact"]
        _require(captured is not None and artifact == dict(raw_artifact_ref=captured["file"]["artifact_ref"],
            source_ref=capture["id"], sha256=captured["file"]["sha256"])
            and capture["artifact_ref"] == artifact["raw_artifact_ref"], "alignment_capture_conflict")


def _control(registry, publication, seen):
    """Authenticate original controls and saved documents without native reads."""
    source, producer = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = {*seen, source["id"]}
    control = decode_json(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, _CONTROL_FIELDS)
    arguments = contracts.validate_conservation_arguments(control["arguments"])
    _require(control["version"] == CONTROL_VERSION and _same(arguments, producer["arguments"])
        and _same(control["invocation"], producer["invocation"]), "control_conflict")
    files = _file_values(registry, control)
    _require(source["artifact_ref"] == files["value_file"]["artifact_ref"], "public_file_conflict")
    input_refs = _input_refs(control["input_artifact_refs"])
    capture = _capture(registry, control["capture_source"])
    ports = _ports()
    if arguments["mode"] == "run_native":
        checked = ports._capture_control(registry, capture, invocation=control["invocation"],
            arguments=arguments, input_artifact_refs=input_refs)
        _require(source.get("parent_source_refs") == [capture["id"]]
            and control["source_admission"] is control["source_decision_admission"] is control["original_source"] is None
            and _same(control["policy"], checked["control"]["policy"])
            and _same(control["selected_resource"], checked["control"]["selected_resource"]), "capture_source_conflict")
        expected_request = checked["request"]
        _require(ports._historical_store_root(control["worker"], control["invocation"], "calculation")
            == checked["store_root"], "worker_store_conflict")
    else:
        original = control["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(arguments["mode"] == "calculate_saved" and original["source_ref"] == arguments["result_ref"]
            and source.get("parent_source_refs") == [original["source_ref"]]
            and control["selected_resource"] is None, "original_source_conflict")
        previous = _metadata_publication(registry, original["source_ref"])
        _require(digest(previous["source"]) == original["record_sha256"], "original_source_conflict")
        owner = _context(registry.store, control["invocation"])
        _frozen_admission(registry.store, owner, control["source_admission"], original["source_ref"],
            "source", control["invocation"]["decision_index"])
        _require(_same(ports._source_admission(registry, owner, original["source_ref"],
            control["invocation"]["decision_index"]), control["source_decision_admission"]),
            "source_decision_admission_conflict")
        prior, _ = _control(registry, previous, seen)
        _require(_same(control["capture_source"], prior["capture_source"])
            and input_refs == prior["input_artifact_refs"]
            and _same(files["alignment_file"], prior["alignment_file"])
            and _same(files["context_file"], prior["context_file"]), "saved_documents_conflict")
        root = ports._historical_store_root(control["worker"], control["invocation"], "calculation")
        expected_request = _saved_request(registry, arguments, prior, store_root=root)
    result_worker.validate_protein_conservation_result_request(expected_request)
    ports._worker_control(control["worker"], expected_request, "protein_conservation_result",
        control["invocation"], "calculation")
    _require(_same(LocalJobPolicy(**control["policy"]).to_dict(), control["policy"])
        and _same(control["worker"]["selection"]["policy"], control["policy"]), "action_policy_conflict")
    _require(control["worker"]["observation"].get("state") == "returned"
        and type(control["worker"]["observation"]["metadata"].get("native_returncode")) is int
        and control["worker"]["observation"]["metadata"].get("native_returncode") == 0,
        "result_worker_failed")
    _require(control["worker"]["result_sha256"] == digest(_worker_result(arguments, files)), "worker_result_conflict")
    _require(source.get("auxiliary_artifact_refs") == _private_files(capture, files, input_refs),
        "private_files_conflict")
    documents = _documents(registry, files, arguments)
    _require(_same(contracts.project_conservation_return(documents["value"], source_ref=source["id"]),
        publication["public"]), "public_packet_conflict")
    if arguments["mode"] == "run_native":
        _native_documents(documents, expected_request, capture, arguments)
    return control, documents


def _read_protein_conservation_publication(registry, context, reader, source_ref, *,
        recovery_operation_key=None, require_documents=False, before_decision_index=None):
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_conservation_").authenticate(context)
    _require(type(require_documents) is bool, "document_selection_invalid")
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication["producer"]["invocation"]
    own = (recovery_operation_key is not None and invocation["operation_key"] == recovery_operation_key
        and (invocation["run_id"], invocation["episode_id"]) == (context.run_id, context.episode_id))
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    _require(type(cutoff) is int and cutoff >= 0, "source_cutoff_invalid")
    if not own:
        publication["received_input"] = _admit(registry.store, reader, context, source_ref, "source", cutoff)
        active = registry._current_invocation.get()
        if before_decision_index is not None or active is not None and active[0] is context:
            publication["source_decision_admission"] = _ports()._source_admission(registry, context, source_ref, cutoff)
    value = contracts.validate_conservation_public_value(
        decode_json(_publication_bytes(registry.store, publication["source"]["artifact_ref"])))
    _require(_same(contracts.project_conservation_return(value, source_ref=source_ref), publication["public"]),
        "public_packet_conflict")
    if require_documents:
        publication["control"], _ = _control(registry, publication, set())
    return publication


def read_retained_protein_conservation_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_protein_conservation_publication(registry, context, reader, source_ref,
            recovery_operation_key=recovery_operation_key)["public"]


def _project_publication(registry, publication, selection):
    """Copy a same-Source view of actual saved documents, without new math."""
    selection = contracts.validate_conservation_selection(selection)
    with registry.store.read_snapshot():
        control, documents = _control(registry, publication, set())
        context = documents["context"]
        value = contracts.conservation_public_value(alignment=documents["alignment"],
            population_request=control["arguments"]["population_request"], population=documents["population"],
            components=documents["components"], input_record=context["input"],
            native_execution=context["native_execution"], associations=context["row_associations"],
            selection=selection, issues=context["issues"])
        return contracts.project_conservation_return(value, source_ref=publication["source"]["id"])


def read_protein_conservation_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = contracts.validate_conservation_arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial") and type(outcome.get("result")) is dict,
        "action_result_unavailable")
    public = contracts.validate_conservation_return(outcome["result"])
    _require(outcome.get("record_refs") == [public["source_ref"]], "action_source_conflict")
    redisplay = arguments["mode"] != "run_native" and public["source_ref"] == arguments["result_ref"]
    with registry.store.read_snapshot():
        publication = _read_protein_conservation_publication(registry, context, reader, public["source_ref"],
            recovery_operation_key=None if redisplay else operation_key,
            before_decision_index=details["invocation"]["decision_index"])
        if redisplay:
            _require(outcome.get("changed_record_refs") == [], "action_source_conflict")
            if arguments["mode"] == "calculate_saved":
                _require(_same(arguments["population_request"], publication["public"]["context"]["population_request"]),
                    "saved_population_conflict")
            expected = _project_publication(registry, publication, arguments["selection"])
        else:
            _require(publication["producer"]["operation_ref"] == details["operation_ref"], "action_source_conflict")
            expected = publication["public"]
        _require(_same(expected, public) and _same(public["selection"], arguments["selection"]),
            "action_source_conflict")
    return public


def validate_protein_conservation_fact(registry, context, reader, value):
    """Authenticate a received Source and its exact retained selected values."""
    value = contracts.validate_conservation_return(value)
    with registry.store.read_snapshot():
        publication = _read_protein_conservation_publication(registry, context, reader, value["source_ref"])
        expected = _project_publication(registry, publication, value["selection"])
        _require(_same(expected, value), "selected_fact_conflict")
        return expected


def _capture_component(registry, directory, declaration, key):
    if declaration is None:
        return None
    _closed(declaration, "relative_path format sha256 size_bytes")
    name, format = result_worker._FILES[key]
    _require(declaration["relative_path"] == name and declaration["format"] == format,
        "component_declaration_conflict")
    file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
        format=format, media_type="application/json")
    _require(type(declaration["size_bytes"]) is int
        and all(file[name] == declaration[name] for name in ("sha256", "size_bytes")), "component_identity_conflict")
    return file


def _publish(registry, arguments, invocation, prepared, result, worker, directory):
    """Publish only inside the transaction that also saves this ToolOperation."""
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    arguments = contracts.validate_conservation_arguments(arguments)
    _require(arguments["mode"] in ("run_native", "calculate_saved"), "producer_mode_invalid")
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments,
        invocation["scope"], invocation["operation_key"])
    _require(_same(_invocation(context, invocation["operation_key"]), invocation), "invocation_conflict")
    _closed(prepared, _PREPARED_FIELDS)
    result = result_worker._validate(result, result_worker.protein_conservation_result_output_schema(), "output_invalid")
    _require(result["mode"] == ("parse" if arguments["mode"] == "run_native" else "calculate_saved")
        and worker["result_sha256"] == digest(result), "worker_result_conflict")
    capture = prepared["capture_source"]
    immutable_record(capture)
    _require(_same(registry.store.get(capture["id"]), capture), "capture_source_conflict")
    input_refs = _input_refs(prepared["input_artifact_refs"])
    ports = _ports()
    if arguments["mode"] == "run_native":
        _require(prepared["alignment_file"] is prepared["context_file"] is prepared["original_source"]
            is prepared["source_admission"] is prepared["source_decision_admission"] is None,
            "native_preparation_conflict")
        checked = ports._capture_control(registry, capture, invocation=invocation, arguments=arguments,
            input_artifact_refs=input_refs)
        _require(_same(prepared["policy"], checked["control"]["policy"])
            and _same(prepared["selected_resource"], checked["control"]["selected_resource"]), "action_policy_conflict")
        request = checked["request"]
    else:
        original = prepared["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(original["source_ref"] == arguments["result_ref"] and prepared["selected_resource"] is None,
            "original_source_conflict")
        previous = _read_protein_conservation_publication(registry, context, reader, arguments["result_ref"],
            require_documents=True, before_decision_index=invocation["decision_index"])
        prior = previous["control"]
        _require(digest(previous["source"]) == original["record_sha256"]
            and _same(previous["received_input"], prepared["source_admission"])
            and _same(previous["source_decision_admission"], prepared["source_decision_admission"])
            and _same(prepared["alignment_file"], prior["alignment_file"])
            and _same(prepared["context_file"], prior["context_file"])
            and _same(dict(source_ref=capture["id"], record_sha256=digest(capture)), prior["capture_source"])
            and input_refs == prior["input_artifact_refs"], "saved_preparation_conflict")
        root = ports._historical_store_root(worker, invocation, "calculation")
        request = _saved_request(registry, arguments, prior, store_root=root)
    result_worker.validate_protein_conservation_result_request(request)
    root = ports._worker_control(worker, request, "protein_conservation_result", invocation, "calculation")
    _require(worker["observation"].get("state") == "returned"
        and type(worker["observation"]["metadata"].get("native_returncode")) is int
        and worker["observation"]["metadata"].get("native_returncode") == 0, "result_worker_failed")
    _require(_same(LocalJobPolicy(**prepared["policy"]).to_dict(), prepared["policy"])
        and _same(worker["selection"]["policy"], prepared["policy"])
        and str(directory) == worker["selection"]["cwd"], "action_policy_conflict")
    if arguments["mode"] == "run_native":
        _require(root == checked["store_root"], "worker_store_conflict")
    files = {}
    files["alignment_file"] = (_capture_component(registry, directory, result["alignment"], "alignment")
        if arguments["mode"] == "run_native" else
        _checked_file(registry, prepared["alignment_file"], result_worker.ALIGNMENT_FORMAT, nullable=True))
    for name in ("context", "population", "components", "value"):
        files[name + "_file"] = _capture_component(registry, directory, result[name], name)
    files = _file_values(registry, files)
    _require(_same(_worker_result(arguments, files), result), "worker_result_conflict")
    documents = _documents(registry, files, arguments)
    if arguments["mode"] == "run_native":
        _native_documents(documents, request, capture, arguments)
    else:
        _require(_same(files["context_file"], prepared["context_file"]), "saved_context_conflict")
    control = dict(version=CONTROL_VERSION, arguments=arguments, invocation=invocation,
        capture_source=dict(source_ref=capture["id"], record_sha256=digest(capture)), **files,
        input_artifact_refs=input_refs, source_admission=prepared["source_admission"],
        source_decision_admission=prepared["source_decision_admission"], original_source=prepared["original_source"],
        policy=prepared["policy"], selected_resource=prepared["selected_resource"], worker=worker)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    source = registry._put("source", dict(provider=TOOL, accession=None, uri=None,
        artifact_ref=files["value_file"]["artifact_ref"], text_ref=None, request_ref=control_ref,
        version=SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[capture["id"]] if arguments["mode"] == "run_native" else [arguments["result_ref"]],
        auxiliary_artifact_refs=_private_files(capture, files, input_refs)), origin="tool")
    return contracts.project_conservation_return(documents["value"], source_ref=source["id"])
