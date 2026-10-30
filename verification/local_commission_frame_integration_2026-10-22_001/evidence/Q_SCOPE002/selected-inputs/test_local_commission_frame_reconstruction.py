"""Factual v3/v6 routing through the actual fixed_case caller and worker.

All provider messages are scripted local RPC replies.  The unchanged production
YieldController compares its estimate's available upper bound with cost=0; the
existing test_case_execution policy supplies an explicit fixture estimate of 1
until stop_after completed actions and 0 thereafter.  Those fixture counts are
not runtime limits or a pending-aware numerical model.  Constant fixture credit
is zero.  Only state.query and an explicitly selected report wait are executed.

Raw synthetic stores, provider requests, worker logs and fixture gates live in
dedicated /tmp directories, never pytest's automatically pruned temporary tree.
The source-pin-gated operator runner records the invocation and retains failures.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import uuid

import pytest

from gene_annotation_episode.case_execution import (
    prepare_case_run, prepared_case_bindings, run_prepared_case)
from gene_annotation_episode.completion_evidence import CompletionEvidence
from gene_annotation_episode.independent_execution import implementation_sha256, open_commission
from gene_annotation_episode.local_commission_frame import LocalCommissionFrame
from gene_annotation_episode.providers import ModelCallError
from gene_annotation_episode.runtime import Workflow, _action_generation_schema, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from method_loop.durable import DurableExecutionStore, canonical, content_digest
from test_case_execution import PARAMETERS, prepared


FRAME = "local_commission_frame_v1"
REQUEST = "runtime_model_call_request_v3"
CONTEXT = "completed_action_estimation_context_v6"
EVIDENCE_ENV = "GENE_EPISODE_FRAME_RECONSTRUCTION_EVIDENCE_ROOT"
AUDIT_ENV = "GENE_EPISODE_FRAME_CAPTURE_AUDIT"


TRANSPORT = r'''import json, os, sys, time
from pathlib import Path
log, gate, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
def emit(value):
    print(json.dumps(value), flush=True)
def record(kind, params):
    with log.open('a') as stream:
        stream.write(json.dumps({'kind': kind, 'pid': os.getpid(), 'params': params})+'\n')
for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params', {})
    if 'id' not in message:
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/start':
        record(method, params)
        result = {'thread': {'id': 'scripted-frame-thread'}, 'model': params['model'],
                  'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        record(method, params)
        if mode == 'interrupt':
            sys.exit(5)  # Deliberate transport interruption after original request save.
        context = json.loads(params['input'][0]['text'])
        assert 'local_commission_frame' not in context
        if context['goal']['parent_goal_id']:
            # Test synchronization only: no episode work is selected by this gate.
            deadline = time.monotonic()+45
            while not gate.exists():
                if time.monotonic() >= deadline:
                    raise AssertionError('fixture report gate was not released')
                time.sleep(.01)
            selected = {'kind': 'tool', 'tool': 'state.query',
                        'arguments': {'refs': context['scope']['subject_refs']}}
            update = {'finding': 'qualified' if context['last_local_outcome'] else 'unknown'}
        elif not context['pending_work']['items'] and not context['child_reports']:
            form = {'type': 'object', 'properties': {
                'finding': {'type': 'string', 'enum': ['unknown', 'qualified']},
                'subjects': {'type': 'array', 'items': {'type': 'string',
                    'format': 'reference', 'x-reference-namespace': 'input'},
                    'x-source': 'subject_refs'}},
                'required': ['finding', 'subjects'], 'additionalProperties': False}
            selected = {'kind': 'child',
                'goal': 'Inspect the original bounded synthetic fixture inputs',
                'scope': context['scope'],
                'purpose': 'Return the original constrained fixture interpretation',
                'schema_json': json.dumps(form),
                'initial_report_json': json.dumps({'finding': 'unknown'})}
            update = {}
        elif context['pending_work']['items']:
            item, = context['pending_work']['items']
            assert item['return_available'] is False
            selected = {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
                'events': [{'handle': item['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}}
            update = {}
        else:
            assert context['child_reports'][0]['finding'] == 'qualified'
            selected = {'kind': 'tool', 'tool': 'state.query',
                        'arguments': {'refs': context['scope']['subject_refs']}}
            update = {}
        response = {'selection': selected, 'report_update': update}
        emit({'id': message['id'], 'result': {'turn': {'id': 'scripted-frame-turn'}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': 'scripted-frame-turn', 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
'''


BOOTSTRAP = '''import os
if 'GENE_EPISODE_FRAME_CAPTURE_AUDIT' in os.environ:
    from pathlib import Path
    from gene_annotation_episode.runtime import Workflow
    from test_local_commission_frame_reconstruction import audited_capture
    Workflow.capture_local_commission_frame = audited_capture(
        Workflow.capture_local_commission_frame,
        Path(os.environ['GENE_EPISODE_FRAME_CAPTURE_AUDIT']))
'''


def forbidden(*args, **kwargs):
    raise AssertionError("saved frame/request/completion replay must not recapture or dispatch")


def audited_capture(original, log):
    """Inspect actual root/worker ownership without replacing any factual input."""
    def capture(workflow, episode_id, *, pending, controller_credit):
        readers = [value for value in vars(workflow).values()
                   if isinstance(value, LocalCommissionFrame)]
        assert len(readers) == 1
        reader, = readers
        assert reader.store is workflow.store
        assert reader.journal is workflow.journal
        assert reader.backend is workflow.execution_backend
        assert reader.returns.backend is workflow.execution_backend
        assert workflow.journal.db is workflow.store.db
        assert workflow.execution_binding is not None
        changes = workflow.store.db.total_changes
        value = original(workflow, episode_id, pending=pending,
                         controller_credit=controller_credit)
        assert workflow.store.db.total_changes == changes
        entry = {"pid": os.getpid(), "episode_id": episode_id,
                 "execution_handle": workflow.execution_handle,
                 "implementation_sha256": workflow.execution_binding["implementation_sha256"],
                 "pending_sha256": content_digest(pending),
                 "controller_credit_sha256": content_digest(controller_credit),
                 "frame_sha256": content_digest(value)}
        with Path(log).open("a") as stream:
            stream.write(json.dumps(entry)+"\n")
        return value
    return capture


@pytest.fixture
def evidence_dir(request):
    parent = os.environ.get(EVIDENCE_ENV)
    label = re.sub(r"[^A-Za-z0-9_-]", "_", request.node.name)
    if parent is None:
        directory = Path(tempfile.mkdtemp(prefix="gene-annotation-frame-reconstruction-"))
    else:
        directory = Path(parent)/f"{label}-{uuid.uuid4().hex}"
        directory.mkdir(parents=True, exist_ok=False)
    (directory/"fixture.json").write_text(json.dumps({
        "test": request.node.nodeid, "fixture_only": True,
        "live_model_network_native_science": False,
        "retention": "dedicated directory; no pytest pruning"}, indent=2)+"\n")
    return directory


def fixture_case(directory, monkeypatch, *, presentation, mode="route"):
    import sys
    case, configuration, policy = prepared(directory, with_protein=False)
    configuration["restoration"] = {"preview_size": 0}
    if presentation:
        configuration["restoration"]["model_presentation"] = "bounded_wait_history_v1"
    transport, turns, gate = (directory/name for name in
                              ("transport.py", "turns.jsonl", "release-worker"))
    transport.write_text(TRANSPORT)
    configuration["models"]["connection"]["command"] = [
        sys.executable, str(transport), str(turns), str(gate), mode]
    bootstrap = directory/"bootstrap"
    bootstrap.mkdir()
    (bootstrap/"sitecustomize.py").write_text(BOOTSTRAP)
    monkeypatch.syspath_prepend(str(bootstrap))
    audit = directory/"capture-audit.jsonl"
    monkeypatch.setenv(AUDIT_ENV, str(audit))
    monkeypatch.setattr(Workflow, "capture_local_commission_frame",
        audited_capture(Workflow.capture_local_commission_frame, audit))
    run = directory/"run"
    manifest = prepare_case_run(case, run, configuration)
    return case, run, policy, manifest, turns, gate, audit


async def release_after_selected_wait(workspace, gate):
    """Fixture gate only; the runtime first saves the episode's selected wait."""
    deadline = asyncio.get_running_loop().time()+45
    while asyncio.get_running_loop().time() < deadline:
        database = workspace/"state.sqlite3"
        db = None
        try:
            db = sqlite3.connect(database.as_uri()+"?mode=ro", uri=True)
            db.execute("PRAGMA query_only=ON")
            selected = db.execute("SELECT 1 FROM episode_waits WHERE outcome IS NULL").fetchone()
        except sqlite3.OperationalError:
            selected = None
        finally:
            if db is not None:
                db.close()
        if selected:
            gate.write_text("release only after actual selected wait\n")
            return
        await asyncio.sleep(.01)
    raise AssertionError("fixture did not observe a selected wait")


