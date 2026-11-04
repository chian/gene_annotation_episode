"""Ordinary selected MUSCLE/IQ-TREE execution and retained phylogeny values.

The parent supplies the candidate/reference panel and retains the evidence for
reference functions. This owner authenticates one selected File, exact native
programs and original worker attempts; it does not infer annotation labels.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re

from .communication import plain
from .domain import ContractError, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import MolecularOperationUnpublished, authenticate_molecular_invocation
from .molecular_sequence_input_contracts import input_record_digest, validate_molecular_sequence_received_file
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import NativeFileCaptureError, _identity, _metadata, capture_native_file
from .alignment_site_native import immutable_record
from .reference_edit_outcome_tools import _admit, _context, _invocation
from . import native_lifecycle
from . import iqtree_phylogeny_driver as iqtree
from . import muscle_alignment_driver as muscle
from . import protein_phylogeny_result_contracts as contracts
from . import protein_phylogeny_result_worker as result_worker


TOOL = contracts.TOOL
CONFIGURATION_VERSION = "ordinary_protein_phylogeny_configuration_v1"
ENVIRONMENT_VERSION = "protein_phylogeny_execution_selection_v1"
CAPTURE_VERSION = "ordinary_protein_phylogeny_native_capture_v1"
CAPTURE_CONTROL_VERSION = "ordinary_protein_phylogeny_native_control_v1"
_WORKERS = {"protein_conservation_native": "gene_annotation_episode.muscle_alignment_driver",
    iqtree.OPERATION: "gene_annotation_episode.iqtree_phylogeny_driver",
    result_worker.OPERATION: "gene_annotation_episode.protein_phylogeny_result_worker"}
_STAGES = ("alignment", "iqtree")
_FILE_URI = "urn:protein-phylogeny-native-file:"


def _require(condition, code):
    if not condition:
        raise ContractError("protein_phylogeny_" + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "fields_invalid")


def _same(first, second):
    return canonical(first) == canonical(second)


class _KnownFailure(ContractError):
    """The original result worker is confirmed terminal and unsuccessful."""


def _environment(value):
    _closed(value, "version environment_realization iqtree_software iqtree_parameters muscle_software muscle_parameters")
    _require(value["version"] == ENVIRONMENT_VERSION
        and value["environment_realization"] == "operation_scoped_tmp_and_cache_v1", "environment_invalid")
    return dict(version=ENVIRONMENT_VERSION, environment_realization=value["environment_realization"],
        iqtree_software=iqtree.validate_iqtree_software(value["iqtree_software"]),
        iqtree_parameters=iqtree.validate_iqtree_parameters(value["iqtree_parameters"]),
        muscle_software=muscle.validate_muscle_alignment_software(value["muscle_software"]),
        muscle_parameters=muscle.validate_muscle_alignment_parameters(value["muscle_parameters"]))


def normalize_protein_phylogeny_configuration(resources, environments, *, policy):
    _require(type(resources) is dict and isinstance(environments, (list, tuple)), "configuration_invalid")
    checked, selected = LocalJobPolicy(**policy).to_dict(), []
    _require(_same(checked, policy), "policy_invalid")
    for row in environments:
        _closed(row, "operation resource_id environment")
        _require(row["operation"] == TOOL and not selected and type(row["resource_id"]) is str
            and bool(row["resource_id"]), "ambiguous_resource_selection")
        resource = resources.get(row["resource_id"])
        _require(type(resource) is dict and resource.get("kind") == "local"
            and _same(resource.get("policy"), checked), "resource_allocation_conflict")
        selected.append(dict(resource_id=row["resource_id"], resource=deepcopy(resource),
            environment=_environment(row["environment"])))
    return dict(version=CONFIGURATION_VERSION, policy=checked, resources=selected, saved_modes=False)


def validate_protein_phylogeny_configuration(value):
    _closed(value, "version policy resources saved_modes")
    _require(value["version"] == CONFIGURATION_VERSION and type(value["saved_modes"]) is bool
        and type(value["resources"]) is list and len(value["resources"]) <= 1, "configuration_invalid")
    resources, environments = {}, []
    for row in value["resources"]:
        _closed(row, "resource_id resource environment")
        resources[row["resource_id"]] = row["resource"]
        environments.append(dict(operation=TOOL, resource_id=row["resource_id"], environment=row["environment"]))
    checked = normalize_protein_phylogeny_configuration(resources, environments, policy=value["policy"])
    checked["saved_modes"] = value["saved_modes"]
    return checked


def protein_phylogeny_tool_arguments_schema(configuration):
    configuration = validate_protein_phylogeny_configuration(configuration)
    allowed = ({"run_native"} if configuration["resources"] else set())
    if configuration["saved_modes"]:
        allowed.update(("calculate_saved", "read_stored"))
    if not allowed:
        return None
    schema = contracts.phylogeny_result_schema("Arguments")
    schema["$defs"]["Arguments"]["oneOf"] = [branch for branch in schema["$defs"]["Arguments"]["oneOf"]
        if branch["properties"]["mode"]["const"] in allowed]
    return schema


def protein_phylogeny_tool_contract(configuration):
    configuration = validate_protein_phylogeny_configuration(configuration)
    schema = protein_phylogeny_tool_arguments_schema(configuration)
    if schema is None:
        return None
    environment = None if not configuration["resources"] else configuration["resources"][0]["environment"]
    return dict(resources="local", invocation_route=dict(kind="direct"),
        description="Infer protein trees for a candidate and supplied characterized reference proteins, retaining native placement and branch support as evidence for the parent's reference-subfamily annotation hypothesis.",
        instructions=("Use the parent-selected protein panel or alignment and exact configured programs/settings. "
            "The parent supplies and retains reference-function evidence; this tool does not fetch references or assign function. "
            "Select supplied_alignment or the predeclared MUSCLE-to-IQ-TREE route explicitly. "
            "The MUSCLE route consumes raw FASTA; supplied_alignment accepts an already aligned FASTA File. "
            "Preserve native tip labels, unresolved member mappings, both native tree roles, branch lengths and report-grounded support. "
            "IQ-TREE uses LG and 1000 ultrafast bootstrap replicates with explicit CPU/seed. Saved modes reuse retained data. "
            "Placement/support inform the parent's annotation decision; they are not calibrated functional confidence or a biological-root assignment."),
        input_schema=schema, configuration=dict(job_limits=configuration["policy"],
            saved_modes=configuration["saved_modes"], native_parameters=None if environment is None else dict(
                iqtree=environment["iqtree_parameters"], muscle=environment["muscle_parameters"]),
            execution="isolated_store_free_worker", algorithm_substitution=False))


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store, value["artifact_ref"])
    _require(metadata["sha256"] == value["sha256"] and metadata["size"] == value["size_bytes"], "file_identity_conflict")
    return value


def _path(registry, file, *, store_root=None):
    root = registry.store.path if store_root is None else store_root
    return str(root / "artifacts" / file["sha256"][:2] / file["sha256"])


def _source_admission(registry, context, reference, cutoff):
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_phylogeny_")
    records.authenticate(context)
    return records.source_admission_before(context, reference, cutoff)


def _input_decision_admission(registry, context, item, cutoff):
    record = registry.store.get(item["reference"])
    _require(record.get("record_type") == item["namespace"], "input_namespace_conflict")
    if item["namespace"] == "source":
        from .materials import source_window_selection
        immutable_record(record)
        artifact, representation, _ = source_window_selection(record, "original")
        _require(representation == "original", "input_representation_conflict")
    else:
        artifact = item["reference"]
    _metadata(registry.store, artifact)
    return EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_phylogeny_").file_admission_before(
        context, item["reference"], item["namespace"], artifact, cutoff)


def _check_input(registry, context, arguments, descriptor, admission, decision, cutoff, *, store_root=None):
    item = arguments["input"]
    received = validate_molecular_sequence_received_file(admission)
    _require(received["failure"] is None and received["selection"] == dict(
        reference=item["reference"], namespace=item["namespace"]), "input_not_received")
    value = received["input"]
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_phylogeny_")
    records.authenticate(context)
    _require(value["receiver"] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(value["scope"], registry.store.validate_scope(plain(context.scope)))
        and _same(value["inheritance_manifest"], EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id))
        and _same(value["witness"]["record"], registry.store.get(item["reference"]))
        and records._received_before(context.episode_id, item["reference"], cutoff)
        and records._received_before(context.episode_id, value["file"]["artifact_ref"], cutoff), "input_admission_conflict")
    file = _file(registry, value["file"])
    _require(file["format"] == item["format"] and value["byte_verification"] == "verified"
        and _same(descriptor, dict(path=_path(registry, file, store_root=store_root), file=file,
            source_ref=item["reference"] if item["namespace"] == "source" else None))
        and _same(decision, _input_decision_admission(registry, context, item, cutoff)), "input_decision_admission_conflict")


def _fresh_input(registry, context, reader, arguments, cutoff):
    item = arguments["input"]
    decision = _input_decision_admission(registry, context, item, cutoff)
    admission, path = reader(context, item["reference"], item["namespace"], file_format=item["format"])
    _require(admission["input"] is not None and path is not None, "input_not_received")
    descriptor = dict(path=str(path), file=admission["input"]["file"],
        source_ref=item["reference"] if item["namespace"] == "source" else None)
    _check_input(registry, context, arguments, descriptor, admission, decision, cutoff)
    return descriptor, admission, decision


def _selected_resource(selected, policy):
    _closed(selected, "resource_id resource environment")
    _require(type(selected["resource_id"]) is str and bool(selected["resource_id"])
        and type(selected["resource"]) is dict and selected["resource"].get("kind") == "local"
        and _same(selected["resource"].get("policy"), policy), "resource_allocation_conflict")
    _environment(selected["environment"])


def _run_selection(registry, owner, selected, policy):
    _selected_resource(selected, policy)
    _require(_same(owner.resources.get(selected["resource_id"]), selected["resource"])
        and _same(registry.local_job_policy.to_dict(), policy), "run_resource_selection_conflict")


def _worker_dispatch(registry, owner, request, directory, operation, policy, selected):
    _require(_same(LocalJobPolicy(**policy).to_dict(), policy), "policy_invalid")
    if selected is not None:
        _selected_resource(selected, policy)
    path = directory / "execution-selection.json"
    if path.exists():
        original = decode_json(path.read_bytes())
        _closed(original, "version command cwd environment policy request python implementation_files")
        _require(original["version"] == "ordinary_molecular_execution_v1" and original["cwd"] == str(directory)
            and _same(original["request"], dict(operation=operation, arguments=dict(request=request)))
            and _same(original["policy"], policy) and original["command"] == [original["python"]["path"],
                "-m", _WORKERS[operation], str(directory / "worker-request.json"), str(directory / "worker-result.json")],
            "original_worker_selection_conflict")
    else:
        _require(_same(registry.local_job_policy.to_dict(), policy), "run_resource_selection_conflict")
        if selected is not None:
            _run_selection(registry, owner, selected, policy)


def _historical_store_root(worker, invocation, stage):
    path = worker["selection"]["cwd"]
    _require(type(path) is str, "worker_selection_conflict")
    directory = PurePosixPath(path)
    _require(directory.is_absolute() and str(directory) == path and ".." not in directory.parts
        and directory.parts[-4:] == ("cache", "molecular-measurements", digest(invocation["operation_key"]), stage),
        "worker_selection_conflict")
    return directory.parents[3]


def _worker_control(worker, request, operation, invocation, stage):
    _closed(worker, "request selection handle observation native_request native_request_raw result_sha256")
    selected, original, observed = worker["selection"], worker["handle"], worker["observation"]
    _closed(selected, "version command cwd environment policy request python implementation_files")
    root = _historical_store_root(worker, invocation, stage)
    directory = root / "cache" / "molecular-measurements" / digest(invocation["operation_key"]) / stage
    _require(selected["version"] == "ordinary_molecular_execution_v1" and _same(worker["request"], request)
        and _same(selected["request"], dict(operation=operation, arguments=dict(request=request)))
        and selected["command"] == [selected["python"]["path"], "-m", _WORKERS[operation],
            str(directory / "worker-request.json"), str(directory / "worker-result.json")]
        and original["command"] == selected["command"] and original["cwd"] == selected["cwd"] == str(directory)
        and original["stdout"] == str(directory / "stdout") and original["stderr"] == str(directory / "stderr")
        and observed["terminal"] is True and observed["quiescent"] is True
        and _same(original["metadata"]["policy"], selected["policy"])
        and _same(observed["metadata"]["policy"], selected["policy"])
        and _same(LocalJobPolicy(**selected["policy"]).to_dict(), selected["policy"]), "worker_control_conflict")
    paths, raw = original["paths"], worker["native_request_raw"]
    _require(all(type(path) is str and PurePosixPath(path).parent == directory for path in paths.values()), "worker_handle_conflict")
    _require(type(raw) is str and hashlib.sha256(raw.encode()).hexdigest() == original["request_sha256"]
        and _same(decode_json(raw.encode()), worker["native_request"])
        and _same(worker["native_request"], dict(command=selected["command"], cwd=str(directory),
            file_bytes=selected["policy"]["scratch_bytes"], ready_path=paths["ready"], release_path=paths["release"],
            result_path=paths["result"], stdin_path=None, env=selected["environment"])), "worker_handle_conflict")
    return root


def _worker_record(registry, work, request, directory, operation, invocation, stage, *, allow_failure=False):
    output = directory / "worker-result.json"
    _require(Path(work.output_path) == output, "worker_output_conflict")
    handle = native_lifecycle.NativeJobHandle(directory / "native-handle.json")
    observed = native_lifecycle.status(handle)
    if not (observed["terminal"] and observed["quiescent"]):
        raise MolecularOperationUnpublished("protein_phylogeny_worker_attempt_unconfirmed")
    _require(_same({key: value for key, value in work.metadata.items() if key != "molecular_failure"},
        observed["metadata"]), "worker_metadata_conflict")
    selected = decode_json((directory / "execution-selection.json").read_bytes())
    original = handle.read()
    with _regular(original["paths"]["request"]) as stream:
        raw = stream.read()
    with _regular(directory / "worker-request.json") as stream:
        _require(_same(decode_json(stream.read()), selected["request"]), "worker_request_conflict")
    result = None
    if output.is_file():
        with _regular(output) as stream:
            try:
                result = decode_json(stream.read())
            except (ValueError, TypeError):
                if not allow_failure:
                    raise
    worker = dict(request=request, selection=selected, handle=original, observation=observed,
        native_request=decode_json(raw), native_request_raw=raw.decode(), result_sha256=None if result is None else digest(result))
    _require(str(_worker_control(worker, request, operation, invocation, stage)) == str(registry.store.path), "worker_store_conflict")
    failed = bool(work.metadata.get("molecular_failure")) or observed["metadata"].get("native_returncode") != 0
    if not allow_failure and (failed or result is None):
        raise _KnownFailure("protein_phylogeny_result_calculation_failed")
    return result, worker


def _manifest(stage, value, request):
    try:
        checked = (muscle.validate_muscle_alignment_native_manifest(value) if stage == "alignment"
            else iqtree.validate_iqtree_native_manifest(value))
        return checked if _same(checked["request"], request) else None
    except (ValueError, TypeError, KeyError):
        return None


def _native_request(stage, descriptor, environment):
    if stage == "alignment":
        return dict(version=muscle.REQUEST_VERSION, input=deepcopy(descriptor),
            software=environment["muscle_software"], parameters=environment["muscle_parameters"])
    return dict(version=iqtree.REQUEST_VERSION, input=deepcopy(descriptor),
        software=environment["iqtree_software"], parameters=environment["iqtree_parameters"])


def _stage_specs(stage):
    if stage == "alignment":
        return (("input", "muscle-alignment-native/input.fasta", "fasta"),
            ("alignment", "muscle-alignment-native/aligned.fasta", "aligned_fasta"),
            ("stdout", "muscle-alignment-native/stdout", "muscle_log"),
            ("stderr", "muscle-alignment-native/stderr", "muscle_log"))
    return tuple((role, iqtree.NATIVE_DIRECTORY_NAME + "/" + name, format) for role, name, format, _ in iqtree._FILES)


def _issue(code, path="/native_execution", *, evidence=()):
    return dict(code=code, phase="native_capture", path=path, severity="qualification", evidence_refs=list(evidence))


def _capture_stage(registry, invocation, arguments, stage, request, manifest, worker, directory):
    """Retain actual files before any later pipeline stage or native parsing."""
    retained_path = directory / "capture.json"
    if retained_path.exists():
        retained = decode_json(retained_path.read_bytes())
        _require(retained["stage"] == stage and _same(retained["request"], request)
            and _same(retained["manifest"], manifest) and _same(retained["worker"], worker), "original_capture_conflict")
        # A prior database transaction may have rolled back after this disk
        # record was written. Re-admit the same pinned bytes and deterministic
        # Sources; the immutable final record must still be exactly identical.
    stamp = directory / "capture-time.json"
    if not stamp.exists():
        _immutable(stamp, dict(retrieved_at=datetime.now(timezone.utc).isoformat()))
    retrieved_at = decode_json(stamp.read_bytes())["retrieved_at"]
    checked = _manifest(stage, manifest, request)
    declarations = {} if checked is None else {row["relative_path"]: row for row in checked["files"]}
    rows, logs = [], []
    operation_ref = identity("operation", dict(key=invocation["operation_key"], name=TOOL, arguments=arguments))
    worker_control_ref = registry.store.artifact(canonical(dict(invocation=invocation, stage=stage,
        request=request, manifest=manifest, worker=worker)), "application/json")
    for role, name, format in _stage_specs(stage):
        file = None
        try:
            file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
                format=format, media_type="application/octet-stream")
        except NativeFileCaptureError as error:
            if error.code != "capture_file_unavailable":
                raise
        declared = declarations.get(name)
        qualification = ("native_output_unavailable" if file is None else "native_output_unbound" if declared is None else
            "native_output_identity_conflict" if any(file[key] != declared[key] for key in ("sha256", "size_bytes")) else None)
        source = None
        if file is not None:
            source = registry._put("source", dict(provider=TOOL, accession=operation_ref,
                uri=_FILE_URI + stage + ":" + role, artifact_ref=file["artifact_ref"], text_ref=None,
                request_ref=worker_control_ref, version=CAPTURE_VERSION, retrieved_at=retrieved_at,
                parent_source_refs=([arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else []),
                auxiliary_artifact_refs=[]), origin="tool")
        rows.append(dict(role=role, relative_path=name, declared=declared, file=file,
            qualification=qualification, source=None if source is None else dict(source_ref=source["id"], record_sha256=digest(source))))
    for name in ("stdout", "stderr"):
        file = None
        try:
            file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
                format="protein_phylogeny_worker_log", media_type="application/octet-stream")
        except NativeFileCaptureError as error:
            if error.code != "capture_file_unavailable":
                raise
        logs.append(dict(name=name, file=file))
    captured = dict(stage=stage, request=request, manifest=manifest, worker=worker,
        outputs=rows, logs=logs, worker_control_ref=worker_control_ref)
    _immutable(retained_path, captured)
    return captured


def _captured_source(registry, stage, role):
    row = next((row for row in stage["outputs"] if row["role"] == role), None)
    if row is None or row["file"] is None or row["qualification"] == "native_output_identity_conflict":
        return None
    source = registry.store.get(row["source"]["source_ref"])
    _require(source["artifact_ref"] == row["file"]["artifact_ref"], "capture_primary_file_conflict")
    return dict(path=_path(registry, row["file"]), file=row["file"], source_ref=source["id"])


def _capture_request(registry, control, body, *, store_root):
    environment = _environment(control["selected_resource"]["environment"])
    stages = {row["stage"]: row for row in body["stages"]}
    alignment = stages.get("alignment")
    fitted = stages.get("iqtree")
    issues, outputs, captures = [], [], []
    def execution(row):
        checked = None if row is None else _manifest(row["stage"], row["manifest"], row["request"])
        code = None if checked is None else checked["returncode"]
        return dict(state="not_attempted" if row is None else "unknown" if code is None else "completed" if code == 0 else "failed",
            returncode=code, reported_version=None)
    for row in body["stages"]:
        checked = _manifest(row["stage"], row["manifest"], row["request"])
        if checked is None:
            issues.append(_issue("protein_phylogeny_native_manifest_unavailable", "/" + row["stage"]))
        else:
            issues.extend(_issue(code, "/" + row["stage"]) for code in checked["issues"])
        issues.extend(_issue("protein_phylogeny_" + item["qualification"], "/" + row["stage"] + "/" + item["role"])
            for item in row["outputs"] if item["qualification"] is not None and item["role"] in
                (*contracts.ROLES, "report", "alignment"))
    aligned = control["input"] if alignment is None and control["arguments"]["input_mode"] == "supplied_alignment" else (
        None if alignment is None else _captured_source(registry, alignment, "alignment"))
    for role in contracts.ROLES:
        descriptor = None if fitted is None else _captured_source(registry, fitted, role)
        file = None if descriptor is None else descriptor["file"]
        outputs.append(dict(role=role, file=file, capture=dict(state="missing" if file is None else "complete",
            retained_size_bytes=None if file is None else file["size_bytes"], original_size_bytes=None if file is None else file["size_bytes"]),
            parser_status="not_parsed", document_completeness=None, retained_tree_count=None))
        if descriptor is not None:
            descriptor["path"] = _path(registry, file, store_root=store_root)
            captures.append(dict(role=role, captured=descriptor))
    report = None if fitted is None else _captured_source(registry, fitted, "report")
    report_capture = dict(state="missing" if report is None else "complete", retained_size_bytes=None if report is None else report["file"]["size_bytes"],
        original_size_bytes=None if report is None else report["file"]["size_bytes"])
    if report is not None:
        report.update(path=_path(registry, report["file"], store_root=store_root), capture=report_capture)
    context = dict(version=contracts.CONTEXT_VERSION, input_mode=control["arguments"]["input_mode"],
        input_file=control["input"]["file"], input_source_ref=control["input"]["source_ref"],
        alignment_file=None if aligned is None else aligned["file"],
        alignment_execution=None if control["arguments"]["input_mode"] == "supplied_alignment" else execution(alignment),
        iqtree_execution=execution(fitted), iqtree_parameters=environment["iqtree_parameters"],
        muscle_parameters=None if control["arguments"]["input_mode"] == "supplied_alignment" else environment["muscle_parameters"],
        branch_unit="native_unknown", support_trace=dict(state="unresolved", method="native_unknown", scale="native_unknown",
            reported_model=None, reported_analysis=None, reported_support=None, report_file=None if report is None else report["file"],
            report_capture=report_capture, reason_codes=["report_not_read"]), outputs=outputs,
        interpretation="Native fitted tree and branch support; no calibrated gene-function confidence or biological-root assignment.", issues=issues)
    return dict(version=result_worker.REQUEST_VERSION, mode="parse", context=context, captured_trees=captures,
        report=report, saved=None, pair_requests=control["arguments"]["pair_requests"], selection=control["arguments"]["selection"])


def _capture_control(registry, capture, *, invocation, arguments, input_artifact_refs):
    from .molecular_measurement_tools import _publication_bytes
    immutable_record(capture)
    _require(capture.get("record_type") == "source" and capture.get("origin") == "tool" and capture.get("provider") == TOOL
        and capture.get("version") == CAPTURE_VERSION and capture.get("uri") is None
        and capture.get("accession") == identity("operation", dict(key=invocation["operation_key"], name=TOOL, arguments=arguments))
        and "operand_refs" not in capture, "capture_source_conflict")
    control = decode_json(_publication_bytes(registry.store, capture["request_ref"]))
    _closed(control, "version invocation arguments selected_resource policy input input_admission input_decision_admission input_artifact_refs manifest_ref")
    _require(control["version"] == CAPTURE_CONTROL_VERSION and _same(control["invocation"], invocation)
        and _same(control["arguments"], arguments) and arguments["mode"] == "run_native"
        and input_artifact_refs == control["input_artifact_refs"] == [control["input"]["file"]["artifact_ref"]], "capture_control_conflict")
    _selected_resource(control["selected_resource"], control["policy"])
    environment = _environment(control["selected_resource"]["environment"])
    body = decode_json(_publication_bytes(registry.store, control["manifest_ref"]))
    _closed(body, "version invocation stages input_artifact_refs")
    _require(body["version"] == CAPTURE_VERSION and _same(body["invocation"], invocation)
        and body["input_artifact_refs"] == input_artifact_refs and type(body["stages"]) is list, "capture_body_conflict")
    names = [row["stage"] for row in body["stages"]]
    _require(names in (["iqtree"], ["alignment"], ["alignment", "iqtree"])
        and (names[0] == "alignment") == (arguments["input_mode"] == "selected_MUSCLE_alignment"), "capture_stage_conflict")
    root, references, parents = None, [], []
    aligned = control["input"]
    for stage in body["stages"]:
        _closed(stage, "stage request manifest worker outputs logs worker_control_ref")
        label = stage["stage"]
        request = _native_request(label, control["input"] if label == "alignment" else aligned, environment)
        _require(_same(request, stage["request"]), "native_request_conflict")
        operation = "protein_conservation_native" if label == "alignment" else iqtree.OPERATION
        current_root = _worker_control(stage["worker"], request, operation, invocation, label)
        _require(root is None or root == current_root, "worker_store_conflict")
        root = current_root
        _require(_same(stage["worker"]["selection"]["policy"], control["policy"])
            and stage["worker"]["result_sha256"] == (None if stage["manifest"] is None else digest(stage["manifest"])),
            "native_worker_conflict")
        checked = _manifest(label, stage["manifest"], request)
        declarations = {} if checked is None else {row["relative_path"]: row for row in checked["files"]}
        specs = _stage_specs(label)
        _require(type(stage["outputs"]) is list and len(stage["outputs"]) == len(specs), "capture_files_conflict")
        for row, (role, name, format) in zip(stage["outputs"], specs):
            _closed(row, "role relative_path declared file qualification source")
            _require(row["role"] == role and row["relative_path"] == name and _same(row["declared"], declarations.get(name)),
                "capture_declaration_conflict")
            if row["file"] is None:
                qualification = "native_output_unavailable"
                _require(row["source"] is None, "capture_source_conflict")
            else:
                file = _file(registry, row["file"])
                _require(file["format"] == format, "capture_format_conflict")
                qualification = ("native_output_unbound" if row["declared"] is None else "native_output_identity_conflict"
                    if any(file[key] != row["declared"][key] for key in ("sha256", "size_bytes")) else None)
                _closed(row["source"], "source_ref record_sha256")
                source = registry.store.get(row["source"]["source_ref"])
                immutable_record(source)
                _require(digest(source) == row["source"]["record_sha256"] and source.get("record_type") == "source"
                    and "operand_refs" not in source and source.get("provider") == TOOL
                    and source.get("version") == CAPTURE_VERSION and source.get("origin") == "tool"
                    and source.get("accession") == capture["accession"] and source.get("uri") == _FILE_URI + label + ":" + role
                    and source["artifact_ref"] == file["artifact_ref"] and source["request_ref"] == stage["worker_control_ref"]
                    and source.get("auxiliary_artifact_refs") == [] and source.get("parent_source_refs") ==
                        ([arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else []), "capture_source_conflict")
                references.extend((file["artifact_ref"], source["request_ref"]))
                parents.append(source["id"])
            _require(row["qualification"] == qualification, "capture_qualification_conflict")
        _require(type(stage["logs"]) is list and [row["name"] for row in stage["logs"]] == ["stdout", "stderr"], "capture_logs_conflict")
        for row in stage["logs"]:
            _closed(row, "name file")
            if row["file"] is not None:
                file = _file(registry, row["file"])
                _require(file["format"] == "protein_phylogeny_worker_log", "capture_format_conflict")
                references.append(file["artifact_ref"])
        recorded = decode_json(_publication_bytes(registry.store, stage["worker_control_ref"]))
        _require(_same(recorded, dict(invocation=invocation, stage=label, request=request,
            manifest=stage["manifest"], worker=stage["worker"])), "native_worker_conflict")
        if label == "alignment":
            aligned = _captured_source(registry, stage, "alignment")
            _require("iqtree" not in names or aligned is not None and checked is not None
                and checked["returncode"] == 0 and checked["issues"] == [], "alignment_stage_not_completed")
            if aligned is not None:
                aligned["path"] = _path(registry, aligned["file"], store_root=root)
    _require(root is not None, "worker_store_conflict")
    _check_input(registry, _context(registry.store, invocation), arguments, control["input"],
        control["input_admission"], control["input_decision_admission"], invocation["decision_index"], store_root=root)
    references.append(control["manifest_ref"])
    _require(capture["artifact_ref"] == control["manifest_ref"]
        and capture.get("parent_source_refs") == list(dict.fromkeys(parents))
        and capture.get("auxiliary_artifact_refs") == [ref for ref in dict.fromkeys(references)
            if ref not in input_artifact_refs and ref != capture["artifact_ref"]], "capture_source_conflict")
    return dict(control=control, body=body, store_root=root, request=_capture_request(registry, control, body, store_root=root))


def _capture_native(registry, invocation, arguments, intent, stages, directory):
    excluded = [intent["input"]["file"]["artifact_ref"]]
    body = dict(version=CAPTURE_VERSION, invocation=invocation, stages=stages, input_artifact_refs=excluded)
    manifest_ref = registry.store.artifact(canonical(body), "application/json")
    control = dict(version=CAPTURE_CONTROL_VERSION, invocation=invocation, arguments=arguments,
        selected_resource=intent["selected_resource"], policy=intent["policy"], input=intent["input"],
        input_admission=intent["input_admission"], input_decision_admission=intent["input_decision_admission"],
        input_artifact_refs=excluded, manifest_ref=manifest_ref)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    references, parents = [], []
    for stage in stages:
        for row in stage["outputs"]:
            if row["file"] is not None:
                references.extend((row["file"]["artifact_ref"], stage["worker_control_ref"]))
                parents.append(row["source"]["source_ref"])
        references.extend(row["file"]["artifact_ref"] for row in stage["logs"] if row["file"] is not None)
    stamp = directory / "publication-time.json"
    if not stamp.exists():
        _immutable(stamp, dict(retrieved_at=datetime.now(timezone.utc).isoformat()))
    source = registry._put("source", dict(provider=TOOL,
        accession=identity("operation", dict(key=invocation["operation_key"], name=TOOL, arguments=arguments)), uri=None,
        artifact_ref=manifest_ref, text_ref=None, request_ref=control_ref, version=CAPTURE_VERSION,
        retrieved_at=decode_json(stamp.read_bytes())["retrieved_at"], parent_source_refs=list(dict.fromkeys(parents)),
        auxiliary_artifact_refs=[ref for ref in dict.fromkeys(references) if ref not in excluded and ref != manifest_ref]), origin="tool")
    checked = _capture_control(registry, source, invocation=invocation, arguments=arguments, input_artifact_refs=excluded)
    return source, checked["request"], excluded


def _outcome(arguments, operation_key, public, *, redisplay=False):
    context = public["context"]
    partial = (bool(context["issues"]) or context["iqtree_execution"]["state"] != "completed"
        or context["support_trace"]["state"] != "resolved"
        or any(row["capture"]["state"] != "complete" or row["parser_status"] != "ok" for row in context["outputs"]))
    return dict(status="partial" if partial else "completed", operation_ref=identity("operation", dict(
        key=operation_key, name=TOOL, arguments=arguments)), record_refs=[public["source_ref"]],
        changed_record_refs=[] if redisplay else [public["source_ref"]], result=public,
        feedback=dict(category="representation", code="protein_phylogeny_selected_result_partial", source_ref=public["source_ref"]) if partial else None)


def _failure(registry, arguments, operation_key, error):
    message = str(error)
    code = message if re.fullmatch(r"[a-z][a-z0-9_]*", message) else "protein_phylogeny_execution_failed"
    diagnostic = registry.store.artifact(canonical(dict(version="protein_phylogeny_diagnostic_v1",
        exception_type=type(error).__module__ + "." + type(error).__name__, exception_message=message)), "application/json")
    return dict(status="failed" if isinstance(error, _KnownFailure) else "unavailable" if isinstance(error, OSError)
        or code.endswith("_unavailable") else "invalid" if isinstance(error, (ValueError, TypeError, KeyError)) else "failed",
        operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[], changed_record_refs=[], result=None, feedback=dict(category="execution", code=code, diagnostic_ref=diagnostic))


async def execute_protein_phylogeny_tool(registry, arguments, *, scope, operation_key, authority):
    from .molecular_measurement_tools import _recorded_molecular_action_details
    from .protein_phylogeny_publication import (_read_protein_phylogeny_publication, _project_publication,
        _publish, _saved_request, read_protein_phylogeny_action_result)
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry and owner.run_id == context.run_id,
        "execution_owner_conflict")
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / "cache" / "molecular-measurements" / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed", "partial"):
                _require(_same(read_protein_phylogeny_action_result(registry, context, arguments,
                    operation_key, reader=reader), outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("failed", "invalid", "unavailable")
                    and outcome.get("result") is None and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        intent_path = directory / "protein-phylogeny-intent.json"
        result_intent_path = directory / "calculation/protein-phylogeny-result-intent.json"
        attempt_possible = intent_path.exists() or result_intent_path.exists()
        try:
            arguments = contracts.validate_phylogeny_arguments(arguments)
            configured = registry._protein_phylogeny_configuration
            configuration = None if configured is None else validate_protein_phylogeny_configuration(configured)
            if arguments["mode"] == "run_native":
                if intent_path.exists():
                    intent = decode_json(intent_path.read_bytes())
                    _closed(intent, "version invocation arguments selected_resource policy input input_admission input_decision_admission")
                    _require(intent["version"] == "ordinary_protein_phylogeny_intent_v1"
                        and _same(intent["invocation"], invocation) and _same(intent["arguments"], arguments), "original_intent_conflict")
                    _check_input(registry, context, arguments, intent["input"], intent["input_admission"],
                        intent["input_decision_admission"], invocation["decision_index"])
                else:
                    _require(configuration is not None and len(configuration["resources"]) == 1, "native_resource_required")
                    selected = configuration["resources"][0]
                    _run_selection(registry, owner, selected, configuration["policy"])
                    descriptor, admission, decision = _fresh_input(registry, context, reader, arguments, invocation["decision_index"])
                    _require(arguments["input_mode"] != "selected_MUSCLE_alignment" or descriptor["file"]["format"] == "fasta",
                        "raw_fasta_input_required")
                    intent = dict(version="ordinary_protein_phylogeny_intent_v1", invocation=invocation, arguments=arguments,
                        selected_resource=selected, policy=configuration["policy"], input=descriptor,
                        input_admission=admission, input_decision_admission=decision)
                    _immutable(intent_path, intent)
                environment = _environment(intent["selected_resource"]["environment"])
                stages, aligned = [], intent["input"]
                names = _STAGES if arguments["input_mode"] == "selected_MUSCLE_alignment" else ("iqtree",)
                for label in names:
                    native_directory = _directory(directory / label)
                    native_directory.mkdir(exist_ok=True)
                    request = _native_request(label, aligned, environment)
                    operation = "protein_conservation_native" if label == "alignment" else iqtree.OPERATION
                    _worker_dispatch(registry, owner, request, native_directory, operation, intent["policy"], intent["selected_resource"])
                    attempt_possible = True
                    work = await registry._sequence_worker_async(operation, dict(request=request),
                        directory=native_directory, owned_directory=native_directory)
                    authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                    _check_input(registry, context, arguments, intent["input"], intent["input_admission"],
                        intent["input_decision_admission"], invocation["decision_index"])
                    manifest, worker = _worker_record(registry, work, request, native_directory, operation,
                        invocation, label, allow_failure=True)
                    with registry.store.transaction():
                        stage = _capture_stage(registry, invocation, arguments, label, request, manifest, worker, native_directory)
                    stages.append(stage)
                    if label == "alignment":
                        aligned = _captured_source(registry, stage, "alignment")
                        checked = _manifest(label, manifest, request)
                        if aligned is None or checked is None or checked["returncode"] != 0 or checked["issues"]:
                            break
                with registry.store.transaction():
                    capture, request, excluded = _capture_native(registry, invocation, arguments, intent, stages, directory)
                prepared = dict(capture_source=capture, sheet_file=None, documents_file=None,
                    input_artifact_refs=excluded, source_admission=None, source_decision_admission=None, original_source=None,
                    policy=intent["policy"], selected_resource=intent["selected_resource"])
            else:
                _require(configuration is not None and configuration["saved_modes"], "saved_modes_not_configured")
                with registry.store.read_snapshot():
                    publication = _read_protein_phylogeny_publication(registry, context, reader, arguments["result_ref"],
                        before_decision_index=invocation["decision_index"])
                if arguments["mode"] == "read_stored" or _same(arguments["pair_requests"], publication["public"]["pair_requests"]):
                    with registry.store.transaction():
                        public = _project_publication(registry, publication, arguments["selection"])
                        outcome = _outcome(arguments, operation_key, public, redisplay=True)
                        registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                    return outcome
                with registry.store.read_snapshot():
                    publication = _read_protein_phylogeny_publication(registry, context, reader, arguments["result_ref"],
                        require_documents=True, before_decision_index=invocation["decision_index"])
                previous = publication["control"]
                prepared = dict(capture_source=registry.store.get(previous["capture_source"]["source_ref"]),
                    sheet_file=previous["sheet_file"], documents_file=previous["documents_file"],
                    input_artifact_refs=previous["input_artifact_refs"], source_admission=publication["received_input"],
                    source_decision_admission=publication["source_decision_admission"],
                    original_source=dict(source_ref=publication["source"]["id"], record_sha256=digest(publication["source"])),
                    policy=configuration["policy"], selected_resource=None)
                saved_version = (decode_json(result_intent_path.read_bytes())["request"]["version"]
                    if result_intent_path.exists() else result_worker.SAVED_REPORT_REQUEST_VERSION)
                request = _saved_request(registry, arguments, previous, store_root=registry.store.path,
                    version=saved_version)
            calculation = _directory(directory / "calculation")
            calculation.mkdir(exist_ok=True)
            if result_intent_path.exists():
                retained = decode_json(result_intent_path.read_bytes())
                _closed(retained, "invocation arguments request source_admission source_decision_admission policy selected_resource")
                _require(_same(retained["invocation"], invocation) and _same(retained["arguments"], arguments)
                    and _same(retained["request"], request) and _same(retained["source_admission"], prepared["source_admission"])
                    and _same(retained["source_decision_admission"], prepared["source_decision_admission"]), "original_result_intent_conflict")
                if arguments["mode"] == "run_native":
                    _require(_same(retained["policy"], intent["policy"])
                        and _same(retained["selected_resource"], intent["selected_resource"]), "action_policy_conflict")
                else:
                    _require(retained["selected_resource"] is None, "action_policy_conflict")
                prepared["policy"], prepared["selected_resource"] = retained["policy"], retained["selected_resource"]
            else:
                _immutable(result_intent_path, dict(invocation=invocation, arguments=arguments, request=request,
                    source_admission=prepared["source_admission"], source_decision_admission=prepared["source_decision_admission"],
                    policy=prepared["policy"], selected_resource=prepared["selected_resource"]))
            _worker_dispatch(registry, owner, request, calculation, result_worker.OPERATION, prepared["policy"], prepared["selected_resource"])
            attempt_possible = True
            work = await registry._sequence_worker_async(result_worker.OPERATION, dict(request=request),
                directory=calculation, owned_directory=calculation)
            authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
            if arguments["mode"] == "run_native":
                _check_input(registry, context, arguments, intent["input"], intent["input_admission"],
                    intent["input_decision_admission"], invocation["decision_index"])
            else:
                _require(_same(_admit(registry.store, reader, context, arguments["result_ref"], "source", invocation["decision_index"]),
                    prepared["source_admission"]) and _same(_source_admission(registry, context, arguments["result_ref"],
                        invocation["decision_index"]), prepared["source_decision_admission"]), "source_admission_conflict")
            result, worker = _worker_record(registry, work, request, calculation, result_worker.OPERATION, invocation, "calculation")
            with registry.store.transaction():
                public = _publish(registry, arguments, invocation, prepared, result, worker, calculation)
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if attempt_possible and not isinstance(error, _KnownFailure):
                raise MolecularOperationUnpublished("protein_phylogeny_original_action_unpublished") from error
            with registry.store.transaction():
                outcome = _failure(registry, arguments, operation_key, error)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


def read_retained_protein_phylogeny_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    from .protein_phylogeny_publication import read_retained_protein_phylogeny_publication as read
    return read(registry, context, reader, source_ref, recovery_operation_key=recovery_operation_key)


def read_protein_phylogeny_action_result(registry, context, arguments, operation_key, *, reader):
    from .protein_phylogeny_publication import read_protein_phylogeny_action_result as read
    return read(registry, context, arguments, operation_key, reader=reader)
