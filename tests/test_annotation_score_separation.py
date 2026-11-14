"""Separate score channels, actual Store/form/runtime and synthetic decisions.

Progress values below are fixture-only. These tests establish channel separation
and replay, not a production scientific-progress rule or biological correctness.
"""
import asyncio
import json

from gene_annotation_episode.episodic_workflow.root.run_execution import run_workflow
from gene_annotation_episode.state import Store
from test_runtime import (FixtureController, FixtureStore, FixtureTools,
    ScriptedProvider, commission, fixture_credit, obj, reason)


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