def snapshot(store):
    queries = {
        "requests": "SELECT episode_id,call_index,request,response FROM runtime_model_calls ORDER BY episode_id,call_index",
        "contexts": "SELECT episode_id,decision_index,data FROM runtime_estimation_contexts ORDER BY episode_id,decision_index",
        "observations": "SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index",
        "commissions": "SELECT * FROM runtime_commission_intents ORDER BY parent_episode_id,original_decision_index",
        "admissions": "SELECT * FROM runtime_return_admissions ORDER BY parent_episode_id,original_decision_index",
        "slots": "SELECT * FROM runtime_completion_slots ORDER BY episode_id,sequence"}
    return {key: [tuple(row) for row in store.db.execute(query)]
            for key, query in queries.items()}


def saved_run(directory):
    value = json.loads((directory/"run.json").read_text())
    return value["run_id"], {key: item for key, item in value.items() if key != "run_id"}


@contextmanager
def reopened_root(workspace, directory, manifest, provider):
    run_id, settings = saved_run(directory)
    binding = json.loads((directory/"episode-execution-binding.json").read_text())
    with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
        workflow = assemble_workflow(store, build_tools(store, manifest["configuration"]),
            provider, directory, run_id, settings,
            **{key: value for key, value in options.items() if key != "binding_definitions"})
        backend = workflow.execution_backend
        workflow.configure_execution(binding)
        assert workflow.execution_backend is backend
        root = workflow.build("annotation", "root", settings["goal"],
            {"subject_refs": [manifest["target_ref"]]})
        yield store, workflow, root


