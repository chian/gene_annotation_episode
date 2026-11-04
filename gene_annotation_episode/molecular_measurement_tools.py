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

from .domain import ContractError, REF, canonical, obj
from .itc_binding_contracts import (
    FIT_SELECTION_VERSION, PARAMETERS, REASONS, SELECTION_VERSION, SHEET_VERSION, copy_json, number,
    validate_itc_binding_components_shape, validate_itc_binding_fit_selection,
    validate_itc_binding_selection, validate_itc_binding_sheet, validate_itc_binding_supplied,
)


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
    from .molecular_reference_privacy import molecular_reference_restriction
    return molecular_reference_restriction(store, context, reference, namespace,
        providers=(ITC_TOOL,))


def _molecular_implementation_files(operation):
    """Pin the selected operation's implementation before its first dispatch."""
    if operation in {"protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"}:
        import importlib
        from importlib import metadata, util
        from .native_atac_differential_software import _source_closure, _PACKAGES, _OPTIONAL
        closure = _source_closure(Path(__file__).parent.parent,
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
    modules = {
        "protein_disorder": ("protein_disorder_tools.py", "protein_disorder_measurements.py",
            "protein_disorder_result_contracts.py", "sequence_composition_grader.py", "sequence_mapping.py",
            "molecular_sequence_result_contracts.py", "acquisition.py", "boundary_validation.py", "domain.py",
            "execution_contracts.py", "native_atac_differential_driver.py", "native_file_capture.py"),
        "arsenic_speciation": ("calibrated_signal_contracts.py", "calibrated_signal_sheet.py",
            "calibrated_signal_calculations.py", "arsenic_speciation_tools.py",
            "arsenic_speciation_result_contracts.py", "molecular_sequence_input_contracts.py"),
        "itc_binding": ("itc_binding_contracts.py", "itc_binding_measurements.py",
            "itc_binding_fit.py", "bivariate_covariance.py"),
        "liftover_point": ("liftover_contracts.py", "liftover_measurements.py"),
        "circular_dichroism": ("circular_dichroism_contracts.py", "circular_dichroism_measurements.py",
            "circular_dichroism_tools.py", "molecular_sequence_input_contracts.py"),
        "macs2_peak_result": ("macs2_peak_result_worker.py", "macs2_peak_result_contracts.py",
            "macs2_peak_components.py", "atac_differential_inputs.py", "atac_differential_contracts.py",
            "atac_differential_result_contracts.py", "native_macs2_peak_execution.py",
            "native_atac_differential_contracts.py", "native_atac_differential_driver.py"),
        "homer_motif_result": ("native_homer_worker.py", "homer_motif_contracts.py",
            "homer_motif_measurements.py", "homer_motif_result_contracts.py",
            "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py",
            "native_flux_balance_storage.py", "native_flux_balance_contracts.py",
            "native_file_capture.py", "materials.py", "domain.py", "execution_contracts.py"),
        "tf_binding_native": ("tf_binding_measurements.py", "blast_fasta_record_identity.py",
            "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py",
            "native_flux_balance_storage.py", "domain.py"),
        "tf_binding_result": ("tf_binding_measurements.py", "blast_fasta_record_identity.py",
            "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py",
            "native_flux_balance_storage.py", "native_file_capture.py", "domain.py"),
        "protease_kinetics_native": ("molecular_sequence_native.py", "protease_kinetics_measurements.py",
            "bivariate_covariance.py", "orf_measurements.py", "primer_placement_measurements.py",
            "glycosylation_measurements.py"),
        "protease_kinetics_saved": ("molecular_sequence_native.py", "protease_kinetics_measurements.py",
            "bivariate_covariance.py", "orf_measurements.py", "primer_placement_measurements.py",
            "glycosylation_measurements.py"),
    }
    if operation not in modules:
        raise ContractError("molecular_tool_operation_unknown")
    files = ([] if operation in {"protease_kinetics_native", "protease_kinetics_saved"} else [Path(__file__)]) + [Path(__file__).with_name(
        _molecular_worker_module(operation).rsplit(".", 1)[-1] + ".py"),
        *(Path(__file__).with_name(name) for name in modules[operation])]
    distributions = {
        "liftover_point": (("pyliftover", "pyliftover"),),
        "tf_binding_native": (("biopython", "Bio"), ("numpy", "numpy")),
        "tf_binding_result": (("biopython", "Bio"), ("numpy", "numpy")),
    }
    for distribution_name, import_name in distributions.get(operation, ()):
        from importlib import metadata, util
        from .acquisition import AcquisitionError
        try:
            distribution = metadata.distribution(distribution_name)
            entries = distribution.files
            if not entries:
                raise ValueError(distribution_name + "_distribution_files_unavailable")
            if operation in {"tf_binding_native", "tf_binding_result"}:
                distribution_root = Path(distribution.locate_file(".")).resolve(strict=True)
                # Imported package code and native libraries belong to this
                # selection. Unused console scripts outside its import root do
                # not become prerequisites of either TF worker.
                entries = [entry for entry in entries
                    if Path(distribution.locate_file(entry)).resolve().is_relative_to(distribution_root)]
            installed = [Path(distribution.locate_file(entry)).resolve(strict=True)
                for entry in entries if entry.suffix != ".pyc" and "__pycache__" not in entry.parts]
            specification = util.find_spec(import_name)
            if (specification is None or specification.origin is None
                    or Path(specification.origin).resolve(strict=True) not in installed
                    or any(not path.is_file() for path in installed)):
                raise ValueError(distribution_name + "_distribution_import_conflict")
        except (metadata.PackageNotFoundError, OSError, ValueError) as error:
            reason = ("distribution_metadata_unavailable" if isinstance(error, metadata.PackageNotFoundError)
                else "distribution_file_unavailable" if isinstance(error, OSError)
                else "distribution_import_or_files_conflict")
            raise AcquisitionError(distribution_name + "_not_installed", phase="local_preflight",
                operational={"software": distribution_name, "reason": reason}) from error
        files.extend(installed)
    return list(dict.fromkeys(files))


def _molecular_worker_module(operation):
    module = {"homer_motif_result": "native_homer_worker",
        "esm_gene_embedding": "esm_gene_embedding_worker",
        "tf_binding_native": "tf_binding_driver", "tf_binding_result": "tf_binding_result_worker",
        "protein_conservation_native": "muscle_alignment_driver",
        "protein_conservation_result": "protein_conservation_result_worker",
        "protein_phylogeny_iqtree_native": "iqtree_phylogeny_driver",
        "protein_phylogeny_result": "protein_phylogeny_result_worker",
        "somatic_variant_native": "somatic_variant_driver",
        "somatic_variant_result": "somatic_variant_result_worker",
        "protease_kinetics_native": "molecular_sequence_driver", "protease_kinetics_saved": "molecular_sequence_driver"}
    return "gene_annotation_episode." + module.get(operation, "sequence_worker")


def run_owned_molecular_worker(operation, arguments, *, directory, owned_directory, policy, cancel_event):
    """Resume one authenticated native handle; retain its immutable controls.

    Unlike the transient sequence-worker default, these files are the recovery
    operands of this ordinary selected action. No release or replacement unit
    occurs when dispatch/completion is uncertain.
    """
    from ._local_job_worker import atomic_json
    from .native_lifecycle import NativeJobHandle, prepare_job, resume_start, wait_job, status, collect
    from .acquisition import AcquisitionError
    from .local_jobs import LocalJobPolicy
    directory, owned = Path(directory).resolve(strict=True), Path(owned_directory).resolve(strict=True)
    if operation not in {"itc_binding", "liftover_point", "circular_dichroism", "macs2_peak_result", "homer_motif_result",
            "tf_binding_native", "tf_binding_result", "protease_kinetics_native", "protease_kinetics_saved",
            "protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result",
            "arsenic_speciation", "protein_disorder", "esm_gene_embedding"} or directory != owned:
        raise ContractError("molecular_tool_owned_directory_conflict")
    request, output = owned / "worker-request.json", owned / "worker-result.json"
    handle_path, stdout, stderr = owned / "native-handle.json", owned / "stdout", owned / "stderr"
    payload = dict(operation=operation, arguments=arguments)
    protease = operation in {"protease_kinetics_native", "protease_kinetics_saved"}
    esm = operation == "esm_gene_embedding"
    worker_body, request_raw = payload, None
    if esm:
        from .esm_gene_embedding_contracts import validate_esm_worker_request
        from .esm_gene_embedding_tools import esm_worker_environment, esm_worker_implementation_files
        if type(arguments) is not dict or set(arguments) != {"request"}:
            raise ContractError("esm_gene_embedding_worker_request_conflict")
        esm_request = validate_esm_worker_request(arguments["request"])
        esm_driver = esm_request["deployment"]["driver"]
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
        if esm and (selected["python"] != dict(path=esm_driver["python_executable"],
                    sha256=esm_driver["python_sha256"])
                or canonical(selected["environment"]) != canonical(esm_worker_environment(esm_request, owned))
                or canonical(selected["implementation_files"]) != canonical(esm_worker_implementation_files(esm_request))):
            raise ContractError("esm_gene_embedding_original_runtime_conflict")
        # The reservation's original resource/argv/environment remain selected.
        # A different parent environment cannot reprice already launched work.
        selected_policy = LocalJobPolicy(**selected["policy"])
    else:
        if handle_path.exists() or request.exists() or output.exists():
            raise ContractError("molecular_tool_original_selection_missing")
        environment = dict(os.environ)
        if operation in {"tf_binding_native", "tf_binding_result", "arsenic_speciation", "protein_disorder",
                "protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} or protease or esm:
            temporary, cache = owned / "temporary", owned / "cache"
            temporary.mkdir(exist_ok=True)
            cache.mkdir(exist_ok=True)
            environment.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary),
                XDG_CACHE_HOME=str(cache), PYTHONDONTWRITEBYTECODE="1")
        package_root = str(Path(__file__).resolve().parent.parent)
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        if esm:
            # This operation binds the caller-selected physical runtime. Host
            # package discovery cannot replace its interpreter or dependencies.
            implementation_files = None
            esm_files = esm_worker_implementation_files(esm_request)
            environment = esm_worker_environment(esm_request, owned)
            python = dict(path=esm_driver["python_executable"], sha256=esm_driver["python_sha256"])
        else:
            implementation_files = _molecular_implementation_files(operation)
            python = dict(path=sys.executable, sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest())
        if operation == "protease_kinetics_native":
            deployment = worker_body["selection"]["deployment"]
            index, _ = native_source._manifest(deployment)
            # Bind the explicitly selected deployment; no host package discovery
            # or identity substitution supplies its interpreter/source closure.
            python = {key: deployment["runtime"]["executable"][key] for key in ("path", "sha256")}
            expected = {str(Path(root) / "gene_annotation_episode" / path.name): path
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
                esm_files if esm else [*index.values(), deployment["software_files_file"]])
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
            if operation in {"homer_motif_result", "tf_binding_native", "tf_binding_result", "arsenic_speciation", "protein_disorder",
                    "protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} or protease or esm:
                preserve_observer = True
            else:
                preserve_observer = False
            if preserve_observer and (
                    cancel_event is not None and cancel_event.is_set()
                    or view["state"] == "execution_unknown"):
                prefix = ("somatic_variant_" if operation in {"somatic_variant_native", "somatic_variant_result"} else "protein_phylogeny_" if operation in {"protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} else "esm_gene_embedding_" if esm else "protein_conservation_" if operation in {"protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} else
                    "protein_disorder_" if operation == "protein_disorder" else "arsenic_speciation_" if operation == "arsenic_speciation" else
                    "protease_kinetics_" if protease else "homer_motif_" if operation == "homer_motif_result" else "tf_binding_")
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
                        prefix = ("somatic_variant_" if operation in {"somatic_variant_native", "somatic_variant_result"} else "protein_phylogeny_" if operation in {"protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} else "esm_gene_embedding_" if esm else "protein_conservation_" if operation in {"protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"} else
                            "protein_disorder_" if operation == "protein_disorder" else "arsenic_speciation_" if operation == "arsenic_speciation" else
                            "protease_kinetics_" if protease else "homer_motif_" if operation == "homer_motif_result" else "tf_binding_")
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


def itc_tool_contract():
    """One local operation; modes do not imply a child or another model call."""
    numeric = {"type": "number"}
    nullable = {"anyOf": [numeric, {"type": "null"}]}
    parameters = obj({name: numeric for name in PARAMETERS})
    ordinals = {"type": "array", "items": {"type": "integer", "minimum": 0}, "uniqueItems": True}
    triple = {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0},
        "minItems": 3, "maxItems": 3}
    positive = {"type": "number", "exclusiveMinimum": 0}
    fit = obj(dict(mode={"const": "fit"},
        input=obj(dict(namespace={"enum": ["source", "artifact"]}, reference=REF)),
        residual_injection_ordinals=ordinals, initial_parameters=parameters,
        bounds=obj({name: obj(dict(lower=nullable, upper=nullable)) for name in PARAMETERS}),
        solver=obj(dict(method={"const": "trf"}, jacobian={"const": "two_point"},
            ftol=positive, xtol=positive, gtol=positive,
            max_nfev={"type": "integer", "minimum": 1}, x_scale=triple, diff_step=triple)),
        weighting=obj(dict(kind={"enum": ["unweighted", "diagonal_sigma"]},
            independent_error_assumption={"enum": [None, True]}, absolute_sigma={"type": "boolean"},
            sigma_heat_joule={"type": "array", "items": positive}))))
    saved = obj(dict(mode={"const": "calculate_saved"}, result_ref=REF,
        parameter_source={"enum": ["fit_observation", "selected_parameters"]},
        parameters={"anyOf": [parameters, {"type": "null"}]},
        injection_ordinals=ordinals, fit_diagnostics={"type": "boolean"}))
    read = obj(dict(mode={"const": "read_stored"}, result_ref=REF, injection_ordinals=ordinals,
        fields={"type": "array", "items": {"enum": list(ROW_FIELDS)}, "uniqueItems": True}))
    return dict(resources="local", description=(
        "Fit the physical one-site ITC model, with stoichiometry n in the binding balance, to an explicitly "
        "received ITC JSON File using your selected injection residuals, bounds, solver and error assumption. "
        "Retain Kd (mol/L), n (sites/macromolecule), enthalpy (J/mol), full injection history, residuals "
        "and the native covariance estimate with its qualifications. Supplied heat/volume/concentration "
        "calibration remains an assertion. Alternatively calculate from the retained sheet with explicitly "
        "selected parameters, or read stored cells without fitting. SSE, objective and covariance still "
        "describe the retained original fitted vector and residual population when you select different "
        "forward parameters. This ordinary tool runs within the "
        "current episode; choose subsequent investigation actions from the returned results."),
        input_schema={"anyOf": [fit, saved, read]})


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


def _ids(supplied, ordinals):
    rows = supplied["injections"] or []
    if (type(ordinals) is not list or any(type(i) is not int or i < 0 or i >= len(rows) for i in ordinals)
            or len(ordinals) != len(set(ordinals))):
        raise ContractError("itc_binding_injection_ordinal_invalid")
    return [rows[i]["injection_id"] for i in ordinals]


def prepare_itc_tool_request(arguments, *, received_input, invocation, original=None):
    """Retain the exact selected ordinal→native-ID mapping, without provenance invention."""
    mode = arguments["mode"]
    supplied = validate_itc_binding_supplied(received_input["content"]["value"] if mode == "fit"
        else original["sheet"]["supplied"])
    ids = _ids(supplied, arguments["residual_injection_ordinals"] if mode == "fit" else arguments["injection_ordinals"])
    fit_selection = None
    if mode == "fit":
        weighting = deepcopy(arguments["weighting"])
        sigmas = weighting.pop("sigma_heat_joule")
        if weighting["kind"] == "unweighted" and sigmas or weighting["kind"] == "diagonal_sigma" and len(sigmas) != len(ids):
            raise ContractError("itc_binding_selected_sigma_population_required")
        weighting["sigma_heat"] = [dict(injection_id=key, sigma=dict(value=value,
            unit="J", canonical_unit="J", to_canonical_factor=1, source_ref=None, source_pointer=None))
            for key, value in zip(ids, sigmas)]
        solver = deepcopy(arguments["solver"]); solver["jacobian"] = "2-point"
        fit_selection = validate_itc_binding_fit_selection(dict(version=FIT_SELECTION_VERSION,
            residual_injection_ids=ids, initial_parameters=arguments["initial_parameters"],
            bounds=arguments["bounds"], solver=solver, weighting=weighting))
        selection = dict(version=SELECTION_VERSION, parameter_source="fit_observation", parameters=None,
            injection_ids=ids, fit_diagnostics=True)
        sheet = dict(version=SHEET_VERSION, supplied=supplied, fit_observation=None)
    else:
        selection = dict(version=SELECTION_VERSION, parameter_source=arguments["parameter_source"],
            parameters=arguments["parameters"], injection_ids=ids, fit_diagnostics=arguments["fit_diagnostics"])
        sheet = original["sheet"]
    return dict(version=REQUEST_VERSION, invocation=deepcopy(invocation), arguments=deepcopy(arguments),
        received_input=deepcopy(received_input), sheet=validate_itc_binding_sheet(sheet),
        fit_selection=fit_selection, selection=validate_itc_binding_selection(selection))


def run_itc_tool_request(request, *, output_directory):
    """Store-free worker: exactly one fit in fit mode; saved mode never imports it."""
    if request.get("version") != REQUEST_VERSION or request["arguments"]["mode"] not in ("fit", "calculate_saved"):
        raise ValueError("ordinary_itc_request_invalid")
    from .itc_binding_measurements import calculate_itc_binding_components
    sheet = validate_itc_binding_sheet(request["sheet"])
    if request["arguments"]["mode"] == "fit":
        from .itc_binding_fit import fit_itc_binding_measurements
        sheet["fit_observation"] = fit_itc_binding_measurements(sheet, selection=request["fit_selection"])
    components = calculate_itc_binding_components(sheet, selection=request["selection"])
    return dict(version=RESULT_VERSION, request=deepcopy(request), sheet=sheet, components=components)


def _worker_request(request):
    """Only scientific operands enter the worker/native scientific result.

    Receiver lineage, run/action identity and admission evidence stay in the
    separately retained host control, rather than source-readable result data.
    """
    return {**{key: deepcopy(request[key]) for key in
        ("version", "arguments", "sheet", "fit_selection", "selection")},
        "input_file": deepcopy(request["received_input"]["file"])}


def _validate_result(value, request=None):
    if (type(value) is not dict or set(value) != {"version", "request", "sheet", "components"}
            or value["version"] != RESULT_VERSION or value["request"].get("version") != REQUEST_VERSION
            or request is not None and canonical(value["request"]) != canonical(request)):
        raise ContractError("ordinary_itc_result_conflict")
    validate_itc_binding_sheet(value["sheet"])
    validate_itc_binding_components_shape(value["components"])
    if (canonical(value["components"]["sheet"]) != canonical(value["sheet"])
            or canonical(value["components"]["selection"]) != canonical(value["request"]["selection"])
            or canonical(value["sheet"]["supplied"]) != canonical(value["request"]["sheet"]["supplied"])):
        raise ContractError("ordinary_itc_result_conflict")
    observation = value["sheet"]["fit_observation"]
    if value["request"]["arguments"]["mode"] == "fit":
        if observation is None or canonical(observation["selection"]) != canonical(value["request"]["fit_selection"]):
            raise ContractError("ordinary_itc_fit_selection_conflict")
    elif canonical(value["sheet"]) != canonical(value["request"]["sheet"]):
        raise ContractError("ordinary_itc_saved_sheet_conflict")
    return value


def _publication_profile(tool_name):
    """Finite ordinary producers; a saved read never becomes a new producer."""
    if tool_name == "generate_gene_embeddings_with_ESM_models":
        return ("esm_gene_embedding_result_v1", "ordinary_esm_gene_embedding_publication_v1",
            ("embed",), "esm_gene_embedding_")
    if tool_name == "detect_and_annotate_somatic_mutations":
        return ("ordinary_somatic_variant_result_v1", "ordinary_somatic_variant_publication_v1",
            ("run_native", "calculate_saved"), "somatic_variant_")
    if tool_name == "analyze_protein_phylogeny":
        return ("ordinary_protein_phylogeny_result_v1", "ordinary_protein_phylogeny_publication_v1",
            ("run_native", "calculate_saved"), "protein_phylogeny_")
    if tool_name == "analyze_protein_conservation":
        return ("ordinary_protein_conservation_result_v1", "ordinary_protein_conservation_publication_v1",
            ("run_native", "calculate_saved"), "protein_conservation_")
    if tool_name == "predict_protein_disorder_regions":
        return ("ordinary_protein_disorder_result_v1", "ordinary_protein_disorder_publication_v1",
            ("predict", "calculate_saved"), "protein_disorder_")
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        return ("ordinary_arsenic_speciation_result_v1", "ordinary_arsenic_speciation_publication_v1",
            ("calculate", "calculate_saved"), "arsenic_speciation_")
    if tool_name == "result.variants.vcf":
        return ("ordinary_vcf_result_v1", "ordinary_vcf_publication_v1",
            ("analyze", "calculate_saved"), "vcf_result_")
    if tool_name == ITC_TOOL:
        return RESULT_VERSION, "ordinary_itc_publication_v1", ("fit", "calculate_saved"), "ordinary_itc_"
    if tool_name == "liftover_coordinates":
        return "ordinary_liftover_result_v1", "ordinary_liftover_publication_v1", ("convert",), "ordinary_liftover_"
    if tool_name == "analyze_circular_dichroism_spectra":
        return "ordinary_cd_result_v1", "ordinary_cd_publication_v1", ("calculate",), "circular_dichroism_"
    if tool_name == "analyze_cas9_mutation_outcomes":
        return ("ordinary_reference_edit_outcome_result_v1", "ordinary_reference_edit_outcome_publication_v1",
            ("analyze", "calculate_saved"), "reference_edit_outcome_")
    if tool_name == "result.macs2.peaks":
        return ("ordinary_macs2_peak_result_v1", "ordinary_macs2_peak_publication_v1",
            ("parse", "project_saved"), "macs2_peak_")
    if tool_name == "find_enriched_motifs_with_homer":
        return ("ordinary_homer_motif_result_v1", "ordinary_homer_motif_publication_v1",
            ("run_native", "calculate_saved"), "homer_motif_")
    if tool_name == "identify_transcription_factor_binding_sites":
        return ("ordinary_tf_binding_result_v1", "ordinary_tf_binding_publication_v1",
            ("run_native", "calculate_saved"), "tf_binding_")
    if tool_name == "analyze_protease_kinetics":
        return ("ordinary_protease_kinetics_result_v1", "ordinary_protease_kinetics_publication_v1",
            ("run_native", "calculate_saved"), "protease_kinetics_")
    raise ContractError("molecular_publication_unknown_producer")


def _recorded_molecular_action_details(registry, context, arguments, operation_key, tool_name, *,
        recovery_context=None, recovery_operation_key=None, selected_only=False):
    """Authenticate one editing action independently of its Source producer."""
    from .communication import plain
    from .domain import identity
    from .episode_bindings import BindingContext
    from .episode_return_records import EpisodeReturnRecords
    from .waiting import validate_pending
    prefix = ("somatic_variant_" if tool_name == "detect_and_annotate_somatic_mutations" else "esm_gene_embedding_" if tool_name == "generate_gene_embeddings_with_ESM_models" else
        "protein_phylogeny_" if tool_name == "analyze_protein_phylogeny" else
        "protein_conservation_" if tool_name == "analyze_protein_conservation" else
        "protein_disorder_" if tool_name == "predict_protein_disorder_regions" else
        "arsenic_speciation_" if tool_name == "analyze_arsenic_speciation_hplc_icpms" else
        "vcf_result_" if tool_name == "result.variants.vcf" else
        "macs2_peak_" if tool_name == "result.macs2.peaks" else
        "homer_motif_" if tool_name == "find_enriched_motifs_with_homer" else
        "tf_binding_" if tool_name == "identify_transcription_factor_binding_sites" else
        "protease_kinetics_" if tool_name == "analyze_protease_kinetics" else "reference_edit_outcome_")
    if tool_name not in {"analyze_cas9_mutation_outcomes", "result.macs2.peaks", "find_enriched_motifs_with_homer",
            "identify_transcription_factor_binding_sites", "result.variants.vcf",
            "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
            "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations",
            "generate_gene_embeddings_with_ESM_models"} or not isinstance(context, BindingContext):
        raise ContractError(prefix + "action_conflict")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix=prefix)
    records.authenticate(context)
    start = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(start):] if type(operation_key) is str and operation_key.startswith(start) else ""
    if not suffix.isdecimal() or str(int(suffix)) != suffix:
        raise ContractError(prefix + "action_conflict")
    if type(selected_only) is not bool or selected_only and tool_name not in {
            "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
            "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations"}:
        raise ContractError(prefix + "action_conflict")
    if selected_only:
        # Metadata-only denial authority for a private native capture produced
        # before its public ToolOperation commits. This grants no read/recovery.
        selected = registry.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
        if selected is None:
            raise ContractError(prefix + "action_conflict")
        actual_selection = json.loads(selected["action"])
        if arguments is None:
            if (type(actual_selection) is not dict or set(actual_selection) != {"kind", "tool", "arguments"}
                    or actual_selection["kind"] != "tool" or actual_selection["tool"] != tool_name):
                raise ContractError(prefix + "action_conflict")
            arguments = actual_selection["arguments"]
        if canonical(actual_selection) != canonical(
                dict(kind="tool", tool=tool_name, arguments=arguments)):
            raise ContractError(prefix + "action_conflict")
        from .execution_contracts import digest as execution_digest
        invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
            decision_index=int(suffix), request_sha256=execution_digest(plain(context.request)), scope=plain(context.scope))
        return dict(arguments=deepcopy(arguments), invocation=invocation, outcome=None,
            operation_ref=identity("operation", dict(key=operation_key, name=tool_name, arguments=arguments)),
            runtime_outcome=None if selected["result"] is None else json.loads(selected["result"]), pending_recovery=False)
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
    if tool_name in {"result.macs2.peaks", "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
            "result.variants.vcf", "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
            "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations", "generate_gene_embeddings_with_ESM_models"}:
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
    from .episode_bindings import BindingContext
    from .episode_return_records import EpisodeReturnRecords
    _, _, modes, prefix = _publication_profile(tool_name)
    editing = tool_name in {"analyze_cas9_mutation_outcomes", "result.macs2.peaks", "find_enriched_motifs_with_homer",
        "identify_transcription_factor_binding_sites", "result.variants.vcf", "analyze_protease_kinetics",
        "analyze_arsenic_speciation_hplc_icpms", "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations",
        "generate_gene_embeddings_with_ESM_models"}
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
            if tool_name in {"result.macs2.peaks", "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
                    "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
                    "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations", "generate_gene_embeddings_with_ESM_models"} and source_ref not in json.loads(row["result"]).get("changed_record_refs", []):
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


