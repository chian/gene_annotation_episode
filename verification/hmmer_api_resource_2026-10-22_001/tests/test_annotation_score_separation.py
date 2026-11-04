"""Separate score channels, actual Store/form/runtime and synthetic decisions.

Progress values below are fixture-only. These tests establish channel separation
and replay, not a production scientific-progress rule or biological correctness.
"""
import asyncio
import json

import pytest

from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.runtime import run_workflow, WorkflowError
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import (FixtureController, FixtureStore, FixtureTools,
    ScriptedProvider, commission, fixture_credit, obj, reason)
from test_scientific_hypervolume_runtime import assessment, annotation, commit, evidence


def test_new_information_can_lower_actual_annotation_score_without_negative_progress(tmp_path):
    scorer = AnnotationSupportScore(CreditPolicy())
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        observation = evidence(store, target, 'alignment')
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        original = store.put('assessment', assessment(hypothesis, observation['id'], 'direct'), origin='reasoning')
        store.put('annotation', annotation(target, hypothesis, [original['id']], 0), origin='reasoning')
        initial_support = scorer(store, scope).credit
        assert initial_support > 0

        def fixture_progress(state, fixed_scope):
            # Explicit synthetic correction flag. This is not an adopted credit
            # rule: no counts or annotation-support changes set this value.
            selected, = state.current_assessments(fixed_scope)
            return float(selected['applicability'] == 'incomparable')

        def correct(context):
            assert context['current_credit'] == 0
            assert context['annotation_score'] == pytest.approx(initial_support)
            assert context['annotation_score_binding']['definition'] == scorer.as_record()
            assert context['annotation_evidence_vector'] == dict(scorer(store, scope).axis_components)
            return commit(store, assessments=[assessment(hypothesis, observation['id'], 'incomparable',
                alias='corrected', revision=original['revision'])],
                annotation_update=annotation(target, hypothesis, ['@corrected'], 1), report={})

        def inspect(context):
            assert context['current_credit'] == 1
            assert context['annotation_score'] == 0
            assert 'episode.annotation_score' in {tool['name'] for tool in context['tools']}
            return {'selection': {'kind': 'tool', 'tool': 'episode.annotation_score',
                'arguments': {'offset': 0, 'limit': 10}}, 'report_update': {}}

        def inspect_operands(context):
            assert context['current_credit'] == 1
            outcome = context['last_local_outcome']
            assert outcome['status'] == 'completed'
            assert outcome['record_refs'] == outcome['changed_record_refs'] == []
            details = outcome['result']
            assert details['annotation_score'] == context['annotation_score'] == 0
            assert 'credit' not in details
            assert details['annotation_score_binding'] == context['annotation_score_binding']
            assert details['policy'] == scorer.policy.as_record()
            assert 'source_contributions' in details and 'inactive_dependencies' in details
            return {'selection': {'kind': 'tool', 'tool': 'state.query',
                'arguments': {'kind': 'annotation', 'offset': 0, 'limit': 1}}, 'report_update': {}}

        controllers = []
        def factory(path, initial):
            controller = FixtureController(str(path), initial, 3)
            controllers.append(controller)
            return controller

        options = {'run_dir': tmp_path/'run', 'controller_factory': factory,
            'project_credit': fixture_progress, 'project_annotation_score': scorer,
            'binding_definitions': {'credit': {'kind': 'fixture_correction_flag'},
                                    'annotation_score': scorer.as_record()}}
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([correct, inspect, inspect_operands]), **options))
        assert summary['credit'] == 1 and summary['annotation_score'] == 0
        assert controllers[0].scores == [1, 0, 0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([]), resume=True, **options)) == summary
        assert len(controllers) == 1
        without_score = {key: value for key, value in options.items()
                         if key not in {'project_annotation_score', 'binding_definitions'}}
        with pytest.raises(WorkflowError, match='same controller and credit bindings'):
            asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([]),
                resume=True, **without_score))


