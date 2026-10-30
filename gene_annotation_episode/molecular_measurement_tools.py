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
    """Finite owner verdict for actual ITC publications; unrelated refs defer.

    Neither source identity nor Store membership grants its private execution
    control or an unreceived scientific File. This reads only matching metadata
    and receipts; it never loads a numerical sheet or calls another resolver.
    """
    if not isinstance(reference, str):
        return None
    if store.db.execute("SELECT 1 FROM tool_operations WHERE name=? "
            "AND json_extract(result,'$.feedback.diagnostic_ref')=? LIMIT 1", (ITC_TOOL, reference)).fetchone():
        return False  # Failed-attempt controls can also retain the private environment.
    rows = store.db.execute("""SELECT source.data FROM records source
        WHERE source.record_type='source' AND source.origin='tool'
        AND json_extract(source.data,'$.provider')=? AND json_extract(source.data,'$.version')=?
        AND (source.id=? OR json_extract(source.data,'$.artifact_ref')=?
            OR json_extract(source.data,'$.request_ref')=? OR EXISTS(
                SELECT 1 FROM json_each(source.data,'$.auxiliary_artifact_refs') artifact WHERE artifact.value=?))
        AND EXISTS(SELECT 1 FROM tool_operations operation, json_each(operation.result,'$.record_refs') published
            WHERE operation.name=? AND published.value=source.id
            AND json_extract(operation.result,'$.status') IN ('completed','partial'))""",
        (ITC_TOOL, RESULT_VERSION, reference, reference, reference, reference, ITC_TOOL))
    sources = [json.loads(row[0]) for row in rows]
    if not sources:
        return None
    if any(source.get('request_ref') == reference for source in sources):
        return False
    kind = 'source' if any(source['id'] == reference for source in sources) else 'artifact'
    if namespace not in (None, kind):
        return False
    from .episode_bindings import BindingContext
    from .episode_return_records import EpisodeReturnRecords
    from .episode_receipts import EpisodeReceipts
    if not isinstance(context, BindingContext):
        return False
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix='molecular_reference_').authenticate(context)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        return reference in set(receipts.known(context.episode_id))
    except (ValueError, TypeError, KeyError):
        return False


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
    if operation != "itc_binding" or directory != owned:
        raise ContractError("molecular_tool_owned_directory_conflict")
    request, output = owned / "worker-request.json", owned / "worker-result.json"
    handle_path, stdout, stderr = owned / "native-handle.json", owned / "stdout", owned / "stderr"
    payload = dict(operation=operation, arguments=arguments)
    selection_path = owned / "execution-selection.json"
    if selection_path.exists():
        selected = json.loads(selection_path.read_bytes())
        fields = {"version", "command", "cwd", "environment", "policy", "request", "python", "implementation_files"}
        if (type(selected) is not dict or set(selected) != fields
                or selected["version"] != "ordinary_molecular_execution_v1"
                or canonical(selected["request"]) != canonical(payload)
                or selected["cwd"] != str(owned) or type(selected["environment"]) is not dict
                or any(type(k) is not str or type(v) is not str for k, v in selected["environment"].items())
                or selected["command"] != [selected["python"]["path"], "-m",
                    "gene_annotation_episode.sequence_worker", str(request), str(output)]):
            raise ContractError("molecular_tool_execution_selection_conflict")
        # The reservation's original resource/argv/environment remain selected.
        # A different parent environment cannot reprice already launched work.
        selected_policy = LocalJobPolicy(**selected["policy"])
    else:
        if handle_path.exists() or request.exists() or output.exists():
            raise ContractError("molecular_tool_original_selection_missing")
        environment = dict(os.environ)
        package_root = str(Path(__file__).resolve().parent.parent)
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        implementation_files = [Path(__file__), Path(__file__).with_name("sequence_worker.py"),
            *(Path(__file__).with_name(name) for name in ("itc_binding_contracts.py", "itc_binding_measurements.py",
                "itc_binding_fit.py", "bivariate_covariance.py"))]
        selected = dict(version="ordinary_molecular_execution_v1",
            command=[sys.executable, "-m", "gene_annotation_episode.sequence_worker", str(request), str(output)],
            cwd=str(owned), environment=environment, policy=policy.to_dict(), request=payload,
            python=dict(path=sys.executable, sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()),
            implementation_files=[dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in implementation_files])
        selected_policy = policy
        atomic_json(selection_path, selected)

    def verify_unstarted_software():
        for file in [selected["python"], *selected["implementation_files"]]:
            try:
                matches = hashlib.sha256(Path(file["path"]).read_bytes()).hexdigest() == file["sha256"]
            except OSError:
                matches = False
            if not matches:
                raise ContractError("molecular_tool_original_software_changed_before_dispatch")

    try:
        if request.exists():
            if canonical(json.loads(request.read_bytes())) != canonical(payload):
                raise ContractError("molecular_tool_worker_request_conflict")
        else:
            if handle_path.exists():
                raise ContractError("molecular_tool_worker_request_missing")
            atomic_json(request, payload)
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
            # A prepared or unreleased handshake can still launch the original
            # command. Its original files must remain available before release.
            if not Path(handle.read()["paths"]["release"]).exists():
                verify_unstarted_software()
            resume_start(handle, cancel_event=cancel_event)
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