def _recorded_molecular_capture_action(registry, operation_ref, tool_name):
    """Find a capture's actual selected action without requiring a ToolOperation.

    An accession is a candidate identity, never authority by itself. Recompute
    it from the saved key/tool/full arguments, then use the shared authenticator.
    This metadata-only port grants no bytes, receipts or pending recovery.
    """
    from .domain import identity
    from .episode_return_records import EpisodeReturnRecords
    if tool_name not in {"find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
            "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations"}:
        raise ContractError("molecular_capture_unknown_producer")
    tool = tool_name
    prefix = _publication_profile(tool)[3]
    matches = []
    rows = registry.store.db.execute("SELECT run_id,episode_id,decision_index,action FROM runtime_actions "
        "WHERE json_extract(action,'$.kind')='tool' AND json_extract(action,'$.tool')=?", (tool,))
    for row in rows:
        selected = json.loads(row["action"])
        if type(row["decision_index"]) is not int or row["decision_index"] < 0:
            continue
        key = f'{row["run_id"]}:{row["episode_id"]}:{row["decision_index"]}'
        arguments = selected.get("arguments")
        if identity("operation", dict(key=key, name=tool, arguments=arguments)) != operation_ref:
            continue
        records = EpisodeReturnRecords(registry.store, row["run_id"], failure_prefix=prefix)
        context = records.context(row["episode_id"])
        matches.append(_recorded_molecular_action_details(registry, context, arguments, key, tool, selected_only=True))
    if len(matches) != 1:
        raise ContractError(prefix + "capture_action_conflict")
    return matches[0]


