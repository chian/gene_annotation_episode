"""Synthetic evidence exercises local accounts; no biological findings claimed."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit, ScientificInvestigationCredit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider, obj
from test_scientific_hypervolume_runtime import annotation, assessment, evidence


def seed(store):
    path = Path(__file__).resolve().parents[1]/'cases/gene_001/target.fna'
    target, = store.create_problem(path, molecule='dna', role='gene')['subject_refs']
    scope = {'subject_refs': [target]}
    observations = [evidence(store, target, kind) for kind in
                    ('alignment', 'mechanism', 'context_measurement')]
    hypothesis = store.put('hypothesis', {'subject_refs': [target],
        'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
        'context_refs': []}, origin='reasoning')['id']
    inherited = store.put('assessment', assessment(hypothesis, observations[0]['id'], 'direct'),
                          origin='reasoning')['id']
    initial = store.put('annotation', annotation(target, hypothesis, [inherited], 0), origin='reasoning')
    return target, scope, observations, hypothesis, inherited, initial


def test_local_accounts_keep_parent_state_and_duplicate_credit_and_owner_boundaries(tmp_path):
    root = ScientificEvidenceCredit(CreditPolicy())
    local = ScientificInvestigationCredit(root.policy)
    with Store(tmp_path/'workspace') as store:
        target, scope, observations, hypothesis, inherited, parent = seed(store)
        baseline = root(store, scope).credit
        mechanism = store.put('assessment', assessment(hypothesis, observations[1]['id'], 'direct'),
                              origin='reasoning')
        record = annotation(target, hypothesis, [inherited, mechanism['id']], 0)
        with pytest.raises(ContractError, match='requires_runtime_owner'):
            store.put('interpretation_account', record, origin='reasoning', scope=scope)
        first = store.put('interpretation_account', record, origin='reasoning', scope=scope,
                          account_owner=('run', 'child_a'))
        assert first['record_type'] == 'interpretation_account'
        assert 'owner' not in first and 'account_owner' not in first
        assert store.current_annotations(scope) == [parent]
        assert root(store, scope).credit == baseline
        score = local(store, scope).credit
        assert score > baseline
        duplicate = store.put('interpretation_account', record, origin='reasoning', scope=scope,
                              account_owner=('run', 'child_b'))
        assert duplicate['id'] != first['id']
        assert local(store, scope).credit == score
        details = local.read_details(store, scope, details_limit=10, details_offset=0)
        assert {row['interpretation_account_ref'] for row in details['source_contributions']} <= {
            first['id'], duplicate['id']}
        assert all('annotation_ref' not in row for row in details['source_contributions'])
        assert store.query_records('interpretation_account', scope, current_only=True)['total'] == 2
        assert store.reference_subset([first['id']], scope) == [first['id']]

        bad = {**record, 'expected_revision': 1}
        with pytest.raises(ContractError, match='revision_conflict'):
            store.put('interpretation_account', bad, origin='reasoning', scope=scope,
                      account_owner=('run', 'child_c'))
        narrowed = {**scope, 'segments': [{'target_ref': target, 'start': 0, 'end': 3, 'unit': 'nt'}]}
        with pytest.raises(ContractError, match='outside_scope_segments'):
            store.put('interpretation_account', record, origin='reasoning', scope=narrowed,
                      account_owner=('run', 'narrow_child'))

        # A real correction invalidates the exact old assessment in all copied
        # accounts. Keeping copies cannot mask that lost current contribution.
        store.put('assessment', assessment(hypothesis, observations[1]['id'], 'incomparable',
                                          revision=mechanism['revision']), origin='reasoning')
        assert local(store, scope).credit == baseline
        assert root(store, scope).credit == baseline
        assert store.current_annotations(scope) == [parent]
        frozen = local.read_details(store, scope, details_limit=10, details_offset=0)
    with Store(tmp_path/'workspace') as reopened:
        assert local.read_details(reopened, scope, details_limit=10, details_offset=0) == frozen


def test_missing_account_allocation_keeps_its_actual_record_kind(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, scope, observations, hypothesis, inherited, parent = seed(store)
        attribution = assessment(hypothesis, observations[1]['id'], 'contextual')
        attribution.update(extent_basis='context_allocation', context_account_scope=scope, context_scope=scope)
        assessed = store.put('assessment', attribution, origin='reasoning')
        account = annotation(target, hypothesis, [assessed['id']], 0)
        account.update(footprint_kind='whole_input_context', context_account_scope=scope)
        stored = store.put('interpretation_account', account, origin='reasoning', scope=scope,
                           account_owner=('run', 'child'))
        details = ScientificInvestigationCredit(CreditPolicy()).read_details(
            store, scope, details_limit=10, details_offset=0)
        inactive, = details['inactive_dependencies']
        assert inactive['interpretation_account_ref'] == stored['id']
        assert inactive['allocation_owner'] == 'interpretation_account'
        assert inactive['reason'] == 'context_allocation_unlocalized'


def test_member_local_account_reference_preserves_its_scope_through_context(tmp_path):
    # A small boundary fixture, not another development workload or target gene.
    from test_library_scope_ownership import fixture, hypothesis
    store, tools, target, member, other, scope = fixture(tmp_path)
    with store:
        h = store.put('hypothesis', hypothesis(member['id']), origin='reasoning', scope=scope)
        account = store.put('interpretation_account', annotation(member['id'], h['id'], [], 0),
                            origin='reasoning', scope=scope, account_owner=('run', 'child'))
        source = store.put('source', {'provider': 'synthetic_fixture', 'accession': 'context',
            'uri': None, 'artifact_ref': store.artifact('SYNTHETIC context'), 'text_ref': None,
            'request_ref': None, 'version': 'fixture', 'retrieved_at': None}, origin='external')
        context = store.put('context', {'context_type': 'sample', 'name': 'SYNTHETIC',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [account['id']]},
            origin='external', scope=scope)
        # Exercise ownership propagation through context.related_refs.
        reached = store._ownership_reach([context['id']])
        assert reached['library_refs'] == []
        assert reached['context_segments'] == store.coverage(member['id'])
        assert {span['member_ref'] for span in reached['context_segments']} == {member['member_ref']}


@pytest.mark.parametrize('interrupt_child', [False, True])
@pytest.mark.parametrize('nested_child', [False, True])
def test_child_account_gains_form_parent_integration_and_recovery_agree(tmp_path, interrupt_child, nested_child):
    root = ScientificEvidenceCredit(CreditPolicy())
    local = ScientificInvestigationCredit(root.policy)
    with Store(tmp_path/'workspace') as store:
        target, scope, observations, hypothesis, inherited, original = seed(store)
        baseline = root(store, scope).credit
        form = obj({
            'accounts': {'type': 'array', 'x-source': 'changed_interpretation_account_refs',
                'items': {'type': 'string', 'format': 'reference',
                          'x-reference-namespace': 'interpretation_account'}},
            'assessments': {'type': 'array', 'x-source': 'changed_assessment_refs',
                'items': {'type': 'string', 'format': 'reference',
                          'x-reference-namespace': 'assessment'}},
            'credit': {'type': 'number', 'x-source': 'credit'},
        })
        child = {'selection': {'kind': 'child', 'goal': 'Iteratively interpret synthetic evidence',
            'scope': scope, 'purpose': 'Return coherent evidence interpretations for parent integration',
            'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}

        def commission_child(context):
            assert context['scientific_child_credit_binding']['definition'] == local.as_record()
            if context['requested_form'] is None:
                assert context['credit_binding']['definition'] == root.as_record()
            return deepcopy(child)

        def improve(index):
            def selected(context):
                assert root(store, scope).credit == baseline
                assert store.current_annotations(scope) == [original]
                assert context['current_credit'] == local(store, scope).credit
                prior = list(store.iter_current_accounts('interpretation_account', scope))
                references = ([inherited] if not prior else
                    prior[0]['coherent_sets'][0]['interpretations'][0]['assessment_refs'])
                payload = {name: [] for name in store.reasoning_schema()['required']}
                payload['assessments'] = [assessment(hypothesis, observations[index]['id'], 'direct', alias='a')]
                payload['interpretation_accounts'] = [annotation(target, hypothesis,
                    references+['@a'], prior[0]['revision'] if prior else 0, alias='account')]
                return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}
            return selected

        received = []
        def outer_observe(context):
            report, = context['child_reports']
            assert context['current_credit'] == report['credit'] == local(store, scope).credit
            assert context['current_credit'] > baseline
            assert root(store, scope).credit == baseline
            return {'selection': {'kind': 'tool', 'tool': 'episode.credit',
                                  'arguments': {'limit': 1, 'offset': 0}}, 'report_update': {}}

        def integrate(context):
            report, = context['child_reports']
            received.append(deepcopy(report))
            assert context['current_credit'] == baseline
            assert report['credit'] == local(store, scope).credit > baseline
            assert len(report['accounts']) == len(report['assessments']) == 2
            account = max((store.get(ref) for ref in report['accounts']), key=lambda r: r['revision'])
            assert account['record_type'] == 'interpretation_account'
            payload = {name: [] for name in store.reasoning_schema()['required']}
            payload['annotation_updates'] = [annotation(target, hypothesis,
                account['coherent_sets'][0]['interpretations'][0]['assessment_refs'],
                original['revision'], alias='integrated')]
            return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}

        controllers = []
        def factory(path, initial):
            controller = FixtureController(str(path), initial, 2)
            controllers.append(controller)
            return controller
        kwargs = dict(run_dir=tmp_path/'run', controller_factory=factory,
            project_credit=root, project_child_credit=local,
            binding_definitions={'credit': root.as_record(), 'scientific_child_credit': local.as_record()})
        saved_observation = None
        if interrupt_child:
            with pytest.raises(KeyboardInterrupt):
                asyncio.run(run_workflow(store, ToolRegistry(store),
                    provider=ScriptedProvider([commission_child, *([commission_child] if nested_child else []),
                                               improve(1), KeyboardInterrupt()]), **kwargs))
            saved_observation = dict(store.db.execute(
                'SELECT episode_id,unit_index,observation FROM runtime_observations').fetchone())
            controllers.clear()
            provider = ScriptedProvider([improve(2), *([outer_observe] if nested_child else []), integrate])
        else:
            provider = ScriptedProvider([commission_child, *([commission_child] if nested_child else []),
                improve(1), improve(2), *([outer_observe] if nested_child else []), integrate])
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
                                          resume=interrupt_child, **kwargs))
        assert summary['credit'] == received[0]['credit'] > baseline
        assert root(store, scope).credit == local(store, scope).credit == summary['credit']
        root_controller, *children = controllers
        child_controller = children[-1]
        assert root_controller.scores == [0, summary['credit']-baseline]
        assert len(child_controller.scores) == 2 and all(value > 0 for value in child_controller.scores)
        assert sum(child_controller.scores) == pytest.approx(summary['credit']-baseline)
        if nested_child:
            assert children[0].scores == [summary['credit']-baseline, 0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == (6 if nested_child else 4)
        assert all(json.loads(row[0]) == received[0] for row in store.db.execute('SELECT form FROM runtime_forms'))
        if saved_observation is not None:
            assert store.db.execute('SELECT observation FROM runtime_observations WHERE episode_id=? AND unit_index=?',
                (saved_observation['episode_id'], saved_observation['unit_index'])).fetchone()[0] == saved_observation['observation']
