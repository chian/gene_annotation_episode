"""Current construction, actual closure and admitted compact process results.

Choices and continuation are engineering fixtures. The original current root
action boundary, child construction, Store, journal and report admission are real.
This verifies typed delivery, not model-facing prompt presentation or biology.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.domain import obj
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import Scenario, action, root_credit, child_credit


def _selector(case, thought='P01'):
    return {'version': 'scientific_process_selection_v3',
        'evidence_axis': case.library.reference('A01'),
        'thought_pattern': case.library.reference(thought),
        'child_tool_info': [{'name': 'fixture.inspect', 'resources': 'local'}]}


def test_current_tool_information_reaches_child_and_compact_return_matches_frozen_source(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = Scenario(tmp_path, store)
        from gene_annotation_episode.scientific_process_reports import report_sources
        tools = ScientificToolLibrary(case.directory / 'scientific-tool-library')
        form = obj({
            'approaches': report_sources(case.library, tools)['scientific_process_results']['report_schema'],
            'sources': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'source'}, 'x-source': 'changed_record_refs'},
        })
        selected = {'version': 'scientific_process_selection_v3',
            'evidence_axis': case.library.reference('A01'),
            'thought_pattern': case.library.reference('P01'),
            'child_tool_info': [{'name': 'fixture.inspect', 'resources': 'local'}]}
        commission = case.commission()
        commission['selection']['assignment']['selection'] = selected
        commission['selection']['schema_json'] = json.dumps(form)
        commission['selection']['initial_report_json'] = '{}'
        child_frames, controllers = [], []

        def inspect(context):
            child_frames.append(deepcopy(context))
            assert context['requested_form'] == form
            supplied = context['scientific_process']['child_tool_info']
            assert len(supplied) == 1
            assert set(supplied[0]) == {'name', 'description', 'resources', 'instructions'}
            assert supplied[0]['name'] == 'fixture.inspect'
            return action('fixture.inspect', {'value': 2})

        def control(path, initial):
            controller = FixtureController(str(path), initial, 1)
            controllers.append(controller)
            return controller

        provider = ScriptedProvider([commission, inspect])
        workflow = Workflow(store, case.tools, provider, case.directory, 'fixture-run',
            control, root_credit, project_child_credit=child_credit,
            episode_binding_descriptors=case.descriptors, episode_record_receipts=True,
            initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Inspect the supplied target', case.scope)
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))
        assert len(child_frames) == 1
        assert len(case.tools.calls) == 1
        assert len(provider.contexts) == 2
        assert [controller.scores for controller in controllers] == [[1], [1]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2

        child = store.db.execute('SELECT * FROM runtime_episodes '
            'WHERE json_array_length(path)=2').fetchone()
        original = json.loads(child['request'])
        full_selection = original['message']['episode_assignment']['selection']
        assert full_selection['child_tool_info'] == child_frames[0]['scientific_process']['child_tool_info']
        frozen = json.loads(workflow.journal.row('runtime_forms', child['episode_id'])['facts'])
        attempt = store.db.execute('SELECT * FROM runtime_report_attempts '
            'WHERE parent_episode_id=?', (root.source.episode_id,)).fetchone()
        assert attempt['failure'] is None
        admitted = json.loads(attempt['form'])
        assert admitted['approaches'] == frozen['scientific_process_results']
        returned, = admitted['approaches']
        assert returned['version'] == 'scientific_process_result_v2'
        assert returned['selection'] == {
            'version': 'scientific_process_selection_report_v1',
            'source_version': 'scientific_process_selection_v3',
            'evidence_axis': selected['evidence_axis'],
            'thought_pattern': selected['thought_pattern'],
            'child_tool_info': selected['child_tool_info'],
        }
        assert returned['initial_credit'] == child['initial_credit'] == 0
        assert returned['credit'] == frozen['credit'] == 1
        assert returned['completed_actions'] == 1
        assert returned['episode_yield'] == frozen['episode_yield']
        assert len(admitted['sources']) == 1
        assert workflow.services.scientific_received_results(
            workflow.binding_context(root.source)) == admitted['approaches']
        assert 'instructions' not in json.dumps(admitted['approaches'])
        assert 'description' not in json.dumps(admitted['approaches'])

        # Reopen the original actual child callback, without executing its work.
        rebuilt = workflow.selected(root.source, commission['selection'], 0).child
        assert rebuilt.request.as_record() == original
        before = store.db.total_changes
        context = workflow.binding_context(rebuilt.source)
        assert workflow.services.scientific_frozen_results(context) == admitted['approaches']
        with pytest.raises(ReportBoundaryError) as failure:
            forged = deepcopy(admitted)
            forged['approaches'][0]['credit'] = 999
            rebuilt.request.report_contract.admit(forged,
                audit_identifiers=(child['episode_id'], original['goal']['goal_id']))
        assert failure.value.diagnostic['code'] == 'scientific_process_result_source_mismatch'
        assert store.db.total_changes == before
        assert len(case.tools.calls) == 1
        # The ordinary redelivery path copies the frozen return and admits it
        # through the reconstructed child context, without rerunning the child.
        observations = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        redelivery = workflow.redeliver(root.source, {
            'delivery_ref': attempt['delivery_ref'],
            'schema_json': json.dumps(form), 'purpose': 'Receive the original closing facts'}, 1)
        assert redelivery.report.as_record() == admitted
        assert redelivery.failure is None
        assert len(case.tools.calls) == 1 and len(provider.contexts) == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == observations
        assert workflow.services.scientific_received_results(context) == []
        assert workflow.services.scientific_received_results(
            workflow.binding_context(root.source)) == admitted['approaches']


@pytest.mark.parametrize('request_results,request_sources,mark_revision', [
    (True, True, True), (False, True, True), (True, False, True), (True, True, False)],
    ids=['revision', 'no_approaches_requested', 'metadata_only', 'ordinary_child'])
def test_current_nested_returns_preserve_each_closure_without_extra_credit(
        tmp_path, request_results, request_sources, mark_revision):
    from gene_annotation_episode.numerical import NumericBand, SignedNumericBand, YieldController, YieldEstimate
    from gene_annotation_episode.scientific_process_records import selector_selection, scientific_digest
    from gene_annotation_episode.scientific_process_reports import report_sources

    with Store(tmp_path / 'state') as store:
        case = Scenario(tmp_path, store)
        tools = ScientificToolLibrary(case.directory / 'scientific-tool-library')
        process_schema = report_sources(case.library, tools)['scientific_process_results']['report_schema']
        source_schema = {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
            'x-reference-namespace': 'source'}, 'x-source': 'committed_record_refs'}
        nested_form = obj({'approaches': process_schema, 'sources': source_schema})
        root_form = obj({
            **({'approaches': process_schema} if request_results else {}),
            **({'sources': source_schema} if request_sources else {})})
        selected = _selector(case)
        commission = case.commission()
        commission['selection']['assignment']['selection'] = selected
        commission['selection']['schema_json'] = json.dumps(root_form)
        commission['selection']['initial_report_json'] = '{}'
        controllers, findings, preparations = {}, [], []
        original_execute = case.tools.execute

        def repeat_received(name, arguments, *, scope, operation_key):
            if not findings:
                outcome = original_execute(name, arguments, scope=scope, operation_key=operation_key)
                findings.extend(outcome['record_refs'])
                return outcome
            case.tools.calls.append((name, deepcopy(arguments), scope, operation_key))
            return {'status': 'completed', 'record_refs': findings[:], 'changed_record_refs': [],
                'result': {'observed': arguments['value']}}
        case.tools.execute = repeat_received

        def control(path, initial):
            depth = len(path)
            def estimate(history, parameters, contexts):
                final = len(history) == {1: 1, 2: 3, 3: 1}[depth]
                band = (SignedNumericBand(-.25, -.5, -.125, uncertainty_code=0, alpha=0)
                    if final and depth == 2 else NumericBand.exact(0 if final else .5))
                return YieldEstimate(len(history), band, parameters, {'private_history': list(history)})
            controller = YieldController(str(path), initial, 0, estimate_with_context=estimate)
            controllers[depth] = controller
            return controller

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

        def revise(context):
            assert context['scientific_process']['selection'] == selected
            assert context['last_local_outcome']['result']['observed'] == 2
            return action('process.revise', {
                'thought_pattern': case.library.reference('P77'),
                'child_tool_info': selected['child_tool_info']})

        def launch_revision(context):
            proposal = context['last_local_outcome']
            preparations.append(deepcopy(proposal))
            assert proposal['record_refs'] == proposal['changed_record_refs'] == []
            full_original = {**selected, 'child_tool_info': tools.resolve_tool_info(selected['child_tool_info'])}
            assert proposal['result']['parent_selection_sha256'] == scientific_digest(full_original)
            nested = case.commission(findings)
            nested['selection']['schema_json'] = json.dumps(nested_form)
            nested['selection']['initial_report_json'] = '{}'
            nested['selection']['assignment']['selection'] = selector_selection(proposal['result']['selection'])
            if mark_revision:
                nested['selection']['assignment']['revision_origin'] = proposal['revision_origin']
            return nested

        def child_reuses_received_source(context):
            assert context['scientific_process']['selection'] == _selector(case, 'P77')
            assert context['current_credit'] == 1
            assert context['requested_form'] == nested_form
            return action('fixture.inspect', {'value': 2})

        provider = ScriptedProvider([commission, action('fixture.inspect', {'value': 2}),
            revise, launch_revision, child_reuses_received_source])
        workflow = Workflow(store, case.tools, provider, case.directory, 'fixture-run', control,
            source_count, project_child_credit=source_count,
            episode_binding_descriptors=case.descriptors, episode_record_receipts=True,
            initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Inspect the supplied target', case.scope)
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))
        assert len(provider.contexts) == 5 and len(case.tools.calls) == 2
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 5
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
        assert {depth: c.state().history for depth, c in controllers.items()} == {
            1: (int(request_sources),), 2: (1, 0, 0), 3: (0,)}

        episodes = {len(json.loads(row['path'])): row for row in store.db.execute('SELECT * FROM runtime_episodes')}
        rows = {}
        for depth, thought in ((2, 'P01'), (3, 'P77')):
            saved = episodes[depth]
            original = json.loads(saved['request'])
            selection = original['message']['episode_assignment']['selection']
            assert selector_selection(selection) == _selector(case, thought)
            assert selection['child_tool_info'] == tools.resolve_tool_info(selected['child_tool_info'])
            frozen = json.loads(workflow.journal.row('runtime_forms', saved['episode_id'])['facts'])
            row = frozen['scientific_process_results'][0]
            rows[depth] = row
            assert row['version'] == 'scientific_process_result_v2'
            assert row['selection']['child_tool_info'] == selected['child_tool_info']
            assert row['initial_credit'] == saved['initial_credit'] == (0 if depth == 2 else 1)
            assert row['credit'] == frozen['credit'] == 1
            assert row['completed_actions'] == {2: 3, 3: 1}[depth]
            assert row['episode_yield'] == frozen['episode_yield']
            assert row['episode_yield']['expected_next_gain'] == controllers[depth].state().estimate.expected_next_gain.as_record()
        assert rows[3]['parent_invocation_ref'] == rows[2]['invocation_ref']
        assert rows[3]['origin_kind'] == ('approach_revision' if mark_revision else 'ordinary_child')
        assert rows[3]['preparation_operation_ref'] == (preparations[0]['operation_ref'] if mark_revision else None)
        assert rows[2]['episode_yield']['expected_next_gain']['value'] == -.25
        attempts = list(store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts'))
        assert len(attempts) == 2 and all(row['failure'] is None for row in attempts)
        forms = {row['parent_episode_id']: json.loads(row['form']) for row in attempts}
        assert forms[episodes[2]['episode_id']]['approaches'] == [rows[3]]
        received = forms[root.source.episode_id]
        expected = [rows[2], rows[3]] if request_results else []
        assert received.get('approaches', []) == expected
        assert workflow.services.scientific_received_results(workflow.binding_context(root.source)) == expected
        assert received.get('sources', []) == (findings if request_sources else [])
        assert 'private_history' not in json.dumps(received)
        assert 'instructions' not in json.dumps(received)
        # Returning approach metadata alone cannot grant receipt of scientific evidence.
        received_sources = [ref for ref in workflow.receipts.known(root.source.episode_id)
            if store.get(ref).get('provider') == 'fixture.scientific_process']
        assert received_sources == (findings if request_sources else [])
