"""Inspect saved full A105 runs without executing scientific work or tests.

Evaluator labels are read only by this report command, after workflow launch.
The live workflow driver never imports this module or loads the evaluator plan.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def capture_initial_prompts(run):
    receipts = []
    for path in run.glob('workflow/providers/*/session-0001/call-00001/request.json'):
        request = json.loads(path.read_text())
        prompt = '\n\n'.join([request.get('model_instructions', '')] + [
            item['text'] for item in request.get('input', []) if item.get('type') == 'text'])
        child = 'For A105 experimental evidence, follow this hierarchy:' in prompt
        # Episode identity prevents a later child from replacing the initial
        # prompt receipt for a different investigation in the same workflow.
        destination = run / 'prompt-receipts' / (request['episode_id'] + '.txt')
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(prompt)
        receipts.append({'episode_id': request['episode_id'], 'request_path': str(path),
            'request_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'prompt_path': str(destination), 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'contains_a105_task': child})
    return receipts


def inspect_case(run, *, review_scope=False):
    database = run / 'state/state.sqlite3'
    if not database.exists():
        return {'case': run.name, 'state': 'not_started'}
    db = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
    tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    records = {key: json.loads(value) for key, value in db.execute('select id,data from records')}
    actions, failures, providers, readers, selections = Counter(), [], [], [], {}
    last_action = None
    for episode, index, action, outcome in db.execute(
            'select episode_id,decision_index,action,result from runtime_actions order by rowid'):
        action = json.loads(action)
        outcome = json.loads(outcome) if outcome else {}
        native = outcome.get('result') or {}
        name = action.get('tool', action.get('kind'))
        actions[name] += 1
        last_action = {'episode_id': episode, 'decision_index': index,
                       'operation': name, 'status': outcome.get('status')}
        if outcome.get('status') in ('failed', 'invalid'):
            failures.append({**last_action, 'action': action, 'feedback': outcome.get('feedback'),
                             'errors': outcome.get('errors')})
        if native.get('version') == 'experimental_database_source_v1':
            providers.append({**last_action, 'arguments': action['arguments'], 'receipt': native})
        if name == 'literature.assay_grading.populate' and native.get('sheet_ref'):
            selections[native['sheet_ref']] = action['arguments']
        elif name.startswith('literature.') and name.endswith('.populate') and native:
            readers.append({**last_action, 'arguments': action.get('arguments'), 'result': native})
    grades = []
    if 'literature_assay_grading_operations' in tables:
        for raw, in db.execute('select outcome from literature_assay_grading_operations order by rowid'):
            native = json.loads(raw).get('result') or {}
            if not native.get('cells'):
                continue
            head = native['cells'][0]
            grades.append({'result': native, 'selection': selections.get(native['sheet_ref']),
                'source': records.get(head['evidence_source_ref']),
                'experiment': records.get(head['experiment_ref']),
                'assertion': records.get(head['assertion_ref'])})
    aggregates = []
    if 'literature_a105_aggregation_operations' in tables:
        aggregates = [json.loads(r[0]).get('result') for r in db.execute(
            'select outcome from literature_a105_aggregation_operations order by rowid')]
    returns = []
    if 'runtime_report_attempts' in tables:
        for episode, form, failure in db.execute(
                'select child_episode_id,form,failure from runtime_report_attempts order by rowid'):
            returns.append({'episode_id': episode, 'accepted': form is not None and failure is None,
                'form': json.loads(form) if form else None, 'failure': json.loads(failure) if failure else None})
    episodes = []
    for episode, path, state, completion in db.execute(
            'select episode_id,path,state,completion from runtime_episodes'):
        observation = db.execute('select observation from runtime_observations '
            'where episode_id=? order by rowid desc limit 1', (episode,)).fetchone()
        episodes.append({'episode_id': episode, 'path': json.loads(path), 'state': state,
            'completion': json.loads(completion) if completion else None,
            'last_continuation': json.loads(observation[0]).get('step') if observation else None})
    candidates = []
    if review_scope and 'runtime_decision_exchanges' in tables:
        for episode, index, raw in db.execute('select episode_id,decision_index,response '
                'from runtime_decision_exchanges where response is not null order by rowid'):
            response = json.loads(raw).get('response') or {}
            selected = response.get('selection') or response.get('lookup') or {}
            if re.search(r'\bblast(?:p|n|x)?\b|\bmmseqs\b|\bdiamond\b|sequence_similarity|homolog',
                         json.dumps(selected), re.I):
                candidates.append({'episode_id': episode, 'decision_index': index,
                    'response_type': response.get('response_type'), 'selected': selected})
    owners = defaultdict(set)
    for grade in grades:
        for cell in grade['result']['cells']:
            if cell['component'] == 'measured_effect':
                for key in cell.get('measurement_keys', []):
                    owners[key].add(cell['experiment_ref'])
    launch = json.loads((run / 'launch.json').read_text())
    db.close()
    return {'case': run.name, 'state': ('finished' if (run / 'result.json').exists()
        else 'timed_out' if (run / 'timeout.json').exists()
        else 'stopped' if (run / 'stopped.json').exists()
        else 'failed' if (run / 'failure.json').exists() else 'running'),
        'goal_sha256': hashlib.sha256(launch['goal'].encode()).hexdigest(),
        'database_focus': launch.get('database_focus'), 'preloaded_evidence': launch['preloaded_evidence'],
        'last_action': last_action, 'action_counts': dict(actions), 'failures': failures,
        'prompt_receipts': capture_initial_prompts(run),
        'provider_results': providers, 'reader_results': readers,
        'grades': grades, 'aggregates': aggregates,
        'returns': returns, 'episodes': episodes, 'scope_review_performed': review_scope,
        'scope_candidates': candidates,
        'measurement_owners': {key: sorted(value) for key, value in owners.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--include-scope-review', action='store_true')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    plan = json.loads((run / 'evaluator/case-plan.json').read_text())
    cases = []
    for entry in plan['case_runs']:
        case = inspect_case(Path(entry['run_dir']), review_scope=args.include_scope_review)
        case['evaluator_label'] = entry['label']
        case['resource_opportunity'] = entry['resource_opportunity']
        case['expected_tool_benefit'] = entry['expected_tool_benefit']
        cases.append(case)
    report = {'captured_at': datetime.now(timezone.utc).isoformat(), 'cases': cases}
    (run / 'evaluator/workflow-report.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Independent A105 workflow observations', '', 'Captured: ' + report['captured_at'], '',
        'Each episode receives an anonymous raw sequence and the identical general task. '
        'Resource opportunities below are evaluator expectations, not model instructions.', '',
        '| Case | Resource opportunity | State | Provider searches | Assay sheets | Aggregates | Accepted returns |',
        '| --- | --- | --- | --- | ---: | ---: | ---: |']
    for case in cases:
        searches = [name.removeprefix('public.') for name in case.get('action_counts', {})
                    if name.endswith(('.search', '.graph_search'))]
        lines.append(f"| {case['case']} / {case['evaluator_label']} | {case['resource_opportunity']} "
            f"| {case['state']} | {', '.join(searches)} | {len(case.get('grades', []))} "
            f"| {len(case.get('aggregates', []))} "
            f"| {sum(r['accepted'] for r in case.get('returns', []))} |")
    lines.extend(['', 'A search invocation, recovered effect, saved assay sheet, saved aggregate '
                  'and accepted report are separate outcomes. Inspect the JSON for actual values '
                  'and unresolved inputs.', ''])
    (run / 'evaluator/workflow-report.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