def read_retained_itc_result(registry, context, reader, source_ref):
    """Frozen values require the original ordinary publication, not shape alone."""
    item = _received(reader, context, source_ref, "source")
    source = item["witness"]["record"]
    value = _validate_result(item["content"]["value"])
    if source["provider"] != ITC_TOOL or source.get("version") != RESULT_VERSION:
        raise ContractError("ordinary_itc_producer_required")
    control = json.loads(registry.store.get_artifact(source["request_ref"]))
    if (type(control) is not dict or set(control) != {"version", "request", "native_artifact_ref",
            "execution_selection", "native_handle", "execution"}
            or control["version"] != "ordinary_itc_publication_v1"
            or control["native_artifact_ref"] != source["artifact_ref"]
            or canonical(_worker_request(control["request"])) != canonical(value["request"])):
        raise ContractError("ordinary_itc_publication_conflict")
    original = control["request"]["invocation"]
    witness = control["request"]["received_input"]["witness"]
    if ("operand_refs" in source or source.get("parent_source_refs") != (
            [witness["reference"]] if witness["namespace"] == "source" else [])):
        raise ContractError("ordinary_itc_publication_conflict")
    operation = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
        (original["operation_key"],)).fetchone()
    action = registry.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND decision_index=?", (original["run_id"], original["episode_id"], original["decision_index"])).fetchone()
    from .tool_grading_artifacts import source_tool_grading_entries
    entries = source_tool_grading_entries(registry.store, source_ref)
    grading = dict(sheet=value["sheet"], scores=value["components"])
    operation_result = None if operation is None else json.loads(operation["result"])
    action_result = None if action is None or action["result"] is None else json.loads(action["result"])
    if (operation is None or action is None or action["result"] is None or operation["name"] != ITC_TOOL
            or operation["arguments"] != canonical(value["request"]["arguments"])
            or source_ref not in operation_result.get("record_refs", [])
            or source_ref not in action_result.get("record_refs", [])
            or operation_result.get("status") not in ("completed", "partial")
            or action_result.get("operation_ref") != operation["id"]
            or operation["scope"] != canonical(original["scope"])
            or canonical(json.loads(action["action"])) != canonical(dict(kind="tool", tool=ITC_TOOL,
                arguments=value["request"]["arguments"])) or len(entries) != 1
            or canonical(entries[0]["grading"]) != canonical(grading)):
        raise ContractError("ordinary_itc_publication_conflict")
    return item, value, entries[0]["artifact_ref"]


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