def _recorded_homer_capture_action(registry, operation_ref):
    return _recorded_molecular_capture_action(registry, operation_ref, "find_enriched_motifs_with_homer")


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
    """The common read within one metadata snapshot; no additional admission."""
    if tool_name == "generate_gene_embeddings_with_ESM_models":
        from .esm_gene_embedding_publication import _read
        return _read(registry, context, reader, source_ref)
    if tool_name == "detect_and_annotate_somatic_mutations":
        from .somatic_variant_publication import _read_somatic_variant_publication
        return _read_somatic_variant_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protein_phylogeny":
        from .protein_phylogeny_publication import _read_protein_phylogeny_publication
        return _read_protein_phylogeny_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protein_conservation":
        from .protein_conservation_publication import _read_protein_conservation_publication
        return _read_protein_conservation_publication(registry, context, reader, source_ref)
    if tool_name == "predict_protein_disorder_regions":
        from .protein_disorder_tools import read_protein_disorder_publication
        return read_protein_disorder_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        from .arsenic_speciation_tools import read_arsenic_speciation_publication
        return read_arsenic_speciation_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protease_kinetics":
        from .protease_kinetics_tools import _read_protease_kinetics_publication
        return _read_protease_kinetics_publication(registry, context, reader, source_ref)
    if tool_name == "result.variants.vcf":
        from .vcf_result_tools import read_retained_vcf_publication
        return read_retained_vcf_publication(registry, context, reader, source_ref)
    if tool_name in {"find_n_glycosylation_motifs", "predict_o_glycosylation_hotspots", "align_sequences"}:
        return registry.molecular_sequence_results_for(context.run_id).read_ordinary_molecular_sequence_publication(
            context, source_ref, operation=tool_name, read_received=reader)
    if tool_name == "identify_transcription_factor_binding_sites":
        from .tf_binding_tools import _read_tf_binding_publication
        return _read_tf_binding_publication(registry, context, reader, source_ref)
    if tool_name == "find_enriched_motifs_with_homer":
        from .homer_motif_tools import _read_homer_publication
        return _read_homer_publication(registry, context, reader, source_ref)
    if tool_name == "result.macs2.peaks":
        from .macs2_peak_tools import _read_publication
        return _read_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_cas9_mutation_outcomes":
        from .reference_edit_outcome_tools import _read_reference_edit_outcome_publication
        return _read_reference_edit_outcome_publication(registry, context, reader, source_ref)
    result_version, control_version, _, prefix = _publication_profile(tool_name)
    if tool_name == ITC_TOOL:
        item = _received(reader, context, source_ref, "source")
    else:
        admitted = reader(context, source_ref, "source", source_metadata_only=True)
        if admitted["failure"] is not None:
            raise ContractError("molecular_tool_" + admitted["failure"]["code"])
        item = admitted["input"]
    source = item["witness"]["record"]
    if (source.get("origin") != "tool" or source.get("provider") != tool_name
            or source.get("version") != result_version):
        raise ContractError(prefix + "producer_required")
    arguments, invocation = _recorded_molecular_producer(registry, source_ref, tool_name)
    if tool_name == ITC_TOOL:
        value = _validate_result(item["content"]["value"])
    elif tool_name == "analyze_circular_dichroism_spectra":
        from .circular_dichroism_contracts import validate_circular_dichroism_tool_result
        value = validate_circular_dichroism_tool_result(json.loads(_publication_bytes(registry.store, source["artifact_ref"])))
    else:
        from .liftover_measurements import validate_liftover_tool_result
        value = validate_liftover_tool_result(json.loads(_publication_bytes(registry.store, source["artifact_ref"])))
    control = json.loads(_publication_bytes(registry.store, source["request_ref"]))
    if (type(control) is not dict or set(control) != {"version", "request", "native_artifact_ref",
            "execution_selection", "native_handle", "execution"}
            or control["version"] != control_version
            or control["native_artifact_ref"] != source["artifact_ref"]):
        raise ContractError(prefix + "publication_conflict")
    request = control["request"]
    if tool_name in {"liftover_coordinates", "analyze_circular_dichroism_spectra"} and (
            type(request) is not dict or set(request) != {
                "version", "arguments", "invocation", "received_input", "request"}
            or request["version"] != ("ordinary_liftover_request_v1" if tool_name == "liftover_coordinates"
                else "ordinary_cd_request_v1")):
        raise ContractError(prefix + "publication_conflict")
    expected = _worker_request(request) if tool_name == ITC_TOOL else request["request"]
    witness = request["received_input"]["witness"]
    if tool_name == "liftover_coordinates" and (
            canonical(expected["chain"]["file"]) != canonical(request["received_input"]["file"])
            or expected["chain"]["source_ref"] != (
                witness["reference"] if witness["namespace"] == "source" else None)
            or canonical(arguments.get("input")) != canonical(
                dict(namespace=witness["namespace"], reference=witness["reference"]))
            or arguments.get("chain_format") != expected["chain"]["file"]["format"]
            or canonical(arguments.get("point")) != canonical(expected["point"])):
        raise ContractError(prefix + "publication_conflict")
    if tool_name == "analyze_circular_dichroism_spectra" and (
            canonical(expected["input_file"]) != canonical(request["received_input"]["file"])
            or canonical(arguments.get("input")) != canonical(
                dict(namespace=witness["namespace"], reference=witness["reference"]))):
        raise ContractError(prefix + "publication_conflict")
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
    return dict(admission_kind="source_and_file" if tool_name == ITC_TOOL else "source_only",
        received_input=item, source=source, stored=value, control=control,
        grading_ref=entries[0]["artifact_ref"])


