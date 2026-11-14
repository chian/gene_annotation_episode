"""Ordinary, explicitly selected molecular measurements in the current episode.

The host authenticates the selected action and received Files. The Store-free
worker owns numerical production; saved reads select its retained cells. This
module creates no episode, model decision, biological annotation or retry.
"""
from copy import deepcopy
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from .domain import REF, canonical, obj
from gene_annotation_episode.domain import ContractError
from .itc_binding_contracts import (
    FIT_SELECTION_VERSION, PARAMETERS, REASONS, SELECTION_VERSION, SHEET_VERSION, copy_json, number,
    validate_itc_binding_components_shape, validate_itc_binding_fit_selection,
    validate_itc_binding_selection, validate_itc_binding_sheet, validate_itc_binding_supplied,
)


from .itc_binding_tool_values import (itc_tool_contract, _ids, prepare_itc_tool_request, run_itc_tool_request, _worker_request, _validate_result, _cell, project_itc_tool_result, itc_parameter_fact_sources, validate_itc_parameter_return, project_itc_parameter_return)

ITC_TOOL = "analyze_itc_binding_thermodynamics"
REQUEST_VERSION = "ordinary_itc_request_v1"
RESULT_VERSION = "ordinary_itc_result_v1"
ROW_FIELDS = ("injection_volume", "syringe_ligand_concentration", "retained_cell_fraction",
    "macromolecule_concentration", "ligand_concentration", "bound_complex_concentration",
    "predicted_heat", "corrected_heat", "residual")
UNIT_CODES = {"L": "litre", "mol/L": "mol_per_litre", "J": "joule", "K": "kelvin",
    "fraction": "fraction", "J/mol": "joule_per_mole", "J^2": "joule_squared",
    "dimensionless": "dimensionless", "sites_per_macromolecule": "sites_per_macromolecule"}


class MolecularOperationUnpublished(RuntimeError):
    """Keep an unfinished runtime action attached to its original owned attempt."""


def itc_reference_access(store, context, reference, namespace):
    """Keep the ITC-only verdict through the common finite publication owner."""
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.molecular_reference_privacy import molecular_reference_restriction
    return molecular_reference_restriction(store, context, reference, namespace,
        providers=(ITC_TOOL,))


def _molecular_implementation_files(operation):
    modules = {
        "itc_binding": ("itc_binding_tool_values.py", "itc_binding_contracts.py", "itc_binding_measurements.py", "itc_binding_fit.py", "bivariate_covariance.py"),
        "protease_kinetics_native": ("molecular_sequence_native.py", "protease_kinetics_measurements.py", "bivariate_covariance.py"),
        "protease_kinetics_saved": ("molecular_sequence_native.py", "protease_kinetics_measurements.py", "bivariate_covariance.py"),
    }
    if operation not in modules:
        raise ContractError("molecular_tool_operation_unknown")
    files = ([] if operation in {"protease_kinetics_native", "protease_kinetics_saved"} else [Path(__file__)]) + [Path(__file__).with_name(
        _molecular_worker_module(operation).rsplit(".", 1)[-1] + ".py"),
        *(Path(__file__).with_name(name) for name in modules[operation])]
    return list(dict.fromkeys(files))

def _molecular_worker_module(operation):
    return "gene_annotation_episode.episodic_workflow.root.a105." + {
        "itc_binding": "itc_binding_worker", "protease_kinetics_native": "molecular_sequence_driver",
        "protease_kinetics_saved": "molecular_sequence_driver"}[operation]

