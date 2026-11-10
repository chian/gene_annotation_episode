"""One genuine ITC fit in an actual iterative scientific episode.

Decisions, the data and continuation are engineering fixtures. Workflow,
method_loop, selected tool/resource contracts, File custody, bounded execution,
ordinary publication and own-action receipts are real. No model RPC is made.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.materials import source_for_artifact
from gene_annotation_episode.molecular_measurement_tools import (
    ITC_TOOL, MolecularOperationUnpublished, authenticate_itc_invocation,
    itc_tool_contract, read_retained_itc_result,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import molecular_measurement_tools as ordinary
from test_itc_binding_fit import independent_engineering_dataset, assert_actual_itc_fit_and_saved_recalculation
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_library import independent_source, write


QUESTION = ("For the supplied engineered 32-injection ITC history and physical one-site model, "
    "what Kd, effective n and molar enthalpy fit the selected heats, and what residuals and native "
    "covariance qualifications follow under the selected independent sigma model?")


def _action(arguments):
    return dict(selection=dict(kind="tool", tool=ITC_TOOL, arguments=arguments), report_update={})


def _request(selection, source_ref):
    weights = selection["weighting"]
    return dict(mode="fit", input=dict(namespace="source", reference=source_ref),
        residual_injection_ordinals=list(range(32)), initial_parameters=deepcopy(selection["initial_parameters"]),
        bounds=deepcopy(selection["bounds"]), solver={**deepcopy(selection["solver"]), "jacobian": "two_point"},
        weighting=dict(kind=weights["kind"], independent_error_assumption=weights["independent_error_assumption"],
            absolute_sigma=weights["absolute_sigma"], sigma_heat_joule=[row["sigma"]["value"] for row in weights["sigma_heat"]]))


def _libraries(directory, tools, *, tool_names=(ITC_TOOL,)):
    source = directory / "engineered-instructions"
    independent_source(source)
    body = json.loads((source / "entries/A01.json").read_bytes())
    instruction = {key: body[key] for key in ("id", "name", "description", "evidence")}
    instruction.update(entry_version="evidence_axis_instruction_v1", slot="evidence_axis",
        investigation_instructions=("Engineering integration fixture. Investigate the assigned supplied ITC data "
            "and preserve model, calibration and uncertainty qualifications. Choose each next action from the "
            "actual preceding result; these instructions establish no biological claim."))
    write(source / "entries/A01.json", instruction)
    index = json.loads((source / "index.json").read_bytes())
    for row in index["slots"]:
        if row["slot"] == "annotation_distinction": row["slot"] = "evidence_axis"
    for row in index["entries"]:
        if row["id"] == "A01": row["slot"] = "evidence_axis"
    write(source / "index.json", index)
    descriptor = prepare_scientific_binding(run_directory=directory, source_directory=source,
        tool_catalog=tools.catalog(), child_roles=["scientific_process"])
    library = ScientificProcessLibrary(directory / "scientific-process-library")
    selected = dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A01"),
        thought_pattern=library.reference("P01"), child_tool_info=[dict(name=name, resources="local") for name in tool_names])
    return descriptor, selected


class _RenderedScript(ScriptedProvider):
    """Observe the real provider presentation method without starting an RPC."""
    def __init__(self, script):
        super().__init__(script)
        self.presentation = SimpleNamespace(scientific_prompt_states={})
        self.turns = []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        text, presented_instructions = _SessionConnection._presentation(
            self.presentation, episode_id, role, instructions, context)
        self.turns.append(dict(episode_id=episode_id, text=text,
            instructions=presented_instructions, output_schema=deepcopy(output_schema)))
        assert role == 'REASONING'
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        return response(context) if callable(response) else deepcopy(response)


def _tables(store):
    return {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name)] for name in (
        "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "runtime_forms",
        "runtime_report_attempts", "runtime_record_receipts", "runtime_receipt_inheritance", "tool_operations")}


def _archives(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()}


def test_registered_itc_fit_same_episode_next_iteration_saved_and_closed_replay(tmp_path, monkeypatch):
    supplied, fit_selection, expected = independent_engineering_dataset()
    raw_input = (json.dumps(supplied, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    directory = tmp_path / "run"
    directory.mkdir()
    native_calls, work_visits, frames, received = [], [], [], []
    with Store(tmp_path / "store") as store:
        problem = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        scope = dict(subject_refs=problem["subject_refs"])
        artifact = store.artifact(raw_input, "application/json")
        input_source = source_for_artifact(store, artifact)
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        assert tools.catalog()[ITC_TOOL]["resources"] == "local"
        assert tools.catalog()[ITC_TOOL]["input_schema"] == itc_tool_contract()["input_schema"]
        descriptor, selected = _libraries(directory, tools)
        request = _request(fit_selection, input_source["id"])
        form = obj(dict(sources={"type": "array", "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "source"}, "x-source": "changed_record_refs"}))
        commission = dict(selection=dict(kind="episode_child", role="scientific_process", goal=QUESTION,
            scope=scope, purpose="Return the retained ITC source identities from this investigation.",
            schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=selected,
                evidence_refs=[input_source["id"], artifact], constraints=dict(calibration="supplied_assertion"),
                context=dict(question=QUESTION, counted_unit="delivered_injection", delivered_injection_count=32))),
            report_update={})
        from gene_annotation_episode import native_lifecycle
        original_prepare = native_lifecycle.prepare_job

        def observe_prepare(command, **kwargs):
            payload = json.loads(Path(command[-2]).read_bytes())
            assert command[:3] == [__import__("sys").executable, "-m", "gene_annotation_episode.sequence_worker"]
            assert payload["operation"] == "itc_binding"
            assert kwargs["policy"].to_dict() == tools.local_job_policy.to_dict()
            native_calls.append(deepcopy(payload))
            return original_prepare(command, **kwargs)

        monkeypatch.setattr(native_lifecycle, "prepare_job", observe_prepare)
        original_worker, original_perform = tools._sequence_worker_async, tools._perform
        interrupt_once = [True]

        async def observe_worker(operation, arguments, **kwargs):
            selection_path = kwargs['directory'] / 'execution-selection.json'
            if arguments['request']['arguments']['mode'] == 'fit' and selection_path.exists():
                frozen_selection = json.loads(selection_path.read_bytes())
                protected = {row['path'] for row in [frozen_selection['python'], *frozen_selection['implementation_files']]}
                original_read = Path.read_bytes
                def deny_live_software_read(path):
                    assert str(path) not in protected, 'closed native collection read current implementation/software bytes'
                    return original_read(path)
                with monkeypatch.context() as guard:
                    guard.setenv('ITC_ENGINEERING_CHANGED_PARENT_ENVIRONMENT', 'different_after_original_dispatch')
                    guard.setattr(Path, 'read_bytes', deny_live_software_read)
                    work = await original_worker(operation, arguments, **kwargs)
            else:
                work = await original_worker(operation, arguments, **kwargs)
            work_visits.append(dict(mode=arguments["request"]["arguments"]["mode"], output=str(work.output_path),
                body=json.loads((work.output_path.parent / "native-handle.json").read_bytes())))
            return work

        def interrupt_after_original_fit(name, arguments, current_scope, prepared):
            if name == ITC_TOOL and arguments["mode"] == "fit" and interrupt_once[0]:
                interrupt_once[0] = False
                raise MolecularOperationUnpublished("engineered_interruption_after_original_worker_before_publication")
            return original_perform(name, arguments, current_scope, prepared)

        monkeypatch.setattr(tools, "_sequence_worker_async", observe_worker)
        monkeypatch.setattr(tools, "_perform", interrupt_after_original_fit)
        original_projection = ordinary.project_itc_tool_result
        projection_failure = [True]
        def fail_first_fit_projection(stored, **kwargs):
            if kwargs['selection']['mode'] == 'fit' and projection_failure[0]:
                projection_failure[0] = False
                raise ContractError('engineered_post_source_projection_failure')
            return original_projection(stored, **kwargs)
        monkeypatch.setattr(ordinary, 'project_itc_tool_result', fail_first_fit_projection)

        def fit_decision(context):
            frames.append(deepcopy(context))
            assert context["goal"]["objective"] == QUESTION
            assert {entry["name"] for entry in context["tools"]} >= {ITC_TOOL}
            assert context["scientific_process"]["selection"] == selected
            child = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()[0]
            actual_context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(child)
            parent_context = workflow.binding_context(root.source)
            original_commission = json.loads(store.db.execute('SELECT action FROM runtime_actions WHERE episode_id=? '
                'AND decision_index=0', (parent_context.episode_id,)).fetchone()['action'])
            compare = workflow.services.molecular_commission_assignment_matches
            def no_current_binding(*args, **kwargs):
                raise AssertionError('received input consulted a live scientific catalog or repriced its binding')
            with monkeypatch.context() as guard:
                guard.setattr(workflow.services, 'tool_catalog', no_current_binding)
                guard.setattr(workflow.services, 'tool_information_catalog', no_current_binding)
                guard.setattr(workflow.scientific_process_binding, 'prepare_assignment', no_current_binding)
                guard.setattr(workflow.scientific_process_binding, 'validate_context', no_current_binding)
                guard.setattr(workflow.scientific_process_binding, 'as_record', no_current_binding)
                before_read = store.db.total_changes
                assert compare(parent_context, actual_context, original_commission, decision_index=0) is True
                admitted = workflow.services.read_received_molecular_input(actual_context,
                    input_source["id"], "source", tag_key="version")
                assert store.db.total_changes == before_read
            altered = deepcopy(original_commission)
            altered['assignment']['context']['question'] = 'different assigned scientific question'
            assert compare(parent_context, actual_context, altered, decision_index=0) is False
            altered = deepcopy(original_commission)
            altered['assignment']['selection']['child_tool_info'][0]['resources'] = 'hpc'
            assert compare(parent_context, actual_context, altered, decision_index=0) is False
            from dataclasses import replace
            from gene_annotation_episode.communication import plain
            forged_request = plain(actual_context.request)
            forged_request['message']['episode_assignment']['selection']['child_tool_info'][0]['instructions'] = 'forged host instruction'
            forged = replace(actual_context, request=forged_request,
                assignment=forged_request['message']['episode_assignment'])
            assert compare(parent_context, forged, original_commission, decision_index=0) is False
            rejected = workflow.services.read_received_molecular_input(forged,
                input_source['id'], 'source', tag_key='version')
            assert rejected['input'] is None and rejected['failure']['code'] == 'invalid_context'
            def missing_frozen_file(*args, **kwargs):
                raise OSError('engineering unavailable frozen publication file')
            for owner, method in ((workflow.scientific_process_binding.tool_library, 'resolve_tool_info'),
                    (workflow.scientific_process_binding.library, 'resolve')):
                with monkeypatch.context() as guard:
                    guard.setattr(owner, method, missing_frozen_file)
                    before_read = store.db.total_changes
                    rejected = workflow.services.read_received_molecular_input(actual_context,
                        input_source['id'], 'source', tag_key='version')
                    assert rejected['input'] is None and rejected['failure']['code'] == 'invalid_commission'
                    assert store.db.total_changes == before_read
            assert admitted["failure"] is None and admitted["input"]["file"]["artifact_ref"] == artifact
            direct_file = workflow.services.read_received_molecular_input(actual_context,
                artifact, "artifact", tag_key="version")
            assert direct_file["failure"] is None and direct_file["input"]["file"] == admitted["input"]["file"]
            assert direct_file["input"]["content"]["value"] == supplied
            withheld = store.artifact('{"version":"withheld_engineering_input"}', "application/json")
            denied = workflow.services.read_received_molecular_input(actual_context, withheld, "artifact", tag_key="version")
            assert denied["failure"]["code"] == "reference_not_received" and denied["input"] is None
            resolver = workflow.episode_bindings.resolve_received_reference
            def deny_file(current, reference, namespace):
                return False if reference == artifact and namespace == "artifact" else resolver(current, reference, namespace)
            with monkeypatch.context() as guard:
                guard.setattr(workflow.episode_bindings, "resolve_received_reference", deny_file)
                denied = workflow.services.read_received_molecular_input(actual_context,
                    input_source["id"], "source", tag_key="version")
                assert denied["failure"]["code"] == "artifact_denied" and denied["input"] is None
            key = f"{workflow.run_id}:{child}:0"
            with tools.current_invocation(actual_context, read_received=workflow.services.read_received_molecular_input,
                    tool_name=ITC_TOOL, arguments=request, operation_key=key):
                with pytest.raises(ContractError, match="selected_action_conflict"):
                    authenticate_itc_invocation(tools, ITC_TOOL, request, scope, key)
            return _action(request)

        def saved_decision(context):
            frames.append(deepcopy(context))
            assert context['last_local_outcome']['status'] == 'partial'
            assert context['last_local_outcome']['feedback']['code'] == 'itc_result_projection_failed'
            partial = context["last_local_outcome"]["result"]
            assert partial['projection_state'] == 'unavailable' and 'source_ref' not in partial
            value, = partial['retained_sources']
            assert value["fit_call_state"] == "returned" and value["fit_call_count"] == 1
            child = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()[0]
            for reference in (value["source_ref"], value["native_file"]["artifact_ref"], value["grading_ref"]):
                receipt = store.db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts "
                    "WHERE episode_id=? AND record_ref=?", (child, reference)).fetchone()
                assert dict(receipt) == dict(receipt_kind="own_action", source_index=0)
            private_control = store.get(value['source_ref'])['request_ref']
            assert private_control not in set(workflow.receipts.known(child))
            received.append(deepcopy(value))
            return _action(dict(mode="calculate_saved", result_ref=value["source_ref"],
                parameter_source="selected_parameters", parameters={**expected, 'kd': 6e-6},
                injection_ordinals=list(range(32)), fit_diagnostics=True))

        def literal_decision(context):
            frames.append(deepcopy(context))
            saved = context["last_local_outcome"]["result"]
            assert saved["source_ref"] != received[0]["source_ref"]
            assert saved['parameter_source'] == 'selected_parameters'
            assert saved['parameters']['kd']['value'] == 6e-6
            assert saved["parameters"]['n']['value'] == pytest.approx(expected['n'], rel=1e-4)
            assert len(saved['rows']) == 32
            assert saved['fit_diagnostics_scope'] == saved['covariance_scope'] == 'retained_original_fit_vector_and_residual_population'
            received.append(deepcopy(saved))
            return _action(dict(mode="read_stored", result_ref=saved["source_ref"],
                injection_ordinals=[31, 0], fields=["predicted_heat", "residual"]))

        provider = _RenderedScript([commission, fit_decision, saved_decision, literal_decision])
        controllers = []

        def control(path, initial):
            result = FixtureController(str(path), initial, 1 if len(path) == 1 else 3)
            controllers.append(result)
            return result

        def zero_credit(store, scope, **assignment): return 0

        def make_workflow():
            return Workflow(store, tools, provider, directory, "ordinary-itc-fixture", control,
                zero_credit, project_child_credit=zero_credit, episode_binding_descriptors=[descriptor],
                episode_record_receipts=True, initial_known_record_refs=[input_source["id"], artifact])

        workflow = make_workflow()
        root = workflow.build("annotation", "root", QUESTION, scope)
        with pytest.raises(MolecularOperationUnpublished, match="engineered_interruption"):
            asyncio.run(root.run_async(workflow.context))
        assert len(native_calls) == 1 and len(work_visits) == 1
        assert not store.db.execute("SELECT 1 FROM tool_operations").fetchone()
        assert store.get_artifact(artifact) == raw_input
        original_handle = deepcopy(work_visits[0]["body"])
        original_identities = [(row["episode_id"], row["path"], row["request"]) for row in
            store.db.execute("SELECT episode_id,path,request FROM runtime_episodes ORDER BY episode_id")]
        assert all(controller.scores == [] for controller in controllers)
        workflow = make_workflow()
        root = workflow.build("annotation", "root", QUESTION, scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        assert len(provider.contexts) == 4 and len(provider.turns) == 4
        assert len(frames) == 3
        assert [len(controller.scores) for controller in controllers] == [0, 0, 1, 3]
        assert [(row["episode_id"], row["path"], row["request"]) for row in
            store.db.execute("SELECT episode_id,path,request FROM runtime_episodes ORDER BY episode_id")] == original_identities
        episodes = [dict(row) for row in store.db.execute("SELECT * FROM runtime_episodes")]
        assert len(episodes) == 2
        child, = [row for row in episodes if len(json.loads(row["path"])) == 2]
        assert json.loads(child["path"])[-1][0] == "scientific_process"
        actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE episode_id=? "
            "ORDER BY decision_index", (child["episode_id"],))]
        assert [json.loads(row["action"])["tool"] for row in actions] == [ITC_TOOL] * 3
        assert all(json.loads(row["action"])["kind"] == "tool" for row in actions)
        assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?",
            (child["episode_id"],)).fetchone()[0] == len(actions) == 3
        assert [call["arguments"]["request"]["arguments"]["mode"] for call in native_calls] == ["fit", "calculate_saved"]
        assert len(work_visits) == 3 and work_visits[0]["body"] == work_visits[1]["body"] == original_handle
        assert work_visits[0]["output"] == work_visits[1]["output"]
        assert work_visits[2]["body"]["unit"] != original_handle["unit"]
        outcomes = [json.loads(row["result"]) for row in actions]
        assert [row['status'] for row in outcomes] == ['partial', 'completed', 'completed']
        assert outcomes[2]["changed_record_refs"] == []
        assert [row["injection_ordinal"] for row in outcomes[2]["result"]["rows"]] == [31, 0]
        assert set(outcomes[2]["result"]["rows"][0]) == {"injection_ordinal", "predicted_heat", "residual"}
        original_source = store.get(outcomes[0]["result"]['retained_sources'][0]["source_ref"])
        assert "operand_refs" not in original_source
        assert original_source["parent_source_refs"] == [input_source["id"]]
        raw_result = store.get_artifact(original_source["artifact_ref"])
        assert raw_result == Path(work_visits[0]["output"]).read_bytes()
        produced = json.loads(raw_result)
        assert produced["request"]["input_file"]["artifact_ref"] == artifact
        assert produced["request"]["input_file"]["sha256"] == hashlib.sha256(raw_input).hexdigest()
        assert produced["request"]["fit_selection"] == fit_selection
        assert produced["request"]["arguments"] == request
        control_record = json.loads(store.get_artifact(original_source["request_ref"]))
        assert control_record["request"]["invocation"]["episode_id"] == child["episode_id"]
        assert control_record["request"]["received_input"]["file"] == produced["request"]["input_file"]
        assert control_record["native_handle"] == original_handle
        assert control_record["native_artifact_ref"] == original_source["artifact_ref"]
        assert 'ITC_ENGINEERING_CHANGED_PARENT_ENVIRONMENT' not in control_record['execution_selection']['environment']
        assert set(produced["request"]) == {"version", "arguments", "sheet", "fit_selection", "selection", "input_file"}
        grading, = source_tool_grading_entries(store, original_source["id"])
        assert grading["grading"] == dict(sheet=produced["sheet"], scores=produced["components"])
        saved_source = store.get(outcomes[1]['result']['source_ref'])
        saved_native = json.loads(store.get_artifact(saved_source['artifact_ref']))
        assert saved_native['sheet'] == produced['sheet']
        assert saved_native['components']['selection']['parameters'] == {**expected, 'kd': 6e-6}
        assert saved_native['components']['fit_diagnostics'] == produced['components']['fit_diagnostics']
        assert any(a['predicted_heat'] != b['predicted_heat'] for a, b in
            zip(saved_native['components']['rows'], produced['components']['rows']))
        assert outcomes[1]['result']['covariance_estimate'] == produced['sheet']['fit_observation']['native_covariance']
        assert outcomes[1]['result']['sse']['value'] == produced['components']['fit_diagnostics']['sse']['value']
        assert store.get_artifact(artifact) == raw_input
        assert_actual_itc_fit_and_saved_recalculation(supplied_input=supplied, selection=fit_selection,
            expected=expected, observation=produced["sheet"]["fit_observation"], sheet=produced["sheet"],
            components=produced["components"], monkeypatch=monkeypatch)
        scientific_turns = [turn for turn in provider.turns if turn["episode_id"] == child["episode_id"]]
        assert len(scientific_turns) == 3
        assert all(turn["text"].startswith("TASK\n") and QUESTION in turn["text"]
            and "\n\nSTEERING\n" in turn["text"] for turn in scientific_turns)
        assert "Selected tool: " + ITC_TOOL in scientific_turns[1]["text"]
        assert original_source['id'] in scientific_turns[1]["text"]
        assert "mol_per_litre" in scientific_turns[2]["text"]
        assert "fit_call_count" in scientific_turns[1]["text"]
        write(tmp_path / "ACTUAL_ITC_TURNS.json", provider.turns)
        write(tmp_path / "ACTUAL_ITC_DELIVERY.json", dict(question=QUESTION,
            input_artifact=artifact, fit_source=original_source["id"], native_handle=original_handle,
            actions=[json.loads(row["action"]) for row in actions], outcomes=outcomes))

        # Shape alone cannot authorize a source relabeling or a forged result.
        context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(child["episode_id"])
        actual_reader = workflow.services.read_received_molecular_input
        resolve_child = workflow.resolver(scope, context=context)
        assert resolve_child(original_source['id'], 'source') is True
        assert resolve_child(original_source['artifact_ref'], 'artifact') is True
        assert resolve_child(grading['artifact_ref'], 'artifact') is True
        assert resolve_child(original_source['request_ref'], 'artifact') is False
        assert workflow.services.reference_in_context(context, original_source['request_ref'], 'artifact') is False
        # This is a typed resolver/form control, not a newly commissioned rich
        # numerical return or another model decision.
        file_form = obj(dict(selected_file={'type': 'string', 'format': 'reference', 'x-reference-namespace': 'artifact'}))
        with pytest.raises(ReportBoundaryError):
            validate_form(dict(selected_file=original_source['request_ref']), file_form, resolve_child)
        legitimate = actual_reader(context, original_source["id"], "source", tag_key="version")
        assert legitimate['failure'] is None
        hidden = actual_reader(context, original_source['request_ref'], 'artifact', tag_key='version')
        assert hidden['input'] is None and hidden['failure']['code'] == 'reference_not_received'
        parent_known = set(workflow.receipts.known(root.source.episode_id))
        parent_context = workflow.binding_context(root.source)
        resolve_parent = workflow.resolver(scope, context=parent_context)
        for value in received:
            assert value['source_ref'] in parent_known
            assert value['native_file']['artifact_ref'] not in parent_known and value['grading_ref'] not in parent_known
            assert store.get(value['source_ref'])['request_ref'] not in parent_known
            assert resolve_parent(value['source_ref'], 'source') is True
            for reference in (value['native_file']['artifact_ref'], value['grading_ref'], store.get(value['source_ref'])['request_ref']):
                assert resolve_parent(reference, 'artifact') is False
                assert workflow.services.reference_in_context(parent_context, reference, 'artifact') is False
        assert resolve_parent(artifact, 'artifact') is True  # Ordinary caller File behavior is unchanged.
        forged = deepcopy(legitimate)
        forged["input"]["witness"]["record"]["provider"] = "caller"
        with pytest.raises(ContractError, match="producer_required"):
            read_retained_itc_result(tools, context, lambda *a, **k: forged, original_source["id"])

        # Completed tree replay consumes frozen facts and the original source;
        # it neither dispatches another worker nor makes another model decision.
        before, archives = _tables(store), _archives(directory / "archive")
        def forbidden(*args, **kwargs): raise AssertionError("closed replay attempted new work")
        with monkeypatch.context() as guard:
            guard.setattr(tools, "_sequence_worker_async", forbidden)
            guard.setattr(native_lifecycle, "prepare_job", forbidden)
            guard.setattr(native_lifecycle, "resume_start", forbidden)
            guard.setattr(provider, "complete", forbidden)
            replay = workflow.build("annotation", "root", QUESTION, scope)
            replay_record = asyncio.run(replay.run_async(workflow.context))
            asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before and _archives(directory / "archive") == archives
        assert store.get_artifact(artifact) == raw_input


def test_itc_registry_without_current_selected_episode_cannot_fit(tmp_path):
    supplied, selection, _ = independent_engineering_dataset()
    with Store(tmp_path / "store") as store:
        problem = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        artifact = store.artifact(canonical(supplied), "application/json")
        source = source_for_artifact(store, artifact)
        tools = ToolRegistry(store)
        with pytest.raises(ContractError, match="current_invocation_required"):
            asyncio.run(tools.execute_async(ITC_TOOL, _request(selection, source["id"]),
                scope=dict(subject_refs=problem["subject_refs"]), operation_key="manual:fit:0"))
        assert not store.db.execute("SELECT 1 FROM tool_operations").fetchone()
        assert not (store.path / "cache/molecular-measurements").exists()


def _terminal_fixture(monkeypatch, kind):
    """Actual-shaped lifecycle data only; never submits or executes a process."""
    from gene_annotation_episode import native_lifecycle as native
    from gene_annotation_episode._local_job_worker import atomic_json
    from gene_annotation_episode.acquisition import AcquisitionError
    from gene_annotation_episode.local_jobs import LocalJobResult
    calls = dict(prepare=0, release=0, collect=0)

    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls['prepare'] += 1
        paths = {key: str(cwd / ('engineering-' + key)) for key in
            ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        for path in (stdout_path, stderr_path): path.write_bytes(b'')
        atomic_json(paths['request'], dict(command=command, cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=env))
        atomic_json(handle_path, dict(version=native.VERSION, unit='engineering_terminal_fixture.service',
            command=command, cwd=str(cwd), stdout=str(stdout_path), stderr=str(stderr_path), paths=paths,
            metadata=native._metadata(policy), stage='prepared', started_at=None, started_monotonic_ns=None,
            boot_id=None, request_sha256=hashlib.sha256(Path(paths['request']).read_bytes()).hexdigest()))
        return native.NativeJobHandle(handle_path)

    def resume(handle, **kwargs):
        calls['release'] += 1
        body = handle.read(); body['stage'] = 'released'
        atomic_json(handle.path, body); Path(body['paths']['release']).touch()
        return handle

    def status(handle):
        body = handle.read(); terminal = body['stage'] == 'released'
        returncode = {'nonzero': 7, 'oom': -9, 'output_missing': 0}[kind]
        return dict(state='returned' if terminal else 'prepared', terminal=terminal, quiescent=True,
            metadata={**body['metadata'], 'native_returncode': returncode if terminal else None},
            native_receipt=dict(native_returncode=returncode, execution_failure=None,
                resource_failure=None) if terminal else None, files={})

    def collect(handle):
        calls['collect'] += 1
        body, view = handle.read(), status(handle)
        if kind == 'oom':
            raise AcquisitionError('local_job_resource_limit', phase='local_execution', operational={
                **view['metadata'], 'resource': 'memory_bytes', 'limit': body['metadata']['policy']['memory_bytes'],
                'evidence': {'engineering_fixture': 'terminal_oom'}})
        return LocalJobResult(view['metadata']['native_returncode'], Path(body['stdout']), Path(body['stderr']), view['metadata'])

    monkeypatch.setattr(native, 'prepare_job', prepare)
    monkeypatch.setattr(native, 'resume_start', resume)
    monkeypatch.setattr(native, 'status', status)
    monkeypatch.setattr(native, 'collect', collect)
    monkeypatch.setattr(native, 'wait_job', lambda handle, **kwargs: collect(handle))
    return calls


@pytest.mark.parametrize('kind,code', [('nonzero', 'local_job_execution_failed'),
    ('oom', 'local_job_resource_limit'), ('output_missing', 'local_job_output_missing')])
def test_known_terminal_worker_failure_is_durable_and_never_invented_fit_zero(tmp_path, monkeypatch, kind, code):
    """Failure classification/custody fixture, not an actual OOM or fit attempt."""
    calls = _terminal_fixture(monkeypatch, kind)
    supplied, selection, _ = independent_engineering_dataset()
    with Store(tmp_path / 'store') as store:
        scope = dict(subject_refs=store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs'])
        file = store.artifact(canonical(supplied), 'application/json')
        source = source_for_artifact(store, file)
        request = _request(selection, source['id'])
        tools = ToolRegistry(store)
        directory = tmp_path / 'run'; directory.mkdir()
        descriptor, selected = _libraries(directory, tools, tool_names=(ITC_TOOL, 'state.query'))
        commission = dict(selection=dict(kind='episode_child', role='scientific_process', goal=QUESTION,
            scope=scope, purpose='Exercise the explicitly selected terminal failure and subsequent inspection.',
            schema_json=json.dumps(obj(dict(sources={'type': 'array', 'items': {'type': 'string',
                'format': 'reference', 'x-reference-namespace': 'source'}, 'x-source': 'changed_record_refs'}))),
            initial_report_json='{}', assignment=dict(selection=selected,
                evidence_refs=[source['id'], file], constraints={}, context=dict(question=QUESTION))), report_update={})
        def inspect_failed(context):
            assert context['feedback']['code'] == code
            failed = store.db.execute('SELECT result FROM tool_operations WHERE name=?', (ITC_TOOL,)).fetchone()
            value = json.loads(failed['result'])
            assert value['status'] == 'failed' and value['feedback'] == context['feedback']
            assert context['feedback']['fit_call_state'] == 'uncertain'
            assert context['feedback']['fit_call_count'] is None
            return dict(selection=dict(kind='tool', tool='state.query', arguments=dict(refs=[file])), report_update={})
        provider = _RenderedScript([commission, _action(request), inspect_failed])
        controllers = []
        def control(path, initial):
            controller = FixtureController(str(path), initial, 1)
            controllers.append(controller)
            return controller
        workflow = Workflow(store, tools, provider, directory, 'itc-terminal-fixture',
            control, lambda store, scope: 0,
            project_child_credit=lambda store, scope, **kwargs: 0,
            episode_binding_descriptors=[descriptor],
            episode_record_receipts=True, initial_known_record_refs=[source['id'], file])
        root = workflow.build('annotation', 'root', QUESTION, scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        failed = store.db.execute('SELECT * FROM tool_operations WHERE name=?', (ITC_TOOL,)).fetchone()
        result = json.loads(failed['result'])
        assert result['status'] == 'failed' and result['record_refs'] == []
        assert result['feedback']['fit_call_count'] is None
        private = json.loads(store.get_artifact(result['feedback']['diagnostic_ref']))['details']
        assert private['handle']['unit'] == 'engineering_terminal_fixture.service'
        assert private['observation']['terminal'] is True
        assert private['selection']['request']['arguments']['request']['arguments'] == request
        assert calls == dict(prepare=1, release=1, collect=1)
        episodes = [dict(row) for row in store.db.execute('SELECT * FROM runtime_episodes')]
        assert len(episodes) == 2
        child, = [row for row in episodes if len(json.loads(row['path'])) == 2]
        assert json.loads(child['path'])[-1][0] == 'scientific_process'
        context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix='test_').context(child['episode_id'])
        assert workflow.resolver(scope, context=context)(result['feedback']['diagnostic_ref'], 'artifact') is False
        with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                tool_name=ITC_TOOL, arguments=request, operation_key=failed['operation_key']):
            assert asyncio.run(tools.execute_async(ITC_TOOL, request, scope=scope,
                operation_key=failed['operation_key'])) == result
        assert calls == dict(prepare=1, release=1, collect=1)
        assert len(provider.contexts) == 3
        actions = [json.loads(row['action']) for row in store.db.execute(
            'SELECT action FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (child['episode_id'],))]
        statuses = [json.loads(row['result'])['status'] for row in store.db.execute(
            'SELECT result FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (child['episode_id'],))]
        assert [action['tool'] for action in actions] == [ITC_TOOL, 'state.query']
        assert statuses == ['failed', 'completed']
        assert len(controllers) == 2 and [len(controller.scores) for controller in controllers] == [1, 1]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
        assert not store.list('source') or all(row['provider'] != ITC_TOOL for row in store.list('source'))


def test_unreleased_original_software_mismatch_rejects_before_dispatch(tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle as native
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    calls = _terminal_fixture(monkeypatch, 'nonzero')
    prepare = native.prepare_job
    def interrupted_prepare(*args, **kwargs):
        prepare(*args, **kwargs)
        raise RuntimeError('engineered_crash_after_preparation_before_dispatch')
    monkeypatch.setattr(native, 'prepare_job', interrupted_prepare)
    directory = tmp_path / 'owned'; directory.mkdir()
    arguments = dict(request=dict(arguments=dict(mode='fit')))
    policy = LocalJobPolicy(20 * 1024 ** 3, 4 * 1024 ** 3)
    with pytest.raises(RuntimeError, match='engineered_crash_after_preparation'):
        ordinary.run_owned_molecular_worker('itc_binding', arguments, directory=directory,
            owned_directory=directory, policy=policy, cancel_event=threading.Event())
    assert calls == dict(prepare=1, release=0, collect=0)
    original = (directory / 'native-handle.json').read_bytes()
    selection = json.loads((directory / 'execution-selection.json').read_bytes())
    changed = selection['implementation_files'][0]['path']
    read = Path.read_bytes
    def changed_bytes(path):
        return b'engineered_changed_software_bytes' if str(path) == changed else read(path)
    monkeypatch.setattr(Path, 'read_bytes', changed_bytes)
    with pytest.raises(ContractError, match='original_software_changed_before_dispatch'):
        ordinary.run_owned_molecular_worker('itc_binding', arguments, directory=directory,
            owned_directory=directory, policy=policy, cancel_event=threading.Event())
    assert (directory / 'native-handle.json').read_bytes() == original
    assert calls == dict(prepare=1, release=0, collect=0)
