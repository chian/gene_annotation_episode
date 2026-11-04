"""Actual ordinary ESM producer custody and calculation-free retained views."""
from datetime import datetime, timezone

from . import esm_gene_embedding_contracts as contracts
from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .molecular_measurement_tools import (
    _publication_bytes, _recorded_molecular_action_details, _recorded_molecular_producer_details,
    authenticate_molecular_invocation,
)
from .native_atac_differential_driver import decode_json
from .native_file_capture import capture_native_file
from .reference_edit_outcome_tools import _admit, _context, _current_cutoff, _invocation


TOOL = contracts.TOOL
CONTROL_VERSION = "ordinary_esm_gene_embedding_publication_v1"
_FILES = {"input":("input.json",contracts.INPUT_VERSION,"json"),
    "document":("embeddings.json",contracts.DOCUMENT_VERSION,"json"),
    "vectors":("vectors.pt","pt","pt")}
_RESULT_KEYS = {"input":"input_document_file","document":"result_document_file","vectors":"vector_file"}


def _ports():
    from . import esm_gene_embedding_tools
    return esm_gene_embedding_tools


def _require(condition,code):
    if not condition:raise ContractError("esm_gene_embedding_"+code)


def _closed(value,fields):
    _require(type(value) is dict and set(value) == set(fields.split()),"fields_invalid")


def _same(left,right):
    return canonical(left) == canonical(right)


def _checked_files(registry,value):
    _closed(value,"input document vectors")
    result = {}
    for role in _FILES:
        file = value[role]
        if file is None:
            _require(role == "vectors","document_missing")
        else:
            file = _ports()._file(registry,file)
            _require(file["format"] == _FILES[role][1],"document_format_conflict")
        result[role] = file
    return result


def _declaration(role,file):
    if file is None:return None
    name,_,file_format = _FILES[role]
    return dict(path="esm-gene-embeddings/"+name,format=file_format,sha256=file["sha256"],size_bytes=file["size_bytes"])


def _private_files(files,protected):
    return [file["artifact_ref"] for file in files.values()
        if file is not None and file["artifact_ref"] not in protected]