def run_owned_molecular_worker(operation, arguments, *, directory, owned_directory, policy, cancel_event):
    """Resume one authenticated native handle; retain its immutable controls.

    Unlike the transient sequence-worker default, these files are the recovery
    operands of this ordinary selected action. No release or replacement unit
    occurs when dispatch/completion is uncertain.
    """
    from ._local_job_worker import atomic_json
    from .native_lifecycle import NativeJobHandle, prepare_job, resume_start, wait_job, status, collect
    from gene_annotation_episode.acquisition import AcquisitionError
    from .local_jobs import LocalJobPolicy
    directory, owned = Path(directory).resolve(strict=True), Path(owned_directory).resolve(strict=True)
    if operation not in {"itc_binding", "protease_kinetics_native", "protease_kinetics_saved"} or directory != owned:
        raise ContractError("molecular_tool_owned_directory_conflict")
    request, output = owned / "worker-request.json", owned / "worker-result.json"
    handle_path, stdout, stderr = owned / "native-handle.json", owned / "stdout", owned / "stderr"
    payload = dict(operation=operation, arguments=arguments)
    protease = operation in {"protease_kinetics_native", "protease_kinetics_saved"}
    worker_body, request_raw = payload, None
    if protease:
        from . import molecular_sequence_driver as driver
        from . import molecular_sequence_native as native_source
        if type(arguments) is not dict or set(arguments) != {"request"}:
            raise ContractError("protease_kinetics_worker_request_conflict")
        worker_body = json.loads(canonical(arguments["request"]))
        if (driver._request(worker_body) != "analyze_protease_kinetics"
                or worker_body["version"] != driver.REQUEST_VERSION_V2
                or worker_body["mode"] != ("native" if operation == "protease_kinetics_native" else "saved_sheet")):
            raise ContractError("protease_kinetics_worker_request_conflict")
        request_raw = json.dumps(worker_body, allow_nan=False).encode("utf-8")
        output = owned / "driver-output" / "declaration.json"
        if operation == "protease_kinetics_native":
            selected_native = worker_body["selection"]
            from .protease_kinetics_measurements import _native_request
            _native_request(selected_native)
            native_source._deployment(selected_native["deployment"], version=native_source.DEPLOYMENT_VERSION_V3,
                source_sha256=native_source.BIOCHEMISTRY_SOURCE_SHA256)
            if Path(selected_native["output_workspace"]) != output.parent:
                raise ContractError("protease_kinetics_worker_output_conflict")

    def command(python):
        if not protease:
            return [python, "-m", _molecular_worker_module(operation), str(request), str(output)]
        return [python, "-B", "-m", _molecular_worker_module(operation),
            "--request-file", str(request), "--request-sha256", hashlib.sha256(request_raw).hexdigest(),
            "--request-size-bytes", str(len(request_raw)), "--output-directory", str(output.parent)]

    def native_environment():
        deployment = worker_body["selection"]["deployment"]
        return {"PYTHONHOME": deployment["runtime"]["home"],
            "PYTHONPATH": os.pathsep.join(deployment["import_roots"]), "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "TMPDIR": str(owned / "temporary"),
            "TMP": str(owned / "temporary"), "TEMP": str(owned / "temporary"),
            **worker_body["selection"]["environment"]}

    selection_path = owned / "execution-selection.json"
    if selection_path.exists():
        selected = json.loads(selection_path.read_bytes())
        fields = {"version", "command", "cwd", "environment", "policy", "request", "python", "implementation_files"}
        if (type(selected) is not dict or set(selected) != fields
                or selected["version"] != "ordinary_molecular_execution_v1"
                or canonical(selected["request"]) != canonical(payload)
                or selected["cwd"] != str(owned) or type(selected["environment"]) is not dict
                or any(type(k) is not str or type(v) is not str for k, v in selected["environment"].items())
                or selected["command"] != command(selected["python"]["path"])):
            raise ContractError("molecular_tool_execution_selection_conflict")
        if operation == "protease_kinetics_native":
            deployment = worker_body["selection"]["deployment"]
            if (selected["python"] != {key: deployment["runtime"]["executable"][key] for key in ("path", "sha256")}
                    or canonical(selected["environment"]) != canonical(native_environment())):
                raise ContractError("protease_kinetics_original_runtime_conflict")
        # The reservation's original resource/argv/environment remain selected.
        # A different parent environment cannot reprice already launched work.
        selected_policy = LocalJobPolicy(**selected["policy"])
    else:
        if handle_path.exists() or request.exists() or output.exists():
            raise ContractError("molecular_tool_original_selection_missing")
        environment = dict(os.environ)
        if protease:
            temporary, cache = owned / "temporary", owned / "cache"
            temporary.mkdir(exist_ok=True)
            cache.mkdir(exist_ok=True)
            environment.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary),
                XDG_CACHE_HOME=str(cache), PYTHONDONTWRITEBYTECODE="1")
        package_root = str(Path(__file__).resolve().parents[4])
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        implementation_files = _molecular_implementation_files(operation)
        python = dict(path=sys.executable, sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest())
        if operation == "protease_kinetics_native":
            deployment = worker_body["selection"]["deployment"]
            index, _ = native_source._manifest(deployment)
            # Bind the explicitly selected deployment; no host package discovery
            # or identity substitution supplies its interpreter/source closure.
            python = {key: deployment["runtime"]["executable"][key] for key in ("path", "sha256")}
            expected = {str(Path(root) / "gene_annotation_episode" / "episodic_workflow" / "root" / "a105" / path.name): path
                for root in deployment["import_roots"] for path in implementation_files}
            for path in implementation_files:
                matches = [pin for name, pin in index.items() if name in expected
                    and expected[name] == path and pin["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()]
                if len(matches) != 1:
                    raise ContractError("protease_kinetics_selected_driver_closure_conflict")
            implementation_files = None
            environment = native_environment()
        selected = dict(version="ordinary_molecular_execution_v1",
            command=command(python["path"]),
            cwd=str(owned), environment=environment, policy=policy.to_dict(), request=payload,
            python=python,
            implementation_files=[dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in implementation_files] if implementation_files is not None else
                [*index.values(), deployment["software_files_file"]])
        selected_policy = policy
        atomic_json(selection_path, selected)

    def verify_unstarted_software():
        if operation == "protease_kinetics_native":
            deployment = worker_body["selection"]["deployment"]
            original_index, _ = native_source._manifest(deployment)
            if canonical(selected["implementation_files"]) != canonical(
                    [*original_index.values(), deployment["software_files_file"]]):
                raise ContractError("protease_kinetics_original_manifest_conflict")
        for file in [selected["python"], *selected["implementation_files"]]:
            try:
                matches = hashlib.sha256(Path(file["path"]).read_bytes()).hexdigest() == file["sha256"]
            except OSError:
                matches = False
            if not matches:
                raise ContractError("molecular_tool_original_software_changed_before_dispatch")

    try:
        if request.exists():
            if (canonical(json.loads(request.read_bytes())) != canonical(worker_body)
                    or protease and request.read_bytes() != request_raw):
                raise ContractError("molecular_tool_worker_request_conflict")
        else:
            if handle_path.exists():
                raise ContractError("molecular_tool_worker_request_missing")
            atomic_json(request, worker_body)
        if handle_path.exists():
            handle = NativeJobHandle(handle_path)
            body = handle.read()
            native_request_path = Path(body["paths"]["request"])
            native_request = json.loads(native_request_path.read_bytes())
            if (body["command"] != selected["command"] or body["cwd"] != str(owned)
                    or body["stdout"] != str(stdout) or body["stderr"] != str(stderr)
                    or canonical(body["metadata"]["policy"]) != canonical(selected_policy.to_dict())
                    or any(not Path(path).resolve().is_relative_to(owned) for path in body["paths"].values())
                    or hashlib.sha256(native_request_path.read_bytes()).hexdigest() != body["request_sha256"]
                    or canonical(native_request) != canonical(dict(command=selected["command"], cwd=str(owned),
                        file_bytes=selected_policy.scratch_bytes, ready_path=body["paths"]["ready"],
                        release_path=body["paths"]["release"], result_path=body["paths"]["result"],
                        stdin_path=None, env=selected["environment"]))):
                raise ContractError("molecular_tool_native_handle_conflict")
        else:
            if output.exists():
                raise ContractError("molecular_tool_native_handle_missing")
            verify_unstarted_software()
            handle = prepare_job(selected["command"], cwd=owned, policy=selected_policy, handle_path=handle_path,
                stdout_path=stdout, stderr_path=stderr, env=selected["environment"])
        view = status(handle)
        if view["terminal"] and view["quiescent"]:
            job = collect(handle)
        else:
            preserve_observer = protease
            if preserve_observer and (
                    cancel_event is not None and cancel_event.is_set()
                    or view["state"] == "execution_unknown"):
                prefix = "protease_kinetics_"
                raise MolecularOperationUnpublished(prefix + "worker_attempt_unconfirmed")
            # A prepared or unreleased handshake can still launch the original
            # command. Its original files must remain available before release.
            if not Path(handle.read()["paths"]["release"]).exists():
                verify_unstarted_software()
            resume_start(handle, cancel_event=cancel_event)
            if preserve_observer:
                # Stopping this observer must leave the independent original
                # unit available to the same action's recovery. wait_job's
                # cancellation policy remains unchanged for all old families.
                import time
                while True:
                    view = status(handle)
                    if view["terminal"] and view["quiescent"]:
                        job = collect(handle)
                        break
                    if ((cancel_event is not None and cancel_event.is_set())
                            or view["state"] == "execution_unknown"):
                        prefix = "protease_kinetics_"
                        raise MolecularOperationUnpublished(prefix + "worker_attempt_unconfirmed")
                    if cancel_event is None:
                        time.sleep(.05)
                    else:
                        cancel_event.wait(.05)
            else:
                job = wait_job(handle, cancel_event=cancel_event)
        if job.returncode != 0 or not output.is_file():
            raise AcquisitionError("local_job_execution_failed" if job.returncode else "local_job_output_missing",
                phase="local_execution", operational={**job.metadata, "worker_operation": operation})
        return output, job.metadata
    except AcquisitionError as error:
        if handle_path.exists():
            view = status(handle)
            if view["terminal"] and view["quiescent"]:
                failure = dict(code=error.code, phase=error.phase,
                    operational=deepcopy(error.operational), diagnostic=dict(
                        selection=selected, handle=handle.read(), observation=view))
                return output, {**view["metadata"], "molecular_failure": failure}
            # Only unconfirmed execution remains pending on its original unit.
            raise MolecularOperationUnpublished("molecular_tool_original_attempt_unconfirmed") from error
        raise




def authenticate_itc_invocation(registry, name, arguments, scope, operation_key):
    """A host context is necessary but its actual saved action is authoritative."""
    invocation = registry._current_invocation.get()
    if invocation is None:
        raise ContractError("molecular_tool_current_invocation_required")
    context, reader, selected_name, selected_arguments, selected_key = invocation
    from .communication import plain
    from .episode_return_records import EpisodeReturnRecords
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="molecular_tool_")
    records.authenticate(context)
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if isinstance(operation_key, str) and operation_key.startswith(prefix) else ""
    if (not suffix.isdecimal() or str(int(suffix)) != suffix or selected_name != name
            or canonical(selected_arguments) != canonical(arguments) or selected_key != operation_key
            or canonical(plain(context.scope)) != canonical(scope) or not callable(reader)):
        raise ContractError("molecular_tool_selected_action_conflict")
    row = registry.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
    if row is None or canonical(json.loads(row["action"])) != canonical(
            dict(kind="tool", tool=name, arguments=arguments)):
        raise ContractError("molecular_tool_selected_action_conflict")
    return context, reader


authenticate_molecular_invocation = authenticate_itc_invocation


def _received(reader, context, reference, namespace):
    value = reader(context, reference, namespace, tag_key="version")
    if value["failure"] is not None:
        raise ContractError("molecular_tool_" + value["failure"]["code"])
    return value["input"]












def _publication_profile(tool_name):
    if tool_name == ITC_TOOL:
        return RESULT_VERSION, "ordinary_itc_publication_v1", ("fit", "calculate_saved"), "ordinary_itc_"
    if tool_name == "analyze_protease_kinetics":
        return ("ordinary_protease_kinetics_result_v1", "ordinary_protease_kinetics_publication_v1",
            ("run_native", "calculate_saved"), "protease_kinetics_")
    raise ContractError("molecular_publication_unknown_producer")

def _recorded_molecular_action_details(registry, context, arguments, operation_key, tool_name, *,
        recovery_context=None, recovery_operation_key=None, selected_only=False):
    """Authenticate one editing action independently of its Source producer."""
    from .communication import plain
    from .domain import identity
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    from .episode_return_records import EpisodeReturnRecords
    from .waiting import validate_pending
    prefix = "protease_kinetics_"
    if tool_name != "analyze_protease_kinetics" or not isinstance(context, BindingContext):
        raise ContractError(prefix + "action_conflict")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix=prefix)
    records.authenticate(context)
    start = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(start):] if type(operation_key) is str and operation_key.startswith(start) else ""
    if not suffix.isdecimal() or str(int(suffix)) != suffix:
        raise ContractError(prefix + "action_conflict")
    if type(selected_only) is not bool or selected_only:
        raise ContractError(prefix + "action_conflict")
    row = registry.store.db.execute("""SELECT operation.*, action.action AS selected_action,
        action.result AS runtime_outcome FROM tool_operations operation JOIN runtime_actions action
          ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index
        WHERE operation.operation_key=? AND action.run_id=? AND action.episode_id=? AND action.decision_index=?""",
        (operation_key, context.run_id, context.episode_id, int(suffix))).fetchone()
    expected = identity("operation", dict(key=operation_key, name=tool_name, arguments=arguments))
    if (row is None or row["id"] != expected or row["name"] != tool_name
            or row["arguments"] != canonical(arguments) or row["scope"] != canonical(plain(context.scope))
            or canonical(json.loads(row["selected_action"])) != canonical(dict(kind="tool", tool=tool_name, arguments=arguments))):
        raise ContractError(prefix + "action_conflict")
    outcome = json.loads(row["result"])
    runtime = None if row["runtime_outcome"] is None else json.loads(row["runtime_outcome"])
    if type(outcome) is not dict or outcome.get("operation_ref") != expected:
        raise ContractError(prefix + "action_conflict")
    pending = runtime is None
    if pending:
        if (not isinstance(recovery_context, BindingContext) or recovery_operation_key != operation_key
                or recovery_context.run_id != context.run_id or recovery_context.episode_id != context.episode_id
                or not records._equal(recovery_context.request, context.request)):
            raise ContractError(prefix + "action_conflict")
        actual, _ = authenticate_molecular_invocation(registry, tool_name, arguments, plain(context.scope), operation_key)
        if actual is not recovery_context:
            raise ContractError(prefix + "action_conflict")
    else:
        if type(runtime) is not dict:
            raise ContractError(prefix + "action_conflict")
        if "pending_work_after_action" in runtime:
            validate_pending(runtime["pending_work_after_action"])
        if canonical({key: value for key, value in runtime.items() if key != "pending_work_after_action"}) != row["result"]:
            raise ContractError(prefix + "action_conflict")
    if tool_name == "analyze_protease_kinetics":
        from .execution_contracts import digest as execution_digest
        request_sha256 = execution_digest(plain(context.request))
    else:
        request_sha256 = hashlib.sha256(canonical(plain(context.request)).encode()).hexdigest()
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=request_sha256,
        scope=plain(context.scope))
    return dict(arguments=json.loads(row["arguments"]), invocation=invocation, outcome=outcome,
        operation_ref=expected, runtime_outcome=runtime, pending_recovery=pending)

