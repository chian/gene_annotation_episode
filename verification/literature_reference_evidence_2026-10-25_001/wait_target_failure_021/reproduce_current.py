"""Isolated engineering reproduction; scripted provider, no models/native jobs."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from detached_workflow_fixture import ControllerFactory, FixtureTools, ScriptedProvider
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.waiting import validate_condition
from method_loop.durable import DurableExecutionStore

OWN = Path(__file__).resolve().parent

def condition(handle=None):
    return {'version': 'event_condition_v1', 'events': [] if handle is None else [
        {'handle': handle, 'event': 'state_changed', 'after_cursor': 0}],
        'reconsider_at': '2026-10-21T12:00:00+00:00'}

async def runtime_case(name, handle_kind):
    directory = OWN / name
    if directory.exists():
        raise RuntimeError('refuse_to_replace_previous_receipt_state:' + name)
    with Store(directory / 'state') as store:
        subject, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        tools = FixtureTools(store)
        if handle_kind == 'source':
            handle = tools.execute('fixture.publish', {'label': 'parent_one'},
                scope={'subject_refs': [subject]}, operation_key='synthetic-only-source')['record_refs'][0]
            assert store.get(handle)['record_type'] == 'source'
        elif handle_kind == 'unknown':
            handle = 'unknown_execution_target_synthetic_021'
        else:
            handle = None
        selected = condition(handle)
        assert validate_condition(selected) == selected
        provider = ScriptedProvider([{'selection': {'kind': 'wait', 'condition': selected},
            'report_update': {}}])
        controllers = ControllerFactory(1)
        error = None
        summary = None
        try:
            summary = await run_workflow(store, tools, provider=provider, run_dir=directory / 'run',
                controller_factory=controllers, project_credit=lambda store, scope: 0.0)
        except Exception as caught:
            error = {'type': type(caught).__name__, 'message': str(caught),
                'traceback': traceback.format_exc()}
        waits = [json.loads(row[0]) for row in store.db.execute('SELECT request FROM episode_waits')]
        wait_rows = [dict(row) for row in store.db.execute('SELECT timing,wake,outcome FROM episode_waits')]
        actions = [dict(row) for row in store.db.execute('SELECT decision_index,result,credit,timing FROM runtime_actions')]
        result = {'case': name, 'selected_condition': selected, 'selected_handle_kind': handle_kind,
            'provider_calls': len(provider.contexts), 'exception': error, 'summary': summary,
            'controller_observations': sum(len(c.deltas) for c in controllers.controllers),
            'runtime_observations': store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0],
            'scientific_observations': store.count('observation'), 'wait_requests': waits,
            'wait_rows': wait_rows, 'actions': actions}
        if handle is not None:
            assert error and error['type'] == 'KeyError' and error['message'] == repr(handle)
            assert result['controller_observations'] == result['runtime_observations'] == 0
            assert len(waits) == 1 and wait_rows[0]['wake'] is wait_rows[0]['outcome'] is None
            assert json.loads(wait_rows[0]['timing'])['intervals'][-1]['state'] == 'raised'
            assert actions[0]['result'] is actions[0]['credit'] is None
        else:
            assert error is None and result['runtime_observations'] == result['controller_observations'] == 1
            assert json.loads(wait_rows[0]['outcome'])['wake_reason'] == 'reconsideration'
        return result

async def main():
    cases = [await runtime_case('current_source_runtime', 'source'),
        await runtime_case('current_unknown_runtime', 'unknown'),
        await runtime_case('current_reconsideration_control', 'reconsideration')]
    backend = DurableExecutionStore(OWN / 'direct_backend')
    try:
        await backend.wait_events(condition('source_34062dfcb91c56513c976b0c'))
    except KeyError as error:
        direct = {'exception': type(error).__name__, 'message': str(error)}
    else:
        raise AssertionError('expected_current_unhandled_lookup')
    paths = ['gene_annotation_episode/runtime.py', 'gene_annotation_episode/waiting.py',
        'gene_annotation_episode/native_event_information.py', 'method_loop/durable.py',
        'method_loop/episode.py', 'method_loop/runtime.py', 'gene_annotation_episode/episode_completion.py',
        'gene_annotation_episode/episode_journal.py', 'gene_annotation_episode/decision_context.py']
    receipt = {'kind': 'synthetic_current_runtime_diagnosis_v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'current_runtime_source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        'no_models_native_jobs_or_real_run_reads': True, 'production_changes': False,
        'direct_backend': direct, 'cases': cases}
    (OWN / 'CURRENT_REPRODUCTION_001.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'receipt': str(OWN / 'CURRENT_REPRODUCTION_001.json'), 'cases': [
        {'case': c['case'], 'exception_type': c['exception']['type'] if c['exception'] else None,
         'runtime_observations': c['runtime_observations'], 'controller_observations': c['controller_observations']}
        for c in cases], 'direct_backend': direct}, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
