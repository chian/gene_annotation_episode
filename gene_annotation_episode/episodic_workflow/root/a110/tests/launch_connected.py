"""Private Launch integration checks.

Actual Store/Journal, HPC planning, private constructors, registry, runtime
selection, task execution and report validation are exercised. The provider,
child execution/acquisition and receipt side effects are controlled ports.
No remote transport or native command is started by these tests.
"""
from __future__ import annotations

import asyncio
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import (
    commission, recorded_queue, resources,
)


AXIS = "a110"
HPC_PARENTS = ("hpc_work_planning", "scientific_process/hpc_work_planning")
EXECUTION_CHILDREN = ("local_job_execution", "hpc_job_execution")


def forbidden(*args, **kwargs):
    pytest.fail("This contract check crossed a controlled execution/acquisition port")


class LaunchConnectedChecks:
    def module(self, name):
        return importlib.import_module(
            "gene_annotation_episode.episodic_workflow.root." + AXIS + "." + name.replace("/", "."))

    @pytest.fixture
    def connected(self, tmp_path):
        runtime = self.module("runtime")
        bindings = self.module("episode_bindings")
        identity = self.module("method_loop.identities").EpisodeRef
        run_id = AXIS + "-launch-connected"
        with self.module("state").Store(tmp_path / "state") as store:
            subject_refs = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")["subject_refs"]
            journal = self.module("episode_journal").Journal(store, run_id)
            services = SimpleNamespace(annotation_task_required=lambda: False)
            libraries = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
            science = self.module("scientific_process/episode").ScientificProcessEpisode(
                services, library=libraries, tool_library=libraries,
                child_roles=("scientific_process", "hpc"))
            hpc_options = dict(store=store, run_id=run_id, directory=tmp_path / "workflow",
                resources=resources(), commissions={"commission": commission()})
            execution_options = dict(store=store, run_id=run_id, directory=tmp_path / "workflow",
                resources=resources(), initial_information={}, tool_registry=None,
                handoff_unit=3., acquired_record_unit=2., log_window_bytes=1024,
                log_roles=("stdout", "stderr"))
            owners, constructors, execution = {}, [science], {}
            for home in HPC_PARENTS:
                for selected in (home, home + "/hpc_allocation_execution"):
                    parent = self.module(selected + "/episode").HPCEpisode(services, **hpc_options)
                    owners[selected] = parent
                    constructors.append(parent)
                    made = self.module(selected + "/episode").create_execution_bindings(
                        services, **execution_options)
                    assert tuple(item.binding_path for item in made) == (
                        selected + "/execution_job_submission",
                        *(selected + "/execution_job_submission/" + name for name in EXECUTION_CHILDREN),
                        selected + "/execution_result_acquisition")
                    execution[selected] = made
                    constructors.extend(made)
                    constructors.append(self.module(selected + "/execution_progress_assessment/episode")
                        .MonitorEpisode(services))
                constructors.append(self.module(home + "/hpc_resource_prediction/episode")
                    .HPCEpisode(services, **hpc_options))
            assert len(constructors) == 27
            registry = bindings.EpisodeBindingRegistry(constructors)
            parent_home = self.binding_path.rsplit("/", 1)[0]
            root_home = parent_home.removesuffix("/hpc_allocation_execution")
            path = ((("scientific_process", "science"), ("hpc", "original"))
                if root_home.startswith("scientific_process/") else
                (("annotation", "root"), ("hpc", "original")))
            scope = {"subject_refs": list(subject_refs)}

            def context(role, path, assignment):
                request = {"message": {"scope": deepcopy(scope),
                    "episode_assignment": deepcopy(assignment), "initial_report": {}}}
                value = bindings.BindingContext(run_id, identity(run_id, path).episode_id,
                    role, path, scope, assignment, request)
                journal.save("runtime_episodes", {"episode_id": value.episode_id,
                    "path": runtime._json(path), "request": runtime._json(request),
                    "initial_credit": 0, "state": "active", "completion": None, "archive": None})
                return value

            root_context = context("hpc", path, {"commission_id": "commission"})
            owners[root_home].initialize(root_context)
            parent_context = root_context
            if parent_home != root_home:
                parent_context = context("hpc_execution", path + (("hpc_execution", "allocation"),),
                    {"commission_id": "commission", "owner_episode_id": root_context.episode_id})
                owners[parent_home].initialize(parent_context)
            parent = owners[parent_home]
            ledger = parent.state(parent_context)
            queue_ref = ledger.put("queue", {"snapshot": recorded_queue(self.module("hpc_queue"))})
            outcome = asyncio.run(parent.execute(parent_context, "hpc.plan", {
                "candidate_id": commission()["candidates"][0]["id"],
                "model_ref": "reference_model", "queue_ref": queue_ref}, "original-plan"))
            assert outcome["status"] == "completed"
            plan = ledger.read(outcome["result"]["plan_ref"])
            launch = execution[parent_home][0]
            launch_context = context("launch", parent_context.path + (("launch", "child_3"),),
                plan["launch_assignment"])
            launch.initialize(launch_context)
            native_context = context("launch_hpc", launch_context.path + (("launch_hpc", "child_5"),),
                plan["practical_assignment"])
            native = registry.for_path(native_context.path)
            contexts = {value.episode_id: value for value in (root_context, parent_context,
                                                            launch_context, native_context)}
            yield SimpleNamespace(runtime=runtime, store=store, journal=journal, run_id=run_id,
                registry=registry, all_bindings=constructors, parents=owners, contexts=contexts,
                parent=parent, parent_context=parent_context, launch=launch, context=launch_context,
                native=native, native_context=native_context, ledger=ledger, plan=plan,
                directory=tmp_path / "workflow", execution_options=execution_options)

    @pytest.fixture
    def informed(self, connected):
        """`connected` with the original-global information catalogs bound on its registry.

        Workflow construction binds these before any registry context is read; every
        execution binding here requires that authority and the registry refuses without it.
        The factory is this fixture's own execution operands.
        """
        v = connected
        options = v.execution_options
        factory = self.module("execution_service_setup").ExecutionServiceFactory(
            options["resources"], options["initial_information"], options["handoff_unit"],
            options["acquired_record_unit"], 1., log_window_bytes=options["log_window_bytes"],
            log_roles=options["log_roles"])
        operands = dict(store=v.store, run_id=v.run_id, directory=v.directory,
            tool_registry=options["tool_registry"], services=v.launch.services)
        initial = self.module("library/execution_initial_information/information_configuration"
            ).InitialInformationConfiguration.original_global_factory(factory).construct(**operands)
        v.registry.configure_initial_information(
            initial, self.module("annotation_initial_information").initial_information)
        received = self.module("library/received_execution_information/received_configuration"
            ).ReceivedExecutionConfiguration.original_global_factory(factory).construct(**operands)
        v.registry.configure_received_execution_information(
            received, self.module("annotation_received_execution_information").received_execution_information)
        return v

    def source(self, v, context):
        return SimpleNamespace(episode_id=context.episode_id, path=context.path,
            scope=v.runtime._plain(context.scope), interpret_schema=v.runtime._object({}),
            _delivery_resolution_ref=None,
            request=SimpleNamespace(goal=v.runtime.EpisodeGoal.root(
                objective="Retain the original planned work and handoff", result_contract={})))

    def workflow(self, v):
        runtime = v.runtime
        def context(source):
            return v.contexts[source.episode_id]
        workflow = SimpleNamespace(store=v.store, journal=v.journal, run_id=v.run_id,
            episode_bindings=v.registry, binding_context=context,
            specialist=lambda source: v.registry.for_path(source.path),
            job_episodes=None, scientific_process_binding=None,
            annotation_child_roles=None, project_credit=lambda *args: 0,
            execution_binding=None, inprocess_replay=None,
            receipts=None, progress_provider=None, native_timing_information=None,
            services=SimpleNamespace(capabilities=lambda: {},
                tool_invocation=lambda *args, **kwargs: nullcontext()),
            launch_instructions=SimpleNamespace(operation_catalog=lambda: [],
                materialize=lambda value: None, instructions="Pinned launch instructions."),
            knowledge=SimpleNamespace(operation_catalog=lambda: [], instructions="Selected knowledge."),
            resource_estimator=None,
            receive_tool_attributions=lambda *args, **kwargs: [],
            validate_child_choice=lambda *args, **kwargs: None,
            _closed_child_commission=lambda *args: None, root_child_return_sources=lambda *args: (),
            child_initial_report_input=lambda *args: "{}", resolver=lambda *args, **kwargs: lambda *args: True)
        workflow.is_job_source = lambda source: runtime.Workflow.is_job_source(workflow, source)
        workflow.permits_common_action = lambda source, action: action in workflow.specialist(
            source).permitted_common_actions(context(source))
        workflow.catalog = lambda scope, source: workflow.specialist(source).catalog(context(source))
        return workflow

    @staticmethod
    def handoff_schema():
        return {"type": "object", "properties": {
            "completed": {"type": "boolean", "x-source": "execution_completed"},
            "handoffs": {"type": "array", "uniqueItems": True, "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "execution_handoff"},
                "x-source": "execution_handoff_refs"}},
            "required": ["completed", "handoffs"], "additionalProperties": False}

    def test_full_registry_keeps_actual_launch_context_and_original_input_file(self, informed):
        v = informed
        assert v.registry.for_path(v.context.path) is v.launch
        assert v.registry.for_child(v.context.path, "launch_hpc") is v.native
        actual = v.registry.initial_decision_context(v.context)
        assert actual["execution_resource_capabilities"] == v.registry._recipient_initial_information(v.context)["execution_resource_capabilities"]
        assert actual["hpc_execution_job"]["scientific_manifest"] == v.plan["manifest"]
        assert json.loads(Path(actual["hpc_execution_job"]["supplied_input_file"]).read_text()) == v.plan
        assert v.runtime.Workflow.is_job_source(self.workflow(v), self.source(v, v.context)) is False
        # Also exercise descendant callbacks; this was a full-registry regression
        # surface, not something that a single binding context can establish.
        v.registry.received_report_sources("launch", path=v.context.path)
        v.registry.received_report_facts(v.context)

    def test_original_parent_resource_exposure_and_nearest_hpc_commissioner(self, informed):
        v = informed
        parent = v.registry.initial_decision_context(v.parent_context)
        assert parent["execution_resource_capabilities"] == v.registry._recipient_initial_information(v.context)["execution_resource_capabilities"]
        assert parent["execution_initial_information"] == {}
        for context in (v.context, v.native_context):
            providers = []
            for binding in v.registry._context_bindings(context):
                callback = getattr(binding, "initial_decision_context", None)
                value = {} if callback is None else callback(context)
                if "hpc_execution_job" in value:
                    providers.append(binding.binding_path)
                    assert value["hpc_execution_job"]["plan_id"] == v.plan["plan_id"]
            assert providers == [v.parent.binding_path]

    def test_original_plan_admission_reservation_and_closed_replay(self, connected):
        v = connected
        original = deepcopy(v.plan["launch_assignment"])
        prepared = v.parent.prepare_child_request(v.parent_context, "launch", original)
        admitted = v.launch.prepare_assignment(v.parent_context, "launch", prepared,
            v.context.scope, "original-commission")
        assert admitted == original == v.plan["launch_assignment"]
        assert v.launch.prepare_assignment(v.parent_context, "launch", prepared,
            v.context.scope, "original-commission") == admitted
        before = deepcopy(v.ledger.records("launch_commission"))
        v.ledger.put("closed", {"plan_id": v.plan["plan_id"]})
        assert v.launch.prepare_assignment(v.parent_context, "launch", prepared,
            v.context.scope, "original-commission") == admitted
        with pytest.raises(ValueError):
            v.launch.prepare_assignment(v.parent_context, "launch", prepared,
                v.context.scope, "replacement-commission")
        assert v.ledger.records("launch_commission") == before
        changed = deepcopy(original)
        changed["constraints"]["changed_original_operand"] = True
        with pytest.raises(ValueError):
            v.launch.prepare_assignment(v.parent_context, "launch", changed,
                v.context.scope, "changed-request")

    def test_native_incoming_schema_and_real_admission_keep_full_frozen_request(self, connected):
        v = connected
        incoming = v.native.child_assignment_schema(v.context, "launch_hpc")
        assert incoming == {"type": "object", "enum": [v.plan["practical_assignment"]]}
        prepared = v.launch.prepare_child_request(v.context, "launch_hpc",
            deepcopy(v.plan["practical_assignment"]))
        assert prepared == v.plan["practical_assignment"]
        admitted = v.native.prepare_assignment(v.context, "launch_hpc", prepared,
            v.context.scope, "original-native-commission")
        assert admitted == v.plan["practical_assignment"]
        with pytest.raises(ValueError, match="unknown_execution_episode_role"):
            v.native.assignment_schema("launch")
        changed = deepcopy(prepared)
        changed["requested_job"]["argv"].append("changed-job")
        with pytest.raises(ValueError):
            v.launch.prepare_child_request(v.context, "launch_hpc", changed)
        assert v.ledger.records("launch_commission") == []
        assert v.ledger.records("handoff") == []

    def test_actual_action_schema_rejects_new_wait_and_reason_before_acquisition(self, connected):
        v = connected
        w, source = self.workflow(v), self.source(v, v.context)
        schema = v.runtime.Workflow.action_schema(w, source)
        branches = schema["properties"]["selection"]["anyOf"]
        kinds = {branch["properties"]["kind"]["const"] for branch in branches}
        assert kinds == {"tool", "episode_child", "redeliver_report"}
        native, = [branch for branch in branches
            if branch["properties"].get("role", {}).get("const") == "launch_hpc"]
        assert native["properties"]["assignment"] == v.native.child_assignment_schema(
            v.context, "launch_hpc")
        for selection in ({"kind": "wait", "condition": {}}, {"kind": "reason", "commit": {}}):
            with pytest.raises(ValueError, match="action_not_available_to_episode"):
                v.runtime.Workflow.selected(w, source, selection, 11)
        assert v.journal.row("runtime_actions", source.episode_id, 11) is None

    @pytest.mark.parametrize("boundary", ["planning_to_launch", "launch_to_native"])
    def test_runtime_commission_routes_request_before_admission_and_preserves_contract(
            self, connected, monkeypatch, boundary):
        v = connected
        outer = boundary == "planning_to_launch"
        sender, context, child, child_context = ((v.parent, v.parent_context, v.launch, v.context)
            if outer else (v.launch, v.context, v.native, v.native_context))
        w, source = self.workflow(v), self.source(v, context)
        schema = self.handoff_schema()
        w.expanded_contract_form = lambda *args: (schema, None)
        events, built = [], []
        prepare, admit = sender.prepare_child_request, child.prepare_assignment
        def outgoing(*args):
            events.append("request")
            return prepare(*args)
        def incoming(*args):
            events.append("admission")
            return admit(*args)
        monkeypatch.setattr(sender, "prepare_child_request", outgoing)
        monkeypatch.setattr(child, "prepare_assignment", incoming)
        selected = {"kind": "episode_child", "role": child_context.role,
            "scope": source.scope, "assignment": v.runtime._plain(child_context.assignment),
            "goal": "Preserve the exact original job", "purpose": "Receive its actual typed handoff",
            "schema_json": json.dumps(schema), "initial_report_json": "{}"}
        proxy = SimpleNamespace(source=self.source(v, child_context))
        def build(*args, **kwargs):
            built.append((args, kwargs))
            return proxy
        w.build = build
        monkeypatch.setattr(v.runtime, "TimedChildUnit", lambda child, *args, **kwargs: child)
        assert v.runtime.Workflow.selected(w, source, selected, 3 if outer else 5) is proxy
        assert events == ["request", "admission"]
        assert built[0][0][0] == child_context.role
        assert built[0][1]["episode_assignment"] == selected["assignment"]
        assert built[0][1]["parent_path"] == context.path
        assert built[0][1]["contract"].schema == schema
        assert v.plan["practical_assignment"]["requested_job"] == (
            selected["assignment"]["requests"]["aurora"]["requested_job"] if outer
            else selected["assignment"]["requested_job"])

    @pytest.mark.parametrize("boundary", ["planning_to_launch", "launch_to_native"])
    def test_missing_handoff_contract_fails_before_request_or_reservation(
            self, connected, monkeypatch, boundary):
        v = connected
        outer = boundary == "planning_to_launch"
        context, sender, child_context = ((v.parent_context, v.parent, v.context) if outer else
                                         (v.context, v.launch, v.native_context))
        w, source = self.workflow(v), self.source(v, context)
        w.expanded_contract_form = lambda *args: (v.runtime._object({}), None)
        monkeypatch.setattr(sender, "prepare_child_request", forbidden)
        w.build = forbidden
        selected = {"kind": "episode_child", "role": child_context.role, "scope": source.scope,
            "assignment": v.runtime._plain(child_context.assignment), "goal": "Original work",
            "purpose": "Original receipt"}
        with pytest.raises(self.module("domain").ContractError,
                           match="hpc_launch_requires_original_handoff_fact_in_return_form"):
            v.runtime.Workflow.selected(w, source, selected, 19)
        assert v.ledger.records("launch_commission") == []

    def task(self, v):
        # Selected type is actual private task after extraction. Construction is
        # independently covered through Workflow.build; here ports isolate the
        # original acquisition/projection/replay boundary.
        task_type = getattr(v.launch, "decision_source_type", v.runtime.DecisionSource)
        task = object.__new__(task_type)
        source = self.source(v, v.context)
        task.__dict__.update(source.__dict__)
        task.calls = 0
        task._execution_context = None
        task.last_outcome = task.last_outcome_index = task.feedback = None
        task.report_values, task.report_basis = {}, []
        task.checkpoint = lambda: None
        task.workflow = w = self.workflow(v)
        executions, observations, projections = [], [], []
        async def execute(source, name, arguments, **kwargs):
            executions.append(kwargs["operation_key"])
            return await v.runtime.Workflow.execute(w, source, name, arguments, **kwargs)
        async def scores(source, index, result):
            return result
        def credit(source):
            projections.append(source.episode_id)
            return v.launch.credit_view(v.context, None)
        w.execute, w.automatic_score_updates, w.source_credit_view = execute, scores, credit
        w.receive_native_outcome = lambda *args: None
        w.receive_outcome = lambda source, selection, result, index: observations.append((index, deepcopy(result)))
        w.controller_value = lambda source, index, credit: {"index": index, "credit": credit}
        w.wait_inputs_version = w.completed_action_inputs_version = None
        w.pending_work = lambda source: []
        return SimpleNamespace(task=task, workflow=w, executions=executions,
            observations=observations, projections=projections)

    @pytest.mark.parametrize("arguments,status", [({}, "completed"), ({"unexpected": True}, "invalid")])
    def test_actual_runtime_task_tool_outcome_enters_original_iterator_once(
            self, connected, arguments, status):
        v = connected
        f = self.task(v)
        selected = {"kind": "tool", "tool": "execution.capabilities", "arguments": arguments}
        before = v.launch.credit_view(v.context, None)
        measured = asyncio.run(f.task.execute(selected, 4))
        assert measured == {"index": 4, "credit": before["credit"]}
        row = v.journal.row("runtime_actions", v.context.episode_id, 4)
        outcome = json.loads(row["result"])
        assert outcome["status"] == status
        assert json.loads(row["action"]) == selected and row["credit"] == measured["credit"]
        assert f.executions == [v.run_id + ":" + v.context.episode_id + ":4"]
        assert len(f.observations) == len(f.projections) == 1
        assert asyncio.run(f.task.execute(selected, 4)) == measured
        assert len(f.executions) == len(f.observations) == len(f.projections) == 1
        with pytest.raises(v.runtime.WorkflowError, match="reconstructed selected work changed"):
            asyncio.run(f.task.execute({**selected, "arguments": {"changed": True}}, 4))

    @pytest.mark.parametrize("status", ["failed", "unavailable"])
    def test_returned_failure_preserves_observation_credit_and_replay(self, connected, status):
        v = connected
        f = self.task(v)
        selected = {"kind": "tool", "tool": "execution.capabilities", "arguments": {}}
        calls = []
        async def returned(*args, **kwargs):
            calls.append(kwargs["operation_key"])
            return {"status": status, "record_refs": [], "changed_record_refs": [],
                "result": None, "feedback": {"category": "controlled_transport", "code": status}}
        f.workflow.execute = returned
        measured = asyncio.run(f.task.execute(selected, 6))
        assert measured == {"index": 6, "credit": v.launch.credit_view(v.context, None)["credit"]}
        assert f.observations[0][1]["status"] == status
        assert asyncio.run(f.task.execute(selected, 6)) == measured
        assert calls == [v.run_id + ":" + v.context.episode_id + ":6"]
        assert len(f.observations) == 1

    def test_completed_saved_wait_keeps_original_credit_without_a_new_wait(self, connected):
        v = connected
        f = self.task(v)
        selection = {"kind": "wait", "condition": {"version": "event_condition_v1", "events": [],
            "reconsider_at": "2026-10-30T00:00:00+00:00"}}
        outcome = {"status": "completed", "record_refs": [], "changed_record_refs": [], "result": None}
        v.journal.save("runtime_actions", {"episode_id": v.context.episode_id, "decision_index": 8,
            "action": json.dumps(selection), "result": json.dumps(outcome), "credit": 7.5})
        f.workflow.perform_selected_wait = f.workflow.source_credit_view = forbidden
        f.workflow.last_observed_credit = f.workflow.automatic_score_updates = forbidden
        assert asyncio.run(f.task.execute(selection, 8)) == {"index": 8, "credit": 7.5}
        assert f.task.last_outcome == outcome and f.task.last_outcome_index == 8
        assert f.executions == f.observations == f.projections == []

    def test_ready_owned_child_precedes_another_model_decision(self, connected):
        v = connected
        f = self.task(v)
        ready, visited = object(), []
        f.task._execution_context = SimpleNamespace(
            _ready_owned_child=lambda path: visited.append(path) or ready)
        assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is ready
        assert visited == [v.context.path] and f.task.calls == 0 and f.executions == []

    def test_original_request_handoff_credit_counts_once_across_physical_retries(self, connected, monkeypatch):
        v = connected
        selected = {"run_id": v.run_id, "episode_id": v.context.episode_id,
            "known_record_refs": ["original-handoff", "retry-handoff"], "initial_known_record_refs": []}
        handoffs = {"original-handoff": {"resource_id": "aurora", "execution_id": "physical-first"},
                    "retry-handoff": {"resource_id": "aurora", "execution_id": "physical-retry"}}
        monkeypatch.setattr(v.launch, "_received", lambda *args, **kwargs: (selected, handoffs, {}))
        monkeypatch.setattr(v.launch.job_progress_provider.targets, "usable_handoff", lambda target: True)
        view = v.launch.credit_view(v.context, None)
        assert view["credit"] == 3. and view["new_handoff_count"] == 1
        assert v.parent.credit_view(v.parent_context, None)["credit"] == 0.
        selected["initial_known_record_refs"] = ["original-handoff"]
        assert v.launch.credit_view(v.context, None)["credit"] == 0.

    def test_typed_launch_report_uses_recorded_facts_and_rejects_fabricated_completion(self, connected):
        v = connected
        schema = self.handoff_schema()
        facts = v.launch.facts(v.context, {})
        form = {key: facts[node["x-source"]] for key, node in schema["properties"].items()}
        v.launch.validate_report(v.context, form, schema)
        assert form == {"completed": False, "handoffs": []}
        with pytest.raises(ValueError, match="execution_report_disagrees_with_recorded_facts"):
            v.launch.validate_report(v.context, {**form, "completed": True}, schema)
        with pytest.raises(v.runtime.ReportBoundaryError):
            v.launch.validate_report(v.context, {**form, "handoffs": 3}, schema)
        v.journal.save("runtime_forms", {"episode_id": v.context.episode_id,
            "facts": json.dumps(facts), "form": json.dumps(form)})
        assert json.loads(v.journal.row("runtime_forms", v.context.episode_id)["form"]) == form


    def test_runtime_build_selects_actual_private_task(self, connected, monkeypatch):
        v = connected
        w = self.workflow(v)
        monkeypatch.setattr(v.runtime.Episode, "identity",
            lambda *args, **kwargs: SimpleNamespace(episode_id=v.context.episode_id))
        monkeypatch.setattr(v.runtime, "FeedbackEpisode", lambda grain, key, source, *args, **kwargs: source)
        w.context, w.grains = object(), {"launch": object()}
        w.inprocess_completion_order = None
        w.contract_information_profile = lambda source: None
        w.source_credit_view = lambda source: v.launch.credit_view(v.context, None)
        w.expose_assigned_job = lambda source: None
        w.archive = SimpleNamespace(store=lambda value: value)
        # The constructor check starts a fresh runtime row. The fixture's
        # detached context is not a complete serialized EpisodeRequest.
        with v.store.transaction():
            v.store.db.execute("DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (v.run_id, v.context.episode_id))
        selected = v.runtime.Workflow.build(w, "launch", "child_3", "Original planned work",
            v.runtime._plain(v.context.scope), parent_path=v.parent_context.path,
            episode_assignment=v.runtime._plain(v.context.assignment))
        assert type(selected) is v.launch.decision_source_type
        assert type(selected) is not v.runtime.DecisionSource
        assert type(selected).__module__.startswith(v.launch.__module__.removesuffix(".episode") + ".")
        assert selected.episode_id == v.context.episode_id

    @pytest.mark.parametrize("declared_renderer", [False, True])
    def test_interrupted_saved_decision_keeps_full_original_payload_and_renderer(
            self, informed, declared_renderer):
        v = informed
        f = self.task(v)
        task, w = f.task, f.workflow
        task._model_snapshot = task._presented_conversation_key = None
        w.contract_information_profile = lambda source: None
        w.decision_protocol = None
        w.native_event_information = None
        w.services.instructions = self.module("runtime_prompt").instructions
        original = {"execution_assignment": deepcopy(v.plan["launch_assignment"]),
            "resource_configuration": deepcopy(v.launch.resources),
            "hpc_execution_job": {"plan_id": v.plan["plan_id"],
                "scientific_manifest": deepcopy(v.plan["manifest"])},
            "execution_resource_capabilities": deepcopy(v.registry._recipient_initial_information(v.context)[
                "execution_resource_capabilities"]),
            "launch_instruction_library": {"preserved": "original selected library"}}
        schema = v.runtime.Workflow.action_schema(w, task)
        request = {"context": original, "schema": schema, "assignment_transport": {
            "version": v.runtime._ASSIGNMENT_TRANSPORT, "action_schema_sha256": v.runtime._digest(schema)}}
        v.journal.save("runtime_model_calls", {"episode_id": task.episode_id, "call_index": 0,
            "purpose": "decision", "request": json.dumps(request), "response": None})
        response = {"selection": {"kind": "tool", "tool": "execution.capabilities", "arguments": {}},
                    "report_update": {}}
        calls = []
        async def complete(*args, **kwargs):
            calls.append((args, kwargs))
            return response
        if declared_renderer:
            # The private task hands its declared renderer only to the genuine provider type
            # (task_decision.decision_completion).
            w.provider = object.__new__(self.module("providers").ModelConnection)
            w.provider.worker_lock = asyncio.Lock()
            w.provider.workers = {}
            w.provider.has_session = lambda *args: True
            w.provider._complete_serial = complete
        else:
            w.provider = SimpleNamespace(has_session=lambda *args: True, complete=complete)
        returned = asyncio.run(task.call({"changed_current_context": True}, v.runtime._object({})))
        assert returned[0] == response and returned[2:] == (original, schema)
        assert calls[0][0][3] == original
        assert calls[0][0][2] == self.module("runtime_prompt").instructions(task, original)
        expected = ({"prompt_renderer": v.launch.decision_prompt_renderer} if declared_renderer else {})
        assert calls[0][1] == expected
        assert v.launch.decision_prompt_renderer is self.module(
            self.binding_path + "/task_presentation").present_launch_context
        saved = v.journal.row("runtime_model_calls", task.episode_id, 0)
        assert json.loads(saved["request"])["context"] == original
        assert json.loads(saved["request"])["schema"] == schema
        task.calls = 0
        assert asyncio.run(task.call({"different": True}, {})) == returned
        assert len(calls) == 1
        assert v.journal.row("runtime_actions", task.episode_id, 0) is None

    def receipt_fixture(self, v, monkeypatch):
        # Actual native admission/initialization and facts, with no native action.
        prepared = v.launch.prepare_child_request(v.context, "launch_hpc",
            v.runtime._plain(v.native_context.assignment))
        assert v.native.prepare_assignment(v.context, "launch_hpc", prepared,
            v.context.scope, "receipt-native-request") == prepared
        v.native.initialize(v.native_context)
        schema = self.handoff_schema()
        facts = v.native.facts(v.native_context, {})
        form = {key: facts[node["x-source"]] for key, node in schema["properties"].items()}
        v.native.validate_report(v.native_context, form, schema)
        v.journal.save("runtime_forms", {"episode_id": v.native_context.episode_id,
            "facts": json.dumps(facts), "form": json.dumps(form)})
        source, w = self.source(v, v.context), self.workflow(v)
        progress, receipts, cached = [], [], {"references": None}
        w.progress_provider = SimpleNamespace(receive_form=lambda *args: progress.append(args))
        w.receipts = SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs)))
        # Registry receipt references are a controlled port here.
        monkeypatch.setattr(v.registry, "received_form_references", lambda *args: [])
        monkeypatch.setattr(self.module("episode_return_records").EpisodeReturnRecords,
            "recorded_admission_references", lambda *args: cached["references"])
        def selected(index, action, child_id=None):
            v.journal.save("runtime_actions", {"episode_id": source.episode_id,
                "decision_index": index, "action": json.dumps(action), "result": None, "credit": None})
            v.journal.save("runtime_report_attempts", {"parent_episode_id": source.episode_id,
                "decision_index": index, "delivery_ref": "original-native-delivery",
                "child_episode_id": child_id or v.native_context.episode_id,
                "contract": json.dumps(schema), "form": json.dumps(form), "failure": None})
        selected(5, {"kind": "episode_child", "role": "launch_hpc",
            "assignment": v.runtime._plain(v.native_context.assignment), "scope": source.scope})
        return SimpleNamespace(workflow=w, source=source, schema=schema, form=form,
            progress=progress, receipts=receipts, cached=cached, selected=selected)

    def test_named_native_report_receipt_redelivery_and_saved_identity(self, connected, monkeypatch):
        v = connected
        r = self.receipt_fixture(v, monkeypatch)
        receiver = v.launch.execution_child_report_receiver("launch_hpc")
        assert receiver.__module__ == v.launch.__module__.removesuffix(".episode") + ".from_child_hpc_job_execution"
        before = v.launch.credit_view(v.context, None)
        assert v.runtime.Workflow._receive_form(
            r.workflow, r.source, r.form, r.schema, 5, child_role="launch_hpc") == []
        r.selected(9, {"kind": "redeliver_report", "delivery_ref": "original-native-delivery"})
        assert v.runtime.Workflow._receive_form(
            r.workflow, r.source, r.form, r.schema, 9, redelivery=True, child_role="launch_hpc") == []
        assert [row[-1] for row in r.progress] == [
            v.run_id + ":" + v.context.episode_id + ":5:typed_form",
            v.run_id + ":" + v.context.episode_id + ":9:typed_form"]
        assert [kwargs for _, kwargs in r.receipts] == [
            {"kind": "child_form", "source_index": 5},
            {"kind": "report_redelivery", "source_index": 9}]
        assert v.launch.credit_view(v.context, None) == before
        assert v.ledger.records("handoff") == []
        wrong_path = v.parent_context.path + (("launch", "other-launch"), ("launch_hpc", "child_5"))
        v.journal.save("runtime_episodes", {"episode_id": "wrong-original-child",
            "path": json.dumps(wrong_path), "request": "{}", "initial_credit": 0,
            "state": "yielded", "completion": None, "archive": None})
        r.selected(10, {"kind": "redeliver_report", "delivery_ref": "original-native-delivery"},
            child_id="wrong-original-child")
        with pytest.raises(v.runtime.WorkflowError, match="original_delivery_parent_conflict"):
            v.runtime.Workflow._receive_form(r.workflow, r.source, r.form, r.schema, 10, redelivery=True)
        assert len(r.progress) == len(r.receipts) == 2

    def test_recorded_native_admission_reuses_original_receipts_without_delivery(self, connected, monkeypatch):
        v = connected
        r = self.receipt_fixture(v, monkeypatch)
        r.cached["references"] = ["source_original_admission"]
        assert v.runtime.Workflow._receive_form(
            r.workflow, r.source, r.form, r.schema, 5) == ["source_original_admission"]
        assert r.progress == r.receipts == []

    def test_original_timing_receipt_branch_remains_axis_specific(self, connected, monkeypatch):
        v = connected
        r = self.receipt_fixture(v, monkeypatch)
        calls = []
        def receive(*args):
            calls.append(args)
            return {"native_execution_refs": ["native_original_timing"]}
        r.workflow.native_timing_information = object()
        r.workflow.job_episodes = SimpleNamespace(roles=(), received_timing_records=receive)
        first = v.runtime.Workflow._receive_form(r.workflow, r.source, r.form, r.schema, 5)
        again = v.runtime.Workflow._receive_form(r.workflow, r.source, r.form, r.schema, 5, redelivery=True)
        row = v.store.db.execute("SELECT timing_receipts FROM runtime_report_attempts WHERE "
            "run_id=? AND parent_episode_id=? AND decision_index=?",
            (v.run_id, v.context.episode_id, 5)).fetchone()
        assert calls == [] and row[0] is None and first == again == []


