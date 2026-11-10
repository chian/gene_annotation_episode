"""Compare continuation costs on an unchanged, retained literature trace.

Use the actual saved real-time fits and the existing native stop predicate.
Later recorded evidence describes omissions on this path, not what an earlier
autonomous return or a different search would have produced. No provider calls,
new scientific decisions, fit changes, or scientific record writes occur.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import runpy
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--episode', required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--selected-cost', type=float, default=0.075)
    parser.add_argument('--costs', type=float, nargs='+', default=[
        .001, .002, .00225, .0025, .003, .005, .01, .025, .03, .05, .075, .08])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if not output.is_relative_to(repo / 'runs'):
        parser.error('output must be beneath runs/')
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.source_root.resolve()))
    from gene_annotation_episode import numerical

    db = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    episode = db.execute('SELECT * FROM runtime_episodes WHERE episode_id=?', (args.episode,)).fetchone()
    if episode is None:
        raise ValueError('original_episode_required')
    run_id = episode['run_id']
    rows = []
    previous = episode['initial_credit']
    for item in db.execute('SELECT unit_index,observation FROM runtime_observations '
                           'WHERE run_id=? AND episode_id=? ORDER BY unit_index',
                           (run_id, args.episode)):
        observation = json.loads(item['observation'])
        step = observation['step']
        band = numerical.NumericBand(**step['decision']['projected_gain'])
        native = numerical.predicted_gain_upper_bound(band, step['decision']['continuation_cost'])
        if native.stop != step['stop'] or item['unit_index'] != len(rows):
            raise ValueError('original_continuation_receipt_mismatch')
        if abs(step['credit'] - previous - step['marginal_credit']) > 1e-10:
            raise ValueError('original_credit_delta_mismatch')
        previous = step['credit']
        rows.append({
            'unit_index': item['unit_index'],
            'action_index': observation['credit']['estimation_action_index'],
            'credit': step['credit'], 'marginal_credit': step['marginal_credit'],
            'band': step['decision']['projected_gain'],
            'elapsed_seconds': step['estimate']['diagnostics'].get('forecast_elapsed_seconds'),
            'estimate': step['estimate'], 'original_stop': step['stop'],
            'original_cost': step['decision']['continuation_cost'],
        })
    if not rows:
        raise ValueError('recorded_progress_required')

    cache = {}

    def record(reference):
        if reference not in cache:
            item = db.execute('SELECT data FROM records WHERE id=?', (reference,)).fetchone()
            cache[reference] = json.loads(item['data']) if item else {}
        return cache[reference]

    effects, papers, findings = {}, {}, []
    action_headers = db.execute("SELECT decision_index,json_extract(action,'$.kind') kind,"
        "json_extract(action,'$.tool') tool FROM runtime_actions WHERE run_id=? AND episode_id=? "
        'ORDER BY decision_index', (run_id, args.episode)).fetchall()
    credit_by_action = {row['action_index']: row['marginal_credit'] for row in rows}
    for header in action_headers:
        if header['kind'] != 'reason' and header['tool'] not in {
                'literature.assay_grading.populate', 'public.literature.read'}:
            continue
        item = db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                          (run_id, args.episode, header['decision_index'])).fetchone()
        action, result = json.loads(item['action']), json.loads(item['result'] or '{}')
        if result.get('status') != 'completed':
            continue
        index = header['decision_index']
        if header['tool'] == 'public.literature.read':
            source = record(result.get('result', {}).get('source_ref'))
            if action.get('arguments', {}).get('pmcid') and source.get('artifact_ref'):
                papers.setdefault(source['artifact_ref'], {
                    'first_action': index, 'source_ref': source['id'],
                    'pmcid': action['arguments']['pmcid'], 'artifact_ref': source['artifact_ref']})
        if header['kind'] == 'reason':
            gradings = (result.get('evidence_processing') or {}).get('gradings', [])
            if credit_by_action.get(index, 0) != 0:
                findings.append({'action_index': index, 'marginal_credit': credit_by_action[index],
                    'assessments': action.get('commit', {}).get('assessments', []),
                    'aliases': result.get('aliases', {})})
        else:
            gradings = [{'result': result.get('result', {})}]
        for grading in gradings:
            for cell in grading.get('result', {}).get('cells', []):
                if cell.get('component') != 'measured_effect' or cell.get('status') != 'populated':
                    continue
                source = record(cell.get('evidence_source_ref'))
                # Descriptive identity for this retained trace, not a new
                # production deduplication or scientific-independence rule.
                identity = (source.get('artifact_ref'), cell.get('experiment_ref'),
                            cell.get('value'), cell.get('unit'), cell.get('quantity_kind'))
                effects.setdefault(identity, {
                    'first_action': index, 'source_ref': cell.get('evidence_source_ref'),
                    'artifact_ref': source.get('artifact_ref'),
                    'experiment_ref': cell.get('experiment_ref'),
                    'value': cell.get('value'), 'unit': cell.get('unit'),
                    'quantity_kind': cell.get('quantity_kind'),
                    'original_measurement_keys': cell.get('measurement_keys', []),
                })

    last = rows[-1]
    candidates = []
    for cost in sorted(set([*args.costs, args.selected_cost])):
        stop = next((row for row in rows if numerical.predicted_gain_upper_bound(
            numerical.NumericBand(**row['band']), cost).stop), None)
        retained = stop or last
        cutoff = retained['action_index']
        elapsed = retained['elapsed_seconds']
        candidates.append({
            'cost': cost, 'would_stop': stop is not None, 'action_index': cutoff,
            'observations_retained': retained['unit_index'] + 1,
            'elapsed_minutes': elapsed / 60 if elapsed is not None else None,
            'effort_saved_minutes': (last['elapsed_seconds'] - elapsed) / 60,
            'effort_saved_percent': 100 * (1 - elapsed / last['elapsed_seconds']),
            'iterator_credit_retained': retained['credit'],
            'later_recorded_credit': last['credit'] - retained['credit'],
            'graded_native_quantities_retained': sum(item['first_action'] <= cutoff for item in effects.values()),
            'full_text_sources_acquired': sum(item['first_action'] <= cutoff for item in papers.values()),
        })

    driver = runpy.run_path(str(repo / 'tests/live_a105_database_workflow.py'))
    factory, definition = driver['build_literature_controller'](args.selected_cost)
    actual = factory(tuple(tuple(part) for part in json.loads(episode['path'])), episode['initial_credit'])
    root = db.execute("SELECT path,initial_credit FROM runtime_episodes WHERE run_id=? AND json_array_length(path)=1",
                      (run_id,)).fetchone()
    root_controller = factory(tuple(tuple(part) for part in json.loads(root['path'])), root['initial_credit'])
    if actual.cost != args.selected_cost or root_controller.cost != definition['cost']:
        raise ValueError('effective_role_cost_mismatch')
    selected = next(item for item in candidates if item['cost'] == args.selected_cost)
    report = {
        'version': 'retained_literature_continuation_cost_replay_v1',
        'database': str(args.database.resolve()), 'episode_id': args.episode,
        'source_root': str(args.source_root.resolve()),
        'native_numerical_sha256': hashlib.sha256((args.source_root / 'gene_annotation_episode/numerical.py').read_bytes()).hexdigest(),
        'original_decisions_verified': len(rows), 'last_recorded_action': last['action_index'],
        'last_recorded_elapsed_seconds': last['elapsed_seconds'],
        'counterfactual_scope': 'same recorded path through first native stop; no future model or parent behavior inferred',
        'credit_is_an_iterator_measure_not_an_evidence_score': True,
        'fit_alpha_and_credit_unchanged': True, 'candidates': candidates, 'selected': selected,
        'configured_controller': definition,
        'effective_costs': {'literature': actual.cost, 'root': root_controller.cost},
        'graded_native_quantities': list(effects.values()),
        'full_text_sources_acquired': list(papers.values()),
        'later_graded_native_quantities': [item for item in effects.values() if item['first_action'] > selected['action_index']],
        'later_full_text_sources': [item for item in papers.values() if item['first_action'] > selected['action_index']],
        'limitations': [
            'No autonomous parent return or main-score completion is established by truncating a recorded trace.',
            'Later graded quantities can already exist in earlier raw database responses; later interpretation is not always new acquisition.',
            'Counts describe retained records, not independent experiments, scientific correctness, or annotation probability.',
            'Calibration uses one problematic trace and is provisional, not a universal optimum.',
        ],
    }
    (output / 'replay.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'timeline.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    (output / 'credited_findings.json').write_text(json.dumps(findings, indent=2) + '\n')
    with (output / 'cutoff_comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(candidates[0]))
        writer.writeheader()
        writer.writerows(candidates)
    db.close()
    print(json.dumps({'selected': selected, 'effective_costs': report['effective_costs'],
        'verified_original_decisions': len(rows), 'native_quantities': list(effects.values()),
        'report': str(output / 'replay.json')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
