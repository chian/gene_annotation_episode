"""C7 resource decisions over real local ordinary operations and shared Episodes.

Decisions and action-count controllers are engineering fixtures. The tiny native
search and parser are real; no model, detached episode worker or scientific
investigation is started by these checks.
"""
import asyncio
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from method_loop import ChildEpisodeUnit, Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain, validate_closed_schema
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_recording import HomologyStatistics
from gene_annotation_episode.homology_episodes import HomologyEpisodes, obj
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, digest
from gene_annotation_episode.homology_results import HomologyResults, NativePhmmerInput
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.local_resources import DIRECTORY_ENV, LocalResources
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_lifecycle import cancel, prepare_job, release, start_prepared
from gene_annotation_episode.resource_episodes import HomologyResourceAdapter, ResourceEpisodes, LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homology_jobs import PROJECT, PROGRAM, QUERY, wait_terminal
from test_runtime import FixtureController


def no_scientific_credit(*args, **kwargs):
    return 0


class ResourceServices:
    """Explicit caller ports and units; a new role supplies no score policy."""
    def __init__(self, store, declarations=()):
        self.store, self.declarations = store, declarations
        self.credit_calls = []

    def capabilities(self):
        return deepcopy(self.declarations)

    def reference_in_scope(self, reference, scope, namespace):
        try:
            record = self.store.get(reference)
            return self.store.reference_subset([reference], plain(scope)) and (namespace is None
                or namespace == record['record_type'] or namespace == 'subject' and record['record_type'] in {
                    'input', 'feature', 'product', 'read_subject'})
        except (KeyError, ValueError):
            return False

    def bound_role_credit(self, context, receiver_selection):
        self.credit_calls.append((context, receiver_selection))
        return {'credit': 0}  # Caller-selected engineering fixture, no production unit.