def test_parent_requests_annotation_fact_and_redelivery_keeps_child_snapshot(tmp_path):
    store = FixtureStore(tmp_path/'state.sqlite3')
    tools = FixtureTools(store)
    def fixture_annotation_score(state, scope):
        return {'credit': 10-fixture_credit(state, scope), 'axis_components': {'synthetic': 0}}
    form = obj({'investigation': {'type': 'number', 'x-source': 'credit'},
                'support': {'type': 'number', 'x-source': 'annotation_score'}})
    delivered = []
    def parent(context):
        report, = context['child_reports']
        delivered.append(report)
        assert report == {'investigation': 2, 'support': 8}
        assert context['annotation_score'] == 8 and context['current_credit'] == 2
        return reason(3)
    def redeliver(context):
        assert context['annotation_score'] == 5 and context['current_credit'] == 5
        delivery, = context['report_deliveries']
        return {'selection': {'kind': 'redeliver_report', 'delivery_ref': delivery['delivery_ref'],
            'purpose': 'Recover the same fixed scientific form', 'schema_json': json.dumps(form)},
            'report_update': {}}
    def after_redelivery(context):
        assert context['annotation_score'] == 5
        assert context['child_reports'][-1] == delivered[0]
        # Redelivery itself has no completed-work observation. Supply the
        # fixture's third actual action without adding progress.
        return reason(0)
    controllers = []
    def factory(path, initial):
        controller = FixtureController(str(path), initial, 3 if len(path) == 1 else 1)
        controllers.append(controller)
        return controller
    try:
        options = {'run_dir': tmp_path/'run', 'controller_factory': factory,
            'project_credit': fixture_credit, 'project_annotation_score': fixture_annotation_score,
            'binding_definitions': {'credit': {'kind': 'fixture_progress'},
                'annotation_score': {'kind': 'fixture_annotation_support'}}}
        summary = asyncio.run(run_workflow(store, tools,
            provider=ScriptedProvider([commission(form, {}), reason(2), parent, redeliver,
                                      after_redelivery]), **options))
        assert summary['credit'] == summary['annotation_score'] == 5
        assert controllers[0].scores == [2, 3, 0]
        assert controllers[1].scores == [2]
        rows = store.db.execute('SELECT form FROM runtime_report_attempts ORDER BY decision_index').fetchall()
        assert len(rows) == 2 and all(json.loads(row[0]) == delivered[0] for row in rows)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert asyncio.run(run_workflow(store, tools, provider=ScriptedProvider([]),
            resume=True, **options)) == summary
    finally:
        store.db.close()


def test_case_harness_records_optional_annotation_binding_without_defaulting_progress(tmp_path):
    from gene_annotation_episode.case_execution import prepare_case_run, run_prepared_case
    from test_case_execution import PARAMETERS, POLICY, inspect_sources, prepared
    from test_homology_episode_runtime import Provider

    case, configuration, policy = prepared(tmp_path)
    body = POLICY.replace('    def job_credit(store, **kwargs):',
        "    def annotation_score(store, scope):\n        return parameters['annotation_support']\n"
        '    def job_credit(store, **kwargs):')
    old = "{'kind':'fixture_estimator','cost':parameters['cost'],'numerical':parameters['numerical']})"
    replacement = (old[:-1]+", project_annotation_score=annotation_score, "
        "annotation_score_definition={'kind':'fixture_annotation_support',"
        "'value':parameters['annotation_support']})")
    assert old in body
    policy.write_text(body.replace(old, replacement))
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    provider = Provider([inspect_sources()])
    summary = asyncio.run(run_prepared_case(run, policy_file=policy,
        parameters={**PARAMETERS, 'annotation_support': 12.5}, provider=provider))
    assert summary['credit'] == 0 and summary['annotation_score'] == 12.5
    assert provider.contexts[0]['annotation_score'] == 12.5
    definition = json.loads((run/'policy-binding.json').read_text())['definitions']['annotation_score']
    assert definition == {'kind': 'fixture_annotation_support', 'value': 12.5}
    settings = json.loads((run/'run.json').read_text())
    assert settings['binding_definitions']['annotation_score']['definition'] == definition
    assert asyncio.run(run_prepared_case(run, resume=True, provider=Provider([]))) == summary
