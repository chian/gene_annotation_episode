"""A104 private durable evolutionary native-worker execution."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from .domain import ContractError, canonical
from .a104_action_custody import MolecularOperationUnpublished

def _molecular_worker_module(operation):
    return "gene_annotation_episode.episodic_workflow.root.a104." + {
        "protein_conservation_native": "muscle_alignment_driver",
        "protein_conservation_result": "protein_conservation_result_worker",
        "protein_phylogeny_iqtree_native": "iqtree_phylogeny_driver",
        "protein_phylogeny_result": "protein_phylogeny_result_worker",
    }[operation]

def _molecular_implementation_files(operation):
    import importlib
    from importlib import metadata, util
    from .a104_worker_implementation import _source_closure, _PACKAGES, _OPTIONAL
    closure = _source_closure(Path(__file__).resolve().parents[4],
        [_molecular_worker_module(operation)])
    files = [Path(__file__), *closure.values()]
    selected = {**_PACKAGES, 'biopython': 'Bio', 'numpy': 'numpy'}
    for name in selected.values():
        importlib.import_module(name)
    selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
    for name, module in selected.items():
        distribution = metadata.distribution(name)
        root = Path(distribution.locate_file('.')).resolve(strict=True)
        entries = distribution.files
        if not entries:
            raise ContractError('protein_conservation_dependency_files_unavailable')
        installed = []
        for entry in entries:
            # Bytecode and unused console scripts are not imported worker
            # dependencies. Filter them before requiring physical files in
            # the explicitly selected, copied package environment.
            if entry.suffix in {'.pyc', '.pyo'} or '__pycache__' in entry.parts:
                continue
            path = Path(distribution.locate_file(entry))
            if not path.resolve().is_relative_to(root):
                continue
            path = path.resolve(strict=True)
            if not path.is_file():
                raise ContractError('protein_conservation_dependency_file_unavailable')
            installed.append(path)
        specification = util.find_spec(module)
        if (specification is None or specification.origin is None
                or Path(specification.origin).resolve(strict=True) not in installed):
            raise ContractError('protein_conservation_dependency_import_conflict')
        files.extend(installed)
    return list(dict.fromkeys(files))

def run_owned_molecular_worker(operation, arguments, *, directory, owned_directory, policy, cancel_event):
    """Resume one authenticated native handle; retain its immutable controls.

    Unlike the transient sequence-worker default, these files are the recovery
    operands of this ordinary selected action. No release or replacement unit
    occurs when dispatch/completion is uncertain.
    """
    from ._local_job_worker import atomic_json
    from .native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect
    from .acquisition import AcquisitionError
    from .local_jobs import LocalJobPolicy
    directory, owned = Path(directory).resolve(strict=True), Path(owned_directory).resolve(strict=True)
    if operation not in {"protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result"} or directory != owned:
        raise ContractError("molecular_tool_owned_directory_conflict")
    request, output = owned / "worker-request.json", owned / "worker-result.json"
    handle_path, stdout, stderr = owned / "native-handle.json", owned / "stdout", owned / "stderr"
    payload = dict(operation=operation, arguments=arguments)
    worker_body = payload

    def command(python):
        return [python, "-m", _molecular_worker_module(operation), str(request), str(output)]

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
        # The reservation's original resource/argv/environment remain selected.
        # A different parent environment cannot reprice already launched work.
        selected_policy = LocalJobPolicy(**selected["policy"])
    else:
        if handle_path.exists() or request.exists() or output.exists():
            raise ContractError("molecular_tool_original_selection_missing")
        environment = dict(os.environ)
        temporary, cache = owned / "temporary", owned / "cache"
        temporary.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)
        environment.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary),
            XDG_CACHE_HOME=str(cache), PYTHONDONTWRITEBYTECODE="1")
        package_root = str(Path(__file__).resolve().parents[4])
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        implementation_files = _molecular_implementation_files(operation)
        python = dict(path=sys.executable)
        selected = dict(version="ordinary_molecular_execution_v1",
            command=command(python["path"]),
            cwd=str(owned), environment=environment, policy=policy.to_dict(), request=payload,
            python=python,
            implementation_files=[dict(path=str(p.resolve())) for p in implementation_files])
        selected_policy = policy
        atomic_json(selection_path, selected)

    def verify_unstarted_software():
        for file in [selected["python"], *selected["implementation_files"]]:
            if not Path(file["path"]).is_file():
                raise ContractError("molecular_tool_original_software_unavailable_before_dispatch")

    try:
        if request.exists():
            if canonical(json.loads(request.read_bytes())) != canonical(worker_body):
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
            if (
                    cancel_event is not None and cancel_event.is_set()
                    or view["state"] == "execution_unknown"):
                prefix = "a104_native_"
                raise MolecularOperationUnpublished(prefix + "worker_attempt_unconfirmed")
            # A prepared or unreleased handshake can still launch the original
            # command. Its original files must remain available before release.
            if not Path(handle.read()["paths"]["release"]).exists():
                verify_unstarted_software()
            resume_start(handle, cancel_event=cancel_event)
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
                    prefix = "a104_native_"
                    raise MolecularOperationUnpublished(prefix + "worker_attempt_unconfirmed")
                if cancel_event is None:
                    time.sleep(.05)
                else:
                    cancel_event.wait(.05)
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


