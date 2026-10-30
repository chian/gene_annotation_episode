"""Retain the controlled primary binding Workflow check as a reopenable example.

This deliberately uses the named engineering test's scripted provider/controller.
It is not live inference or production continuation evidence. The separate actual
configured-model run retains its own unmodified models, controller, pin and Store.
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
    from test_literature_binding_integration import (
        test_primary_selected_child_return_preserves_limit_once_with_ordinary_accounting as check)
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(BASE):
        raise ValueError('owned_verification_directory_required')
    directory.mkdir(parents=True, exist_ok=False)
    check(directory)
    with sqlite3.connect('file:' + str(directory / 'state/state.sqlite3') + '?mode=ro', uri=True) as saved:
        counts = {name: saved.execute('select count(*) from ' + name).fetchone()[0]
                  for name in ['runtime_observations', 'runtime_report_attempts',
                               'literature_binding_operations', 'literature_binding_received']}
        run, = saved.execute('select run_id from runtime_runs').fetchone()
    files = ['tests/test_literature_binding_integration.py',
        'gene_annotation_episode/literature_binding_reader.py',
        'gene_annotation_episode/literature_binding_calculations.py',
        'gene_annotation_episode/literature_binding_storage.py',
        'gene_annotation_episode/literature_episodes.py',
        'gene_annotation_episode/episode_services.py']
    receipt = {'scope': 'retained primary source; scripted decisions and fixture controller',
        'model_backed': False, 'ordinary_workflow_executed': True, 'run_id': run,
        'assertions': 'passed', 'counts': counts, 'source_bookkeeping_scientific_credit': 0,
        'implementation_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in files},
        'limitation': 'No binding observation-model index or configured-model binding investigation is established.'}
    (directory / 'RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