def assert_request_view(request, sent, *, presentation):
    assert request["version"] == REQUEST
    fields = {"version", "context", "schema", "local_commission_frame"}
    if presentation:
        fields.add("model_presentation")
    assert set(request) == fields
    actual = request["model_presentation"]["context"] if presentation else request["context"]
    assert sent["input"] == [{"type": "text", "text": json.dumps(actual, allow_nan=False)}]
    assert json.dumps(sent["outputSchema"], allow_nan=False) == json.dumps(
        _action_generation_schema(request["schema"]), allow_nan=False)
    assert "local_commission_frame" not in canonical(actual)
    assert "local_commission_frame" not in request["context"]["waiting_support"]
    assert request["local_commission_frame"]["version"] == FRAME
    assert request["local_commission_frame"]["pending_captured_at"] == request[
        "context"]["pending_work"]["captured_at"]


@pytest.mark.parametrize("presentation", [False, True])
def test_actual_fixed_case_root_worker_frames_preserve_prompt_payoff_and_replay(
        evidence_dir, monkeypatch, presentation):
    case, run, policy, manifest, turns, gate, audit = fixture_case(
        evidence_dir, monkeypatch, presentation=presentation)
    workspace = case/"workspace"

    async def exercise():
        release = asyncio.create_task(release_after_selected_wait(workspace, gate))
        try:
            result = await asyncio.wait_for(run_prepared_case(run, policy_file=policy,
                parameters={**PARAMETERS, "stop_after": 3}), 60)
            await release
            return result
        finally:
            # Keep a failed fixture's selected worker able to close; do not cancel it.
            gate.write_text("fixture cleanup release\n")
            if not release.done():
                release.cancel()
            await asyncio.gather(release, return_exceptions=True)

    result = asyncio.run(exercise())
    assert result["completed_actions"] == 3 and result["credit"] == 0
    assert result["pending_handles"] == []
    assert result["scientific_completion"] == "not_established_by_termination"
    run_id, settings = saved_run(run)
    binding = json.loads((run/"episode-execution-binding.json").read_text())
    assert binding["arguments"]["kind"] == "fixed_case"
    assert binding["implementation_sha256"] == implementation_sha256()
    messages = [json.loads(line) for line in turns.read_text().splitlines()]
    sent = [item for item in messages if item["kind"] == "turn/start"]
    assert len(sent) == 6
    assert all("local_commission_frame" not in canonical(item["params"])
               for item in messages)
    sent_by_role = {role: [item for item in sent
        if bool(json.loads(item["params"]["input"][0]["text"])["goal"]["parent_goal_id"])
            == (role == "improvement")]
        for role in ("annotation", "improvement")}
    assert all(len(rows) == 3 for rows in sent_by_role.values())
    assert len({item["pid"] for item in sent_by_role["improvement"]}) == 1

    with Store(workspace) as store:
        spec, = [json.loads(row[0]) for row in store.db.execute(
            "SELECT spec FROM runtime_commission_intents")]
        assert spec["runtime_binding"] == binding
        root_id, child_id = (spec[side]["episode_id"] for side in ("parent", "child"))
        assert spec["child"]["request"] == json.loads(store.db.execute(
            "SELECT request FROM runtime_episodes WHERE episode_id=?", (child_id,)).fetchone()[0])
        requests = {}
        contexts = {}
        observations = {}
        for episode_id, role in ((root_id, "annotation"), (child_id, "improvement")):
            requests[episode_id] = [json.loads(row[0]) for row in store.db.execute(
                "SELECT request FROM runtime_model_calls WHERE episode_id=? ORDER BY call_index",
                (episode_id,))]
            contexts[episode_id] = {row[0]: json.loads(row[1]) for row in store.db.execute(
                "SELECT decision_index,data FROM runtime_estimation_contexts WHERE episode_id=?",
                (episode_id,))}
            observations[episode_id] = [json.loads(row[0]) for row in store.db.execute(
                "SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index",
                (episode_id,))]
            for request, actual in zip(requests[episode_id], sent_by_role[role]):
                assert_request_view(request, actual["params"], presentation=presentation)
            assert len(observations[episode_id]) == len(contexts[episode_id]) == 3
            for sequence, observed in enumerate(observations[episode_id]):
                index = observed["decision_index"]
                context = contexts[episode_id][index]
                assert context["version"] == CONTEXT
                assert context["local_commission_frame_at_selection"] == requests[episode_id][index][
                    "local_commission_frame"]
                assert context["current_completion_evidence"]["unit_ref"] == observed["unit_ref"]
                assert context["current_completion_evidence"]["original_decision_index"] == index
                assert context["pending_work_after_action"] == json.loads(store.db.execute(
                    "SELECT result FROM runtime_actions WHERE episode_id=? AND decision_index=?",
                    (episode_id, index)).fetchone()[0])["pending_work_after_action"]
                assert "pending_wait_models" not in context
                step = observed["step"]
                assert step["marginal_credit"] == 0
                assert step["estimate"]["turns"] == sequence+1
                assert step["estimate"]["diagnostics"] == {"kind": "fixture_only_not_production"}
                assert step["decision"]["continuation_cost"] == 0
                assert step["decision"]["projected_gain"]["upper"] == (0 if sequence == 2 else 1)
                assert step["decision"]["stop"] is (sequence == 2)
        assert [row["decision_index"] for row in observations[root_id]] == [1, 0, 2]
        assert [row["decision_index"] for row in observations[child_id]] == [0, 1, 2]
        initial = requests[root_id][0]["local_commission_frame"]
        assert initial["population_status"] == "complete" and initial["population_count"] == 0
        before_wait, = requests[root_id][1]["local_commission_frame"]["commissions"]
        assert before_wait["handle"] == spec["handle"]
        assert before_wait["accounting_status"] == "pending"
        assert before_wait["pending_status_fact"]["return_available"] is False
        assert before_wait["return_presence"] == "not_observed_in_completed_scan"
        assert before_wait["admission_evidence"] is None
        wait_context = contexts[root_id][1]
        after_wait, = wait_context["local_commission_frame_after_action"]["commissions"]
        assert after_wait["accounting_status"] == "pending"
        assert after_wait["return_presence"] == "observed"
        assert after_wait["return_metadata"]["outcome"] == "closed"
        assert after_wait["pending_status_fact"]["return_available"] is True
        assert after_wait["admission_evidence"] is None
        assert wait_context["current_completion_evidence"]["child_return"] is None
        assert wait_context["wait_outcome"]["wake_reason"] == "returned"
        returned_context = contexts[root_id][0]
        admitted, = returned_context["local_commission_frame_after_action"]["commissions"]
        sample = admitted["admission_evidence"]["sample"]
        assert sample["admission_state"] == "admitted"
        assert sample["observation_state"] == "unobserved"
        assert sample["raw_controller_delta"] is sample["unit_ref"] is None
        assert sample["completion_sequence"] == 1
        assert returned_context["current_completion_evidence"]["child_return"]["admission_id"] == sample["admission_id"]
        observed_sample = requests[root_id][2]["local_commission_frame"]["commissions"][0]["admission_evidence"]["sample"]
        assert observed_sample["observation_state"] == "observed"
        assert observed_sample["raw_controller_delta"] == 0
        assert observed_sample["unit_ref"] == observations[root_id][1]["unit_ref"]
        assert observed_sample["sample_ref"] == sample["sample_ref"]
        raw_history = requests[root_id][2]["context"]["waiting_support"]["own_completed_action_history"]
        assert [row["decision_index"] for row in raw_history] == [1, 0]
        assert [row["controller_step"]["marginal_credit"] for row in raw_history] == [0, 0]
        assert all(request["local_commission_frame"]["population_count"] == 0
                   for request in requests[child_id])
        assert store.db.execute("SELECT count(*) FROM runtime_return_admissions").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 6
        assert store.count("native_execution") == store.count("annotation") == 0
        original = snapshot(store)

    entries = [json.loads(line) for line in audit.read_text().splitlines()]
    assert {entry["episode_id"] for entry in entries} == {root_id, child_id}
    assert {entry["implementation_sha256"] for entry in entries} == {binding["implementation_sha256"]}
    worker_entries = [entry for entry in entries if entry["episode_id"] == child_id]
    assert worker_entries and all(entry["pid"] != os.getpid() for entry in worker_entries)
    assert {entry["execution_handle"] for entry in worker_entries} == {spec["handle"]}
    backend = DurableExecutionStore(run/"episode-execution")
    item, = backend.return_page(root_id, 0, 16)["items"]
    original_return = backend.load_return(spec["handle"], item["return_id"])
    assert original_return["outcome"] == "closed"
    assert original_return["completion"]["units_consumed"] == 3
    assert original_return["form"] == {"finding": "qualified", "subjects": [manifest["target_ref"]]}

    # The real saved slots and v6 pair are replayed through the shared Episode
    # controller.  No provider, pending/frame/CE capture or tool work is needed.
    class UnusedProvider:
        complete = staticmethod(forbidden)
        async def release(self, episode_id):
            pass

    with monkeypatch.context() as patched:
        patched.setattr(Workflow, "capture_local_commission_frame", forbidden)
        patched.setattr(LocalCommissionFrame, "capture", forbidden)
        patched.setattr(CompletionEvidence, "capture", forbidden)
        with reopened_root(workspace, run, manifest, UnusedProvider()) as (store, workflow, root):
            patched.setattr(workflow, "pending_work", forbidden)
            patched.setattr(workflow, "source_credit_view", forbidden)
            patched.setattr(workflow.tools, "execute", forbidden)
            record = asyncio.run(root.run_async(workflow.context))
            assert record.units_consumed == 3
            assert snapshot(store) == original
        async def replay_worker():
            async with open_commission(spec) as runtime:
                worker = runtime["episode"].source.workflow
                assert worker.execution_backend is next(value.backend for value in vars(worker).values()
                    if isinstance(value, LocalCommissionFrame))
                patched.setattr(worker, "pending_work", forbidden)
                patched.setattr(worker, "source_credit_view", forbidden)
                patched.setattr(worker.provider, "complete", forbidden)
                patched.setattr(worker.tools, "execute", forbidden)
                record = await runtime["episode"].run_async(runtime["context"])
                assert record.units_consumed == 3
        asyncio.run(replay_worker())
    with Store(workspace) as store:
        assert snapshot(store) == original
    assert backend.load_return(spec["handle"], item["return_id"]) == original_return
    assert [json.loads(line) for line in audit.read_text().splitlines()] == entries
    assert [json.loads(line) for line in turns.read_text().splitlines()] == messages
    # Preserve the first-dispatch evidence even if the caller's original file changes.
    policy.write_text('raise AssertionError("Only the saved caller may be reopened")\n')
    assert asyncio.run(run_prepared_case(run, resume=True, provider=UnusedProvider())) == result


