"""Connected synthetic support metadata; decisions/controller units are fixtures.

Actual Workflow, Store, receipt projection and AnnotationSupportScore remain in
control. Nothing here adopts support content or demonstrates model science.
"""
import asyncio
from copy import deepcopy
import json
import shutil

import pytest

from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.scientific_process_records import scientific_digest
from gene_annotation_episode.scientific_support_metadata import annotation_policy_routes
from gene_annotation_episode.state import Store
from test_actual_tool_retriever_runtime import ActualToolCase, FORM, GOAL, action
from test_runtime import ScriptedProvider
from test_scientific_findings import finding
from test_scientific_hypervolume_runtime import assessment, annotation, evidence


def annotation_binding(scorer):
    return {'projector': 'gene_annotation_episode.scientific_credit.AnnotationSupportScore',
        'versions': {'requirement': 'same_caller_injected_executable'},
        'definition': scorer.as_record(), 'scope_source': 'context.scope',
        'meaning': 'Explicit synthetic caller annotation policy; separate from progress.'}


class SupportCase(ActualToolCase):
    def __init__(self, *args, policy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = ScientificFindingProgress(FindingProgressPolicy(3))
        self.support = AnnotationSupportScore(policy or CreditPolicy())
        self.binding = annotation_binding(self.support)
        self.initial_known = []

    def workflow(self, provider):
        return Workflow(self.store, self.tools, provider, self.directory, 'support-runtime-fixture',
            self.factory, self.progress, project_child_credit=self.progress,
            project_annotation_score=self.support, annotation_score_binding=self.binding,
            episode_binding_descriptors=[self.descriptor], episode_record_receipts=True,
            initial_known_record_refs=self.initial_known)


def complete(workflow, root):
    closed = asyncio.run(root.run_async(workflow.context))
    asyncio.run(root.build_result(closed))
    return closed


def observations(store, episode_id=None):
    query = 'SELECT observation FROM runtime_observations'
    rows = store.db.execute(query + (' WHERE episode_id=?' if episode_id else '')
        + ' ORDER BY episode_id,unit_index', () if episode_id is None else (episode_id,))
    return [json.loads(row[0]) for row in rows]


def records(store):
    return [tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY id')]


def test_selected_parent_entry_full_child_support_and_separate_revision_preserve_accounting(tmp_path):
    with Store(tmp_path/'state') as store:
        policy = CreditPolicy(observation_axes=(('alignment', 'mechanistic'),))
        case = SupportCase(tmp_path, store, policy=policy, stops={1: 3, 2: 4, 3: 1})
        before = records(store)
        entry, proposal, forms = {}, {}, []
        workflow = case.workflow(ScriptedProvider([]))
        process_schema = workflow.report_sources('scientific_process')['scientific_process_results']['report_schema']
        form = deepcopy(FORM)
        form['properties']['processes'] = process_schema
        form['required'].append('processes')

        def commission(context):
            entry.update(deepcopy(context['last_local_outcome']['result']))
            assert entry['entry'] == case.library.entry('A01')['entry']
            assert entry['annotation_support_routes']['policy'] == policy.as_record()
            assert entry['annotation_support_routes']['routes'] == [
                {'observation_kind': 'alignment', 'status': 'mapped', 'axis': 'mechanistic'},
                {'observation_kind': 'assay_report', 'status': 'unmapped', 'axis': None}]
            # The complete selected entry is received before the child exists.
            assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1
            child = case.commission([])
            child['selection']['schema_json'] = json.dumps(form)
            return child

        def check_frame(context):
            frame = context['scientific_process']
            assert frame['annotation'] == {key: entry['entry'][key]
                for key in ('id', 'name', 'description', 'support')}
            assert frame['annotation_support_routes'] == entry['annotation_support_routes']
            assert frame['selection']['annotation_ref'] == entry['option_ref']
            assert frame['initial_selection_sha256'] == scientific_digest(frame['selection'])
            assert context['requested_form'] == form
            assert context['current_credit'] == context['annotation_score'] == 0
            return frame

        def sources(context):
            check_frame(context)
            return action('process.sources', {'option_ref': entry['option_ref'], 'offset': 0, 'limit': 1}, 'unresolved')

        def revise(context):
            check_frame(context)
            assert context['last_local_outcome']['record_refs'] == []
            return action('process.revise', {'thought_ref': case.library.reference('P77'), 'tools': []}, 'unresolved')

        def separate_child(context):
            check_frame(context)
            proposal.update(deepcopy(context['last_local_outcome']))
            child = case.commission([], thought='P77', revision_origin=proposal['revision_origin'])
            child['selection']['schema_json'] = json.dumps(form)
            return child

        def revised_frame(context):
            frame = check_frame(context)
            assert frame['thought']['id'] == 'P77'
            assert frame['assignment']['revision_origin'] == proposal['revision_origin']
            return action('process.entry', {'option_id': 'A01'}, 'measured')

        def original_receives(context):
            frame = check_frame(context)
            assert frame['thought']['id'] == 'P01'
            revised, = context['child_reports']
            row, = revised['processes']
            assert row['origin_kind'] == 'approach_revision'
            assert row['preparation_operation_ref'] == proposal['operation_ref']
            assert row['completed_actions'] == 1 and row['credit'] == 0
            assert row['selection'] == proposal['result']['selection']
            return action('episode.history', {'view': 'index'}, 'measured')

        def parent_receives(context):
            received, = context['child_reports']
            forms.append(deepcopy(received))
            assert received['records'] == []
            original, revised = received['processes']
            assert original['origin_kind'] == 'ordinary_child'
            assert original['completed_actions'] == 4
            assert original['selection'] == case.selection([])
            assert revised['parent_invocation_ref'] == original['invocation_ref']
            assert all(row['initial_credit'] == row['credit'] == 0 for row in received['processes'])
            return action('episode.history', {'view': 'index'})

        provider = ScriptedProvider([action('process.entry', {'option_id': 'A01'}), commission,
            sources, revise, separate_child, revised_frame, original_receives, parent_receives])
        workflow.provider = provider
        root = workflow.build('annotation', 'root', GOAL, case.scope)
        complete(workflow, root)
        assert records(store) == before
        assert [controller.scores for _, controller in case.controllers] == [[0]*3, [0]*4, [0]]
        assert len(observations(store)) == 8
        actions = list(store.db.execute('SELECT result FROM runtime_actions'))
        assert len(actions) == 8
        assert all(json.loads(row[0])['record_refs'] == [] for row in actions)
        assert all(json.loads(row[0])['changed_record_refs'] == [] for row in actions)
        assert all(frame['scientific_process']['annotation_support_routes'] == entry['annotation_support_routes']
            for frame in provider.contexts if 'scientific_process' in frame)
        assert len(forms) == 1 and store.count('assessment') == store.count('observation') == 0
        assert workflow.context.runtime._controllers == {} and workflow.context._active_episodes == {}


@pytest.mark.parametrize('metadata', ['available', 'omitted', 'unbound', 'custom', 'missing', 'mismatch'])
def test_actual_entry_unavailable_routes_do_not_gate_selected_tool_or_infer_defaults(tmp_path, metadata):
    with Store(tmp_path/'state') as store:
        case = SupportCase(tmp_path, store, stops={1: 2, 2: 1})
        if metadata == 'omitted':
            case.support = AnnotationSupportScore(CreditPolicy(observation_axes=()))
            case.binding = annotation_binding(case.support)
        elif metadata == 'unbound':
            case.support, case.binding = None, None
        elif metadata == 'custom':
            case.support = lambda *args, **kwargs: {'credit': 17}
        elif metadata == 'missing':
            case.binding['definition'] = None
        elif metadata == 'mismatch':
            case.binding['definition']['policy']['scale'] += 1
        received = {}
        def commission(context):
            received.update(context['last_local_outcome']['result'])
            declaration = received['annotation_support_routes']
            if metadata in ('available', 'omitted'):
                assert declaration['status'] == 'available'
                expected = 'mapped' if metadata == 'available' else 'unmapped'
                assert {row['status'] for row in declaration['routes']} == {expected}
            else:
                assert declaration['status'] == 'unavailable'
                assert {row['status'] for row in declaration['routes']} == {'unavailable'}
                assert declaration['policy'] is None
            return case.commission(['sequence.inspect'])
        def work(context):
            assert context['scientific_process']['annotation_support_routes'] == received['annotation_support_routes']
            assert context['scientific_process']['annotation']['support'] == received['entry']['support']
            return action('sequence.inspect', {'subject_ref': case.target}, 'measured')
        workflow = case.workflow(ScriptedProvider([
            action('process.entry', {'option_id': 'A01'}), commission, work]))
        root = workflow.build('annotation', 'root', GOAL, case.scope)
        complete(workflow, root)
        assert store.count('observation') == 1 and store.count('assessment') == 0
        assert len(observations(store)) == 3
        assert [controller.scores for _, controller in case.controllers] == [[0, 0], [0]]
        assert [row[0] for row in store.db.execute('SELECT name FROM tool_operations')] == ['sequence.inspect']


@pytest.mark.parametrize("routes_available", [True, False])
def test_received_negative_outside_support_operands_preserves_progress_support_and_signed_loss(tmp_path, routes_available):
    with Store(tmp_path/'state') as store:
        case = SupportCase(tmp_path, store, stops={1: 3, 2: 2})
        if not routes_available:
            case.binding['definition']['policy']['scale'] += 1
        target, scope = case.target, case.scope
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')['id']
        positive = evidence(store, target, 'alignment')
        negative = evidence(store, target, 'comparison')
        base = assessment(hypothesis, positive['id'], 'direct')
        base['investigation_finding'] = finding(target)
        inherited = store.put('assessment', base, origin='reasoning')
        initial_annotation = annotation(target, hypothesis, [inherited['id']], 0)
        initial_annotation['coherent_sets'][0]['interpretations'][0]['disposition'] = 'supported'
        store.put('annotation', initial_annotation, origin='reasoning')
        case.initial_known = [inherited['id'], negative['id'], hypothesis]
        initial_support = case.support(store, scope).credit
        assert initial_support > 0
        saved = {}
        def commit_negative(context):
            assert context['scientific_process']['annotation_support_routes']['status'] == (
                'available' if routes_available else 'unavailable')
            operand = context['scientific_process']['annotation']['support']['operands'][0]
            assert 'comparison' not in operand['observation_kinds']
            assert 'biological_role' not in operand['hypothesis_predicates']
            current, = store.current_annotations(scope)
            row = assessment(hypothesis, negative['id'], 'direct', alias='negative')
            row['relation'] = 'weakens'
            row['investigation_finding'] = finding(target, value='negative',
                qualification='measurement_does_not_establish_claim')
            account = annotation(target, hypothesis, [inherited['id'], '@negative'], current['revision'], alias='account')
            account['coherent_sets'][0]['interpretations'][0]['disposition'] = 'supported'
            payload = {key: [] for key in store.reasoning_schema()['required']}
            payload.update(assessments=[row], annotation_updates=[account])
            return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {'status': 'unresolved'}}
        def repeat_child(context):
            saved.update(context['last_local_outcome']['aliases'])
            assert context['current_credit'] == 6
            assert 0 < context['annotation_score'] < initial_support
            assert context['annotation_score'] == case.support(store, scope).credit
            return action('episode.credit', {'limit': 2, 'offset': 0}, 'measured')
        def repeat_parent(context):
            assert context['current_credit'] == 6
            report, = context['child_reports']
            assert saved['negative'] in report['records']
            return action('state.query', {'refs': [saved['negative']]})
        def withdraw_parent(context):
            assert context['current_credit'] == 6
            previous = store.get(saved['negative'])
            row = {key: deepcopy(previous[key]) for key in ('hypothesis_ref', 'observation_ref',
                'relation', 'applicability', 'extent_basis', 'condition_refs', 'assumption_refs', 'investigation_finding')}
            row['expected_revision'] = previous['revision']
            row['alias'] = 'withdrawn'
            row['investigation_finding'].update(status='withdrawn', withdrawal_reason='source_misread')
            payload = {key: [] for key in store.reasoning_schema()['required']}
            payload['assessments'] = [row]
            return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}
        workflow = case.workflow(ScriptedProvider([case.commission([]), commit_negative,
            repeat_child, repeat_parent, withdraw_parent]))
        root = workflow.build('annotation', 'root', GOAL, scope)
        complete(workflow, root)
        assert [controller.scores for _, controller in case.controllers] == [[3, 0, -3], [3, 0]]
        assert len(observations(store)) == 5
        assert workflow.project_credit is case.progress and workflow.project_child_credit is case.progress
        assert workflow.project_annotation_score is case.support
        assert workflow.source_credit_view(root.source)['credit'] == 3
