"""Retain primary-unreported and synthetic conditional-model engineering cases.

Uses the named actual Workflow checks with scripted providers/controllers. It
does not claim live inference or give the primary paper synthetic covariance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def main():
    from test_literature_binding_model_integration import (
        test_primary_without_error_model_preserves_limit_and_specific_unknown as primary,
        test_selected_model_action_returns_conditional_values_once as synthetic)
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(BASE):
        raise ValueError('owned_verification_directory_required')
    directory.mkdir(parents=True, exist_ok=False)
    jobs = [('primary_unreported', lambda path: primary(path)),
            ('synthetic_points', lambda path: synthetic(path, False)),
            ('synthetic_threshold', lambda path: synthetic(path, True))]
    receipts = []
    for name, run in jobs:
        path = directory / name
        path.mkdir()
        run(path)
        state = path / ('state/state.sqlite3' if name.startswith('synthetic') else 'state.sqlite3')
        with sqlite3.connect('file:' + str(state) + '?mode=ro', uri=True) as saved:
            tables = {row[0] for row in saved.execute("select name from sqlite_master where type='table'")}
            counts = {table: saved.execute('select count(*) from ' + table).fetchone()[0]
                for table in ['runtime_observations', 'runtime_report_attempts',
                    'literature_binding_operations', 'literature_binding_model_operations',
                    'literature_binding_model_received'] if table in tables}
            outcome, = saved.execute('select outcome from literature_binding_model_operations').fetchone()
            result = json.loads(outcome)['result']
            admitted = [json.loads(row[0]) for row in saved.execute('select cells from literature_binding_model_received')]
            receipts.append({'name': name, 'primary_source': name == 'primary_unreported',
                'model_origin': result['model_origin'], 'model_backed': False,
                'ordinary_workflow_executed': name.startswith('synthetic'),
                'execution': 'scripted_provider_fixture_controller' if name.startswith('synthetic') else 'direct_selected_adapter',
                'counts': counts, 'result': result, 'admitted_parent_subsets': admitted})
    files = ['gene_annotation_episode/literature_binding_models.py',
        'gene_annotation_episode/literature_binding_model_inputs.py',
        'gene_annotation_episode/literature_binding_model_storage.py',
        'gene_annotation_episode/literature_episodes.py',
        'gene_annotation_episode/literature_experimental_prompt.py',
        'tests/test_literature_binding_model_integration.py']
    report = {'status': 'passed', 'scope': 'primary case without supplied model; separate synthetic known-model cases',
        'cases': receipts, 'implementation_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                                    for name in files},
        'limitations': ['No new primary scientific measurement', 'No model-backed binding execution',
            'No known-covariance assumption applied to the primary paper',
            'No target correspondence or final annotation aggregation']}
    (directory / 'POPULATED_MODEL_EXAMPLES.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': 'passed', 'cases': len(receipts), 'directory': str(directory), 'model_backed': False}))


if __name__ == '__main__':
    main()