def read_retained_itc_result(registry, context, reader, source_ref):
    """Preserve the existing ITC reader's admitted input/result/grading triple."""
    result = read_retained_molecular_publication(registry, context, reader, source_ref, tool_name=ITC_TOOL)
    return result["received_input"], result["stored"], result["grading_ref"]


def _cell(value):
    return {**deepcopy(value), "unit": UNIT_CODES[value["unit"]]}


def project_itc_tool_result(stored, *, selection, source_ref, artifact_ref, grading_ref):
    """Select literal stored cells; no fitting or numerical reconstruction."""
    components = stored["components"]
    ordinals = selection.get("injection_ordinals", selection.get("residual_injection_ordinals", []))
    _ids(stored["sheet"]["supplied"], ordinals)
    fields = selection.get("fields", ROW_FIELDS)
    rows = {row["delivered_ordinal"]: row for row in components["rows"]}
    if any(i not in rows for i in ordinals):
        raise ContractError("ordinary_itc_cells_not_stored")
    observation = stored["sheet"]["fit_observation"]
    diagnostics = components["fit_diagnostics"]
    return dict(version="ordinary_itc_values_v1", mode=selection["mode"], source_ref=source_ref,
        native_file=dict(artifact_ref=artifact_ref, format="json"), grading_ref=grading_ref,
        parameters={name: _cell(value) for name, value in components["parameter_values"].items()},
        rows=[dict(injection_ordinal=i, **{name: _cell(rows[i][name]) for name in fields}) for i in ordinals],
        fit_call_state=observation["call_state"] if observation else "not_started",
        fit_call_count=observation["call_count"] if observation else 0,
        fit_call_scope="retained_fit_observation", this_operation_fit=selection["mode"] == "fit",
        parameter_source=components["selection"]["parameter_source"],
        residual_population_count=None if diagnostics is None else diagnostics["observation_count"],
        residual_degrees_of_freedom=None if diagnostics is None else diagnostics["residual_degrees_of_freedom"],
        sse=None if diagnostics is None else _cell(diagnostics["sse"]),
        selected_objective=None if diagnostics is None else _cell(diagnostics["selected_objective"]),
        covariance_estimate=None if observation is None else deepcopy(observation["native_covariance"]),
        fit_diagnostics_scope=None if diagnostics is None else "retained_original_fit_vector_and_residual_population",
        covariance_scope=None if observation is None or observation['native_covariance'] is None else
            "retained_original_fit_vector_and_residual_population",
        covariance_parameter_order=list(PARAMETERS),
        covariance_parameter_units=["mol_per_litre", "sites_per_macromolecule", "joule_per_mole"],
        covariance_validity="not_assessed", identifiability="not_assessed",
        weighting=None if observation is None else observation["selection"]["weighting"]["kind"],
        independent_error_assumption=None if observation is None else
            observation["selection"]["weighting"]["independent_error_assumption"],
        absolute_sigma=None if observation is None else observation["selection"]["weighting"]["absolute_sigma"],
        warning_locations=[] if observation is None else [dict(source_ref=source_ref,
            location="fit_warning", occurrence=i) for i in range(len(observation["warnings"]))],
        failure_location=None if observation is None or observation["failure"] is None else
            dict(source_ref=source_ref, location="fit_failure", occurrence=0))


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
            from .acquisition import AcquisitionError
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
    if tool_name == "predict_protein_disorder_regions":
        from .protein_disorder_tools import _retain_protein_disorder_publication
        return _retain_protein_disorder_publication(registry, prepared)
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        from .arsenic_speciation_tools import _retain_arsenic_speciation_publication
        return _retain_arsenic_speciation_publication(registry, prepared)
    if tool_name == "analyze_protease_kinetics":
        from .protease_kinetics_tools import _retain_protease_kinetics_publication
        return _retain_protease_kinetics_publication(registry, prepared)
    if tool_name == "result.variants.vcf":
        from .vcf_result_tools import _retain_vcf_result_publication
        return _retain_vcf_result_publication(registry, prepared)
    if tool_name == "analyze_cas9_mutation_outcomes":
        from .reference_edit_outcome_tools import _retain_reference_edit_outcome_publication
        return _retain_reference_edit_outcome_publication(registry, prepared)
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


