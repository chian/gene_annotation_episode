"""Resource evidence through actual Workflow forms, receipts and controllers.

The native search/parser and M1/M2 readers are real. Decisions, scalar units,
continuation and the durable transport publication are explicit test fixtures.
No configured model, scientific parent or worker subprocess is run here.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from method_loop import EpisodeGoal
from method_loop.durable import canonical, content_digest
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.homology_episodes import obj
from gene_annotation_episode.homology_results import HomologyResults
from gene_annotation_episode.resource_episodes import (
    HANDOFF_SCHEMA, RESULTS_VERSION, HomologyResourceAdapter, ResourceEpisodes,
)
from gene_annotation_episode.resource_operational_credit import ResourceOperationalCredit
from gene_annotation_episode.runtime import ReleasingContext, TypedReportContract, Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_homology_jobs import wait_terminal
from test_resource_episode_branches import context, resources, selected
from test_resource_information import (
    checked_job, record_episode, save_outcome, select_check,
)
from test_runtime import FixtureController, ScriptedProvider


HANDOFF_UNIT = 3.25
RECORD_UNIT = 0.375
GOAL = 'Exercise the original assigned resource information and return form'
FORM = obj({'handoff': {**deepcopy(HANDOFF_SCHEMA), 'type': ['object', 'null'],
    'x-source': 'execution_handoff'}})
EXECUTION_BINDING = {'factory_module': 'fixture', 'factory_name': 'recorded_transport',
    'arguments': {}, 'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}


class RecordingController(FixtureController):
    def __init__(self, *args):
        super().__init__(*args)
        self.inputs = []

    def observe(self, label, value, *, is_root):
        self.inputs.append(deepcopy(value.as_record()))
        return super().observe(label, value, is_root=is_root)


def own(name, **arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments},
        'report_update': {}}


def local_child(r):
    return {'selection': {'kind': 'episode_child', 'role': 'launch_local',
        'goal': GOAL, 'scope': r.scope, 'purpose': 'Return the original checked execution',
        'schema_json': json.dumps(FORM), 'initial_report_json': '{}',
        'assignment': selected(r)}, 'report_update': {}}


def native_script():
    return [own(name) for name in ('homology.environment', 'homology.configure',
        'homology.stage', 'homology.submit', 'homology.check_handoff')]


def host(r, directory, *, script=(), counts=None, initial=(), detached=False):
    """Construct the exact RI2 service value without a production profile choice."""
    controllers, projections, readers = {}, [], []

    def services(store, *, run_id, directory, job_episodes, resource_estimator):
        adapter = HomologyResourceAdapter(job_episodes, store, Journal(store, run_id),
            resource_estimator)
        credit = ResourceOperationalCredit(adapter.information, handoff_unit=HANDOFF_UNIT,
            acquired_record_unit=RECORD_UNIT)
        readers.append(adapter.information)

        def project(bound, selection):
            view = credit(bound, selection)
            projections.append((bound.episode_id, deepcopy(selection), deepcopy(view)))
            return view

        binding = ResourceEpisodes(None, resource_adapters=[adapter])
        return EpisodeApplicationServices([binding.as_record()], {
            role: {'definition': credit.as_record(), 'project': project}
            for role in binding.roles})

    limits = {'launch': 1, 'launch_local': 5, 'results': 3, **(counts or {})}

    def controller(path, initial_credit):
        value = RecordingController(str(path), initial_credit, limits.get(path[-1][0], 1))
        controllers[path] = value
        return value

    provider = ScriptedProvider(script)
    workflow = Workflow(r.store, ToolRegistry(r.store), provider, directory,
        r.journal.run_id, controller_factory=controller, project_credit=lambda *_: 0,
        job_episodes=r.homology, resource_estimator=r.adapter.resource_estimator,
        episode_service_factory=services, episode_service_binding={'kind': 'RI1_test_fixture'},
        episode_record_receipts=True, initial_known_record_refs=list(initial),
        execution_binding=EXECUTION_BINDING if detached else None)
    # This saved owner supplies only the immutable boundary. Its Episode never
    # runs, creates a controller or makes a scientific decision.
    owner = workflow.build('annotation', 'unexecuted_owner', GOAL, r.scope)
    return SimpleNamespace(workflow=workflow, owner=owner, provider=provider,
        controllers=controllers, projections=projections, readers=readers)


def resource_episode(h, r, role, assignment, *, key=None, schema=FORM, initial=None):
    workflow, holder = h.workflow, {}
    owner = h.owner
    if role in {'launch_api', 'launch_local', 'launch_hpc'}:
        # Resource-specific work belongs beneath launch even when that parent
        # is represented only by its original saved ownership boundary.
        owner = workflow.build('launch', 'unexecuted_launch_owner', GOAL, r.scope,
            parent=h.owner.goal, parent_path=h.owner.source.path,
            contract=TypedReportContract('Return the original execution', FORM, lambda *_: False),
            initial={}, episode_assignment=r.launch)

    def resolve(reference, namespace):
        return workflow.resolver(r.scope, context=holder['context'])(reference, namespace)

    def validate(form):
        workflow.episode_bindings.for_role(role).validate_report(holder['context'], form, schema)

    contract = TypedReportContract('Return only the assigned recorded resource facts', schema,
        resolve, validate)
    episode = workflow.build(role, key or role, GOAL, r.scope, parent=owner.goal,
        parent_path=owner.source.path, contract=contract, initial=initial or {},
        episode_assignment=assignment)
    holder['context'] = workflow.binding_context(episode.source)
    boundary = ReleasingContext.from_commission(tree=workflow.tree, run_id=workflow.run_id,
        parent_path=owner.source.path, parent_goal_id=owner.goal.goal_id,
        child_goal_id=episode.goal.goal_id, grain=role, key=episode.key)
    return episode, boundary


def observations(r, episode_id):
    return [json.loads(row[0]) for row in r.store.db.execute(
        'SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? '
        'ORDER BY unit_index', (r.journal.run_id, episode_id))]


def no_native_reads(monkeypatch, jobs):
    def forbidden(*args, **kwargs):
        pytest.fail('receipt, typed admission, closure or replay selected a new native read')
    for name in ('check_handoff', 'receive', 'status', 'handoff', '_handle'):
        monkeypatch.setattr(jobs, name, forbidden)


def test_launch_receives_original_child_proof_before_credit_and_closes_without_recheck(resources, tmp_path, monkeypatch):
    r = resources
    h = host(r, tmp_path / 'runtime', script=[local_child(r), *native_script()])
    launch, boundary = resource_episode(h, r, 'launch', r.launch)
    native_check, checks = r.jobs.check_handoff, []

    with monkeypatch.context() as patched:
        def original_check(handoff):
            outcome = native_check(handoff)
            checks.append(deepcopy(outcome))
            no_native_reads(patched, r.jobs)
            return outcome
        patched.setattr(r.jobs, 'check_handoff', original_check)
        record = asyncio.run(launch.run_async(boundary))
        asyncio.run(launch.build_result(record))

    assert record.units_consumed == 1 and len(checks) == 1
    parent_id = launch.source.episode_id
    child_row = next(row for row in r.store.db.execute(
        'SELECT * FROM runtime_episodes WHERE run_id=?', (h.workflow.run_id,))
        if json.loads(row['path'])[-1][0] == 'launch_local')
    child_id = child_row['episode_id']
    parent_form = json.loads(h.workflow.journal.row('runtime_forms', parent_id)['form'])
    child_form = json.loads(h.workflow.journal.row('runtime_forms', child_id)['form'])
    assert parent_form == child_form and parent_form['handoff']['state'] == 'usable'
    proof, = h.readers[0]._sources()
    body = h.readers[0].read_handoff_source(proof['id'], scope=r.scope)
    assert body['episode_id'] == child_id
    assert body['execution_handoff'] == parent_form['handoff']
    assert body['execution_handoff']['submitted_input_versions'] == r.launch['immutable_input_versions']
    receipt = r.store.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? AND record_ref=?',
        (h.workflow.run_id, parent_id, proof['id'])).fetchone()
    assert tuple(receipt) == ('child_form', 0)
    positive = [item for item in h.projections if item[0] == parent_id and item[2]['credit']]
    assert positive and all(proof['id'] in item[1]['known_record_refs'] for item in positive)
    assert h.controllers[launch.source.path].scores == [HANDOFF_UNIT]
    child_path = tuple(tuple(part) for part in json.loads(child_row['path']))
    assert h.controllers[child_path].scores == [0, 0, 0, 0, HANDOFF_UNIT]
    assert len(observations(r, parent_id)) == 1
    assert len(observations(r, child_id)) == 5
    assert observations(r, parent_id)[0]['credit']['credit'] == HANDOFF_UNIT
    original_selection = h.workflow.record_selection(parent_id)
    original_observations = observations(r, parent_id)
    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        h.workflow.receive_form(launch.source, child_form, FORM, 1, redelivery=True)
        assert h.workflow.source_credit_view(launch.source)['new_handoff_count'] == 1
    assert h.workflow.record_selection(parent_id) == original_selection
    assert observations(r, parent_id) == original_observations
    assert r.store.count('assessment') == r.store.count('annotation') == 0


@pytest.mark.parametrize('inherited_reference', [False, True])
def test_results_original_baseline_partial_own_rows_and_duplicate_pages(resources, tmp_path, monkeypatch, inherited_reference):
    r = resources
    _, _, checked = checked_job(r)
    handoff = checked['execution_handoff']
    wait_terminal(r.jobs, handoff['execution_handle'])
    assigned = r.binding.prepare_assignment(context(r, 'annotation', {}), 'results', {
        'version': RESULTS_VERSION, 'handoff': handoff,
        'requested_data_selector': {'offset': 0, 'limit': 10}}, r.scope, 'foreign-results')
    foreign = context(r, 'results', assigned, key='foreign_results')
    record_episode(r, foreign)
    operation = select_check(r, foreign, tool='homology.extract', arguments={'limit': 10})
    foreign_outcome = asyncio.run(r.binding.execute(foreign, 'homology.extract', {'limit': 10}, operation))
    assert foreign_outcome['status'] == 'completed'
    save_outcome(r, foreign, 0, foreign_outcome)
    foreign_rows = r.adapter.information.own_result_rows(foreign)
    reference = next(row['record_ref'] for row in foreign_rows if row['record_type'] == 'reference')
    original_publication, fail_publication = HomologyResults._publication, [True]

    def partial_publication(adapter, snapshot_ref, ordinal, record_ref, record_type, row, snapshot):
        if record_type == 'observation' and fail_publication[0]:
            raise ContractError('RI1_fixture_partial_publication')
        return original_publication(adapter, snapshot_ref, ordinal, record_ref, record_type, row, snapshot)

    def repair(context):
        assert context['last_local_outcome']['status'] == 'partial'
        assert context['current_credit'] == (0 if inherited_reference else RECORD_UNIT)
        fail_publication[0] = False
        return own('homology.extract', limit=10,
            snapshot_ref=context['last_local_outcome']['result']['snapshot_ref'])

    def repeated(context):
        return own('homology.extract', limit=10,
            snapshot_ref=context['last_local_outcome']['result']['snapshot_ref'])

    h = host(r, tmp_path / 'results-runtime', script=[own('homology.extract', limit=10), repair, repeated],
        initial=[reference] if inherited_reference else [])
    schema = obj({'original_handoff': deepcopy(HANDOFF_SCHEMA),
        'acquired': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
            'x-source': 'committed_record_refs'}})
    results, boundary = resource_episode(h, r, 'results', assigned, schema=schema,
        initial={'original_handoff': handoff})
    source, episode_id = results.source, results.source.episode_id
    initial_selection = h.workflow.record_selection(episode_id)
    proof, = checked['resource_information_refs']
    assert proof in initial_selection['initial_known_record_refs']
    assert h.workflow.journal.row('runtime_episodes', episode_id)['initial_credit'] == 0
    assert h.workflow.source_credit_view(source)['credit'] == 0
    assert h.readers[0].own_result_rows(h.workflow.binding_context(source)) == []
    assert foreign_rows  # Global witnesses exist before this episode's first own page.
    with monkeypatch.context() as patched:
        patched.setattr(HomologyResults, '_publication', partial_publication)
        record = asyncio.run(results.run_async(boundary))
        asyncio.run(results.build_result(record))
    assert record.units_consumed == 3
    expected = [0 if inherited_reference else RECORD_UNIT, RECORD_UNIT, 0]
    assert h.controllers[source.path].scores == expected
    assert [row['step']['delta'] for row in observations(r, episode_id)] == expected
    own_rows = h.readers[0].own_result_rows(h.workflow.binding_context(source))
    own_refs = {row['record_ref'] for row in own_rows}
    assert own_refs == {row['record_ref'] for row in foreign_rows}
    assert len(own_rows) > len(own_refs)  # Repeated publication witnesses are retained.
    assert h.workflow.source_credit_view(source)['new_acquired_record_count'] == (1 if inherited_reference else 2)
    first = json.loads(h.workflow.journal.row('runtime_actions', episode_id, 0)['result'])
    assert first['status'] == 'partial' and len(first['result']['publication_rows']) == 1
    assert first['result']['publication_rows'][0]['record_ref'] == reference
    assert h.workflow.record_selection(episode_id)['initial_known_record_refs'] == initial_selection['initial_known_record_refs']
    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        assert h.workflow.source_credit_view(source)['credit'] == sum(expected)
        form = json.loads(h.workflow.journal.row('runtime_forms', episode_id)['form'])
        assert results.request.report_contract.admit(form,
            audit_identifiers=(episode_id, results.goal.goal_id)).as_record() == form
    assert form['original_handoff'] == handoff
    assert r.store.count('assessment') == r.store.count('annotation') == 0


def test_interruption_after_proof_publication_recovers_original_selected_check(resources, tmp_path, monkeypatch):
    r = resources
    assignment = r.binding.prepare_assignment(context(r, 'launch', r.launch), 'launch_local',
        selected(r), r.scope, 'runtime-publication-recovery')
    job_ref = assignment['adapter_assignment']['job_ref']
    r.jobs.configure(job_ref, 2)
    r.jobs.stage(job_ref)
    r.jobs.submit(job_ref)
    directory = tmp_path / 'interrupted-runtime'
    first = host(r, directory, script=[own('homology.check_handoff')],
        counts={'launch_local': 1}, detached=True)
    episode, boundary = resource_episode(first, r, 'launch_local', assignment)
    episode_id = episode.source.episode_id
    initial = first.workflow.record_selection(episode_id)
    original_publish = first.readers[0].publish_handoff

    def interrupt(*args, **kwargs):
        outcome = original_publish(*args, **kwargs)
        assert outcome['resource_information_refs']
        raise KeyboardInterrupt('RI1 after immutable proof publication')

    # Composition reopens an equivalent reader. Intercept its actual publisher.
    actual_reader = first.workflow.episode_bindings.for_role('launch_local').adapters[
        r.adapter.resource_id].information
    with monkeypatch.context() as patched:
        patched.setattr(actual_reader, 'publish_handoff', interrupt)
        with pytest.raises(KeyboardInterrupt, match='after immutable proof publication'):
            asyncio.run(episode.run_async(boundary))
    assert first.workflow.journal.row('runtime_actions', episode_id, 0)['result'] is None
    proof, = first.readers[0]._sources()
    body = first.readers[0].read_handoff_source(proof['id'], scope=r.scope)
    assert observations(r, episode_id) == []
    interrupted_selection = first.workflow.record_selection(episode_id)
    assert interrupted_selection['initial_known_record_refs'] == initial['initial_known_record_refs']
    assert proof['id'] not in interrupted_selection['known_record_refs']
    original_prefix = [tuple(row) for row in r.store.db.execute(
        'SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? ORDER BY receipt_index', (r.journal.run_id, episode_id))]

    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        recovered = host(r, directory, counts={'launch_local': 1}, detached=True)
        restored, restored_boundary = resource_episode(recovered, r, 'launch_local', assignment)
        record = asyncio.run(restored.run_async(restored_boundary))
        asyncio.run(restored.build_result(record))
    assert record.units_consumed == 1
    assert recovered.controllers[restored.source.path].scores == [HANDOFF_UNIT]
    assert not recovered.provider.contexts
    assert first.readers[0]._sources() == [proof]
    saved = json.loads(recovered.workflow.journal.row('runtime_actions', episode_id, 0)['result'])
    assert saved['execution_handoff'] == body['execution_handoff']
    assert saved['resource_information_refs'] == [proof['id']]
    assert recovered.workflow.record_selection(episode_id)['initial_known_record_refs'] == initial['initial_known_record_refs']
    final_receipts = [tuple(row) for row in r.store.db.execute(
        'SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? ORDER BY receipt_index', (r.journal.run_id, episode_id))]
    assert final_receipts[:len(original_prefix)] == original_prefix
    assert len(observations(r, episode_id)) == 1


def publish_actual_child(h, spec, record):
    """Fixture transport publishes a real completed resource Episode's form."""
    workflow, backend = h.workflow, h.workflow.execution_backend
    child_id = spec['child']['episode_id']
    saved = workflow.journal.row('runtime_forms', child_id)
    form, facts = json.loads(saved['form']), json.loads(saved['facts'])
    facts.pop('interpretations', None)
    payload = {'version': 'returned_episode_v1', 'handle': spec['handle'], 'return_id': '',
        'commission_sha256': content_digest(spec), 'returned_at': datetime.now(timezone.utc).isoformat(),
        'outcome': 'closed', 'completion': {'ended_by': record.ended_by,
            'end_reason': record.end_reason, 'units_consumed': record.units_consumed},
        'episode_archive': (record.archived_record or workflow.archive.store(record)).descriptor(),
        'result_archive': workflow.archive.store({'form': form}).descriptor(), 'form': form,
        'facts_archive': workflow.archive.store(facts).descriptor(), 'pending_handles': [], 'failure': None}
    payload['return_id'] = content_digest({key: value for key, value in payload.items() if key != 'return_id'})
    with backend._connect() as connection:
        token = connection.execute('SELECT execution_token FROM commissions WHERE handle=?',
            (spec['handle'],)).fetchone()[0]
    assert backend._claim(spec['handle'], token)
    backend.publish_return(spec['handle'], token, payload)
    return payload