def _recorded_molecular_producer_details(registry, source_ref, tool_name, *,
        recovery_context=None, recovery_operation_key=None):
    """Join original producer metadata, with one exact editing-action recovery.

    The old profiles retain their committed-only checks. A NULL runtime outcome
    is usable only for the new editing producer's actual current invocation;
    neither a Source handle nor a supplied recovery key establishes authority.
    """
    from .communication import plain
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    from .episode_return_records import EpisodeReturnRecords
    _, _, modes, prefix = _publication_profile(tool_name)
    editing = tool_name == "analyze_protease_kinetics"
    if ((recovery_context is None) != (recovery_operation_key is None)
            or recovery_context is not None and (not editing or not isinstance(recovery_context, BindingContext))):
        raise ContractError(prefix + "publication_conflict")
    candidates = []
    rows = registry.store.db.execute("""SELECT operation.*,
        action.run_id AS producer_run_id, action.episode_id AS producer_episode_id,
        action.decision_index AS producer_decision_index, action.action AS selected_action,
        action.result AS recorded_outcome
        FROM tool_operations operation JOIN runtime_actions action
          ON (json_extract(action.result,'$.operation_ref')=operation.id
            OR (? AND action.result IS NULL AND operation.operation_key=?
              AND operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index))
        WHERE operation.name=? AND json_extract(operation.result,'$.status') IN ('completed','partial')
          AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') published
                     WHERE published.value=?)""",
        (editing and recovery_context is not None, recovery_operation_key, tool_name, source_ref))
    for row in rows:
        arguments = json.loads(row["arguments"])
        if type(arguments) is dict and arguments.get("mode") in modes:
            if tool_name == "analyze_protease_kinetics" and source_ref not in json.loads(row["result"]).get("changed_record_refs", []):
                continue  # An unchanged saved window reads its original Source.
            candidates.append((row, arguments))
    if len(candidates) != 1:
        raise ContractError(prefix + "publication_conflict")
    row, arguments = candidates[0]
    records = EpisodeReturnRecords(registry.store, row["producer_run_id"], failure_prefix=prefix)
    producer = records.context(row["producer_episode_id"])
    records.authenticate(producer)
    operation_key = f'{producer.run_id}:{producer.episode_id}:{row["producer_decision_index"]}'
    if editing:
        context = recovery_context if row["recorded_outcome"] is None else producer
        if context is None or not records._equal(context.request, producer.request) or context.path != producer.path:
            raise ContractError(prefix + "publication_conflict")
        details = _recorded_molecular_action_details(registry, context, arguments, operation_key, tool_name,
            recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
        outcome = details["outcome"]
        if (source_ref not in outcome.get("record_refs", []) or type(outcome.get("result")) is not dict
                or outcome["result"].get("source_ref") != source_ref):
            raise ContractError(prefix + "publication_conflict")
        return details
    runtime_outcome = None if row["recorded_outcome"] is None else json.loads(row["recorded_outcome"])
    outcome = json.loads(row["result"])
    if (row["operation_key"] != operation_key
            or row["scope"] != canonical(plain(producer.scope))
            or canonical(json.loads(row["selected_action"])) != canonical(
                dict(kind="tool", tool=tool_name, arguments=arguments))
            or source_ref not in outcome.get("record_refs", [])):
        raise ContractError(prefix + "publication_conflict")
    if (runtime_outcome is None or source_ref not in runtime_outcome.get("record_refs", [])
            or canonical({k: v for k, v in runtime_outcome.items() if k != "pending_work_after_action"}) != row["result"]):
        raise ContractError(prefix + "publication_conflict")
    invocation = dict(run_id=producer.run_id, episode_id=producer.episode_id,
        operation_key=operation_key, decision_index=row["producer_decision_index"],
        request_sha256=hashlib.sha256(canonical(plain(producer.request)).encode()).hexdigest(),
        scope=plain(producer.scope))
    return dict(arguments=arguments, invocation=invocation, outcome=outcome,
        operation_ref=row["id"], runtime_outcome=runtime_outcome, pending_recovery=False)

def _recorded_molecular_producer(registry, source_ref, tool_name):
    """Preserve the committed producer reader's original two-value return."""
    details = _recorded_molecular_producer_details(registry, source_ref, tool_name)
    return details["arguments"], details["invocation"]


def read_retained_molecular_publication(registry, context, reader, source_ref, *, tool_name):
    """Read an admitted producer's saved values without delivering its Files.

    ITC preserves its existing dual Source/File admission. Source-only producers
    authenticate metadata and the original selected action before any private
    native, control or grading bytes are opened. The shared association checks
    do not calculate measurements, grant receipts or invoke native software.
    """
    with registry.store.read_snapshot():
        return _read_retained_molecular_publication(registry, context, reader, source_ref,
            tool_name=tool_name)


def _publication_bytes(store, reference):
    """Verify the original artifact ID, metadata and complete retained bytes."""
    from .native_file_capture import NativeFileCaptureError, _metadata
    metadata = _metadata(store, reference)
    # This is an authenticated producer's internal read. Model-facing material
    # access has separate File permissions; no such permission is conferred here.
    raw = store.get_artifact(reference)
    if len(raw) != metadata["size"] or hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise NativeFileCaptureError("retained_artifact_mismatch")
    return raw


def _read_retained_molecular_publication(registry, context, reader, source_ref, *, tool_name):
    if tool_name == "analyze_protease_kinetics":
        from .protease_kinetics_tools import _read_protease_kinetics_publication
        return _read_protease_kinetics_publication(registry, context, reader, source_ref)
    result_version, control_version, _, prefix = _publication_profile(tool_name)
    item = _received(reader, context, source_ref, "source")
    source = item["witness"]["record"]
    if (source.get("origin") != "tool" or source.get("provider") != tool_name
            or source.get("version") != result_version):
        raise ContractError(prefix + "producer_required")
    arguments, invocation = _recorded_molecular_producer(registry, source_ref, tool_name)
    value = _validate_result(item["content"]["value"])
    control = json.loads(_publication_bytes(registry.store, source["request_ref"]))
    if (type(control) is not dict or set(control) != {"version", "request", "native_artifact_ref",
            "execution_selection", "native_handle", "execution"}
            or control["version"] != control_version
            or control["native_artifact_ref"] != source["artifact_ref"]):
        raise ContractError(prefix + "publication_conflict")
    request = control["request"]
    expected = _worker_request(request)
    witness = request["received_input"]["witness"]
    if (canonical(expected) != canonical(value["request"])
            or canonical(request["arguments"]) != canonical(arguments)
            or canonical(request["invocation"]) != canonical(invocation)
            or "operand_refs" in source or source.get("parent_source_refs") != (
                [witness["reference"]] if witness["namespace"] == "source" else [])):
        raise ContractError(prefix + "publication_conflict")
    from .tool_grading_artifacts import MEDIA_TYPE, source_tool_grading_entries
    from .native_file_capture import _metadata
    for reference in source.get("auxiliary_artifact_refs", ()):
        if _metadata(registry.store, reference)["media_type"] == MEDIA_TYPE:
            _publication_bytes(registry.store, reference)
    entries = source_tool_grading_entries(registry.store, source_ref)
    if (len(entries) != 1 or canonical(entries[0]["grading"]) != canonical(
            dict(sheet=value["sheet"], scores=value["components"]))):
        raise ContractError(prefix + "publication_conflict")
    return dict(admission_kind="source_and_file",
        received_input=item, source=source, stored=value, control=control,
        grading_ref=entries[0]["artifact_ref"])



def read_retained_itc_result(registry, context, reader, source_ref):
    """Preserve the existing ITC reader's admitted input/result/grading triple."""
    result = read_retained_molecular_publication(registry, context, reader, source_ref, tool_name=ITC_TOOL)
    return result["received_input"], result["stored"], result["grading_ref"]






async def prepare_itc_work(registry, arguments, *, scope, operation_key, authority):
    from .communication import plain
    context, reader = authority
    if arguments["mode"] == "fit":
        item = _received(reader, context, arguments["input"]["reference"], arguments["input"]["namespace"])
        original = None
    else:
        item, original, grading = read_retained_itc_result(registry, context, reader, arguments["result_ref"])
        if arguments["mode"] == "read_stored":
            projection = project_itc_tool_result(original, selection=arguments,
                source_ref=arguments["result_ref"], artifact_ref=item["file"]["artifact_ref"], grading_ref=grading)
            return dict(stored=original, projection=projection, item=item, grading_ref=grading)
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id,
        operation_key=operation_key, decision_index=int(operation_key.rsplit(":", 1)[1]),
        request_sha256=hashlib.sha256(canonical(plain(context.request)).encode()).hexdigest(), scope=deepcopy(scope))
    request = prepare_itc_tool_request(arguments, received_input=item, invocation=invocation, original=original)
    directory = registry.store.path / "cache" / "molecular-measurements" / hashlib.sha256(operation_key.encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    from ._local_job_worker import atomic_json
    binding = directory / "host-binding.json"
    if binding.exists():
        if canonical(json.loads(binding.read_bytes())) != canonical(request):
            raise ContractError("ordinary_itc_original_binding_conflict")
    else:
        if (directory / "native-handle.json").exists():
            raise ContractError("ordinary_itc_original_binding_missing")
        atomic_json(binding, request)
    work = await registry._sequence_worker_async("itc_binding", dict(request=_worker_request(request)), directory=directory,
        owned_directory=directory)
    failure = work.metadata.get("molecular_failure")
    if failure is None:
        stored = _validate_result(json.loads(work.output_path.read_bytes()), _worker_request(request))
    else:
        try:
            stored = _validate_result(json.loads(work.output_path.read_bytes()), _worker_request(request))
        except (OSError, ValueError, TypeError, KeyError) as invalid:
            from gene_annotation_episode.acquisition import AcquisitionError
            from .materials import artifact_file
            diagnostics = deepcopy(failure["diagnostic"])
            diagnostics["native_output_validation"] = dict(exception_type=type(invalid).__name__, message=str(invalid))
            diagnostics["retained_artifacts"] = {name: artifact_file(registry.store, path, "application/octet-stream")
                for name, path in (("stdout", directory / "stdout"), ("stderr", directory / "stderr"),
                    ("worker_output", work.output_path)) if path.is_file()}
            original = failure["operational"] or {}
            raise AcquisitionError(failure["code"], phase=failure["phase"], diagnostic=diagnostics,
                operational={**{key: original[key] for key in ("resource", "limit", "evidence") if key in original},
                    "known_terminal": True, "native_returncode": work.metadata.get("native_returncode"),
                    "fit_call_state": "uncertain", "fit_call_count": None}) from invalid
    return dict(work=work, stored=stored, item=item, request=request, operational_failure=failure)


def partial_itc_publication(registry, prepared):
    """Expose only already-retained scientific outputs after a projection error."""
    from .tool_grading_artifacts import source_tool_grading_entries
    rows, references = [], []
    for reference in registry._written:
        source = registry.store.get(reference)
        if source.get("provider") != ITC_TOOL or source.get("version") != RESULT_VERSION:
            continue
        native = source["artifact_ref"]
        value = _validate_result(json.loads(registry.store.get_artifact(native)), _worker_request(prepared["request"]))
        entries = source_tool_grading_entries(registry.store, reference)
        if len(entries) != 1 or canonical(entries[0]["grading"]) != canonical(dict(sheet=value["sheet"], scores=value["components"])):
            raise ContractError("ordinary_itc_partial_publication_conflict")
        observation = value["sheet"]["fit_observation"]
        rows.append(dict(source_ref=reference, native_file=dict(artifact_ref=native, format="json"),
            grading_ref=entries[0]["artifact_ref"], fit_call_state=None if observation is None else observation["call_state"],
            fit_call_count=None if observation is None else observation["call_count"], fit_call_scope="retained_fit_observation"))
        references.extend((reference, native, entries[0]["artifact_ref"]))
    if not rows:
        raise ContractError("ordinary_itc_partial_scientific_source_missing")
    return dict(version="ordinary_itc_partial_values_v1", mode=prepared["request"]["arguments"]["mode"],
        projection_state="unavailable", retained_sources=rows), list(dict.fromkeys(references))


def retain_molecular_publication(registry, prepared, *, tool_name):
    """Retain an owned worker's validated output through one publication path."""
    if tool_name == "analyze_protease_kinetics":
        from .protease_kinetics_tools import _retain_protease_kinetics_publication
        return _retain_protease_kinetics_publication(registry, prepared)
    from .materials import artifact_file
    from .tool_grading_artifacts import retain_tool_grading
    result_version, control_version, _, prefix = _publication_profile(tool_name)
    work, stored, item = prepared["work"], prepared["stored"], prepared["item"]
    native = artifact_file(registry.store, work.output_path, "application/json")
    if canonical(json.loads(_publication_bytes(registry.store, native))) != canonical(stored):
        raise ContractError(prefix + "native_capture_conflict")
    grading = retain_tool_grading(registry.store, provider=tool_name, native_artifact_ref=native,
        grading=dict(sheet=stored["sheet"], scores=stored["components"]))
    controls = registry.store.artifact(canonical(dict(version=control_version,
        request=prepared["request"], native_artifact_ref=native,
        execution_selection=json.loads((work.output_path.parent / "execution-selection.json").read_bytes()),
        native_handle=json.loads((work.output_path.parent / "native-handle.json").read_bytes()),
        execution=work.metadata)), "application/json")
    source = registry._put("source", dict(provider=tool_name, accession=None, uri=None,
        artifact_ref=native, text_ref=None, request_ref=controls, version=result_version,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[item["witness"]["reference"]] if item["witness"]["namespace"] == "source" else [],
        auxiliary_artifact_refs=[grading]), origin="tool")
    return dict(source=source, native_artifact_ref=native, grading_ref=grading)


def publish_itc_work(registry, arguments, prepared):
    if arguments["mode"] == "read_stored":
        projection = prepared["projection"]
        return projection, [projection["source_ref"], projection["native_file"]["artifact_ref"], projection["grading_ref"]]
    publication = retain_molecular_publication(registry, prepared, tool_name=ITC_TOOL)
    projection = project_itc_tool_result(prepared["stored"], selection=arguments,
        source_ref=publication["source"]["id"], artifact_ref=publication["native_artifact_ref"],
        grading_ref=publication["grading_ref"])
    return projection, [publication["source"]["id"], publication["native_artifact_ref"], publication["grading_ref"]]


ITC_PARAMETER_SOURCE = "itc_binding_parameters"
_FIT_QUALIFICATIONS = ("underdetermined_selected_population", "nonpositive_residual_degrees_of_freedom",
    "later_unavailable_history_not_in_objective", "fit_does_not_establish_identifiability",
    "in_process_software_observation_is_not_host_commission")
_PREDICTION_QUALIFICATIONS = ("supplied_history_completeness_is_an_assertion",
    "unit_conversions_are_supplied_assertions", "binary64_equilibrium_evaluation",
    "n_is_effective_sites_per_declared_macromolecule")
_ORIGINAL_FIT_SCOPE = "retained_original_fit_vector_and_residual_population"








def merge_itc_parameter_facts(*groups):
    """Keep the ITC API through the shared Source-group merge."""
    from .molecular_result_facts import merge_molecular_facts
    return merge_molecular_facts(*groups, fact_source=ITC_PARAMETER_SOURCE)


def requested_itc_parameter_fields(schema):
    """Keep the exact ITC source contract through the finite shared selector."""
    from .molecular_result_facts import requested_molecular_fact_fields
    return requested_molecular_fact_fields(schema, fact_source=ITC_PARAMETER_SOURCE)


def validate_frozen_itc_parameter_return(form, schema, frozen):
    """Validate the original ITC cells without reopening their Files."""
    from .molecular_result_facts import validate_frozen_molecular_return
    return validate_frozen_molecular_return(form, schema, frozen, fact_source=ITC_PARAMETER_SOURCE)


def own_itc_parameter_facts(registry, context, *, read_received):
    """Authenticate own ITC actions through the common Source-group owner."""
    from .molecular_result_facts import own_molecular_facts
    return own_molecular_facts(registry, context, read_received=read_received,
        fact_source=ITC_PARAMETER_SOURCE)


def frozen_itc_parameter_facts(store, run_id, context):
    """Read the original frozen ITC group through the shared owner."""
    from .molecular_result_facts import frozen_molecular_facts
    return frozen_molecular_facts(store, run_id, context, fact_source=ITC_PARAMETER_SOURCE)


def received_itc_parameter_facts(store, run_id, context):
    """Consume actual ITC child forms and frozen ancestor receipt prefixes."""
    from .molecular_result_facts import received_molecular_facts
    return received_molecular_facts(store, run_id, context, fact_source=ITC_PARAMETER_SOURCE)
