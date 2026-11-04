"""Scientific projection/form/accounting integration, with scripted reasoning.

The target sequence is the fixed ybhP case. Every scientific evidence row below
is explicitly synthetic. This verifies the runtime integration, not YbhP biology,
model reasoning, production scoring choices or numerical stopping behavior.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.credit import CreditPolicy, project_credit, softened_hypervolume
from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.runtime import run_workflow
from test_runtime import FixtureController, ScriptedProvider, obj


def evidence(store, target, kind):
    artifact = store.artifact('SYNTHETIC runtime integration evidence: '+kind)
    source = store.put('source', {
        'provider': 'synthetic_fixture', 'accession': kind, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')
    return store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [target], 'kind': kind,
        'source_ref': source['id'], 'measurements': [], 'dependencies': [],
        'anchor': None}, origin='external')


def assessment(hypothesis, observation, applicability, *, alias=None, revision=0):
    result = {'hypothesis_ref': hypothesis, 'observation_ref': observation,
        'relation': 'strengthens', 'applicability': applicability,
        'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': revision}
    if alias is not None:
        result['alias'] = alias
    return result


def annotation(target, hypothesis, assessments, revision, *, alias=None):
    result = {'subject_ref': target, 'footprint_kind': 'localized',
        'coherent_sets': [{'interpretations': [{'hypothesis_ref': hypothesis,
            'disposition': 'unresolved', 'assessment_refs': assessments}], 'context_refs': []}],
        'alternative_refs': [hypothesis], 'resolution': 'unresolved',
        'expected_revision': revision}
    if alias is not None:
        result['alias'] = alias
    return result


def commit(store, *, assessments, annotation_update, report):
    payload = {name: [] for name in store.reasoning_schema()['required']}
    payload['assessments'] = assessments
    payload['annotation_updates'] = [annotation_update]
    return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': report}


def test_scientific_child_form_parent_revision_and_hypervolume_describe_same_work(tmp_path):
    # Nondefault numbers demonstrate binding fidelity, not approved values.
    policy = CreditPolicy(scale=137, epsilon=.4, unresolved_factor=.7)
    scorer = ScientificEvidenceCredit(policy)
    definition = scorer.as_record()
    target_file = Path(__file__).resolve().parents[1]/'cases/gene_001/target.fna'
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(target_file, molecule='dna', role='gene')['subject_refs']
        scope = {'subject_refs': [target]}
        comparative, mechanistic, context = [evidence(store, target, kind) for kind in
            ('alignment', 'mechanism', 'context_measurement')]
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        inherited = store.put('assessment', assessment(hypothesis, comparative['id'], 'direct'),
                              origin='reasoning')
        store.put('annotation', annotation(target, hypothesis, [inherited['id']], 0), origin='reasoning')
        baseline = scorer(store, scope).credit
        assert baseline > 0

        form = obj({
            'interpretation': {'type': 'string', 'enum': ['unresolved']},
            'local_credit': {'type': 'number', 'x-source': 'credit'},
            'assessments': {'type': 'array', 'x-source': 'changed_assessment_refs', 'items': {
                'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}},
            'annotations': {'type': 'array', 'x-source': 'changed_annotation_refs', 'items': {
                'type': 'string', 'format': 'reference', 'x-reference-namespace': 'annotation'}},
        })
        report = {'interpretation': 'unresolved'}
        initial = {'selection': {'kind': 'child',
            'goal': 'Iteratively assess the explicitly synthetic evidence fixture',
            'scope': scope, 'purpose': 'Revise the synthetic account using source-linked evidence',
            'schema_json': json.dumps(form), 'initial_report_json': json.dumps(report)}, 'report_update': {}}

        def first(context_input):
            assert context_input['current_credit'] == pytest.approx(baseline)
            assert context_input['credit_binding']['definition'] == definition
            current, = store.current_annotations(scope)
            return commit(store, assessments=[assessment(hypothesis, mechanistic['id'], 'transfer', alias='m')],
                annotation_update=annotation(target, hypothesis, [inherited['id'], '@m'], current['revision'], alias='n'),
                report=report)

        def second(context_input):
            current = project_credit(store, scope, policy)
            assert context_input['current_credit'] == pytest.approx(current.credit)
            assert current.credit > baseline
            assert context_input['current_evidence_vector'] == dict(current.axis_components)
            original, = store.current_annotations(scope)
            mechanism_assessment = next(a for a in store.current_assessments(scope)
                                        if a['observation_ref'] == mechanistic['id'])
            return commit(store, assessments=[assessment(hypothesis, context['id'], 'contextual', alias='c')],
                annotation_update=annotation(target, hypothesis,
                    [inherited['id'], mechanism_assessment['id'], '@c'], original['revision'], alias='n'), report=report)

        delivered = []
        def parent_uses_child(context_input):
            child_report, = context_input['child_reports']
            delivered.append(deepcopy(child_report))
            current = project_credit(store, scope, policy)
            assert child_report['local_credit'] == pytest.approx(current.credit)
            assert context_input['current_credit'] == pytest.approx(current.credit)
            assert context_input['current_evidence_vector'] == dict(current.axis_components)
            assert child_report['interpretation'] == 'unresolved'
            assert inherited['id'] not in child_report['assessments']
            assert len(child_report['assessments']) == len(child_report['annotations']) == 2
            selected = next(store.get(ref) for ref in child_report['assessments']
                            if store.get(ref)['observation_ref'] == mechanistic['id'])
            original, = store.current_annotations(scope)
            remaining = [ref for ref in original['coherent_sets'][0]['interpretations'][0]['assessment_refs']
                         if ref != selected['id']]
            # A concrete correction of this contribution removes its current
            # support. It must reach state, next credit and the signed history.
            return commit(store, assessments=[assessment(hypothesis, mechanistic['id'], 'incomparable',
                alias='corrected', revision=selected['revision'])],
                annotation_update=annotation(target, hypothesis, remaining+['@corrected'],
                                             original['revision'], alias='n'), report={})

        controllers = []
        def factory(path, initial_credit):
            controller = FixtureController(str(path), initial_credit, 2)
            controllers.append(controller)
            return controller

        provider = ScriptedProvider([initial, first, second, parent_uses_child])
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path/'run', controller_factory=factory, project_credit=scorer,
            project_child_credit=scorer,
            binding_definitions={'credit': definition, 'scientific_child_credit': definition}))
        final = project_credit(store, scope, policy)
        expected_axes = {'comparative': .7, 'biological_context': .35*.7}
        assert final.credit == pytest.approx(policy.scale*softened_hypervolume(expected_axes, policy))
        assert summary['credit'] == pytest.approx(final.credit)
        assert summary['completed_actions'] == 2
        root, child = controllers
        assert root.scores[0] == pytest.approx(delivered[0]['local_credit']-baseline)
        assert root.scores[1] == pytest.approx(final.credit-delivered[0]['local_credit'])
        assert root.scores[1] < 0
        assert sum(child.scores) == pytest.approx(root.scores[0])
        assert len(child.scores) == len(root.scores) == 2
        assert sum(root.scores) == pytest.approx(final.credit-baseline)
        saved_form, = store.db.execute('SELECT form FROM runtime_forms').fetchone()
        assert json.loads(saved_form) == delivered[0]
        assert delivered[0]['local_credit'] > final.credit
        details = scorer.read_details(store, scope, details_limit=10, details_offset=0)
        assert details['policy'] == policy.as_record()
        assert details['credit'] == pytest.approx(final.credit)
        assert {row['source_ref'] for row in details['source_contributions']} == {
            comparative['source_ref'], context['source_ref']}
        assert len(store.targets()) == 1


def test_scientific_binding_requires_explicit_policy_and_preserves_commission_scope(tmp_path):
    with pytest.raises(TypeError, match='explicit_scientific_CreditPolicy_required'):
        ScientificEvidenceCredit({})
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        narrow = {**scope, 'segments': [{'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]}
        scorer = ScientificEvidenceCredit(CreditPolicy())
        with pytest.raises(ValueError, match='differs_from_original_commission'):
            scorer(store, scope, assignment={'scope': narrow}, episode_id='fixture', run_id='fixture')
        assert scorer(store, narrow, assignment={'scope': narrow}).credit == 0


def test_assessment_only_child_returns_its_work_but_selected_binding_waits_for_parent_account(tmp_path):
    """Characterize the disclosed scoring gap, not a desired child-credit rule.

    The explicit fixture controller does not establish numerical saturation.
    This trace isolates valid child work/form delivery from parent integration.
    """
    scorer = ScientificEvidenceCredit(CreditPolicy())
    target_file = Path(__file__).resolve().parents[1]/'cases/gene_001/target.fna'
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(target_file, molecule='dna', role='gene')['subject_refs']
        scope = {'subject_refs': [target]}
        observed = [evidence(store, target, kind) for kind in ('alignment', 'mechanism')]
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        form = obj({
            'assessment_refs': {'type': 'array', 'x-source': 'changed_assessment_refs',
                'items': {'type': 'string', 'format': 'reference',
                          'x-reference-namespace': 'assessment'}},
            'local_credit': {'type': 'number', 'x-source': 'credit'},
        })
        child = {'selection': {'kind': 'child',
            'goal': 'Iteratively assess the two synthetic evidence sources for the fixed gene',
            'scope': scope, 'purpose': 'Return source-linked assessments for parent integration',
            'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}

        def assess(index):
            def selected(context):
                assert context['current_credit'] == 0
                assert store.current_annotations(scope) == []
                payload = {name: [] for name in store.reasoning_schema()['required']}
                payload['assessments'] = [assessment(hypothesis, observed[index]['id'], 'direct',
                                                     alias='axis_'+str(index))]
                return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}
            return selected

        received = []
        def integrate(context):
            report, = context['child_reports']
            received.append(report)
            assert context['current_credit'] == report['local_credit'] == 0
            assert store.current_annotations(scope) == []
            assert len(report['assessment_refs']) == 2
            assert {store.get(ref)['observation_ref'] for ref in report['assessment_refs']} == {
                row['id'] for row in observed}
            return commit(store, assessments=[], annotation_update=annotation(
                target, hypothesis, report['assessment_refs'], 0, alias='integrated'), report={})

        controllers = []
        def factory(path, initial):
            controller = FixtureController(str(path), initial, 2 if len(path) == 1 else 3)
            controllers.append(controller)
            return controller

        provider = ScriptedProvider([child, assess(0), assess(1),
            {'selection': {'kind': 'tool', 'tool': 'episode.credit',
                           'arguments': {'limit': 1, 'offset': 0}}, 'report_update': {}}, integrate])
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path/'run', controller_factory=factory,
            project_credit=scorer, project_child_credit=scorer,
            binding_definitions={'credit': scorer.as_record(),
                                 'scientific_child_credit': scorer.as_record()}))
        root_controller, child_controller = controllers
        assert summary['credit'] > 0
        assert child_controller.scores == [0, 0, 0]
        assert root_controller.scores == [0, summary['credit']]
        assert json.loads(store.db.execute('SELECT form FROM runtime_forms').fetchone()[0]) == received[0]
        assert received[0]['local_credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