def test_original_c9_contract_c4_admission_and_replay_without_live_child(resources, tmp_path, monkeypatch):
    r = resources
    directory = tmp_path / 'durable-resource-runtime'
    h = host(r, directory, script=[local_child(r), *native_script()], detached=True)
    launch, boundary = resource_episode(h, r, 'launch', r.launch)
    workflow = h.workflow
    response, index, model_context, action_schema = asyncio.run(launch.source.call(
        {'visible_record_refs': []}, workflow.action_schema(launch.source)))
    unit = launch.source.apply_response(response, index, model_context, action_schema)
    assert unit is not None
    spec, = workflow.commissions.recover_selected(launch.source.episode_id)
    # Install C2's original intent without spawning a process; the actual child
    # runs next under its restored ordinary Episode boundary.
    with monkeypatch.context() as patched:
        patched.setattr(workflow.execution_backend, 'start', lambda handle: workflow.execution_backend.status(handle))
        workflow.dispatch_commission(launch.source, index, spec)
    request = workflow.returned_request(spec)
    # build() requires the actual parent goal, not a relabelled child goal.
    parent_goal = EpisodeGoal.from_record(json.loads(workflow.journal.row(
        'runtime_episodes', launch.source.episode_id)['request'])['goal'])
    child = workflow.build('launch_local', spec['child']['key'], GOAL, r.scope,
        parent=parent_goal, parent_path=launch.source.path, contract=request.report_contract,
        initial={}, episode_assignment=spec['child']['request']['message']['episode_assignment'])
    child_boundary = ReleasingContext.from_commission(tree=workflow.tree, run_id=workflow.run_id,
        parent_path=launch.source.path, parent_goal_id=launch.goal.goal_id,
        child_goal_id=child.goal.goal_id, grain='launch_local', key=child.key)
    child_record = asyncio.run(child.run_async(child_boundary))
    asyncio.run(child.build_result(child_record))
    returned = publish_actual_child(h, spec, child_record)
    child_form = deepcopy(returned['form'])
    original_context = BindingContext(workflow.run_id, child.source.episode_id, 'launch_local',
        child.source.path, r.scope, spec['child']['request']['message']['episode_assignment'],
        spec['child']['request'])

    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        reconstructed = workflow.returned_request(spec).report_contract
        assert reconstructed.admit(child_form,
            audit_identifiers=(child.source.episode_id, child.goal.goal_id)).as_record() == child_form
        resolve = workflow.resolver(r.scope, context=original_context)
        handoff = child_form['handoff']
        for value, namespace in ((handoff['execution_handle'], 'resource_execution'),
                (handoff['resource_selection']['resource_id'], 'resource_binding'),
                (handoff['monitoring']['contract_ref'], 'resource_interface'),
                (handoff['submitted_input_versions'][0]['content_sha256'], 'resource_input_digest'),
                (handoff['checked_at'], 'resource_check_timestamp')):
            assert resolve(value, namespace)
        result = asyncio.run(launch.run_async(boundary))
        asyncio.run(launch.build_result(result))
        history = asyncio.run(workflow.execute(launch.source, 'episode.history',
            {'view': 'records', 'decision_indices': [0]}, decision_index=1,
            operation_key='RI1-explicit-history-read'))
        assert history['result']['records'][0]['admitted_report'] == child_form
        delivery_ref = r.store.db.execute('SELECT delivery_ref FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND decision_index=0',
            (workflow.run_id, launch.source.episode_id)).fetchone()[0]
        revised = obj({'original_execution': deepcopy(FORM['properties']['handoff'])})
        redelivered = workflow.redeliver(launch.source, {'delivery_ref': delivery_ref,
            'purpose': 'Return the same original execution in the revised fact field',
            'schema_json': json.dumps(revised)}, 1)
        assert redelivered.failure is None
        assert redelivered.report.as_record() == {'original_execution': child_form['handoff']}
    assert result.units_consumed == 1 and child_record.units_consumed == 5
    assert h.controllers[launch.source.path].scores == [HANDOFF_UNIT]
    parent_id = launch.source.episode_id
    admission = json.loads(r.store.db.execute('SELECT admission FROM runtime_return_admissions '
        'WHERE parent_episode_id=?', (parent_id,)).fetchone()[0])
    assert admission['state'] == 'admitted' and admission['report'] == child_form
    proof, = [reference for reference in admission['received_record_refs']
        if r.store.get(reference).get('provider') == 'episode.resource_handoff']
    assert admission['controller_input']['credit'] == HANDOFF_UNIT
    original_observations = observations(r, parent_id)
    original_receipts = workflow.record_selection(parent_id)
    original_slot = workflow.completions.slot(parent_id, 0)
    original_form = json.loads(workflow.journal.row('runtime_forms', parent_id)['form'])

    def forbidden(*args, **kwargs):
        pytest.fail('committed C4/F2 replay normalized or projected again')

    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        restored = host(r, directory, detached=True)
        replay, replay_boundary = resource_episode(restored, r, 'launch', r.launch)
        receiver = ReceiverBindingV1(r.store, restored.workflow.journal, 0,
            restored.workflow.returned_request(spec).report_contract,
            forbidden, forbidden, forbidden, forbidden)
        assert admit_return(spec, returned, receiver) == admission
        patched.setattr(restored.workflow, 'receive_form', forbidden)
        patched.setattr(restored.workflow, 'source_credit_view', forbidden)
        replay_record = asyncio.run(replay.run_async(replay_boundary))
        asyncio.run(replay.build_result(replay_record))
    assert replay_record.units_consumed == 1
    assert restored.controllers[replay.source.path].inputs == h.controllers[launch.source.path].inputs
    assert observations(r, parent_id) == original_observations
    assert restored.workflow.record_selection(parent_id) == original_receipts
    assert restored.workflow.completions.slot(parent_id, 0) == original_slot
    assert json.loads(restored.workflow.journal.row('runtime_forms', parent_id)['form']) == original_form
    assert not restored.provider.contexts

    with pytest.raises(ValueError):
        restored.workflow.resolver(r.scope, context=replace(original_context, run_id='other-run'))
    altered_spec = deepcopy(spec)
    altered_spec['run_id'] = 'another-run'
    with pytest.raises(ValueError):
        restored.workflow.returned_request(altered_spec)
    with pytest.raises(TypeError):
        restored.workflow.resolver(r.scope, source=replay.source,
            context={'run_id': restored.workflow.run_id})
    changed_assignment = plain(original_context.assignment)
    changed_assignment['constraints']['cpu'] = 1
    with pytest.raises(ValueError):
        restored.workflow.resolver(r.scope, context=replace(original_context,
            assignment=changed_assignment))
    with pytest.raises((ValueError, ContractError)):
        restored.workflow.resolver({'subject_refs': []}, context=original_context)
    altered = deepcopy(child_form)
    altered['handoff']['checked_at'] = '2020-01-01T00:00:00+00:00'
    with pytest.raises(ReportBoundaryError):
        restored.workflow.returned_request(spec).report_contract.admit(altered,
            audit_identifiers=(child.source.episode_id, child.goal.goal_id))


