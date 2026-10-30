"""Authenticate/rebuild056 pure stage and capture its actual narrow terminal."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_controlled_response_calculations import populate_controlled_response


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stage = BASE / 'a105_controlled_response_design_056/pure_stage_003'
    delivery = json.loads((stage / 'DELIVERY_006.json').read_bytes())
    for name, row in delivery['artifacts'].items():
        path = stage / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    for name, row in {**delivery['owned_new_paths'], **delivery['existing_dependencies_unchanged']}.items():
        assert (ROOT / name).stat().st_size == row['bytes'] and digest(ROOT / name) == row['sha256'], name
    reconstructed = OUT / 'reconstructed_stage_006'
    reconstructed.mkdir()
    applied = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(stage / 'NEW_FILES_006.patch')],
                             cwd=reconstructed, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert 'offset' not in applied.stdout and 'fuzz' not in applied.stdout
    for name, row in delivery['owned_new_paths'].items():
        assert digest(reconstructed / name) == row['sha256'], name
    saved = json.loads((stage / 'NUMERICAL_FIXTURES_005.json').read_bytes())
    for name, result in saved['cases'].items():
        assert populate_controlled_response(result['inputs']) == result, name
    tracked = [*delivery['owned_new_paths'], *delivery['existing_dependencies_unchanged'],
               'tests/test_literature_rate_calculations.py']
    before = {name: digest(ROOT / name) for name in tracked}
    command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        'tests/test_literature_controlled_response_calculations.py',
        'tests/test_literature_rate_calculations.py', 'tests/test_literature_transport_calculations.py']
    # Owner retained a truthful summary rather than full stdout. Capture this
    # one narrow final-generation command for direct root terminal evidence.
    with (OUT / 'TERMINAL_STAGE_006.log').open('xb') as stream:
        run = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    assert run.returncode == 0
    after = {name: digest(ROOT / name) for name in tracked}
    assert before == after
    unit_receipt = json.loads((OUT / 'DIMENSION_AND_UNIT_RECEIPT_001.json').read_bytes())
    calculator = 'gene_annotation_episode/literature_controlled_response_calculations.py'
    assert before[calculator] == unit_receipt['calculator_sha256']
    receipt = {'passed': True, 'delivery_artifacts_verified': len(delivery['artifacts']),
        'new_files_independently_reconstructed': len(delivery['owned_new_paths']),
        'whole_synthetic_sheets_reproduced_exactly': len(saved['cases']),
        'actual_root_command': command, 'actual_root_exit_code': run.returncode,
        'actual_root_terminal': (OUT / 'TERMINAL_STAGE_006.log').read_text(),
        'before_after_tracked_files': before, 'root_unit_invariance_generation_exact': True,
        'scope': 'Accepted pure-calculator stage only; no reader, native operation, source/model/Episode work or complete A105 claim'}
    with (OUT / 'STAGE_RECEIPT_006.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in receipt.items() if key not in ('before_after_tracked_files', 'actual_root_command')}))


if __name__ == '__main__':
    main()
