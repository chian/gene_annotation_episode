"""Ordinary selected FBA tools, with actual action and retained-file custody.

Fixed native operations use the existing producer and finite result worker.
This host authenticates decisions and publishes their controlled results; it
does not choose reactions, annotations, resources, solver settings or retries.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path

from .communication import plain
from .acquisition import AcquisitionError
from .domain import ContractError, identity, obj
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_contracts import flux_balance_schema, validate_flux_balance_record
from .flux_balance_model_tools import (flux_balance_model_schema,
    project_flux_balance_model_result, validate_flux_balance_model_result)
from .flux_balance_operands import bind_flux_balance_job_inputs, freeze_flux_balance_input_binding
from .flux_balance_ordinary import (SELECTION_VERSION, compile_flux_balance_requested_job,
    run_selected_flux_balance_native, run_selected_flux_balance_result_worker)
from .flux_balance_request_binding import _file_schema, _files, scientific_request_schema
from .flux_balance_result_contracts import (fba_result_schema, validate_fba_projection,
    validate_fba_saved_sheet_reference)
from .flux_balance_result_receipts import public_issue, qualified_files
from .flux_balance_result_views import project_fba_result
from .flux_balance_worker_contracts import (build_native_flux_balance_worker_plan,
    build_saved_flux_balance_worker_plan)
from .genomic_overlap_result_receipts import immutable, read_control
from .local_jobs import LocalJobPolicy, run_cancellable_native
from .native_file_capture import _metadata, capture_native_file, retained_native_file
from .native_flux_balance_bindings import validate_flux_balance_bindings
from .native_flux_balance_capture import capture_flux_balance_native_files
from .native_flux_balance_contracts import POLICY, path_value
from .native_flux_balance_preparation import validate_prepared_flux_balance_worker
from .native_flux_balance_storage import decode_json
from .molecular_measurement_tools import MolecularOperationUnpublished
from .waiting import validate_pending


FBA_TOOL = "perform_flux_balance_analysis"
RESULT_VERSION = "ordinary_flux_balance_result_v1"
CAPSULE_VERSION = "ordinary_flux_balance_capsule_v1"
ARGUMENT_VERSION = "ordinary_flux_balance_arguments_v1"
ENVIRONMENT_SELECTION = {"version": "flux_balance_execution_selection_v1",
    "environment_realization": "operation_scoped_tmp_and_cache_v1"}
_FACT_FIELDS = {"flux_balance_measurements": "measurements",
    "flux_balance_model_views": "model_views", "flux_balance_saved_sheets": "saved_sheets",
    "flux_balance_edited_models": "edited_models", "flux_balance_failures": "failures"}


def _require(condition, code):
    if not condition:
        raise ContractError("ordinary_fba_" + code)


def normalize_flux_balance_configuration(resources, environments, policy):
    _require(isinstance(environments, (list, tuple)), "environment_table_required")
    if not environments:
        return None
    resources, environments = plain(resources), plain(environments)
    _require(type(resources) is dict and type(environments) is list, "configuration_invalid")
    _require(policy.to_dict() == POLICY, "allocation_conflict")
    rows, seen = [], set()
    for entry in environments:
        _require(type(entry) is dict and set(entry) == {"resource_id", "binding_ordinal_0based", "environment"},
            "environment_record_invalid")
        name, ordinal = entry["resource_id"], entry["binding_ordinal_0based"]
        _require(type(name) is str and bool(name) and type(ordinal) is int and ordinal >= 0, "binding_invalid")
        _require((name, ordinal) not in seen, "binding_duplicate")
        seen.add((name, ordinal))
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get("kind") == "local", "local_resource_required")
        _require(canonical(resource.get("policy")) == canonical(POLICY)
            and canonical(entry["environment"]) == canonical(ENVIRONMENT_SELECTION),
            "environment_or_allocation_conflict")
        path_value(resource["workspace"], absolute=True)
        bindings = validate_flux_balance_bindings(resource.get("native_flux_balance"))
        _require(ordinal < len(bindings), "binding_invalid")
        rows.append({"resource_id": name, "binding_ordinal_0based": ordinal,
            "binding": bindings[ordinal], "workspace": resource["workspace"],
            "environment": entry["environment"]})
    return json.loads(canonical({"version": "ordinary_flux_balance_configuration_v1", "policy": POLICY,
        "bindings": sorted(rows, key=lambda row: (row["resource_id"], row["binding_ordinal_0based"]))}))


def flux_balance_tool_catalog(configuration):
    if configuration is None:
        return {}
    projection = fba_result_schema("FBAProjectionSelector")
    parameters = flux_balance_schema("FBACalculationParameters")
    variants = []
    for mode in ("inspect", "edit", "solve", "read_stored", "calculate_saved"):
        fields = {"version": {"const": ARGUMENT_VERSION}, "mode": {"const": mode}}
        if mode != "read_stored":
            fields.update(resource_id={"type": "string"}, binding_ordinal_0based={"type": "integer", "minimum": 0})
        if mode in {"inspect", "edit"}:
            model = _file_schema()
            model["properties"]["format"] = {"enum": ["sbml", "cobra_json"]}
            fields.update(model=model, edits={"type": "null"} if mode == "inspect" else flux_balance_model_schema("Edits"),
                view=flux_balance_model_schema("ViewSelector"), return_edited_model={"const": False} if mode == "inspect" else {"type": "boolean"})
        elif mode == "solve":
            fields.update(request=scientific_request_schema(), calculation_parameters=parameters,
                projection=projection, return_saved_sheet={"type": "boolean"})
        elif mode == "calculate_saved":
            fields.update(sheet=_file_schema(), calculation_parameters=parameters,
                projection=projection, return_saved_sheet={"type": "boolean"})
        else:
            fields.update(result_ref={"type": "string", "format": "reference"},
                view={"oneOf": [obj({"kind": {"const": "model"}, "selector": flux_balance_model_schema("ViewSelector")}),
                    obj({"kind": {"const": "measurement"}, "selector": projection})]})
        branch = obj(fields)
        if mode != "read_stored":
            branch["allOf"] = [{"anyOf": [{"properties": {
                "resource_id": {"const": row["resource_id"]},
                "binding_ordinal_0based": {"const": row["binding_ordinal_0based"]}}}
                for row in configuration["bindings"]]}]
        variants.append(branch)
    choices = "\n".join(["| Resource | Binding ordinal (zero-based) | Solver | Model formats |",
        "| --- | --- | --- | --- |", *("| " + " | ".join((row["resource_id"].replace("|", "\\|"),
            str(row["binding_ordinal_0based"]), row["binding"]["software"]["solver_interface"],
            ", ".join(row["binding"]["model_formats"]))) + " |" for row in configuration["bindings"])])
    schema = {"oneOf": variants}
    schema["$id"] = "urn:gene-annotation:ordinary-fba-tool:" + digest(schema)
    return {FBA_TOOL: {"description": "Inspect or explicitly edit a supplied metabolic model, solve its selected steady-state linear FBA objective, or read/recalculate retained results.",
        "instructions": "Answer the parent's assigned scientific question. Use the supplied model and the explicitly selected software, reaction bounds, objective and solver settings. Growth uses the declared growth objective; reaction fluxes retain the selected reaction identities. Reaction additions require supplied stoichiometry and compartments. Setting a reaction's bounds to zero tests that reaction perturbation. Annotation-to-reaction mappings are supplied evidence; preserve their references and assumptions. Inspect/edit performs no optimization. Preserve original bytes, native units, missing values and partial results. Read stored values without a new solve; calculate a saved sheet only when explicitly selected. Return the requested controlled measurements, model views and selected Files.\n\nConfigured software choices\n\n" + choices,
        "resources": "local", "invocation_route": {"kind": "direct"}, "input_schema": schema,
        "configuration": {"job_limits": configuration["policy"], "bindings": [{
            "resource_id": row["resource_id"], "binding_ordinal_0based": row["binding_ordinal_0based"],
            "solver": row["binding"]["software"]["solver_interface"], "model_formats": row["binding"]["model_formats"]}
            for row in configuration["bindings"]]}}}


def _read_file(store, file):
    file = validate_flux_balance_record("File", file)
    return decode_json(retained_native_file(store, file).read_bytes())


def _artifact(store, value, format_):
    raw = canonical(value).encode()
    reference = store.artifact(raw, "application/json")
    return {"artifact_ref": reference, "sha256": reference[9:], "size_bytes": len(raw), "format": format_}


def _owned_output_references(store, prepared, public):
    """Index finite retained output/control ports, never caller input Files."""
    excluded = {row["file"]["artifact_ref"] for row in prepared["resolved_inputs"]}
    references = []

    def reference(value):
        if value is not None:
            _metadata(store, value)
            references.append(value)

    def file(value):
        if value is not None:
            value = validate_flux_balance_record("File", value)
            metadata = _metadata(store, value["artifact_ref"])
            _require(metadata["sha256"] == value["sha256"] and metadata["size"] == value["size_bytes"],
                "owned_output_identity_conflict")
            references.append(value["artifact_ref"])

    capture = prepared.get("capture")
    if capture is not None:
        excluded.update(row["file"]["artifact_ref"] for row in capture["prior_sources"])
        for row in capture["files"]:
            if row["role"] == "original_model":
                if row["retained"] is not None:
                    excluded.add(row["retained"]["file"]["artifact_ref"])
            elif row["role"] in {"selected_request", "effective_model", "effective_problem", "solution", "flux_csv", "native_log", "manifest"}:
                file(None if row["retained"] is None else row["retained"]["file"])
        for role in ("owner", "started", "environment"):
            row = capture["controls"][role]
            file(None if row is None else row["file"])
        for key in ("source_action_receipt_ref", "writer_closure_receipt_ref"):
            reference(capture[key])
        file(capture["input_binding_file"])
    worker = prepared["worker"]
    if worker is not None:
        for key in ("plan_file", "execution_receipt_file", "worker_result_file"):
            file(worker["capture"][key])
        for row in worker["capture"]["outputs"]:
            file(row["observed"])
        for role in ("sheet", "calculations", "projection", "diagnostics"):
            file(worker["files"][role])
        for key in ("handle_file", "request_file", "stdout_file", "stderr_file"):
            file(worker["execution"][key])
    for value in public["edited_models"]:
        file(value)
    return list(dict.fromkeys(ref for ref in references if ref not in excluded))


@asynccontextmanager
async def _action_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root / ".action.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    task = asyncio.create_task(asyncio.to_thread(fcntl.flock, descriptor, fcntl.LOCK_EX))
    acquired = False
    try:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    pass
            task.result()
            acquired = True
            raise
        acquired = True
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class OrdinaryFluxBalanceTools:
    def __init__(self, registry):
        self.registry, self.store = registry, registry.store

    def retained_reference_access(self, context, reference, namespace):
        from .molecular_reference_privacy import molecular_reference_restriction
        return molecular_reference_restriction(self.store, context, reference, namespace, providers=(FBA_TOOL,))

    def _selection(self, arguments):
        config = self.registry._flux_balance_configuration
        _require(config is not None, "configuration_required")
        found = [row for row in config["bindings"] if row["resource_id"] == arguments["resource_id"]
            and row["binding_ordinal_0based"] == arguments["binding_ordinal_0based"]]
        _require(len(found) == 1, "binding_invalid")
        return deepcopy(found[0])

    def _invocation(self, context, operation_key):
        return {"run_id": context.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "decision_index": int(operation_key.rsplit(":", 1)[1]), "request_sha256": digest(plain(context.request)),
            "scope": plain(context.scope)}

    def _resolve(self, context, reader, selection):
        reference = selection["witness_ref"]
        if selection["artifact_field"] is None:
            namespace, artifact = "artifact", reference
            record = self.store.get(reference)
        else:
            namespace = "source"
            result = reader(context, reference, namespace, source_metadata_only=True)
            _require(result["failure"] is None, "selected_source_not_received")
            record = result["input"]["witness"]["record"]
            artifact = record.get(selection["artifact_field"])
        _require(selection["version"] is None or str(record.get("revision")) == selection["version"], "input_version_conflict")
        result, path = reader(context, artifact, "artifact", file_format=selection["format"])
        _require(result["failure"] is None and path is not None, "selected_file_not_received")
        return {"selection": deepcopy(selection), "file": result["input"]["file"], "path": str(path),
            "witness": {"reference": reference, "namespace": namespace, "record": record}}

    async def _worker(self, plan, software):
        from .state import Store
        path, policy = self.store.path, self.registry.local_job_policy
        def run():
            with Store(path) as store:
                return run_selected_flux_balance_result_worker(store, plan=plan, software=software, policy=policy)
        task = asyncio.create_task(asyncio.to_thread(run))
        try:
            capture = await asyncio.shield(task)
        except AcquisitionError as error:
            from . import native_lifecycle as native
            handle = native.NativeJobHandle(Path(plan["directory"] + ".execution") / "worker.handle.json")
            if handle.path.exists():
                try:
                    view = native.status(handle)
                except AcquisitionError as unknown:
                    raise MolecularOperationUnpublished("ordinary_fba_result_worker_attempt_unconfirmed") from unknown
                if not (view["terminal"] and view["quiescent"]):
                    raise MolecularOperationUnpublished("ordinary_fba_result_worker_attempt_unconfirmed") from error
            raise
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    pass
                except BaseException:
                    break
            if not task.cancelled():
                task.exception()
            raise
        capture = validate_prepared_flux_balance_worker(self.store, capture, plan=plan)
        execution = _read_file(self.store, capture["execution_receipt_file"])
        files = qualified_files(capture, execution)
        return {"plan": plan, "capture": capture, "execution": execution, "files": files,
            "sheet": _read_file(self.store, files["sheet"]) if files["sheet"] else None,
            "calculations": _read_file(self.store, files["calculations"]) if files["calculations"] else None,
            "projection": validate_fba_projection(_read_file(self.store, files["projection"])) if files["projection"] else None}

    async def prepare(self, arguments, *, scope, operation_key, authority):
        context, reader = authority
        invocation = self._invocation(context, operation_key)
        mode = arguments["mode"]
        if mode == "read_stored":
            capsule, source = self.read_publication(context, arguments["result_ref"], reader=reader)
            return {"arguments": arguments, "invocation": invocation, "original": capsule,
                "source": source, "stored_read": True}
        selected = self._selection(arguments)
        root = self.store.path / "cache" / "ordinary-fba" / digest(operation_key)
        _require(not self.store.db.in_transaction, "native_work_requires_no_transaction")
        async with _action_lock(root):
            control = {"version": "ordinary_flux_balance_action_v1", "invocation": invocation,
                "arguments": arguments, "selected": selected}
            immutable(root / "selection.json", control)
            prior = read_control(root / "prepared.json")
            if prior is not None:
                _require(prior["control"] == control, "prepared_control_conflict")
                return prior
            prepared = {"control": control, "arguments": arguments, "invocation": invocation,
                "selected": selected, "resolved_inputs": [], "model": None, "native": None,
                "worker": None, "stored_read": False}
            if mode in {"inspect", "edit"}:
                item = self._resolve(context, reader, arguments["model"])
                _require(item["file"]["format"] in selected["binding"]["model_formats"], "model_format_not_bound")
                prepared["resolved_inputs"].append(item)
                if mode == "edit":
                    refs = [ref for key in ("add_metabolites", "add_reactions", "bounds")
                        for row in arguments["edits"][key] for ref in row["source_refs"]]
                    refs += arguments["edits"]["objective"].get("source_refs", [])
                    for ref in dict.fromkeys(refs):
                        received = reader(context, ref, "source", source_metadata_only=True)
                        _require(received["failure"] is None, "edit_source_not_received")
                from .flux_balance_model_execution import run_selected_flux_balance_model
                request = {"version": "flux_balance_model_request_v1", "mode": mode,
                    "model_file": item["file"], "edits": arguments["edits"]}
                prepared["model"] = await run_cancellable_native(run_selected_flux_balance_model, request,
                    model_path=item["path"], root=root / "model", software=selected["binding"]["software"],
                    policy=self.registry.local_job_policy)
            elif mode == "solve":
                resolved = [self._resolve(context, reader, choice) for choice in _files(arguments["request"])]
                prepared["resolved_inputs"] = resolved
                job = compile_flux_balance_requested_job(arguments["request"], binding=selected["binding"],
                    resolved_files=[{key: row[key] for key in ("selection", "file", "path")} for row in resolved],
                    lifecycle_directory=str(root / "runtime"))
                compiled = {"version": SELECTION_VERSION, "mode": "solve", "resource_id": selected["resource_id"],
                    "resource_kind": "local", "binding_ordinal_0based": selected["binding_ordinal_0based"],
                    "workspace": selected["workspace"], "requested_job": job,
                    "constraints": {"allocation": POLICY}, "native_flux_balance_execution": selected["environment"]}
                allowed = {(row["witness"]["reference"], row["witness"]["namespace"]) for row in resolved}
                allowed.update((row["file"]["artifact_ref"], "artifact") for row in resolved)
                versions = list({row["selection"]["witness_ref"]: {"reference": row["selection"]["witness_ref"],
                    "version": row["selection"]["version"], "content_sha256": None} for row in resolved}.values())
                bound = bind_flux_balance_job_inputs(self.store, context, compiled, input_versions=versions,
                    reference_access=lambda current, ref, namespace: (ref, namespace) in allowed)
                receipt = freeze_flux_balance_input_binding(self.store, binding=bound)
                input_file = _artifact(self.store, receipt, "flux_balance_input_binding_receipt_v1")
                immutable(root / "input-binding.json", receipt)
                native_root = Path(selected["workspace"]) / ".episode-operations" / digest({
                    "run": context.run_id, "episode": context.episode_id}) / digest(operation_key)
                native = await run_cancellable_native(run_selected_flux_balance_native, compiled, operation_key,
                    run_id=context.run_id, episode_id=context.episode_id, root=native_root,
                    policy=self.registry.local_job_policy, input_binding_receipt=receipt, input_binding_file=input_file)
                prepared["native"] = native
                action = self.store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                    (context.run_id, context.episode_id, invocation["decision_index"])).fetchone()
                source_action = _artifact(self.store, {"version": "ordinary_flux_balance_source_action_v1",
                    "invocation": invocation, "selected_action": json.loads(action["action"])}, "ordinary_flux_balance_source_action_v1")
                closure = _artifact(self.store, {"version": "ordinary_flux_balance_writer_closure_v1",
                    "invocation": invocation, "native": native}, "ordinary_flux_balance_writer_closure_v1")
                capture = capture_flux_balance_native_files(self.store, original_plan=native["plan"],
                    source_action_receipt_ref=source_action["artifact_ref"], writer_closure_receipt_ref=closure["artifact_ref"],
                    input_binding_file=input_file, prior_sources=[{"file": row["file"], "path": row["path"]}
                        for row in bound["prior_sources"]], driver_started=native["driver_started"])
                prepared["capture"] = capture
                selector = {"version": "flux_balance_result_selector_v1", "mode": "native_result",
                    "saved_sheet_file": None,
                    "calculation_parameters": arguments["calculation_parameters"], "projection": arguments["projection"]}
                prepared["worker"] = await self._worker(build_native_flux_balance_worker_plan(
                    directory=str(self.store.path / "cache" / "ordinary-fba-result-workers" / digest(operation_key) / "output"),
                    original_plan=native["plan"], capture=capture, selector=selector),
                    selected["binding"]["software"])
            else:
                _require(mode == "calculate_saved", "mode_invalid")
                item = self._resolve(context, reader, arguments["sheet"])
                file = validate_fba_saved_sheet_reference(item["file"])
                prepared["resolved_inputs"].append(item)
                selector = {"version": "flux_balance_result_selector_v1", "mode": "saved_sheet_recalculation",
                    "saved_sheet_file": file, "calculation_parameters": arguments["calculation_parameters"],
                    "projection": arguments["projection"]}
                prepared["worker"] = await self._worker(build_saved_flux_balance_worker_plan(
                    directory=str(self.store.path / "cache" / "ordinary-fba-result-workers" / digest(operation_key) / "output"),
                    sheet={"file": file, "path": item["path"]}, selector=selector),
                    selected["binding"]["software"])
            immutable(root / "prepared.json", prepared)
            return prepared

    def publish(self, prepared):
        arguments = prepared["arguments"]
        public = {"version": RESULT_VERSION, "mode": arguments["mode"], "source_ref": None,
            "measurements": [], "model_views": [], "saved_sheets": [], "edited_models": [], "failures": []}
        if prepared["stored_read"]:
            capsule, source = prepared["original"], prepared["source"]
            view = arguments["view"]
            if view["kind"] == "model":
                _require(capsule["model_result"] is not None, "stored_model_unavailable")
                public["model_views"] = [project_flux_balance_model_result(capsule["model_result"], selector=view["selector"])]
            else:
                _require(capsule["sheet"] is not None and capsule["calculations"] is not None, "stored_measurements_unavailable")
                public["measurements"] = [validate_fba_projection(project_fba_result(capsule["sheet"],
                    capsule["calculations"], selector=view["selector"]))]
            public["source_ref"] = source["id"]
            return public, [source["id"]]
        model, worker = prepared["model"], prepared["worker"]
        model_result = None if model is None else model["result"]
        if model_result is not None:
            validate_flux_balance_model_result(model_result)
            public["failures"] = [public_issue(row) for row in model_result["issues"]]
            try:
                public["model_views"] = [project_flux_balance_model_result(model_result, selector=arguments["view"])]
            except ValueError:
                public["failures"].append({"code": "projection_invalid", "stage": "project", "field": "/view",
                    **{key: None for key in ("source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")}})
            if arguments["mode"] == "edit" and arguments["return_edited_model"] and model_result["edited_model"]:
                declaration = model_result["edited_model"]
                file = capture_native_file(self.store, directory=str(Path(model["output_path"]).parent / "model-output"),
                    relative_path=declaration["relative_path"], format=declaration["file"]["format"])
                _require(file == declaration["file"], "edited_model_identity_conflict")
                public["edited_models"] = [file]
        if worker is not None:
            if worker["projection"] is not None:
                public["measurements"] = [worker["projection"]]
            failures = list(worker["capture"]["failures"])
            if worker["capture"]["result"] is not None:
                failures.extend(worker["capture"]["result"]["failures"])
            public["failures"].extend(public_issue(row) for row in failures)
            if arguments["return_saved_sheet"] and worker["files"]["sheet"] is not None:
                public["saved_sheets"] = [worker["files"]["sheet"]]
        if model is not None and model_result is None:
            public["failures"].append({"code": "binding_unavailable", "stage": "capture", "field": "/model_worker",
                **{key: None for key in ("source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")}})
        packet = {key: value for key, value in public.items() if key != "source_ref"}
        packet_file = _artifact(self.store, packet, "ordinary_flux_balance_public_packet_v1")
        capsule = {"version": CAPSULE_VERSION, "prepared": prepared, "public_packet": packet_file,
            "model_result": model_result, "sheet": None if worker is None else worker["sheet"],
            "calculations": None if worker is None else worker["calculations"]}
        capsule_file = _artifact(self.store, capsule, CAPSULE_VERSION)
        parents = [row["witness"]["reference"] for row in prepared["resolved_inputs"] if row["witness"]["namespace"] == "source"]
        if arguments["mode"] == "edit":
            parents.extend(ref for key in ("add_metabolites", "add_reactions", "bounds")
                for row in arguments["edits"][key] for ref in row["source_refs"])
            parents.extend(arguments["edits"]["objective"].get("source_refs", []))
        source = self.registry._put("source", {"provider": FBA_TOOL, "accession": None, "uri": None,
            "artifact_ref": packet_file["artifact_ref"], "text_ref": None, "request_ref": capsule_file["artifact_ref"],
            "version": RESULT_VERSION, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "parent_source_refs": list(dict.fromkeys(parents)),
            "auxiliary_artifact_refs": _owned_output_references(self.store, prepared, public)}, origin="tool")
        public["source_ref"] = source["id"]
        references = [source["id"], *(file["artifact_ref"] for key in ("saved_sheets", "edited_models") for file in public[key])]
        return public, list(dict.fromkeys(references))

    def _operation(self, context, key, *, pending=False):
        prefix = f"{context.run_id}:{context.episode_id}:"
        suffix = key[len(prefix):] if isinstance(key, str) and key.startswith(prefix) else ""
        _require(suffix.isdecimal() and str(int(suffix)) == suffix, "operation_identity_conflict")
        records = EpisodeReturnRecords(self.store, context.run_id, failure_prefix="ordinary_fba_")
        records.authenticate(context)
        action = self.store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (context.run_id, context.episode_id, int(suffix))).fetchone()
        operation = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        _require(action is not None and operation is not None and operation["name"] == FBA_TOOL
            and operation["scope"] == canonical(plain(context.scope)), "operation_identity_conflict")
        arguments, outcome = json.loads(operation["arguments"]), json.loads(operation["result"])
        _require(operation["id"] == identity("operation", {"key": key, "name": FBA_TOOL, "arguments": arguments}),
            "operation_identity_conflict")
        _require(canonical(json.loads(action["action"])) == canonical({"kind": "tool", "tool": FBA_TOOL, "arguments": arguments}),
            "selected_action_conflict")
        _require(operation["id"] == outcome.get("operation_ref"), "operation_identity_conflict")
        if outcome.get("status") in {"completed", "partial"} and isinstance(outcome.get("result"), dict):
            _require(outcome["result"].get("source_ref") in outcome.get("record_refs", []), "published_source_required")
        if action["result"] is None:
            _require(pending, "completed_action_required")
        else:
            actual = json.loads(action["result"])
            if "pending_work_after_action" in actual:
                validate_pending(actual.pop("pending_work_after_action"))
            _require(canonical(actual) == canonical(outcome),
                "operation_outcome_conflict")
        return operation, arguments, outcome

    def _source(self, reference):
        source = self.store.get(reference)
        _require(source.get("record_type") == "source" and source.get("origin") == "tool"
            and source.get("provider") == FBA_TOOL and source.get("version") == RESULT_VERSION, "source_invalid")
        payload = {k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}}
        _require(identity("source", {"origin": "tool", "record": payload}) == reference, "source_identity_conflict")
        return source

    def read_publication(self, context, reference, *, reader=None, pending_operation_key=None):
        if reader is not None:
            received = reader(context, reference, "source", source_metadata_only=True)
            _require(received["failure"] is None, "result_source_not_received")
        source = self._source(reference)
        tables = {row[0] for row in self.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        _require({"runtime_actions", "runtime_episodes", "tool_operations"} <= tables, "publication_owner_required")
        rows = self.store.db.execute("""SELECT operation.operation_key,
            action.run_id, action.episode_id FROM tool_operations operation
            JOIN runtime_actions action ON operation.operation_key =
                action.run_id || ':' || action.episode_id || ':' || action.decision_index
            WHERE operation.name=? AND json_extract(operation.arguments,'$.mode')!='read_stored'
              AND json_extract(operation.result,'$.result.source_ref')=?
              AND json_extract(operation.result,'$.status') IN ('completed','partial')""",
            (FBA_TOOL, reference)).fetchall()
        _require(len(rows) == 1, "publication_owner_required")
        owner = rows[0]
        records = EpisodeReturnRecords(self.store, owner["run_id"], failure_prefix="ordinary_fba_")
        producer = records.context(owner["episode_id"])
        operation, arguments, outcome = self._operation(producer, owner["operation_key"], pending=(
            owner["operation_key"] == pending_operation_key and producer.run_id == context.run_id
            and producer.episode_id == context.episode_id))
        self.store.validate_scope(plain(producer.scope), parent_scope=plain(context.scope))
        raw = self.store.get_artifact(source["request_ref"])
        _require(source["request_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest(), "capsule_identity_conflict")
        capsule = decode_json(raw)
        _require(type(capsule) is dict and capsule.get("version") == CAPSULE_VERSION, "capsule_invalid")
        invocation = capsule["prepared"]["invocation"]
        _require(invocation == self._invocation(producer, owner["operation_key"])
            and canonical(arguments) == canonical(capsule["prepared"]["arguments"]) and outcome["result"]["source_ref"] == reference,
            "publication_identity_conflict")
        packet = _read_file(self.store, capsule["public_packet"])
        _require(source["artifact_ref"] == capsule["public_packet"]["artifact_ref"]
            and canonical(packet) == canonical({k: v for k, v in outcome["result"].items() if k != "source_ref"}), "public_packet_conflict")
        self.store.validate_scope(invocation["scope"], parent_scope=plain(context.scope))
        return capsule, source

    def _fact_record(self, context, key, *, verify_artifacts, pending=False):
        from .flux_balance_return_views import fba_fact_sources, validate_fba_fact_values
        operation, arguments, outcome = self._operation(context, key, pending=pending)
        if outcome.get("status") not in {"completed", "partial"} or not isinstance(outcome.get("result"), dict):
            return None
        result = outcome["result"]
        if result.get("version") != RESULT_VERSION:
            return None
        _require(set(result) == {"version", "mode", "source_ref", *_FACT_FIELDS.values()}
            and result["mode"] == arguments["mode"], "public_result_invalid")
        source = self._source(result["source_ref"])
        if verify_artifacts:
            capsule, _ = self.read_publication(context, source["id"], pending_operation_key=key if pending else None)
            if arguments["mode"] == "read_stored":
                _require(arguments["result_ref"] == source["id"], "stored_source_conflict")
                view = arguments["view"]
                expected = {field: [] for field in _FACT_FIELDS.values()}
                if view["kind"] == "model":
                    _require(capsule["model_result"] is not None, "stored_model_unavailable")
                    expected["model_views"] = [project_flux_balance_model_result(capsule["model_result"], selector=view["selector"])]
                else:
                    _require(capsule["sheet"] is not None and capsule["calculations"] is not None, "stored_measurements_unavailable")
                    expected["measurements"] = [validate_fba_projection(project_fba_result(capsule["sheet"],
                        capsule["calculations"], selector=view["selector"]))]
                _require(canonical({field: result[field] for field in expected}) == canonical(expected), "stored_view_conflict")
            else:
                _require(capsule["prepared"]["invocation"]["operation_key"] == key, "producer_operation_conflict")
            for field in ("saved_sheets", "edited_models"):
                for file in result[field]:
                    retained_native_file(self.store, file)
        groups = {name: validate_fba_fact_values(name, result[_FACT_FIELDS[name]]) for name in fba_fact_sources()}
        return {"witness": {"version": "ordinary_flux_balance_fact_witness_v1", "operation_key": key,
            "operation_ref": operation["id"], "result_sha256": digest(outcome), "source_ref": source["id"]}, "facts": groups}

    def own_fact_records(self, context, *, sources, verify_artifacts=True):
        if context.role != "scientific_process":
            return []
        keys = [row[0] for row in self.store.db.execute("""SELECT operation.operation_key
            FROM tool_operations operation JOIN runtime_actions action ON operation.operation_key =
                action.run_id || ':' || action.episode_id || ':' || action.decision_index
            WHERE operation.name=? AND action.run_id=? AND action.episode_id=? ORDER BY action.decision_index""",
            (FBA_TOOL, context.run_id, context.episode_id))]
        result = []
        for key in sorted(keys, key=lambda key: int(key.rsplit(":", 1)[1])):
            row = self._fact_record(context, key, verify_artifacts=verify_artifacts)
            if row is not None:
                row["facts"] = {name: row["facts"][name] for name in sources}
                result.append(row)
        return result

    def authenticate_saved_operation(self, context, *, operation_key, name, arguments, scope, outcome):
        _require(name == FBA_TOOL and canonical(scope) == canonical(plain(context.scope)), "saved_operation_conflict")
        operation, actual, saved = self._operation(context, operation_key, pending=True)
        _require(canonical(actual) == canonical(arguments) and canonical(saved) == canonical(outcome), "saved_operation_conflict")
        return self._fact_record(context, operation_key, verify_artifacts=True, pending=True)

    def authenticate_frozen_fact_records(self, context, *, witnesses, sources):
        groups = {name: [] for name in sources}
        seen = set()
        for witness in witnesses:
            _require(type(witness) is dict and witness.get("operation_key") not in seen, "frozen_witness_conflict")
            seen.add(witness["operation_key"])
            row = self._fact_record(context, witness["operation_key"], verify_artifacts=False)
            _require(row is not None and row["witness"] == witness, "frozen_witness_conflict")
            for name in sources:
                groups[name].extend(row["facts"][name])
        return groups