def publish_itc_work(registry, arguments, prepared):
    if arguments["mode"] == "read_stored":
        projection = prepared["projection"]
        return projection, [projection["source_ref"], projection["native_file"]["artifact_ref"], projection["grading_ref"]]
    from .materials import artifact_file
    from .tool_grading_artifacts import retain_tool_grading
    work, stored, item = prepared["work"], prepared["stored"], prepared["item"]
    native = artifact_file(registry.store, work.output_path, "application/json")
    grading = retain_tool_grading(registry.store, provider=ITC_TOOL, native_artifact_ref=native,
        grading=dict(sheet=stored["sheet"], scores=stored["components"]))
    controls = registry.store.artifact(canonical(dict(version="ordinary_itc_publication_v1",
        request=prepared["request"], native_artifact_ref=native,
        execution_selection=json.loads((work.output_path.parent / "execution-selection.json").read_bytes()),
        native_handle=json.loads((work.output_path.parent / "native-handle.json").read_bytes()),
        execution=work.metadata)), "application/json")
    source = registry._put("source", dict(provider=ITC_TOOL, accession=None, uri=None,
        artifact_ref=native, text_ref=None, request_ref=controls, version=RESULT_VERSION,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[item["witness"]["reference"]] if item["witness"]["namespace"] == "source" else [],
        auxiliary_artifact_refs=[grading]), origin="tool")
    projection = project_itc_tool_result(stored, selection=arguments, source_ref=source["id"],
        artifact_ref=native, grading_ref=grading)
    return projection, [source["id"], native, grading]


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
    """Deduplicate an identical Source group; never overwrite conflicting facts."""
    result, seen = [], {}
    for group in groups:
        if type(group) is not list:
            raise ContractError("itc_parameter_facts_array_required")
        for item in group:
            value = validate_itc_parameter_return(item)
            reference, body = value["source_ref"], canonical(value)
            if reference in seen and seen[reference] != body:
                raise ContractError("itc_parameter_facts_source_conflict")
            if reference not in seen:
                result.append(value); seen[reference] = body
    return result


def requested_itc_parameter_fields(schema):
    """A requested group keeps the complete finite ParameterReturn meaning."""
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if not isinstance(properties, Mapping) or not any(isinstance(node, Mapping)
            and node.get("x-source") == ITC_PARAMETER_SOURCE for node in properties.values()):
        return []
    from .communication import plain, validate_closed_schema
    schema = validate_closed_schema(plain(schema))
    available = itc_parameter_fact_sources()[ITC_PARAMETER_SOURCE]["report_schema"]
    fields = []
    for name, node in schema["properties"].items():
        if node.get("x-source") == ITC_PARAMETER_SOURCE:
            if canonical(node) != canonical(available):
                raise ContractError("itc_parameter_requested_schema_conflict")
            fields.append(name)
    return fields


def validate_frozen_itc_parameter_return(form, schema, frozen):
    """Compare the literal frozen array, without reading its scientific Files."""
    from .communication import ReportBoundaryError, plain
    for name in requested_itc_parameter_fields(schema):
        actual = plain(form).get(name)
        try:
            if type(frozen) is not list or type(actual) is not list:
                raise ContractError("itc_parameter_frozen_source_unavailable")
            for item in [*actual, *frozen]:
                validate_itc_parameter_return(item)
            if canonical(actual) != canonical(frozen):
                raise ContractError("itc_parameter_frozen_source_mismatch")
        except ValueError as error:
            raise ReportBoundaryError("Return differs from the retained ITC parameter facts",
                code=str(error), field=name) from error


def own_itc_parameter_facts(registry, context, *, read_received):
    """Join actual selected actions and publications, then copy their saved cells."""
    from .communication import plain
    from .episode_return_records import EpisodeReturnRecords
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="itc_parameter_")
    records.authenticate(context)
    if context.role != "scientific_process":
        raise ContractError("itc_parameter_scientific_owner_required")
    result = []
    rows = registry.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND json_extract(action,'$.kind')='tool' AND json_extract(action,'$.tool')=? "
        "AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
        (context.run_id, context.episode_id, ITC_TOOL))
    for row in rows:
        action, actual = json.loads(row["action"]), json.loads(row["result"])
        key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
        operation = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        if (operation is None or operation["name"] != ITC_TOOL
                or operation["arguments"] != canonical(action["arguments"])
                or operation["scope"] != canonical(plain(context.scope))
                or operation["id"] != actual.get("operation_ref")
                or canonical({k: v for k, v in actual.items() if k != "pending_work_after_action"}) != operation["result"]):
            raise ContractError("itc_parameter_action_conflict")
        for reference in actual.get("record_refs", []):
            source = registry.store.get(reference)
            if source.get("record_type") != "source" or source.get("provider") != ITC_TOOL:
                continue
            item, stored, grading = read_retained_itc_result(registry, context, read_received, reference)
            required = (reference, item["file"]["artifact_ref"], grading)
            if not all(ref in actual["record_refs"] for ref in required):
                raise ContractError("itc_parameter_action_files_conflict")
            arguments = action["arguments"]
            if arguments["mode"] == "read_stored":
                if arguments["result_ref"] != reference:
                    raise ContractError("itc_parameter_action_source_conflict")
            else:
                control = json.loads(registry.store.get_artifact(source["request_ref"]))
                if control["request"]["invocation"]["operation_key"] != key:
                    raise ContractError("itc_parameter_action_source_conflict")
            result.append(project_itc_parameter_return(stored, source_ref=reference))
    return merge_itc_parameter_facts(result)


