"""Connected shared-loop checks; decisions, credit units and stops are fixtures.

The Store, forms, journal, receipts, option snapshot and episode machinery are
real. These tests make no claim of configured-model scientific behavior.
"""
import asyncio
from copy import deepcopy
import json
import hashlib

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.domain import obj
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.numerical import NumericBand, SignedNumericBand, YieldController, YieldEstimate
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_digest, scientific_invocation_ref
from gene_annotation_episode.scientific_process_reports import credit_binding_ref, report_sources
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from test_runtime import FixtureController, ScriptedProvider
from test_runtime_expectations import make_history
from test_scientific_process_library import independent_source, write


FORM = obj({'status': {'type': 'string', 'enum': ['unresolved', 'qualified']},
    'sources': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'source'}, 'x-source': 'changed_record_refs'}})


def action(name, arguments, status=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments},
        'report_update': {} if status is None else {'status': status}}


class Tools:
    def __init__(self, store):
        self.store, self.calls = store, []

    def catalog(self, scope=None):
        return [{'name': name, 'input_schema': obj({'value': {
            'type': 'integer', 'minimum': 0, 'maximum': 10}})}
            for name in ('fixture.inspect', 'fixture.excluded')]

    def execute(self, name, arguments, *, scope, operation_key):
        assert name == 'fixture.inspect'
        self.calls.append((name, deepcopy(arguments), scope, operation_key))
        artifact = self.store.artifact(json.dumps(arguments).encode(), 'application/json')
        source = self.store.put('source', {'provider': 'fixture.scientific_process',
            'accession': hashlib.sha256(operation_key.encode()).hexdigest(), 'uri': None, 'artifact_ref': artifact,
            'text_ref': artifact, 'request_ref': None, 'version': 'fixture',
            'retrieved_at': None, 'parent_source_refs': [], 'operand_refs': scope['subject_refs']},
            origin='tool')['id']
        return {'status': 'completed', 'record_refs': [source], 'changed_record_refs': [source],
            'result': {'observed': arguments['value']}}


def received_credit(store, episode_id):
    refs = set()
    for row in store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=? '
            "AND json_extract(result,'$.status')='completed'", (episode_id,)):
        refs.update(json.loads(row[0]).get('record_refs', []))
    return sum(store.get(ref).get('provider') == 'fixture.scientific_process' for ref in refs)


def root_credit(store, scope):
    row = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()
    return 0 if row is None else received_credit(store, row[0])


def child_credit(store, scope, *, assignment, episode_id, run_id):
    return received_credit(store, episode_id)


class Scenario:
    def __init__(self, tmp_path, store, *, tools=None):
        self.store, self.directory, self.source = store, tmp_path/'run', tmp_path/'source'
        self.directory.mkdir()
        independent_source(self.source, extra=True)
        self.library = ScientificProcessLibrary.freeze(self.directory/'scientific-process-library', source=self.source)
        self.tools = tools or Tools(store)
        descriptor = prepare_scientific_binding(run_directory=self.directory, source_directory=self.source,
            tool_catalog=self.tools.catalog(), child_roles=['scientific_process', 'literature'])
        self.descriptors = [descriptor, LiteratureEpisodes(None).as_record()]
        problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        self.scope = {'subject_refs': problem['subject_refs']}
        self.controllers = []

    def selection(self, thought='P01', tools=('fixture.inspect',)):
        return {'version': 'scientific_process_selection_v2',
            'annotation_ref': self.library.reference('A01'),
            'thought_ref': self.library.reference(thought), 'tools': list(tools)}

    def commission(self, evidence_refs=()):
        return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Resolve the scoped fixture alternatives using changing outcomes',
            'scope': self.scope, 'purpose': 'Return the selected qualification and actual source refs',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{"status":"unresolved"}',
            'assignment': {'selection': self.selection(), 'evidence_refs': list(evidence_refs),
                'constraints': {'target_only': True}, 'context': {'condition': 'fixture'}}},
            'report_update': {}}

    def factory(self, path, initial):
        controller = FixtureController(str(path), initial, 2 if len(path) == 1 else 4)
        self.controllers.append(controller)
        return controller

    def workflow(self, provider, **kwargs):
        return Workflow(self.store, self.tools, provider, self.directory, 'fixture-run', self.factory,
            root_credit, project_child_credit=child_credit,
            episode_binding_descriptors=self.descriptors, episode_record_receipts=True,
            initial_known_record_refs=[], **kwargs)