def itc_parameter_fact_sources():
    """Describe literal parameter cells, without granting Files or fit authority."""
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string",
            "enum": [*values, None] if nullable else list(values)}
    def cell(unit):
        return obj(dict(state=enum(("present", "unavailable")), value={"type": ["number", "null"]},
            unit={"const": unit, "type": "string"}, reason=enum(REASONS, True)))
    fields = dict(version={"const": "itc_parameter_return_v1", "type": "string"},
        source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source"},
        parameter_source=enum(("fit_observation", "selected_parameters")),
        kd=cell("mol_per_litre"), n=cell("sites_per_macromolecule"), delta_h=cell("joule_per_mole"),
        cell_scope={"type": "string", "const": "retained_components_parameter_vector"},
        fit_call_state=enum(("not_started", "returned", "raised", "uncertain"), True),
        fit_call_count={"type": ["integer", "null"], "minimum": 0, "maximum": 1},
        fit_diagnostics_scope=enum((_ORIGINAL_FIT_SCOPE,), True),
        weighting=enum(("unweighted", "diagonal_sigma"), True),
        independent_error_assumption={"type": ["boolean", "null"]},
        absolute_sigma={"type": ["boolean", "null"]},
        fit_qualification_codes={"type": ["array", "null"], "items": enum(_FIT_QUALIFICATIONS)},
        prediction_qualification_codes={"type": ["array", "null"], "items": enum(_PREDICTION_QUALIFICATIONS)},
        calibration_authority={"type": "string", "const": "supplied_assertion"},
        n_meaning={"type": "string", "const": "effective_sites_per_declared_macromolecule"},
        identifiability={"type": "string", "const": "not_assessed"},
        statistical_covariance_validity={"type": "string", "const": "not_assessed"},
        warning_locations={"type": "array", "items": obj(dict(
            location_code={"type": "string", "const": "fit_warning"}, ordinal={"type": "integer", "minimum": 0}))},
        failure_location={**obj(dict(location_code={"type": "string", "const": "fit_failure"},
            ordinal={"type": "integer", "const": 0}, stage=enum(("input", "software", "fit", "serialization")))),
            "type": ["object", "null"]})
    return {ITC_PARAMETER_SOURCE: dict(type="array", meaning=(
        "Literal retained ITC parameter cells and original-fit qualifications; supplied calibration remains an assertion, "
        "and parameter identifiability and statistical covariance validity remain unassessed."),
        report_schema={"type": "array", "items": obj(fields), "x-source": ITC_PARAMETER_SOURCE})}