def frozen_itc_parameter_facts(store, run_id, context):
    """Read this episode's frozen array literally; absence remains unknown."""
    from .episode_return_records import EpisodeReturnRecords
    EpisodeReturnRecords(store, run_id, failure_prefix="itc_parameter_").authenticate(context)
    row = store.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (run_id, context.episode_id)).fetchone()
    if row is None:
        return None
    facts = json.loads(row["facts"])
    if ITC_PARAMETER_SOURCE not in facts:
        return None
    values = facts[ITC_PARAMETER_SOURCE]
    if type(values) is not list:
        raise ContractError("itc_parameter_frozen_source_invalid")
    for value in values:
        validate_itc_parameter_return(value)
    return deepcopy(values)


def received_itc_parameter_facts(store, run_id, context):
    """Consume actual admitted child forms and frozen ancestor report prefixes."""
    from .episode_receipts import EpisodeReceipts
    from .episode_return_records import EpisodeReturnRecords
    from .execution_contracts import digest
    records = EpisodeReturnRecords(store, run_id, failure_prefix="itc_parameter_")
    records.authenticate(context)
    groups, current, prefix, seen = [], context, None, set()
    while True:
        if current.episode_id in seen:
            raise ContractError("itc_parameter_receipt_lineage_cycle")
        seen.add(current.episode_id)
        if prefix is None:
            attempts = [dict(row) for row in store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,"
                "contract,form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                "AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index", (run_id, current.episode_id))]
        else:
            attempts = []
            for frozen in prefix["attempts"]:
                row = store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,contract,form,failure "
                    "FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                    (run_id, current.episode_id, frozen["decision_index"])).fetchone()
                if (row is None or row["failure"] is not None or row["form"] is None
                        or any(row[name] != frozen[name] for name in ("delivery_ref", "child_episode_id"))
                        or digest(json.loads(row["contract"])) != frozen["contract_sha256"]
                        or digest(json.loads(row["form"])) != frozen["form_sha256"]):
                    raise ContractError("itc_parameter_received_prefix_conflict")
                attempts.append(dict(row))
        for attempt in attempts:
            schema = json.loads(attempt["contract"])["measurements"]["schema"]
            fields = requested_itc_parameter_fields(schema)
            if not fields:
                continue
            _, form, authenticated_schema = records._attempt(current, attempt["decision_index"])
            if canonical(schema) != canonical(authenticated_schema):
                raise ContractError("itc_parameter_received_schema_conflict")
            for name in fields:
                group = form[name]
                if type(group) is not list:
                    raise ContractError("itc_parameter_received_array_required")
                for value in group:
                    validate_itc_parameter_return(value)
                    if itc_reference_access(store, context, value["source_ref"], "source") is not True:
                        raise ContractError("itc_parameter_received_source_not_granted")
                groups.append(group)
        manifest = EpisodeReceipts.read_manifest(store.db, run_id, current.episode_id)
        parent = manifest["parent_episode_id"]
        if parent is None:
            break
        if "received_report_prefix" not in manifest:
            raise ContractError("itc_parameter_received_prefix_unavailable")
        prefix = manifest["received_report_prefix"]
        parent_context = records.context(parent)
        if current.path[:-1] != parent_context.path:
            raise ContractError("itc_parameter_received_lineage_conflict")
        current = parent_context
    return merge_itc_parameter_facts(*groups)