@pytest.fixture
def resources(tmp_path, monkeypatch):
    # This fixture explicitly tests a two-CPU allocation. Its caller-owned host
    # budget must permit that allocation; production defaults remain one CPU.
    monkeypatch.setenv(DIRECTORY_ENV, str(tmp_path/'local-resources'))
    LocalResources.configured({'cpu_threads': 2})
    with Store(tmp_path / 'workspace') as store:
        target, = store.create_problem(PROJECT / 'cases/gene_001/target.fna',
            molecule='dna', role='gene')['subject_refs']
        scope = {'subject_refs': [target]}
        translated = ToolRegistry(store).execute('sequence.translate',
            {'subject_ref': target, 'code': 11, 'cds': True}, scope=scope)
        query = translated['result']['records'][0]['product_ref']
        policy = LocalJobPolicy.from_config()
        database = tmp_path / 'references.faa'
        database.write_text(QUERY.replace('>gene_001', '>reference_self_fixture'))
        jobs = HomologyJobs.create(tmp_path / 'jobs', executable=FileAsset(PROGRAM, digest(PROGRAM)),
            reference_database=FileAsset(database, digest(database)), policy=policy, max_cpu=2,
            search_modes=['native_defaults', 'maximum_sensitivity'])
        history = RunHistory(tmp_path / 'history.sqlite')
        history.close()
        statistics = HomologyStatistics(tmp_path / 'history.sqlite', 'resource-fixture-host', 1, 253)
        homology = HomologyEpisodes(jobs, parser_policy=policy, credit_projector=no_scientific_credit,
            credit_binding={'kind': 'engineering_fixture_zero'}, monitoring_projector=no_scientific_credit,
            monitoring_binding={'kind': 'engineering_fixture_zero'}, statistics=statistics)
        journal = Journal(store, 'resource-fixture')
        adapter = HomologyResourceAdapter(homology, store, journal, ResourceToolEstimator())
        services = ResourceServices(store)
        binding = ResourceEpisodes(services, resource_adapters=[adapter])
        query_record = store.get(query)
        inputs = [{'reference': query, 'version': None,
            'content_sha256': hashlib.sha256(artifact_path(store, query_record['sequence_ref']).read_bytes()).hexdigest()}]
        launch = {'version': LAUNCH_VERSION, 'job_request': {'query_ref': query, 'cpu': 2,
            'search_mode': 'maximum_sensitivity'}, 'immutable_input_versions': inputs,
            'constraints': {'allowed_kinds': ['local'], 'cpu': 2, **policy.to_dict()},
            'resource_selection': None, 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
        value = SimpleNamespace(store=store, scope=scope, query=query, jobs=jobs, homology=homology,
            journal=journal, services=services, binding=binding, adapter=adapter, launch=launch, policy=policy,
            initial_observation_count=store.count('observation'))
        try:
            yield value
        finally:
            for row in jobs.db.execute('SELECT job_ref FROM orders'):
                handle = jobs._handle(row[0])
                if handle.path.exists():
                    cancel(handle)
            jobs.close()


def context(resources, role, assignment, key='fixture'):
    return BindingContext('resource-fixture', 'episode_' + key, role, ((role, key),),
        resources.scope, assignment, {})


def selected(resources):
    return {**deepcopy(resources.launch), 'resource_selection': resources.adapter._selection(2)}


class OrdinaryResourceConsumer:
    """A C7 fixture: every role runs an ordinary shared Episode and controller."""
    def __init__(self, resources, choose, counts):
        self.resources, self.choose = resources, choose
        self.sources, self.controllers, self.inputs, self.forms = {}, {}, [], []
        self.observations = defaultdict(list)

        def controller(path):
            value = FixtureController(str(path), 0, counts[path[-1][0]])
            self.controllers[path] = value
            return value
        binding = resources.binding
        self.grains = {role: Grain(role, 'Selected assigned resource work', 'Caller bound credit', controller)
            for role in ('annotation', *binding.roles)}
        self.loop = Context(tree=EpisodeTree(self.grains['annotation'], {
            self.grains['annotation']: tuple(self.grains[role] for role in binding.entry_roles),
            **{
            self.grains[role]: tuple(self.grains[child] for child in binding.child_roles(role))
            for role in binding.roles}}), run_id='resource-fixture')

    def contract(self, role, holder):
        binding, r = self.resources.binding, self.resources
        fields = {'handoff': binding.fact_sources(role)['execution_handoff']['report_schema']}
        if role == 'results':
            fields = {'coverage': binding.fact_sources(role)['job_result_progress']['report_schema'],
                'acquired': {'type': 'array', 'x-source': 'changed_record_refs', 'items': {
                    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'observation'}}}
        return TypedReportContract('Return selected checked facts, retaining scientific ownership', obj(fields),
            lambda reference, namespace: binding.resolve(holder['context'], reference, namespace),
            lambda form: binding.validate_report(holder['context'], form, obj(fields)))

    def build(self, role, key, assignment, *, parent=None, parent_path=(), contract=None, holder=None):
        r, consumer = self.resources, self
        path = (*parent_path, (role, key))
        grain = self.grains[role]
        identity = Episode.identity(self.loop, grain, key, parent_path=parent_path)
        goal = (EpisodeGoal.root(objective='Establish the assigned receiving interfaces', result_contract={})
            if parent is None else EpisodeGoal.child(parent, objective='Investigate the assigned local execution',
                result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({'assignment': assignment}), contract)
        bound = BindingContext('resource-fixture', identity.episode_id, role, path, r.scope, assignment, request.as_record())
        if holder is not None:
            holder['context'] = bound

        class Source:
            binding_context = bound
            last_result = None

            def __init__(self):
                self.changed = []

            def credit(self):
                return Record(r.binding.credit_view(bound, {'episode_id': bound.episode_id,
                    'known_record_refs': self.changed, 'initial_known_record_refs': [],
                    'known_progress_refs': [], 'initial_progress_refs': []}))

            def record(self, selection, result, index):
                self.last_result = result
                self.changed.extend(ref for ref in result.get('changed_record_refs', []) if ref not in self.changed)
                with r.store.transaction():
                    r.journal.save('runtime_actions', {'episode_id': bound.episode_id, 'decision_index': index,
                        'action': json.dumps(selection), 'result': json.dumps(result), 'credit': 0})
                return self.credit()

            def next(self, view):
                specialized = r.binding.decision_context(bound, view) if bound.role != 'annotation' else {}
                inputs = view.model_inputs({**specialized,
                    'last_local_outcome': self.last_result}, reports=view.child_reports)
                consumer.inputs.append((bound.role, view.units_consumed, deepcopy(inputs)))
                selection = consumer.choose(bound, view.units_consumed, inputs)
                index = view.units_consumed
                if selection['kind'] == 'child':
                    child_role = selection['role']
                    assert child_role in (r.binding.entry_roles if bound.role == 'annotation'
                        else r.binding.allowed_children(bound, ()))
                    assigned = r.binding.prepare_assignment(bound, child_role, selection['assignment'], r.scope,
                        f'{bound.episode_id}:{index}')
                    child_holder = {}
                    child_contract = consumer.contract(child_role, child_holder)
                    child = consumer.build(child_role, 'selected_' + str(index), assigned,
                        parent=goal, parent_path=path, contract=child_contract, holder=child_holder)

                    def receive(result, *_):
                        form = result.as_record()['form']
                        child_contract.admit(form, audit_identifiers=(child_holder['context'].episode_id,))
                        consumer.forms.append((child_role, deepcopy(form)))
                        return self.record(selection, {'status': 'completed', 'record_refs': [],
                            'changed_record_refs': [], 'result': form, 'feedback': None}, index)
                    return ChildEpisodeUnit(child, receive, lambda result, *_: result.as_record()['form'])

                async def perform(_):
                    with r.store.transaction():
                        r.journal.save('runtime_actions', {'episode_id': bound.episode_id,
                            'decision_index': index, 'action': json.dumps(selection),
                            'result': None, 'credit': None})
                    result = await r.binding.execute(bound, selection['tool'], selection['arguments'],
                        f'{bound.run_id}:{bound.episode_id}:{index}')
                    assert result['status'] in {'completed', 'partial'}, result
                    return self.record(selection, result, index)
                return Leaf(None, perform, lambda _, result: result, label=selection['tool'])

            def finish(self, _):
                if contract is None:
                    return self.credit()
                facts = r.binding.facts(bound, {})
                facts['changed_record_refs'] = self.changed
                form = form_with_facts({}, contract.schema, facts)
                return Record({'form': contract.admit(form, audit_identifiers=(bound.episode_id,)).as_record()})

        source = Source()
        self.sources[path] = source
        return Episode(grain, key, source, request, source.finish)


def tool(name, **arguments):
    return {'kind': 'tool', 'tool': name, 'arguments': arguments}


def test_nested_launch_real_local_job_checked_handoff_and_separate_results(resources):
    r = resources
    assert r.policy.to_dict() == {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
    EpisodeBindingRegistry([r.binding])
    handoffs = []

    def choose(bound, index, inputs):
        if bound.role == 'annotation':
            if index == 0:
                return {'kind': 'child', 'role': 'launch', 'assignment': r.launch}
            handoff = inputs['child_reports'][-1]['handoff']
            assert r.store.count('observation') == r.initial_observation_count
            native = r.adapter._native_handoff(handoff)
            received = r.jobs.receive(native)  # Actual monitoring receiving interface.
            assert received['job_ref'] == handoff['execution_handle']
            assert received['progress_kind'] == 'native_execution_state_and_output_bytes_not_search_fraction'
            wait_terminal(r.jobs, handoff['execution_handle'])
            return {'kind': 'child', 'role': 'results', 'assignment': {
                'version': RESULTS_VERSION, 'handoff': handoff,
                'requested_data_selector': {'offset': 0, 'limit': 10}}}
        if bound.role == 'launch':
            if index == 0:
                assert inputs['assignment'] == r.launch
                assert inputs['resource_tool_estimates'][0]['job_ref'] is None
                assert inputs['resource_tool_estimates'][0]['status'] == 'no_matching_history'
                assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
                assert inputs['resource_capabilities'][0]['availability'] == 'available'
                return {'kind': 'child', 'role': 'launch_local', 'assignment': selected(r)}
            handoff = inputs['child_reports'][-1]['handoff']
            assert handoff['state'] == 'usable'
            handoffs.append(handoff)
            return tool('resource.check_handoff', handoff=handoff)
        if bound.role == 'launch_local':
            assert plain(bound.assignment)['resource_selection'] == r.adapter._selection(2)
            if index == 0:
                return tool('homology.environment')
            if index == 1:
                assert inputs['last_local_outcome']['result']['configured_cpu'] == 2
                assert inputs['last_local_outcome']['result']['staged'] is False
                return tool('homology.configure')
            if index == 2:
                return tool('homology.stage')
            if index == 3:
                assert inputs['last_local_outcome']['result']['staged'] is True
                return tool('homology.submit')
            assert inputs['last_local_outcome']['result']['new_submission'] is True
            return tool('homology.check_handoff')
        if index == 0:
            return tool('homology.extract', limit=0)
        result = inputs['last_local_outcome']['result']
        return (tool('homology.extract', limit=10, snapshot_ref=result['snapshot_ref']) if index == 1
            else tool('homology.coverage', snapshot_ref=result['snapshot_ref']))

    consumer = OrdinaryResourceConsumer(r, choose,
        {'annotation': 2, 'launch': 2, 'launch_local': 5, 'results': 3})
    episode = consumer.build('annotation', 'root', {})
    trace = asyncio.run(episode.run_async(consumer.loop)).as_record()
    assert trace['controller_state']['credit'] == 0 and trace['units_consumed'] == 2
    forms = dict(consumer.forms)
    handoff = forms['launch']['handoff']
    assert handoff['execution_handle'] == handoffs[0]['execution_handle']
    assert handoff['resource_selection'] == r.adapter._selection(2)
    assert handoff['submitted_input_versions'] == r.launch['immutable_input_versions']
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    assert r.jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 1
    command = r.jobs._handle(handoff['execution_handle']).read()['command']
    assert command[command.index('--cpu') + 1] == '2' and '--max' in command
    assert r.jobs._handle(handoff['execution_handle']).read()['metadata']['policy'] == r.policy.to_dict()
    assert [role for role, _ in consumer.forms] == ['launch_local', 'launch', 'results']
    form = forms['results']
    assert form['coverage']['execution_context']['job_ref'] == handoff['execution_handle']
    assert form['coverage']['parser_finished'] is True
    assert form['coverage']['all_parsed_rows_acquired'] is True
    assert form['coverage']['native_result_complete'] is True
    assert len(form['acquired']) == 1
    assert r.store.get(form['acquired'][0])['kind'] == 'alignment'
    assert r.store.count('assessment') == r.store.count('annotation') == 0
    assert sum(len(controller.scores) for controller in consumer.controllers.values()) == 12
    assert r.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 12
    assert all(score == 0 for controller in consumer.controllers.values() for score in controller.scores)
    results_context = next(source.binding_context for path, source in consumer.sources.items()
        if path[-1][0] == 'results')
    assert 'homology.submit' not in {item['name'] for item in r.binding.catalog(results_context)}
    before = r.store.count('observation')
    outside = asyncio.run(r.binding.execute(results_context, 'homology.extract',
        {'limit': 11, 'snapshot_ref': form['coverage']['snapshot_ref']}, 'outside_requested_rows'))
    assert outside['status'] == 'failed'
    assert outside['feedback']['code'] == 'requested_data_selector_conflict'
    assert r.store.count('observation') == before
    launch_context = next(source.binding_context for path, source in consumer.sources.items()
        if path[-1][0] == 'launch')
    for index, field in enumerate(('checked_at', 'submitted_input_versions', 'resource_selection', 'monitoring'), 3):
        altered = deepcopy(handoff)
        if field == 'checked_at':
            altered[field] = '2020-01-01T00:00:00+00:00'
        elif field == 'submitted_input_versions':
            altered[field][0]['content_sha256'] = '0' * 64
        elif field == 'resource_selection':
            altered[field]['allocation']['cpu'] = 1
        else:
            altered[field]['contract_ref'] = 'unbound.status.v1'
        arguments = {'handoff': altered}
        with r.store.transaction():
            r.journal.save('runtime_actions', {'episode_id': launch_context.episode_id,
                'decision_index': index, 'action': json.dumps(tool('resource.check_handoff', **arguments)),
                'result': None, 'credit': None})
        failed = asyncio.run(r.binding.execute(launch_context, 'resource.check_handoff', arguments,
            f'{launch_context.run_id}:{launch_context.episode_id}:{index}'))
        assert failed['status'] == 'failed' and failed['feedback']['code'] == 'invalid_resource_handoff'
    with pytest.raises(ReportBoundaryError, match='differs from selected recorded check'):
        r.binding.validate_report(launch_context, {'handoff': altered},
            obj({'handoff': r.binding.fact_sources('launch')['execution_handoff']['report_schema']}))
    repair = {**deepcopy(r.launch), 'job_request': {'existing_job_ref': handoff['execution_handle']}}
    repair_context = context(r, 'launch', repair, key='repair')
    estimates = r.binding.decision_context(repair_context, None)['resource_tool_estimates']
    assert estimates[0]['job_ref'] == handoff['execution_handle']
    repair_assignment = r.binding.prepare_assignment(repair_context, 'launch_local',
        {**repair, 'resource_selection': r.adapter._selection(2)}, r.scope, 'selected_repair')
    assert repair_assignment['adapter_assignment']['job_ref'] == handoff['execution_handle']
    repair_child = context(r, 'launch_local', repair_assignment, key='repair_child')
    assert r.binding.facts(repair_child, {})['execution_handoff'] is None
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1


@pytest.mark.parametrize('field', ['job_request', 'immutable_input_versions', 'constraints',
    'software_knowledge_refs', 'resource_knowledge_refs'])
def test_launch_child_cannot_replace_parent_work(resources, field):
    selection = selected(resources)
    if isinstance(selection[field], dict):
        selection[field]['substituted'] = True
    else:
        selection[field] = ['substituted']
    with pytest.raises(ValueError, match='resource_assignment_conflict|invalid_resource_assignment'):
        resources.binding.prepare_assignment(context(resources, 'launch', resources.launch), 'launch_local',
            selection, resources.scope, 'substitution')
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


def test_selected_allocation_and_input_digest_are_verified_before_ordering(resources):
    r = resources
    parent = context(r, 'launch', r.launch)
    wrong_cpu = selected(r)
    wrong_cpu['resource_selection']['allocation']['cpu'] = 1
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        r.binding.prepare_assignment(parent, 'launch_local', wrong_cpu, r.scope, 'cpu-substitution')
    broken = deepcopy(r.launch)
    broken['immutable_input_versions'][0]['content_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='resource_input_version_conflict'):
        r.binding.prepare_assignment(context(r, 'launch', broken), 'launch_local',
            {**broken, 'resource_selection': r.adapter._selection(2)}, r.scope, 'wrong-digest')
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert not list(r.jobs.directory.glob('homology_job_*'))


@pytest.mark.parametrize('kind,availability,code', [
    ('api', 'authentication_required', 'resource_authentication_required'),
    ('hpc', 'unavailable', 'resource_unavailable'),
    ('api', 'unknown', 'resource_availability_unknown'),
    ('hpc', 'available', 'resource_not_bound')])
def test_unbound_declarations_return_actual_structured_availability(resources, kind, availability, code):
    r = resources
    declaration = {'resource_id': 'declared-resource', 'kind': kind, 'availability': availability,
        'observed_at': '2026-10-21T00:00:00+00:00', 'provenance_refs': [],
        'knowledge_entry_ids': [], 'tool_names': ['unbound.submit']}
    r.services.declarations = [declaration]
    bound = context(r, 'launch', r.launch)
    capabilities = r.binding.capabilities()
    assert capabilities[0]['tool_names'] == []
    assert 'launch_' + kind not in r.binding.allowed_children(bound, ())
    result = asyncio.run(r.binding.execute(bound, 'resource.inspect',
        {'resource_id': 'declared-resource'}, 'inspect'))
    assert result['status'] == 'failed'
    assert result['feedback'] == {'code': code, 'affected_refs': ['declared-resource'],
        'diagnostic_ref': None, 'partial_record_refs': []}
    assert result['result']['capability']['availability'] == availability
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


def test_handoff_schema_is_closed_and_missing_binding_does_not_supply_credit(resources):
    schema = obj({'checked': resources.binding.fact_sources('launch_local')['execution_handoff']['report_schema']})
    assert validate_closed_schema(schema) == schema
    class UnboundServices(ResourceServices):
        def bound_role_credit(self, context, receiver_selection):
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
    binding = ResourceEpisodes(UnboundServices(resources.store))
    with pytest.raises(ValueError, match='explicit_role_credit_binding_required:launch'):
        binding.credit_view(context(resources, 'launch', resources.launch), {})


@pytest.mark.parametrize('selector', [{'query': 'replace'}, {'offset': -1}, {'limit': True}])
def test_unsupported_results_selectors_are_rejected_before_receiving_work(resources, selector):
    with pytest.raises(ValueError, match='invalid_resource_selector'):
        resources.adapter.prepare_assignment(context(resources, 'annotation', {}), 'results',
            {'requested_data_selector': selector}, resources.scope, 'invalid-selector')


def test_busy_feedback_preserves_original_homology_job_and_retries_after_capacity_frees(resources,tmp_path):
    r=resources
    holder_directory=tmp_path/'capacity-holder'
    holder_directory.mkdir()
    holder=prepare_job([sys.executable,'-c',
        "from pathlib import Path\nimport time\nwhile not Path('finish').exists():time.sleep(.01)"],
        cwd=holder_directory,policy=LocalJobPolicy(64*1024**2,4*1024**2),
        handle_path=holder_directory/'native.json')
    try:
        start_prepared(holder)
        assignment=r.binding.prepare_assignment(context(r,'launch',r.launch),'launch_local',
            selected(r),r.scope,'capacity-blocked-assignment')
        bound=context(r,'launch_local',assignment)
        source=r.adapter._legacy(bound)
        job=assignment['adapter_assignment']['job_ref']
        r.jobs.configure(job,2)
        r.jobs.stage(job)
        result=asyncio.run(r.homology.execute(source,'homology.submit',{},operation_key='blocked-submit'))
        assert result['status']=='failed'
        feedback=result['feedback']
        assert feedback['code']=='local_resource_busy'
        assert feedback['phase']=='local_admission'
        assert feedback['retryable'] and feedback['retry_same_prepared_job']
        assert feedback['local_resources']['available']['job_slots']==0
        assert feedback['job_ref']==job
        original=r.jobs._handle(job).read()
        assert original['stage']=='prepared'
        assert not (r.jobs._directory(job)/'domains.tbl').exists()
        cancel(holder)
        result=asyncio.run(r.homology.execute(source,'homology.submit',{},operation_key='retry-submit'))
        assert result['status']=='completed'
        assert result['result']['new_submission']
        assert r.jobs._handle(job).read()['unit']==original['unit']
        assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0]==1
        wait_terminal(r.jobs,job)
        handoff=asyncio.run(r.homology.execute(source,'homology.check_handoff',{},operation_key='retry-handoff'))
        inputs=NativePhmmerInput.from_job(r.jobs,handoff['result']['handoff'])
        parser_directory=tmp_path/'parser-capacity-holder'
        parser_directory.mkdir()
        parser_holder=prepare_job([sys.executable,'-c',
            "from pathlib import Path\nimport time\nwhile not Path('finish').exists():time.sleep(.01)"],
            cwd=parser_directory,policy=LocalJobPolicy(64*1024**2,4*1024**2),
            handle_path=parser_directory/'native.json')
        try:
            start_prepared(parser_holder)
            parser=HomologyResults(r.store,policy=r.policy)
            with pytest.raises(AcquisitionError) as blocked:
                asyncio.run(parser.extract(inputs,scope=r.scope,limit=10,attempt_key='busy-parser'))
            assert blocked.value.code=='local_resource_busy'
            assert r.store.db.execute('SELECT count(*) FROM homology_parse_cache').fetchone()[0]==0
            assert r.store.db.execute('SELECT count(*) FROM homology_result_snapshots').fetchone()[0]==0
            parser_handle,=list((r.store.path/'cache/phmmer_results').glob('*/parser.handle.json'))
            parser_unit=json.loads(parser_handle.read_text())['unit']
            assert not (parser_handle.parent/'parse_outcome.json').exists()
            cancel(parser_holder)
            parsed=asyncio.run(parser.extract(inputs,scope=r.scope,limit=10,attempt_key='retry-parser'))
            assert parsed['status']=='completed'
            assert json.loads(parser_handle.read_text())['unit']==parser_unit
            assert r.store.db.execute('SELECT count(*) FROM homology_parse_cache').fetchone()[0]==1
            assert r.store.db.execute('SELECT count(*) FROM homology_result_snapshots').fetchone()[0]==1
        finally:
            cancel(parser_holder)
            release(parser_holder)
    finally:
        cancel(holder)
        release(holder)