def test_invalid_initial_c9_values_are_rejected_before_episode_credit_or_publication(resources, tmp_path, monkeypatch):
    r = resources
    _, _, checked = checked_job(r)
    handoff = checked['execution_handoff']
    assigned = r.binding.prepare_assignment(context(r, 'annotation', {}), 'results', {
        'version': RESULTS_VERSION, 'handoff': handoff, 'requested_data_selector': {}},
        r.scope, 'initial-validation-results')
    h = host(r, tmp_path / 'initial-validation-runtime')
    schema = obj({'original_handoff': deepcopy(HANDOFF_SCHEMA)})
    original_episodes = r.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0]
    original_projections = len(h.projections)
    with monkeypatch.context() as patched:
        no_native_reads(patched, r.jobs)
        for field in ('checked_at', 'content_sha256', 'execution_handle'):
            changed = deepcopy(handoff)
            if field == 'checked_at':
                changed[field] = '2020-01-01T00:00:00+00:00'
            elif field == 'content_sha256':
                changed['submitted_input_versions'][0][field] = '0' * 64
            else:
                changed[field] = 'homology_job_unknown_fixture'
            with pytest.raises(ReportBoundaryError):
                resource_episode(h, r, 'results', assigned, key='invalid-' + field,
                    schema=schema, initial={'original_handoff': changed})
    assert r.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == original_episodes
    assert len(h.projections) == original_projections
    assert not h.provider.contexts