@pytest.mark.parametrize("presentation", [False, True])
def test_interrupted_actual_v3_request_retries_original_text_view_schema_and_instructions(
        evidence_dir, monkeypatch, presentation):
    case, run, policy, manifest, turns, gate, audit = fixture_case(
        evidence_dir, monkeypatch, presentation=presentation, mode="interrupt")
    with pytest.raises(ModelCallError):
        asyncio.run(run_prepared_case(run, policy_file=policy,
            parameters={**PARAMETERS, "stop_after": 1}))
    workspace = case/"workspace"
    with Store(workspace) as store:
        row = store.db.execute("SELECT * FROM runtime_model_calls").fetchone()
        request_text, episode_id = row["request"], row["episode_id"]
        assert row["response"] is None
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    saved = json.loads(request_text)
    messages = [json.loads(line) for line in turns.read_text().splitlines()]
    original_thread, = [item["params"] for item in messages if item["kind"] == "thread/start"]
    original_turn, = [item["params"] for item in messages if item["kind"] == "turn/start"]
    assert_request_view(saved, original_turn, presentation=presentation)
    entries = audit.read_bytes()
    response = {"selection": {"kind": "tool", "tool": "state.query",
        "arguments": {"refs": [manifest["target_ref"]]}}, "report_update": {}}

    class RetryProvider:
        calls = []
        async def complete(self, actual_episode, role, instructions, context, schema):
            assert actual_episode == episode_id and role == "REASONING"
            assert instructions == original_thread["developerInstructions"]
            assert json.dumps(context, allow_nan=False) == original_turn["input"][0]["text"]
            assert json.dumps(schema, allow_nan=False) == json.dumps(
                original_turn["outputSchema"], allow_nan=False)
            self.calls.append(deepcopy((context, schema)))
            return deepcopy(response)
        async def release(self, episode_id):
            pass

    retry = RetryProvider()
    with monkeypatch.context() as patched:
        for name in ("capture_local_commission_frame", "pending_work", "waiting_support",
                     "native_estimation_context", "history_preview", "api_execution_planning_context"):
            patched.setattr(Workflow, name, forbidden)
        patched.setattr(LocalCommissionFrame, "capture", forbidden)
        with reopened_root(workspace, run, manifest, retry) as (store, workflow, root):
            answer, index, context, schema = asyncio.run(root.source.call(
                {"replacement_context_must_be_ignored": True}, {"replacement_schema": True}))
            assert answer == response and index == 0
            assert canonical(context) == canonical(saved["context"])
            assert json.dumps(schema, allow_nan=False) == json.dumps(saved["schema"], allow_nan=False)
            current = workflow.journal.row("runtime_model_calls", episode_id, 0)
            assert current["request"] == request_text
            assert json.loads(current["response"]) == response
            assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
            assert store.db.execute("SELECT count(*) FROM runtime_estimation_contexts").fetchone()[0] == 0
        # A completed saved response still validates v3 before returning it,
        # and does not make a provider call or fresh capture.
        retry.complete = forbidden
        with reopened_root(workspace, run, manifest, retry) as (store, workflow, root):
            assert asyncio.run(root.source.call({}, {}))[0] == response
            assert workflow.journal.row("runtime_model_calls", episode_id, 0)["request"] == request_text
    assert len(retry.calls) == 1
    assert audit.read_bytes() == entries
    assert [json.loads(line) for line in turns.read_text().splitlines()] == messages