def validate_itc_parameter_return(value):
    """Validate closed public meaning only; this confers no source authority."""
    from jsonschema import Draft202012Validator
    import re
    value = copy_json(value)
    schema = itc_parameter_fact_sources()[ITC_PARAMETER_SOURCE]["report_schema"]["items"]
    if not Draft202012Validator(schema).is_valid(value):
        raise ContractError("itc_parameter_return_invalid")
    if re.fullmatch(r"source_[a-f0-9]{24,64}", value["source_ref"]) is None:
        raise ContractError("itc_parameter_return_source_invalid")
    for name in PARAMETERS:
        cell = value[name]
        if not ((cell["state"] == "present" and number(cell["value"]) and cell["reason"] is None)
                or (cell["state"] == "unavailable" and cell["value"] is None and cell["reason"] in REASONS)):
            raise ContractError("itc_parameter_return_cell_invalid")
    count = value["fit_call_count"]
    if (count is not None and type(count) is not int
            or (value["fit_call_state"], count) not in
                ((None, None), ("not_started", 0), ("returned", 1), ("raised", 1), ("uncertain", None))):
        raise ContractError("itc_parameter_return_call_conflict")
    if any(type(row["ordinal"]) is not int for row in value["warning_locations"]):
        raise ContractError("itc_parameter_return_location_invalid")
    failure = value["failure_location"]
    if failure is not None and type(failure["ordinal"]) is not int:
        raise ContractError("itc_parameter_return_location_invalid")
    return value