def test_two_selected_checks_keep_both_original_proofs_but_one_physical_contribution(resources, tmp_path, monkeypatch):
    r = resources
    assignment = r.binding.prepare_assignment(context(r, 'launch', r.launch), 'launch_local',
        selected(r), r.scope, 'repeated-physical-check')
    job_ref = assignment['adapter_assignment']['job_ref']
    r.jobs.configure(job_ref, 2)
    r.jobs.stage(job_ref)
    r.jobs.submit(job_ref)
    h = host(r, tmp_path / 'repeated-check-runtime', counts={'launch_local': 2},
        script=[own('homology.check_handoff'), own('homology.check_handoff')])
    episode, boundary = resource_episode(h, r, 'launch_local', assignment)
    original_check, checks = r.jobs.check_handoff, []

    with monkeypatch.context() as patched:
        def selected_check(handoff):
            outcome = original_check(handoff)
            checks.append(deepcopy(outcome))
            if len(checks) == 2:
                no_native_reads(patched, r.jobs)
            return outcome

        patched.setattr(r.jobs, 'check_handoff', selected_check)
        record = asyncio.run(episode.run_async(boundary))
        asyncio.run(episode.build_result(record))
        assert h.workflow.source_credit_view(episode.source)['new_handoff_count'] == 1
    assert record.units_consumed == 2 and len(checks) == 2
    assert h.controllers[episode.source.path].scores == [HANDOFF_UNIT, 0]
    assert [row['step']['delta'] for row in observations(r, episode.source.episode_id)] == [HANDOFF_UNIT, 0]
    proofs = [h.readers[0].read_handoff_source(source['id'], scope=r.scope)
        for source in h.readers[0]._sources()]
    assert {proof['operation_key'] for proof in proofs} == {
        f'{r.journal.run_id}:{episode.source.episode_id}:{index}' for index in (0, 1)}
    assert {proof['execution_handoff']['execution_handle'] for proof in proofs} == {job_ref}
    form = json.loads(h.workflow.journal.row('runtime_forms', episode.source.episode_id)['form'])
    assert form['handoff']['checked_at'] == max(proof['execution_handoff']['checked_at'] for proof in proofs)