def _metadata(registry,reference,*,recovery_context=None,recovery_operation_key=None):
    source = registry.store.get(reference)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == TOOL and source.get("version") == contracts.SOURCE_VERSION
        and source.get("accession") is source.get("uri") is source.get("text_ref") is None
        and "operand_refs" not in source,"producer_required")
    producer = _recorded_molecular_producer_details(registry,reference,TOOL,
        recovery_context=recovery_context,recovery_operation_key=recovery_operation_key)
    arguments = contracts.validate_esm_embedding_arguments(producer["arguments"])
    public = contracts.validate_esm_embedding_return(producer["outcome"]["result"])
    _require(arguments["mode"] == "embed" and public["source_ref"] == reference
        and producer["outcome"]["record_refs"] == [reference]
        and producer["outcome"]["changed_record_refs"] == [reference]
        and _same(public["selection"],arguments["selection"])
        and _same(public["context"]["parameters"],arguments["parameters"]),"publication_conflict")
    parents = [arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else []
    _require(source.get("parent_source_refs") == parents and public["context"]["input_source_ref"] ==
        (parents[0] if parents else None),"parent_sources_conflict")
    if not parents:
        _require(public["context"]["input_file"]["artifact_ref"] == arguments["input"]["reference"],"input_file_conflict")
    return dict(source=source,producer=producer,public=public,control=None,document=None,admission=None)


def _documents(registry,files):
    supplied = contracts.validate_esm_input_document(decode_json(_publication_bytes(registry.store,files["input"]["artifact_ref"])))
    document = contracts.validate_esm_embedding_document(decode_json(_publication_bytes(registry.store,files["document"]["artifact_ref"])))
    _require(_same(document["input"],supplied),"input_document_conflict")
    return document


def _control(registry,publication):
    source,producer = publication["source"],publication["producer"]
    control = decode_json(_publication_bytes(registry.store,source["request_ref"]))
    _closed(control,"version arguments invocation intent worker result files public_file protected_input_artifact_refs")
    _require(control["version"] == CONTROL_VERSION and _same(control["arguments"],producer["arguments"])
        and _same(control["invocation"],producer["invocation"]),"control_conflict")
    arguments,invocation,intent = control["arguments"],control["invocation"],control["intent"]
    _closed(intent,"version arguments invocation selected_resource policy input input_admission input_decision_admission request")
    ports = _ports()
    _require(intent["version"] == ports.INTENT_VERSION and _same(intent["arguments"],arguments)
        and _same(intent["invocation"],invocation),"original_intent_conflict")
    ports._selected_resource(intent["selected_resource"],intent["policy"])
    request = ports._native_request(arguments,intent["input"],intent["selected_resource"])
    _require(_same(intent["request"],request),"native_request_conflict")
    root = ports._worker_control(control["worker"],request,invocation)
    owner = _context(registry.store,invocation)
    ports._check_input(registry,owner,arguments,intent["input"],intent["input_admission"],
        intent["input_decision_admission"],invocation["decision_index"],store_root=root)
    protected = [intent["input"]["file"]["artifact_ref"]]
    _require(control["protected_input_artifact_refs"] == protected,"protected_input_conflict")
    files = _checked_files(registry,control["files"])
    public_file = ports._file(registry,control["public_file"])
    _require(public_file["format"] == contracts.VALUE_VERSION and public_file["artifact_ref"] == source["artifact_ref"]
        and source.get("auxiliary_artifact_refs") == list(dict.fromkeys(_private_files(files,protected))),"private_files_conflict")
    _require(_same(control["worker"]["selection"]["policy"],intent["policy"])
        and control["worker"]["observation"].get("state") == "returned"
        and type(control["worker"]["observation"]["metadata"].get("native_returncode")) is int
        and control["worker"]["observation"]["metadata"]["native_returncode"] == 0,"native_worker_failed")
    document = _documents(registry,files)
    result = contracts.validate_esm_worker_result(control["result"],request=request,document=document)
    _require(control["worker"]["result_sha256"] == digest(result)
        and all(_same(result[_RESULT_KEYS[role]],_declaration(role,files[role])) for role in _FILES),"worker_result_conflict")
    _require(_same(document["input"]["file"],request["input"]["file"])
        and document["input"]["source_ref"] == request["input"]["source_ref"],"input_document_conflict")
    expected = contracts.project_esm_embedding_return(document,arguments["selection"],source["id"])
    _require(_same(expected,publication["public"]),"public_packet_conflict")
    return control,document


def _read(registry,context,reader,reference,*,recovery_operation_key=None,before_decision_index=None,require_documents=False):
    records = EpisodeReturnRecords(registry.store,context.run_id,failure_prefix="esm_gene_embedding_")
    records.authenticate(context)
    publication = _metadata(registry,reference,recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication["producer"]["invocation"]
    own = recovery_operation_key is not None and invocation["operation_key"] == recovery_operation_key and (
        invocation["run_id"],invocation["episode_id"]) == (context.run_id,context.episode_id)
    cutoff = _current_cutoff(registry,context) if before_decision_index is None else before_decision_index
    _require(type(cutoff) is int and cutoff >= 0,"source_cutoff_invalid")
    if not own:publication["admission"] = _admit(registry.store,reader,context,reference,"source",cutoff)
    packet = contracts.validate_esm_embedding_value(decode_json(_publication_bytes(registry.store,publication["source"]["artifact_ref"])))
    _require(_same(dict(source_ref=reference,**packet),publication["public"]),"public_packet_conflict")
    if require_documents:
        publication["control"],publication["document"] = _control(registry,publication)
    return publication


def _project(registry,publication,selection):
    selection = contracts.validate_esm_selection(selection)
    with registry.store.read_snapshot():
        _,document = _control(registry,publication)
        return contracts.project_esm_embedding_return(document,selection,publication["source"]["id"])


def read_retained_esm_gene_embedding_publication(registry,context,reader,source_ref,*,recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read(registry,context,reader,source_ref,recovery_operation_key=recovery_operation_key)["public"]


def read_esm_gene_embedding_action_result(registry,context,arguments,operation_key,*,reader):
    arguments = contracts.validate_esm_embedding_arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry,context,arguments,operation_key,TOOL,
        recovery_context=recovery,recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed","partial") and type(outcome.get("result")) is dict,"action_result_unavailable")
    public = contracts.validate_esm_embedding_return(outcome["result"])
    _require(outcome.get("record_refs") == [public["source_ref"]]
        and _same(public["selection"],arguments["selection"]),"action_source_conflict")
    with registry.store.read_snapshot():
        publication = _read(registry,context,reader,public["source_ref"],
            recovery_operation_key=operation_key if arguments["mode"] == "embed" else None,
            before_decision_index=details["invocation"]["decision_index"])
        if arguments["mode"] == "embed":
            _require(publication["producer"]["operation_ref"] == details["operation_ref"]
                and _same(publication["public"],public),"action_source_conflict")
        else:
            # This is the original authenticated read action's frozen literal
            # result, not a fresh arbitrary candidate. Cache/frozen reads do not
            # open its private input, vector, software or native document bodies.
            _require(public["source_ref"] == arguments["result_ref"] and outcome.get("changed_record_refs") == []
                and _same(public["context"],publication["public"]["context"]),"action_source_conflict")
    return public


def validate_esm_gene_embedding_fact(registry,context,reader,value):
    value = contracts.validate_esm_embedding_return(value)
    with registry.store.read_snapshot():
        publication = _read(registry,context,reader,value["source_ref"])
        expected = _project(registry,publication,value["selection"])
        _require(_same(value,expected),"selected_fact_conflict")
        return expected


def _capture(registry,directory,declaration,role):
    if declaration is None:
        _require(role == "vectors","document_missing")
        return None
    _closed(declaration,"path format sha256 size_bytes")
    name,file_format,wire_format = _FILES[role]
    _require(declaration["path"] == "esm-gene-embeddings/"+name and declaration["format"] == wire_format,"output_declaration_conflict")
    file = capture_native_file(registry.store,directory=str(directory),relative_path=declaration["path"],format=file_format,
        media_type="application/octet-stream" if role == "vectors" else "application/json")
    _require(all(file[k] == declaration[k] for k in ("sha256","size_bytes")),"output_file_identity_conflict")
    return file


def _publish(registry,arguments,invocation,intent,result,worker,directory):
    _require(registry.store.db.in_transaction,"publication_transaction_required")
    arguments = contracts.validate_esm_embedding_arguments(arguments)
    _require(arguments["mode"] == "embed","producer_mode_invalid")
    context,reader = authenticate_molecular_invocation(registry,TOOL,arguments,invocation["scope"],invocation["operation_key"])
    _require(_same(_invocation(context,invocation["operation_key"]),invocation)
        and _same(intent["arguments"],arguments) and _same(intent["invocation"],invocation),"invocation_conflict")
    ports = _ports()
    ports._check_input(registry,context,arguments,intent["input"],intent["input_admission"],
        intent["input_decision_admission"],invocation["decision_index"])
    request = ports._native_request(arguments,intent["input"],intent["selected_resource"])
    _require(_same(intent["request"],request),"native_request_conflict")
    root = ports._worker_control(worker,request,invocation)
    _require(str(root) == str(registry.store.path) and str(directory) == worker["selection"]["cwd"]
        and _same(worker["selection"]["policy"],intent["policy"])
        and worker["result_sha256"] == digest(result)
        and worker["observation"].get("state") == "returned"
        and type(worker["observation"]["metadata"].get("native_returncode")) is int
        and worker["observation"]["metadata"]["native_returncode"] == 0,"native_worker_failed")
    files = {role:_capture(registry,directory,result[_RESULT_KEYS[role]],role) for role in _FILES}
    files = _checked_files(registry,files)
    document = _documents(registry,files)
    result = contracts.validate_esm_worker_result(result,request=request,document=document)
    packet = contracts.select_esm_embedding_values(document,arguments["selection"])
    packet_ref = registry.store.artifact(canonical(packet),"application/json")
    public_file = ports._file(registry,dict(artifact_ref=packet_ref,sha256=packet_ref.removeprefix("artifact_"),
        size_bytes=len(canonical(packet).encode()),format=contracts.VALUE_VERSION))
    protected = [intent["input"]["file"]["artifact_ref"]]
    control = dict(version=CONTROL_VERSION,arguments=arguments,invocation=invocation,intent=intent,worker=worker,
        result=result,files=files,public_file=public_file,protected_input_artifact_refs=protected)
    control_ref = registry.store.artifact(canonical(control),"application/json")
    source = registry._put("source",dict(provider=TOOL,accession=None,uri=None,artifact_ref=packet_ref,text_ref=None,
        request_ref=control_ref,version=contracts.SOURCE_VERSION,retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[intent["input"]["source_ref"]] if intent["input"]["source_ref"] is not None else [],
        auxiliary_artifact_refs=list(dict.fromkeys(_private_files(files,protected)))),origin="tool")
    return contracts.validate_esm_embedding_return(dict(source_ref=source["id"],**packet))


__all__ = ["CONTROL_VERSION","read_retained_esm_gene_embedding_publication","read_esm_gene_embedding_action_result",
    "validate_esm_gene_embedding_fact"]