def test_constructor_iteration_prepares_revision_with_fixed_process_and_original_return(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        timing = make_history(tmp_path/'statistics.sqlite')
        forecasts = ExecutionExpectations(tmp_path/'statistics.sqlite', by_grain={
            'annotation': [timing], 'scientific_process': [timing]})
        inherited = case.scope['subject_refs'][0]
        frames, received = [], []

        def first(context):
            frames.append(deepcopy(context))
            assert context['execution_expectations']['status'] == 'available'
            assert context['requested_form'] == FORM
            assert context['scientific_process']['thought']['id'] == 'P01'
            assert 'fixture.excluded' not in [row['name'] for row in context['tools']]
            assert 'waiting_support' in context and 'pending_work' in context
            return action('fixture.inspect', {'value': 2}, 'unresolved')

        def revise(context):
            frames.append(deepcopy(context))
            assert context['last_local_outcome']['result']['observed'] == 2
            return action('process.revise', {'thought_ref': case.library.reference('P77'),
                "tools": []}, 'qualified')

        def after_revision(context):
            frames.append(deepcopy(context))
            frame = context['scientific_process']
            assert frame['thought']['id'] == 'P01' and [entry['name'] for entry in frame['tools']] == ['fixture.inspect']
            assert 'fixture.inspect' in [row['name'] for row in context['tools']]
            assert frame['assignment']['selection'] == case.selection()
            assert 'revision_decision_index' not in frame and 'revision' not in frame
            proposal = context['last_local_outcome']
            assert proposal['result']['selection'] == case.selection('P77', ())
            assert proposal['revision_origin']['preparation_operation_ref'] == proposal['operation_ref']
            return action('process.entry', {'option_id': 'P77'}, 'qualified')

        def parent_uses_form(context):
            received.extend(context['child_reports'])
            assert len(received) == 1 and received[0]['status'] == 'qualified'
            assert len(received[0]['sources']) == 1
            return action('process.entry', {'option_id': 'A01'})

        provider = ScriptedProvider([case.commission([inherited]), first, revise, after_revision,
            action('episode.history', {'view': 'index'}, 'qualified'), parent_uses_form])
        workflow = case.workflow(provider, execution_expectations=forecasts)
        root = workflow.build('annotation', 'root', 'Resolve the fixture uncertainty', case.scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        assert [controller.scores for controller in case.controllers] == [[1, 0], [1, 0, 0, 0]]
        assert len(case.tools.calls) == 1
        assert len(workflow.episode_bindings.roles) == 8  # one scientific + existing seven literature roles
        child_row = store.db.execute("SELECT * FROM runtime_episodes WHERE json_extract(path,'$[1][0]')="
            "'scientific_process'").fetchone()
        request = json.loads(child_row['request'])
        assert request['message']['episode_assignment']['selection'] == case.selection()
        assert request['report_contract']['measurements']['schema'] == FORM
        baseline = set(workflow.receipts.known(child_row['episode_id'], baseline=True))
        assert inherited in baseline and not baseline.intersection(received[0]['sources'])
        outcomes = [json.loads(row[0]) for row in store.db.execute('SELECT result FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (child_row['episode_id'],))]
        assert all(row['record_refs'] == [] for row in outcomes[1:])
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        assert not store.list('observation') and not store.list('assessment')
        assert frames[0]['scientific_process']['selection'] == case.selection()
        assert all(frame['scientific_process']['selection'] == case.selection() for frame in frames)


def workflow_tools(case):
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    return ScientificToolLibrary(case.directory/'scientific-tool-library')


def prepared_child(case, workflow):
    root = workflow.build('annotation', 'root', 'Resolve fixture uncertainty', case.scope)
    unit = workflow.selected(root.source, case.commission()['selection'], 0)
    return root, unit.child


@pytest.mark.parametrize('request_results,request_sources,mark_revision',
    [(True, True, True), (False, True, True), (True, False, True), (True, True, False)],
    ids=['requested_lineage', 'unrequested_lineage', 'metadata_only', 'ordinary_changed_selection'])
def test_nested_revision_returns_existing_local_results_only_through_requested_forms(
        tmp_path, request_results, request_sources, mark_revision):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        process_source = report_sources(case.library, workflow_tools(case))['scientific_process_results']['report_schema']
        outer_form = deepcopy(FORM)
        if not request_sources:
            outer_form['properties'].pop('sources')
            outer_form['required'].remove('sources')
        if request_results:
            outer_form['properties']['approaches'] = process_source
            outer_form['required'].append('approaches')
        nested_form = obj({'status': FORM['properties']['status'],
            'sources': {**FORM['properties']['sources'], 'x-source': 'committed_record_refs'},
            'approaches': process_source})
        controllers, fits, received, preparations = {}, {}, {}, []

        def controller_factory(path, initial):
            depth = len(path)
            fits[depth] = []
            def estimate(history, parameters, contexts):
                fits[depth].append(tuple(history))
                # Caller fixture estimates exercise the real controller and its
                # unchanged upper-band comparison, in the existing source-count unit.
                final = len(history) == {1: 2, 2: 4, 3: 2}[depth]
                band = (SignedNumericBand(-.25, -.25, -.25, uncertainty_code=0, alpha=0)
                    if final and depth == 2 else NumericBand.exact(0 if final else .5))
                return YieldEstimate(len(history), band, parameters, {'private_fixture_history': list(history)})
            controllers[depth] = YieldController(str(path), initial, 0, estimate_with_context=estimate)
            return controllers[depth]

        def source_count(store, scope, **assignment):
            episode_id = assignment.get('episode_id')
            if episode_id is None:
                row = store.db.execute('SELECT episode_id FROM runtime_episodes '
                    'WHERE json_array_length(path)=1').fetchone()
                if row is None:
                    return 0
                episode_id = row[0]
            return sum(store.get(ref).get('provider') == 'fixture.scientific_process'
                for ref in workflow.receipts.known(episode_id))
        source_count.requires_episode_receipts = True

        original_execute, findings = case.tools.execute, []
        def repeat_existing(name, arguments, *, scope, operation_key):
            if not findings:
                outcome = original_execute(name, arguments, scope=scope, operation_key=operation_key)
                findings.extend(outcome['record_refs'])
                return outcome
            # This actual selected read repeats the inherited source. It does
            # not publish another finding or mark the existing source changed.
            case.tools.calls.append((name, deepcopy(arguments), scope, operation_key))
            return {'status': 'completed', 'record_refs': findings[:], 'changed_record_refs': [],
                'result': {'observed': arguments['value']}}
        case.tools.execute = repeat_existing

        outer = case.commission()
        outer['selection']['schema_json'] = json.dumps(outer_form)
        def select_revision(context):
            assert context['scientific_process']['selection'] == case.selection()
            proposal = context['last_local_outcome']
            preparations.append(deepcopy(proposal))
            assert proposal['record_refs'] == proposal['changed_record_refs'] == []
            assert proposal['result']['parent_selection_sha256'] == scientific_digest(case.selection())
            nested = case.commission(findings)
            nested['selection'].update(goal='Test the alternative explanation against the existing finding',
                purpose='Return this alternative and its recorded process result',
                schema_json=json.dumps(nested_form))
            nested['selection']['assignment']['selection'] = proposal['result']['selection']
            if mark_revision:
                nested['selection']['assignment']['revision_origin'] = proposal['revision_origin']
            nested['report_update'] = {'status': 'qualified'}
            return nested

        def revised_read(context):
            assert context['requested_form'] == nested_form
            assert context['scientific_process']['selection'] == case.selection('P77')
            assert context['scientific_process']['assignment'].get('revision_origin') == (
                preparations[0]['revision_origin'] if mark_revision else None)
            assert context['current_credit'] == 1
            return action('fixture.inspect', {'value': 2}, 'qualified')

        def child_uses_revision(context):
            assert context['scientific_process']['selection'] == case.selection()
            assert context['requested_form'] == outer_form
            report, = context['child_reports']
            received['child'] = deepcopy(report)
            assert report['sources'] == findings
            assert context['current_credit'] == 1
            return action('process.entry', {'option_id': 'P01'}, 'qualified')

        def root_uses_original_form(context):
            report, = context['child_reports']
            received['root'] = deepcopy(report)
            assert set(report) == set(outer_form['properties'])
            assert context['current_credit'] == int(request_sources)
            return action('process.entry', {'option_id': 'A01'})

        provider = ScriptedProvider([outer, action('fixture.inspect', {'value': 2}, 'unresolved'),
            action('process.revise', {'thought_ref': case.library.reference('P77'),
                "tools": ["fixture.inspect"]}, 'qualified'), select_revision,
            revised_read, action('process.entry', {'option_id': 'P77'}, 'qualified'),
            child_uses_revision, root_uses_original_form])
        workflow = Workflow(store, case.tools, provider, case.directory, 'fixture-run', controller_factory,
            source_count, project_child_credit=source_count,
            episode_binding_descriptors=case.descriptors, episode_record_receipts=True,
            initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Resolve the fixture uncertainty', case.scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        assert {depth: controller.state().history for depth, controller in controllers.items()} == {
            1: (int(request_sources), 0), 2: (1, 0, 0, 0), 3: (0, 0)}
        assert {depth: len(history) for depth, history in fits.items()} == {1: 3, 2: 5, 3: 3}
        assert len(provider.contexts) == 8 and len(case.tools.calls) == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        assert workflow.source_credit_view(root.source)['credit'] == int(request_sources)
        episodes = {len(json.loads(row['path'])): row for row in store.db.execute('SELECT * FROM runtime_episodes')}
        own_rows = {}
        for depth in (2, 3):
            saved = episodes[depth]
            request = json.loads(saved['request'])
            selection = case.selection() if depth == 2 else case.selection('P77')
            assert request['message']['episode_assignment']['selection'] == selection
            assert request['message']['scientific_process']['selection'] == selection
            assert request['report_contract']['measurements']['schema'] == (outer_form if depth == 2 else nested_form)
            frozen = json.loads(store.db.execute('SELECT facts FROM runtime_forms WHERE episode_id=?',
                (saved['episode_id'],)).fetchone()[0])
            row = frozen['scientific_process_results'][0]
            own_rows[depth] = row
            assert row['selection'] == selection
            assert row['initial_credit'] == saved['initial_credit'] == (0 if depth == 2 else 1)
            assert row['credit'] == frozen['credit'] == 1
            assert row['episode_yield'] == frozen['episode_yield']
            assert row['episode_yield']['expected_next_gain'] == controllers[depth].state().estimate.expected_next_gain.as_record()
            assert row['completed_actions'] == len(controllers[depth].state().history)
            assert row['credit_kind'] == 'scientific'
            assert row['credit_binding_ref'] == credit_binding_ref({
                'credit_kind': 'scientific', 'credit_binding': workflow.child_credit_binding})
        # Both levels use the same caller child projection. Its declared binding
        # is identified, while its local scalar/history remains the child's own.
        assert own_rows[2]['credit_binding_ref'] == own_rows[3]['credit_binding_ref']
        child_row, revision_row = own_rows[2], own_rows[3]
        assert child_row['origin_kind'] == 'ordinary_child' and child_row['preparation_operation_ref'] is None
        assert revision_row['origin_kind'] == ('approach_revision' if mark_revision else 'ordinary_child')
        assert revision_row['parent_invocation_ref'] == child_row['invocation_ref']
        assert revision_row['preparation_operation_ref'] == (preparations[0]['operation_ref'] if mark_revision else None)
        assert child_row['parent_invocation_ref'] == scientific_invocation_ref(workflow.run_id, root.source.path)
        assert received['child']['approaches'] == [revision_row]
        expected = [child_row, revision_row] if request_results else []
        assert received['root'].get('approaches', []) == expected
        assert workflow.services.scientific_received_results(workflow.binding_context(root.source)) == expected
        # Rows are communication metadata, never Store evidence or a separate
        # score/observation. A metadata-only return supplies no scientific refs.
        root_return = json.loads(store.db.execute('SELECT result FROM runtime_actions '
            'WHERE episode_id=? AND decision_index=0', (root.source.episode_id,)).fetchone()[0])
        assert root_return['record_refs'] == (findings if request_sources else [])
        assert 'private_fixture_history' not in json.dumps(received)


def test_final_catalog_and_direct_dispatch_keep_selected_choices_narrow(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root, child = prepared_child(case, workflow)
        schema = workflow.action_schema(root.source)
        assert not any(row['properties']['kind'].get('const') == 'child'
                       for row in schema['properties']['selection']['anyOf'])
        with pytest.raises(ValueError, match='requires_filled_process'):
            workflow.selected(root.source, {**case.commission()['selection'], 'kind': 'child'}, 1)
        for name, arguments in [('fixture.excluded', {'value': 2}), ('fixture.inspect', {'value': 11})]:
            outcome = asyncio.run(workflow.execute(child.source, name, arguments,
                decision_index=0, operation_key='rejected'))
            assert outcome['status'] == 'invalid'
        assert case.tools.calls == []
        actual = next(row for row in workflow.catalog(child.source.scope, source=child.source)
                      if row['name'] == 'fixture.inspect')
        assert Draft202012Validator(actual['input_schema']).is_valid({'value': 2})
        assert not Draft202012Validator(actual['input_schema']).is_valid({'value': 11})
        binding = workflow.specialist(child.source)
        monkeypatch.setattr(binding, 'permitted_common_actions', lambda context: ('reason',))
        kinds = {row['properties']['kind']['const'] for row in
                 workflow.action_schema(child.source)['properties']['selection']['anyOf']}
        assert kinds == {'reason'}
        with pytest.raises(ValueError, match='action_not_available'):
            workflow.selected(child.source, {'kind': 'redeliver_report'}, 2)
        with pytest.raises(ValueError, match='action_not_available'):
            workflow.selected(child.source, action('process.entry', {'option_id': 'P77'})['selection'], 2)
        outcome = asyncio.run(workflow.execute(child.source, 'process.entry', {'option_id': 'P77'},
            decision_index=2, operation_key='excluded-common-action'))
        assert outcome['status'] == 'invalid'


def test_revision_preparation_reconstructs_origin_without_changing_original_process(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root, child = prepared_child(case, workflow)
        context = workflow.binding_context(child.source)
        original = deepcopy(child.request.as_record())
        args = {'thought_ref': case.library.reference('P77'), "tools": []}
        revised = asyncio.run(workflow.execute(child.source, 'process.revise', args,
            decision_index=0, operation_key=f'{workflow.run_id}:{child.source.episode_id}:0'))
        selected = action('process.revise', args)['selection']
        workflow.journal.save('runtime_actions', {'episode_id': child.source.episode_id,
            'decision_index': 0, 'action': json.dumps(selected), 'result': json.dumps(revised), 'credit': 0})
        prepared = workflow.services.scientific_preparation(context, revised['operation_ref'])
        assert prepared['proposal']['selection'] == case.selection('P77', ())
        assert workflow.specialist(child.source).decision_context(context, {})['scientific_process']['selection'] == case.selection()
        reopened = case.workflow(ScriptedProvider([]))
        assert reopened.services.scientific_preparation(context, revised['operation_ref']) == prepared
        assert child.request.as_record() == original
        selected_child = case.commission()['selection']
        selected_child['assignment']['selection'] = revised['result']['selection']
        selected_child['assignment']['revision_origin'] = revised['revision_origin']
        grandchild = workflow.selected(child.source, selected_child, 1).child
        assert grandchild.request.message.as_record()['episode_assignment']['revision_origin'] == revised['revision_origin']
        assert child.request.as_record() == original
        # A forged completed preparation cannot authorize a revision child.
        revised['result']['parent_selection_sha256'] = '0' * 64
        workflow.journal.save('runtime_actions', {'episode_id': child.source.episode_id,
            'decision_index': 0, 'action': json.dumps(selected), 'result': json.dumps(revised), 'credit': 0})
        with pytest.raises(ValueError):
            reopened.services.scientific_preparation(context, revised['operation_ref'])


def test_scientific_library_does_not_add_slots_or_choices_to_literature(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root, scientific = prepared_child(case, workflow)
        selection = case.commission()['selection']
        selection.update(role='literature', assignment={'version': 'literature_assignment_v1',
            'question_context_refs': [], 'source_refs': []})
        literature = workflow.selected(root.source, selection, 1).child
        for source in (root.source, scientific.source):
            assert 'process.search' in {entry['name'] for entry in workflow.catalog(source.scope, source=source)}
        names = {entry['name'] for entry in workflow.catalog(literature.source.scope, source=literature.source)}
        assert not names.intersection({'process.search', 'process.entry', 'process.sources', 'process.revise'})
        assert 'scientific_process' not in literature.request.message.as_record()
        assert workflow.specialist(literature.source).child_roles('literature') == ('literature_strategy',)
        outcome = asyncio.run(workflow.execute(literature.source, 'process.entry', {'option_id': 'P77'},
            decision_index=0, operation_key='outside-scientific-library'))
        assert outcome['status'] == 'invalid' and not outcome['record_refs']


def test_initial_filled_request_is_required_before_credit_or_decisions(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build('annotation', 'root', 'Resolve fixture uncertainty', case.scope)
        from gene_annotation_episode.runtime import TypedReportContract
        contract = TypedReportContract('Return the exact parent form', FORM, workflow.resolver(case.scope))
        with pytest.raises(ValueError, match='scientific_filled_request_required'):
            workflow.build('scientific_process', 'missing', 'Investigate', case.scope,
                parent=root.goal, parent_path=root.source.path, contract=contract,
                initial={'status': 'unresolved'}, episode_assignment=case.commission()['selection']['assignment'])
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1


def test_interrupted_pending_decision_replays_preparation_with_fixed_process_and_form(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)

        def run(provider, *, resume=False):
            return asyncio.run(run_workflow(store, case.tools, provider=provider,
                run_dir=case.directory, resume=resume, controller_factory=case.factory,
                project_credit=root_credit, project_child_credit=child_credit,
                episode_record_receipts=True, initial_known_record_refs=[],
                **({} if resume else {'episode_binding_descriptors': case.descriptors})))

        with pytest.raises(KeyboardInterrupt):
            run(ScriptedProvider([case.commission(), action('fixture.inspect', {'value': 2}, 'unresolved'),
                action('process.revise', {'thought_ref': case.library.reference('P77'),
                    "tools": []}, 'qualified'), KeyboardInterrupt()]))
        child = store.db.execute("SELECT * FROM runtime_episodes WHERE json_extract(path,'$[1][0]')="
            "'scientific_process'").fetchone()
        identity = child['episode_id']
        request = child['request']
        prefix = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (identity,))]
        observed = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations '
            'WHERE episode_id=? ORDER BY unit_index', (identity,))]
        pending = store.db.execute('SELECT request FROM runtime_model_calls WHERE episode_id=? '
            'AND call_index=2', (identity,)).fetchone()[0]
        assert json.loads(pending)['context']['scientific_process']['thought']['id'] == 'P01'
        # The original source can disappear; only the pinned run snapshot is used.
        import shutil
        shutil.rmtree(case.source)
        provider = ScriptedProvider([action('process.entry', {'option_id': 'P77'}, 'qualified'),
            action('episode.history', {'view': 'index'}, 'qualified'),
            action('process.entry', {'option_id': 'A01'})])
        summary = run(provider, resume=True)
        assert summary['completed_actions'] == 2 and summary['credit'] == 1
        assert len(case.tools.calls) == 1  # completed physical fixture action was not repeated
        assert store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (identity,)).fetchone()[0] == request
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions '
            'WHERE episode_id=? AND decision_index<2 ORDER BY decision_index', (identity,))] == prefix
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations '
            'WHERE episode_id=? AND unit_index<2 ORDER BY unit_index', (identity,))] == observed
        assert store.db.execute('SELECT request FROM runtime_model_calls WHERE episode_id=? '
            'AND call_index=2', (identity,)).fetchone()[0] == pending
        assert provider.contexts[0]['scientific_process']['selection'] == case.selection()
        assert provider.contexts[-1]['child_reports'][0]['status'] == 'qualified'


def test_failed_commission_construction_can_roll_back_its_receipt_prefix(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build('annotation', 'root', 'Resolve fixture uncertainty', case.scope)
        with store.transaction():
            with pytest.raises(RuntimeError, match='fixture_commission_failure'):
                with store.transaction():
                    workflow.receipts.bind('uncommitted-child', root.source.episode_id)
                    raise RuntimeError('fixture_commission_failure')
            assert store.db.execute('SELECT 1 FROM runtime_receipt_inheritance '
                'WHERE episode_id=?', ('uncommitted-child',)).fetchone() is None
            assert workflow.receipts.manifest(root.source.episode_id)['parent_episode_id'] is None