def project_itc_parameter_return(stored, *, source_ref):
    """Copy the retained parameter vector; do not calculate or read Files."""
    value = _validate_result(stored)
    components, observation = value["components"], value["sheet"]["fit_observation"]
    prediction = components["full_prediction"]
    weights = None if observation is None else observation["selection"]["weighting"]
    return validate_itc_parameter_return(dict(version="itc_parameter_return_v1", source_ref=source_ref,
        parameter_source=components["selection"]["parameter_source"],
        **{name: _cell(components["parameter_values"][name]) for name in PARAMETERS},
        cell_scope="retained_components_parameter_vector",
        fit_call_state=None if observation is None else observation["call_state"],
        fit_call_count=None if observation is None else observation["call_count"],
        fit_diagnostics_scope=None if components["fit_diagnostics"] is None else _ORIGINAL_FIT_SCOPE,
        weighting=None if weights is None else weights["kind"],
        independent_error_assumption=None if weights is None else weights["independent_error_assumption"],
        absolute_sigma=None if weights is None else weights["absolute_sigma"],
        fit_qualification_codes=None if observation is None else deepcopy(observation["qualifications"]),
        prediction_qualification_codes=None if prediction is None else deepcopy(prediction["qualifications"]),
        calibration_authority="supplied_assertion", n_meaning="effective_sites_per_declared_macromolecule",
        identifiability="not_assessed", statistical_covariance_validity="not_assessed",
        warning_locations=[] if observation is None else [dict(location_code="fit_warning", ordinal=i)
            for i in range(len(observation["warnings"]))],
        failure_location=None if observation is None or observation["failure"] is None else dict(
            location_code="fit_failure", ordinal=0, stage=observation["failure"]["stage"])))


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
