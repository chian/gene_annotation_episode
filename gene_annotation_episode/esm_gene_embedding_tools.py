"""Ordinary authenticated ESM work over explicitly received protein evidence."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re

from . import esm_gene_embedding_contracts as contracts
from . import native_lifecycle
from .communication import plain
from .domain import ContractError, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .materials import source_window_selection
from .molecular_measurement_tools import MolecularOperationUnpublished, authenticate_molecular_invocation
from .molecular_sequence_input_contracts import input_record_digest, validate_molecular_sequence_received_file
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import _identity, _metadata
from .reference_edit_outcome_tools import _context, _invocation


TOOL = contracts.TOOL
OPERATION = "esm_gene_embedding"
CONFIGURATION_VERSION = "ordinary_esm_gene_embedding_configuration_v1"
INTENT_VERSION = "ordinary_esm_gene_embedding_intent_v1"


def _require(condition, code):
    if not condition: raise ContractError("esm_gene_embedding_" + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "fields_invalid")


def _same(left, right):
    return canonical(left) == canonical(right)


class _KnownFailure(ContractError):
    """The original owned worker is confirmed terminal and failed."""


def normalize_esm_gene_embedding_configuration(resources, environments, *, policy):
    _require(type(resources) is dict and type(environments) in (list,tuple), "configuration_invalid")
    checked = LocalJobPolicy(**policy).to_dict()
    _require(_same(checked,policy), "policy_invalid")
    selected = []
    for row in environments:
        _closed(row,"operation resource_id deployment")
        _require(row["operation"] == TOOL and not selected and type(row["resource_id"]) is str
            and row["resource_id"], "ambiguous_resource_selection")
        resource = resources.get(row["resource_id"])
        _require(type(resource) is dict and resource.get("kind") == "local"
            and type(resource.get("workspace")) is str and Path(resource["workspace"]).is_absolute()
            and _same(resource.get("policy"),checked), "resource_allocation_conflict")
        selected.append(dict(resource_id=row["resource_id"],resource=deepcopy(resource),
            deployment=contracts.validate_esm_deployment(row["deployment"])))
    return dict(version=CONFIGURATION_VERSION,policy=checked,resources=selected,stored_reads=False)


def validate_esm_gene_embedding_configuration(value):
    _closed(value,"version policy resources stored_reads")
    _require(value["version"] == CONFIGURATION_VERSION and type(value["stored_reads"]) is bool
        and type(value["resources"]) is list and len(value["resources"]) <= 1, "configuration_invalid")
    resources,environments = {},[]
    for row in value["resources"]:
        _closed(row,"resource_id resource deployment")
        resources[row["resource_id"]] = row["resource"]
        environments.append(dict(operation=TOOL,resource_id=row["resource_id"],deployment=row["deployment"]))
    result = normalize_esm_gene_embedding_configuration(resources,environments,policy=value["policy"])
    result["stored_reads"] = value["stored_reads"]
    return result


def esm_gene_embedding_tool_contract(configuration):
    configuration = validate_esm_gene_embedding_configuration(configuration)
    allowed = ({"embed"} if configuration["resources"] else set()) | ({"read_stored"} if configuration["stored_reads"] else set())
    if not allowed: return None
    schema = contracts.esm_gene_embedding_schema("Arguments")
    schema["oneOf"] = [branch for branch in schema["oneOf"] if branch["properties"]["mode"]["const"] in allowed]
    return dict(resources="local",invocation_route=dict(kind="direct"),input_schema=schema,
        description="Generate retained ESM2 representations from supplied protein FASTA and an explicit gene/isoform occurrence map, or read selected stored vectors.",
        instructions="Use the actually received original FASTA File and explicit occurrence map. No sequence is fetched. "
            "Select the configured ESM2 t6 8M layer6 CPU profile and both pooling meanings explicitly. "
            "The native worker means non-special model-token representations per protein, then gives each successful "
            "supplied isoform occurrence equal weight for its gene. Duplicate names remain distinct occurrences. "
            "Length-filtered, invalid, missing and failed members supply no invented vector or zero value. "
            "No case conversion, truncation, OOM retry, model download or device fallback occurs. "
            "Native vectors are dimensionless representations, not function probabilities. Stored row/component paging "
            "does not change the original calculation or infer another embedding.",
        configuration=dict(job_limits=configuration["policy"],stored_reads=configuration["stored_reads"],
            model_name=contracts.MODEL,layer=6,device="cpu",execution="isolated_store_free_worker"))


def esm_worker_environment(request, directory):
    """Exact selected interpreter/import roots; no package discovery or fallback."""
    request = contracts.validate_esm_worker_request(request)
    driver = request["deployment"]["driver"]
    executable = PurePosixPath(driver["python_executable"])
    _require(executable.parent.name == "bin", "selected_python_layout_required")
    roots = [driver["module_root"], *[str(PurePosixPath(d["package_root"]).parent) for d in driver["dependencies"]]]
    directory = Path(directory)
    return dict(PYTHONHOME=str(executable.parent.parent),PYTHONPATH=":".join(dict.fromkeys(roots)),
        PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",PYTHONSAFEPATH="1",
        TMPDIR=str(directory/"temporary"),TMP=str(directory/"temporary"),TEMP=str(directory/"temporary"),
        XDG_CACHE_HOME=str(directory/"cache"),TORCH_HOME=str(directory/"cache/torch"),
        OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1")


def esm_worker_implementation_files(request):
    """Flatten the selected pin declarations without opening or importing them."""
    request = contracts.validate_esm_worker_request(request)
    deployment,files = request["deployment"],{}
    driver = deployment["driver"]
    declared = [dict(path=str(PurePosixPath(driver["module_root"])/(r["module"].replace(".","/")+".py")),
        sha256=r["sha256"]) for r in driver["implementation_files"]]
    declared.extend(pin for dependency in driver["dependencies"] for pin in dependency["files"])
    declared.extend(deployment[key] for key in ("checkpoint","regression_checkpoint"))
    for pin in declared:
        _require(pin["path"] not in files or files[pin["path"]] == pin["sha256"],"selected_pin_conflict")
        files[pin["path"]] = pin["sha256"]
    return [dict(path=path,sha256=sha) for path,sha in files.items()]


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store,value["artifact_ref"])
    _require(metadata["sha256"] == value["sha256"] and metadata["size"] == value["size_bytes"], "file_identity_conflict")
    return value


def _path(registry, file, *, store_root=None):
    root = registry.store.path if store_root is None else store_root
    return str(root/"artifacts"/file["sha256"][:2]/file["sha256"])


def _input_artifact(registry, item):
    record = registry.store.get(item["reference"])
    _require(record.get("record_type") == item["namespace"], "input_namespace_conflict")
    if item["namespace"] == "artifact": return item["reference"]
    from .alignment_site_native import immutable_record
    immutable_record(record)
    reference,representation,_ = source_window_selection(record,"original")
    _require(representation == "original" and type(reference) is str, "input_representation_conflict")
    return reference


def _input_decision(registry, context, item, cutoff):
    artifact = _input_artifact(registry,item)
    _metadata(registry.store,artifact)
    records = EpisodeReturnRecords(registry.store,context.run_id,failure_prefix="esm_gene_embedding_")
    return records.file_admission_before(context,item["reference"],item["namespace"],artifact,cutoff)


def _check_input(registry, context, arguments, descriptor, received, decision, cutoff, *, store_root=None):
    received = validate_molecular_sequence_received_file(received)
    item = arguments["input"]
    _require(received["failure"] is None and received["selection"] == item, "input_not_received")
    value = received["input"]
    records = EpisodeReturnRecords(registry.store,context.run_id,failure_prefix="esm_gene_embedding_")
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db,context.run_id,context.episode_id)
    _require(value["receiver"] == dict(run_id=context.run_id,episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)),assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(value["scope"],registry.store.validate_scope(plain(context.scope)))
        and _same(value["inheritance_manifest"],manifest)
        and _same(value["witness"]["record"],registry.store.get(item["reference"]))
        and value["byte_verification"] == "verified", "input_admission_conflict")
    file = _file(registry,value["file"])
    _require(file["format"] == "fasta" and file["artifact_ref"] == _input_artifact(registry,item), "input_file_conflict")
    expected = dict(path=_path(registry,file,store_root=store_root),file=file,
        source_ref=item["reference"] if item["namespace"] == "source" else None)
    _require(_same(descriptor,expected) and _same(decision,_input_decision(registry,context,item,cutoff)),
        "input_decision_admission_conflict")
    return received


def _fresh_input(registry,context,reader,arguments,cutoff):
    item = arguments["input"]
    decision = _input_decision(registry,context,item,cutoff)
    received,path = reader(context,item["reference"],item["namespace"],file_format="fasta")
    received = validate_molecular_sequence_received_file(received)
    _require(received["failure"] is None and received["input"] is not None and path is not None, "input_not_received")
    descriptor = dict(path=str(path),file=received["input"]["file"],
        source_ref=item["reference"] if item["namespace"] == "source" else None)
    _check_input(registry,context,arguments,descriptor,received,decision,cutoff)
    return descriptor,received,decision


def _selected_resource(selected,policy):
    _closed(selected,"resource_id resource deployment")
    checked = normalize_esm_gene_embedding_configuration({selected["resource_id"]:selected["resource"]},
        [dict(operation=TOOL,resource_id=selected["resource_id"],deployment=selected["deployment"])],policy=policy)
    _require(_same(checked["resources"],[selected]),"resource_selection_conflict")
    return selected


def _native_request(arguments,descriptor,selected):
    return contracts.validate_esm_worker_request(dict(version=contracts.REQUEST_VERSION,input=descriptor,
        genes=arguments["genes"],parameters=arguments["parameters"],deployment=selected["deployment"]))


def _historical_store_root(worker,invocation):
    value = worker["selection"]["cwd"]
    path = PurePosixPath(value)
    _require(type(value) is str and path.is_absolute() and str(path) == value and ".." not in path.parts
        and path.parts[-4:] == ("cache","molecular-measurements",digest(invocation["operation_key"]),"worker"),
        "worker_directory_conflict")
    return path.parents[3]


def _worker_control(worker,request,invocation):
    _closed(worker,"request selection handle observation native_request native_request_raw result_sha256")
    selected,handle,observed = worker["selection"],worker["handle"],worker["observation"]
    _closed(selected,"version command cwd environment policy request python implementation_files")
    root = _historical_store_root(worker,invocation)
    directory = root/"cache/molecular-measurements"/digest(invocation["operation_key"])/"worker"
    driver = request["deployment"]["driver"]
    command = [driver["python_executable"],"-m","gene_annotation_episode.esm_gene_embedding_worker",
        str(directory/"worker-request.json"),str(directory/"worker-result.json")]
    _require(selected["version"] == "ordinary_molecular_execution_v1" and _same(worker["request"],request)
        and _same(selected["request"],dict(operation=OPERATION,arguments=dict(request=request)))
        and selected["python"] == dict(path=driver["python_executable"],sha256=driver["python_sha256"])
        and _same(selected["implementation_files"],esm_worker_implementation_files(request))
        and selected["command"] == handle["command"] == command
        and selected["cwd"] == handle["cwd"] == str(directory)
        and handle["stdout"] == str(directory/"stdout") and handle["stderr"] == str(directory/"stderr")
        and _same(selected["environment"],esm_worker_environment(request,directory))
        and observed["terminal"] is True and observed["quiescent"] is True
        and _same(selected["policy"],handle["metadata"]["policy"])
        and _same(selected["policy"],observed["metadata"]["policy"])
        and _same(selected["policy"],LocalJobPolicy(**selected["policy"]).to_dict()), "worker_control_conflict")
    paths = handle["paths"]
    _require(all(type(p) is str and PurePosixPath(p).parent == directory for p in paths.values()), "worker_handle_conflict")
    raw = worker["native_request_raw"]
    _require(type(raw) is str and hashlib.sha256(raw.encode()).hexdigest() == handle["request_sha256"]
        and _same(decode_json(raw.encode()),worker["native_request"])
        and _same(worker["native_request"],dict(command=command,cwd=str(directory),file_bytes=selected["policy"]["scratch_bytes"],
            ready_path=paths["ready"],release_path=paths["release"],result_path=paths["result"],stdin_path=None,
            env=selected["environment"])),"worker_handle_conflict")
    return root


def _worker_record(registry,work,request,directory,invocation):
    output = directory/"worker-result.json"
    _require(Path(work.output_path) == output,"worker_output_conflict")
    handle = native_lifecycle.NativeJobHandle(directory/"native-handle.json")
    observed = native_lifecycle.status(handle)
    if not (observed["terminal"] and observed["quiescent"]):
        raise MolecularOperationUnpublished("esm_gene_embedding_worker_attempt_unconfirmed")
    _require(_same({k:v for k,v in work.metadata.items() if k != "molecular_failure"},observed["metadata"]),
        "worker_metadata_conflict")
    selection = decode_json((directory/"execution-selection.json").read_bytes())
    original = handle.read()
    with _regular(original["paths"]["request"]) as stream:raw = stream.read()
    with _regular(directory/"worker-request.json") as stream:
        _require(_same(decode_json(stream.read()),selection["request"]),"worker_request_conflict")
    if observed["metadata"].get("native_returncode") != 0 or work.metadata.get("molecular_failure") or not output.is_file():
        raise _KnownFailure("esm_gene_embedding_native_worker_failed")
    with _regular(output) as stream:result = contracts.validate_esm_worker_result(decode_json(stream.read()),request=request)
    worker = dict(request=request,selection=selection,handle=original,observation=observed,
        native_request=decode_json(raw),native_request_raw=raw.decode(),result_sha256=digest(result))
    _require(str(_worker_control(worker,request,invocation)) == str(registry.store.path),"worker_store_conflict")
    return result,worker


def _outcome(arguments,key,public,*,redisplay=False):
    context = public["context"]
    partial = (context["execution"]["state"] != "completed" or not context["input_catalog_complete"]
        or bool(context["input_issues"]) or bool(context["length_filtered_protein_ordinals"])
        or bool(context["failed_protein_ordinals"]) or bool(context["unavailable_requested_protein_ordinals"])
        or any(g["status"] != "available" for g in context["gene_populations"]))
    return dict(status="partial" if partial else "completed",operation_ref=identity("operation",dict(
        key=key,name=TOOL,arguments=arguments)),record_refs=[public["source_ref"]],
        changed_record_refs=[] if redisplay else [public["source_ref"]],result=public,
        feedback=dict(category="representation",code="esm_gene_embedding_selected_result_partial",source_ref=public["source_ref"])
            if partial else None)


def _failure(registry,arguments,key,error):
    text = str(error)
    code = text if re.fullmatch(r"[a-z][a-z0-9_]*",text) else "esm_gene_embedding_execution_failed"
    diagnostic = registry.store.artifact(canonical(dict(version="esm_gene_embedding_diagnostic_v1",
        exception_type=type(error).__module__+"."+type(error).__name__,exception_message=text)),"application/json")
    return dict(status="failed" if isinstance(error,_KnownFailure) else "unavailable" if isinstance(error,OSError)
        or code.endswith("_unavailable") else "invalid" if isinstance(error,(ValueError,TypeError,KeyError,ContractError)) else "failed",
        operation_ref=identity("operation",dict(key=key,name=TOOL,arguments=arguments)),record_refs=[],changed_record_refs=[],result=None,
        feedback=dict(category="execution",code=code,diagnostic_ref=diagnostic))


async def execute_esm_gene_embedding_tool(registry,arguments,*,scope,operation_key,authority):
    from .molecular_measurement_tools import _recorded_molecular_action_details
    from .esm_gene_embedding_publication import _read,_project,_publish,read_esm_gene_embedding_action_result
    context,reader = authenticate_molecular_invocation(registry,TOOL,arguments,plain(scope),operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry and owner.run_id == context.run_id,"execution_owner_conflict")
    invocation = _invocation(context,operation_key)
    directory = _directory(registry.store.path/"cache/molecular-measurements"/digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry,TOOL,arguments,plain(scope),operation_key)
        if registry.store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?",(operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry,context,arguments,operation_key,TOOL,
                recovery_context=context,recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed","partial"):
                _require(_same(read_esm_gene_embedding_action_result(registry,context,arguments,operation_key,reader=reader),
                    outcome["result"]),"cached_result_conflict")
            else:
                _require(outcome.get("status") in ("failed","invalid","unavailable") and outcome.get("result") is None
                    and outcome.get("record_refs") == [],"cached_failure_conflict")
            return outcome
        intent_path = directory/"esm-gene-embedding-intent.json"
        attempt_possible = intent_path.exists()
        try:
            arguments = contracts.validate_esm_embedding_arguments(arguments)
            configured = registry._esm_gene_embedding_configuration
            configuration = None if configured is None else validate_esm_gene_embedding_configuration(configured)
            if arguments["mode"] == "read_stored":
                _require(configuration is not None and configuration["stored_reads"],"stored_reads_not_configured")
                with registry.store.transaction():
                    publication = _read(registry,context,reader,arguments["result_ref"],before_decision_index=invocation["decision_index"])
                    public = _project(registry,publication,arguments["selection"])
                    outcome = _outcome(arguments,operation_key,public,redisplay=True)
                    registry._save(operation_key,TOOL,arguments,plain(scope),outcome)
                return outcome
            if intent_path.exists():
                intent = decode_json(intent_path.read_bytes())
                _closed(intent,"version arguments invocation selected_resource policy input input_admission input_decision_admission request")
                _require(intent["version"] == INTENT_VERSION and _same(intent["arguments"],arguments)
                    and _same(intent["invocation"],invocation),"original_intent_conflict")
            else:
                _require(configuration is not None and len(configuration["resources"]) == 1,"native_resource_required")
                selected = configuration["resources"][0]
                _require(_same(owner.resources.get(selected["resource_id"]),selected["resource"])
                    and _same(registry.local_job_policy.to_dict(),configuration["policy"]),"run_resource_selection_conflict")
                descriptor,received,decision = _fresh_input(registry,context,reader,arguments,invocation["decision_index"])
                intent = dict(version=INTENT_VERSION,arguments=arguments,invocation=invocation,selected_resource=selected,
                    policy=configuration["policy"],input=descriptor,input_admission=received,input_decision_admission=decision,
                    request=_native_request(arguments,descriptor,selected))
                _immutable(intent_path,intent)
            _selected_resource(intent["selected_resource"],intent["policy"])
            _check_input(registry,context,arguments,intent["input"],intent["input_admission"],
                intent["input_decision_admission"],invocation["decision_index"])
            _require(_same(intent["request"],_native_request(arguments,intent["input"],intent["selected_resource"])),"native_request_conflict")
            worker_directory = _directory(directory/"worker")
            worker_directory.mkdir(exist_ok=True)
            if not (worker_directory/"native-handle.json").exists():
                _require(configuration is not None and _same(configuration["resources"],[intent["selected_resource"]]),
                    "unstarted_resource_selection_conflict")
            selection_path = worker_directory/"execution-selection.json"
            if selection_path.exists():
                selection = decode_json(selection_path.read_bytes())
                _require(_same(selection["request"],dict(operation=OPERATION,arguments=dict(request=intent["request"])))
                    and _same(selection["policy"],intent["policy"])
                    and _same(selection["environment"],esm_worker_environment(intent["request"],worker_directory)),"original_worker_selection_conflict")
            else:
                _require(_same(owner.resources.get(intent["selected_resource"]["resource_id"]),intent["selected_resource"]["resource"])
                    and _same(registry.local_job_policy.to_dict(),intent["policy"])
                    and configuration is not None and _same(configuration["resources"],[intent["selected_resource"]]),
                    "run_resource_selection_conflict")
            attempt_possible = True
            work = await registry._sequence_worker_async(OPERATION,dict(request=intent["request"]),
                directory=worker_directory,owned_directory=worker_directory)
            authenticate_molecular_invocation(registry,TOOL,arguments,plain(scope),operation_key)
            _check_input(registry,context,arguments,intent["input"],intent["input_admission"],
                intent["input_decision_admission"],invocation["decision_index"])
            result,worker = _worker_record(registry,work,intent["request"],worker_directory,invocation)
            with registry.store.transaction():
                public = _publish(registry,arguments,invocation,intent,result,worker,worker_directory)
                outcome = _outcome(arguments,operation_key,public)
                registry._save(operation_key,TOOL,arguments,plain(scope),outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if attempt_possible and not isinstance(error,_KnownFailure):
                raise MolecularOperationUnpublished("esm_gene_embedding_original_action_unpublished") from error
            with registry.store.transaction():
                outcome = _failure(registry,arguments,operation_key,error)
                registry._save(operation_key,TOOL,arguments,plain(scope),outcome)
            return outcome


def read_retained_esm_gene_embedding_publication(*args,**kwargs):
    from .esm_gene_embedding_publication import read_retained_esm_gene_embedding_publication as read
    return read(*args,**kwargs)


def read_esm_gene_embedding_action_result(*args,**kwargs):
    from .esm_gene_embedding_publication import read_esm_gene_embedding_action_result as read
    return read(*args,**kwargs)
