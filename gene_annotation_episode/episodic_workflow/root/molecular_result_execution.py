"""Original molecular result responsibility: molecular_result_execution."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import immutable, read_control, same
from .molecular_result_actions import unique
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FACT_SOURCES, FAILURE_SOURCE, FILE_ROLES, MODES, PLAN_VERSION, PROJECTION_SOURCE, SAVED_SOURCE, empty_file_state, failure, require, select_molecular_sequence_return_facts, select_stored_molecular_sequence_values, validate_file_state, validate_molecular_sequence_fact_values, validate_molecular_sequence_projection, validate_molecular_sequence_result_worker_result, SCHEMAS
from gene_annotation_episode.native_file_capture import retained_native_file
from .library.retained_file_pin import file_pin
from .library.retained_file_read import read_bytes
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import POLICY, PUBLIC_VERSION, VERSION, _facts, _json, _retained

class MolecularResultExecution:

    async def _worker(self, action, plan):
        """Only an explicitly selected deployment may execute a finite worker."""
        software = getattr(self.owner, "molecular_sequence_result_software", None)
        if software is None:
            return None, failure("worker_unavailable", "worker")
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_native import _manifest
        index, _ = _manifest(software)
        require(index.get(software["python"]["path"]) == software["python"])
        for selected in index.values(): require(file_pin(selected["path"]) == selected, "molecular_sequence_worker_selected_pin_conflict")
        from gene_annotation_episode.local_jobs import LocalJobPolicy
        from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, wait_job
        plan_path = action.directory / "worker-plan.json"; immutable(plan_path, plan)
        pin = file_pin(plan_path)
        command = [software["python"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_result_worker",
            "--plan-file", str(plan_path), "--sha256", pin["sha256"], "--size-bytes", str(pin["size_bytes"]),
            "--output-directory", plan["directory"]]
        handle = NativeJobHandle(action.directory / "worker-handle.json")
        environment = {"PYTHONHOME": software["python_home"], "PYTHONPATH": ":".join(software["import_roots"]),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
        policy = POLICY
        if plan["version"] == supplied.SUPPLIED_PLAN_VERSION:
            require(plan["software"] == software)
            environment, policy = plan["selected_environment"], plan["policy"]
        if not handle.path.exists():
            prepare_job(command, cwd=action.directory, policy=LocalJobPolicy(**policy), handle_path=handle.path, env=environment)
        else:
            body = handle.read(); require(body["command"] == command and body["metadata"]["policy"] == policy)
        if plan["version"] == supplied.SUPPLIED_PLAN_VERSION:
            self._supplied_worker_request(handle, command=command, cwd=action.directory, environment=environment, policy=policy)
        def finish():
            resume_start(handle)
            return wait_job(handle)
        task = asyncio.create_task(asyncio.to_thread(finish))
        try:
            execution = await asyncio.shield(task)
            immutable(action.directory / "worker-execution.json", {"returncode": execution.returncode, "metadata": execution.metadata})
            result = validate_molecular_sequence_result_worker_result(_json(read_bytes(Path(plan["directory"]) / "result.json")))
        except asyncio.CancelledError:
            while not task.done():
                try: await asyncio.shield(task)
                except asyncio.CancelledError: continue
                except BaseException: break
            if not task.cancelled(): task.exception()
            raise
        except (AcquisitionError, OSError, ValueError):
            return None, failure("worker_failed", "worker")
        require(result["plan_sha256"] == digest(plan) and same(result["selector"], plan["selector"]))
        return result, None

    def _admit_projection(self, *, selector, sources, association, calculation):
        documents = {"sheet": None, "components": None}
        issues = []
        for role in documents:
            if sources[role]["file"] is not None:
                try:
                    document = _json(read_bytes(retained_native_file(self.store, sources[role]["file"])))
                    expected = SCHEMAS[selector["operation"]][0 if role == "sheet" else 1]
                    require(type(document) is dict and (document.get("schema") == expected if role == "sheet" else document.get("schema") in expected))
                    if selector["version"] in (supplied.N_SELECTOR_VERSION, supplied.O_SELECTOR_VERSION):
                        require((type(document.get("inputs")) is dict
                            and document["inputs"].get("operation") == selector["operation"])
                            if role == "sheet" else document.get("operation") == selector["operation"],
                            "molecular_sequence_ordinary_document_operation_conflict")
                    documents[role] = document
                except (OSError, ValueError):
                    issues.append(failure("schema_invalid", "load", role=role, source_ref=sources[role]["file"]["artifact_ref"]))
        projection = select_stored_molecular_sequence_values(operation=selector["operation"], sheet=documents["sheet"],
            components=documents["components"], selection=selector, source_files=sources, association=association, calculation=calculation)
        projection["public"]["failures"].extend(issues)
        return projection

    def _publication(self, selector, sources, projection, failures):
        groups = _facts()
        if projection is not None: groups[PROJECTION_SOURCE] = validate_molecular_sequence_fact_values(PROJECTION_SOURCE, [projection["public"]])
        components_schema = None if projection is None else projection["public"]["components_schema"]
        for role in selector["return_files"]:
            if sources[role]["file"] is not None:
                groups[SAVED_SOURCE].append(dict(operation=selector["operation"], role=role, artifact_ref=sources[role]["file"]["artifact_ref"],
                    source_kind="original_stored" if selector["mode"] == MODES[0] else "selected_saved_calculation",
                    source_sheet_ref=None if sources["sheet"]["file"] is None else sources["sheet"]["file"]["artifact_ref"], components_schema=components_schema))
        groups[FAILURE_SOURCE] = unique([*failures, *(row["failure"] for row in sources.values() if row["failure"] is not None),
            *([] if projection is None else projection["public"]["failures"])])
        return groups

    def _outcome(self, receipt):
        files = receipt["facts"][SAVED_SOURCE]
        return {"status": "completed", "record_refs": [row["artifact_ref"] for row in files],
            "changed_record_refs": [row["artifact_ref"] for row in files], "feedback": None,
            "result": {"version": "molecular_sequence_public_result_v2" if receipt["version"] == "molecular_sequence_result_receipt_v2" else PUBLIC_VERSION,
                "facts": deepcopy(receipt["facts"]), "delivery_complete": receipt["delivery_complete"]}}

    async def execute(self, context, target, tool_name, arguments, operation_key):
        async with self.locked_action(context, target=target, tool_name=tool_name, arguments=arguments, operation_key=operation_key) as action:
            if action.intent["assignment"]["selector"]["version"] == supplied.SUPPLIED_SELECTOR_VERSION:
                return await self._execute_supplied(action)
            saved = read_control(action.directory / "receipt.json")
            if saved is not None: return self._outcome(self._validate_receipt(saved, action.intent))
            selector = action.intent["assignment"]["selector"]
            sources = {role: empty_file_state() for role in FILE_ROLES}
            association = dict(state="unavailable", reason="scientific_binding_unavailable", proof_file=None, original_identity=None)
            failures, projection, worker_plan, result, received_file = [], None, None, None, None
            if tool_name == "execution.results.collect":
                if selector["mode"] == MODES[0]:
                    observed, association, issue = self._original(action)
                    if observed is not None: sources = observed
                    if issue is not None: failures.append(issue)
                else:
                    identity, received = self._received_sheet(context)
                    received_file = self.capture_control(action, "received-sheet.json", received, received["version"])
                    sources["sheet"] = _retained(identity)
                worker_plan = dict(version=PLAN_VERSION, directory=str(action.directory / "worker"), selector=selector,
                    source_files=deepcopy(sources), inputs=[dict(role=role, file=row["file"], path=str(retained_native_file(self.store, row["file"])))
                        for role, row in sources.items() if row["file"] is not None], association=association, received_sheet_receipt_file=received_file,
                    software=deepcopy(getattr(self.owner, "molecular_sequence_result_software", None)),
                    selected_environment={}, policy=deepcopy(POLICY))
                if worker_plan["software"] is not None:
                    selected_software = worker_plan["software"]
                    worker_plan["selected_environment"] = {"PYTHONHOME": selected_software["python_home"], "PYTHONPATH": ":".join(selected_software["import_roots"]),
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
                try:
                    result, issue = await self._worker(action, worker_plan)
                except (AcquisitionError, OSError, ValueError):
                    result, issue = None, failure("worker_failed", "worker")
                if issue is not None: failures.append(issue)
                calculation = {"kind": "original_stored", "calculator_id": None}
                if result is not None:
                    failures.extend(result["failures"])
                if selector["mode"] == MODES[1] and Path(worker_plan["directory"]).is_dir():
                    declaration = None if result is None else next(row["declaration"] for row in result["outputs"] if row["role"] == "calculated_components")
                    sources["components"] = self._capture_files(directory=worker_plan["directory"],
                        declarations={} if declaration is None else {"components": declaration}, capture_directory=action.directory / "calculated-capture",
                        roles=("components",), relative_paths={"components": "calculated_components.json"})["components"]
                    calculation = {"kind": "selected_saved_calculation", "calculator_id": "existing_operation_specific_pure_authority"}
                # This is literal source selection after actual Store retention,
                # not a second scientific calculation or a worker success gate.
                projection = self._admit_projection(selector=selector, sources=sources, association=association, calculation=calculation)
            facts = self._publication(selector, sources, projection, failures)
            requested = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
            facts = {source: rows if source in select_molecular_sequence_return_facts(facts, schema=requested) else [] for source, rows in facts.items()}
            complete = bool(tool_name == "execution.results.collect" and result is not None and projection is not None
                and all(sources[role]["file"] is not None for role in selector["return_files"]))
            receipt = dict(version=VERSION, intent=action.intent, source_files=sources, association=association,
                received_sheet_receipt_file=received_file, worker_plan=worker_plan, worker_result=result,
                projection=projection, failures=failures, facts=facts, acquired_population=None, delivery_complete=complete)
            immutable(action.directory / "receipt.json", self._validate_receipt(receipt, action.intent))
            return self._outcome(receipt)

    def _validate_receipt(self, receipt, intent):
        if receipt.get("version") == "molecular_sequence_result_receipt_v2":
            return self._validate_supplied_receipt(receipt, intent)
        require(type(receipt) is dict and set(receipt) == {"version", "intent", "source_files", "association", "received_sheet_receipt_file",
            "worker_plan", "worker_result", "projection", "failures", "facts", "acquired_population", "delivery_complete"})
        require(receipt["version"] == VERSION and same(receipt["intent"], intent) and receipt["acquired_population"] is None)
        require(receipt["association"]["state"] in ("unavailable", "conflict"), "molecular_sequence_independent_scientific_binding_unavailable")
        require(set(receipt["source_files"]) == set(FILE_ROLES) and set(receipt["facts"]) == set(FACT_SOURCES))
        for row in receipt["source_files"].values():
            validate_file_state(row)
            if row["file"] is not None: self.file_metadata(row["file"])
        for source, values in receipt["facts"].items(): validate_molecular_sequence_fact_values(source, values)
        if receipt["projection"] is not None:
            validate_molecular_sequence_projection(receipt["projection"])
            require(same(receipt["projection"]["source_files"], receipt["source_files"]))
            require(same(receipt["projection"]["association"], receipt["association"]))
            require(not receipt["facts"][PROJECTION_SOURCE] or same(receipt["facts"][PROJECTION_SOURCE], [receipt["projection"]["public"]]))
        expected = self._publication(intent["assignment"]["selector"], receipt["source_files"], receipt["projection"], receipt["failures"])
        schema = plain(self.context(intent["episode_id"]).request)["report_contract"]["measurements"]["schema"]
        wanted = select_molecular_sequence_return_facts(expected, schema=schema)
        require(same(receipt["facts"], {source: rows if source in wanted else [] for source, rows in expected.items()}), "molecular_sequence_publication_conflict")
        require(type(receipt["delivery_complete"]) is bool)
        return deepcopy(receipt)

    def _completed(self, context):
        self.authenticate(context)
        result = []
        for row in self.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index", (self.run_id, context.episode_id)):
            action = json.loads(row["action"])
            if action.get("tool") != "execution.results.collect" or row["result"] is None: continue
            key = f'{self.run_id}:{context.episode_id}:{row["decision_index"]}'
            receipt = read_control(self.action_directory(context.episode_id, key) / "receipt.json")
            require(receipt is not None and same(json.loads(row["result"]), self._outcome(receipt)), "molecular_sequence_completed_action_conflict")
            result.append(self._validate_receipt(receipt, self.intent(context, receipt["intent"]["target"], action["tool"], {}, key)))
        return result
