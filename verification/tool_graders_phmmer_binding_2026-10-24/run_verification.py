"""Explicit verification driver; test native jobs use the bounded runner."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
sys.path.insert(0, str(ROOT))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


command = [str(ROOT/'.venv/bin/python'), '-m', 'pytest', '-q',
    'tests/test_phmmer_grading_binding.py', 'tests/test_phmmer_grading_returns.py',
    'tests/test_homology_results.py', '--basetemp='+str(DIRECTORY/'pytest')]
export_only = '--export-examples' in sys.argv
if '--summarize-existing' in sys.argv or export_only:
    result_code = json.loads((DIRECTORY/'commands.json').read_text())['returncode']
else:
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (DIRECTORY/'pytest.log').write_text(result.stdout)
    write(DIRECTORY/'commands.json', {'command': command, 'cwd': str(ROOT), 'started_at': started,
        'finished_at': datetime.now(timezone.utc).isoformat(), 'returncode': result.returncode,
        'output': 'pytest.log', 'native_policy': {'memory_bytes': 20*1024**3,
            'scratch_bytes': 4*1024**3, 'wall_seconds': None},
        'qualification': 'New grading tests use the required policy. Original retained-output regression tests retain their explicitly smaller parser-only fixture policy.'})
    print(result.stdout, end='')
    result_code = result.returncode
if result_code and not export_only:
    raise SystemExit(result_code)
if export_only:
    print('Exporting retained examples only; original suite return code:', result_code)

from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores

examples = []
for pattern, state_name, label in (
    ('test_retained_17_targets_20_do*', 'workspace', 'retained_real_17_hit_20_domain_output'),
    ('test_tiny_capture_paging_custo*', 'state', 'new_actual_tiny_native_output')):
    case, = [path for path in DIRECTORY.joinpath('pytest').glob(pattern) if not path.is_symlink()]
    with Store(case/state_name) as store:
        for observation in store.list('observation'):
            source = store.get(observation['source_ref'])
            if source.get('provider') != 'native.phmmer.alignment':
                continue
            grading, = source_tool_gradings(store, source['id'])
            row, = grading['scores']['domains']
            if (row['target_name'] not in {'sp|P0AAW1|YBHP_ECOLI', 'sp|A6H7I3|ANGE2_BOVIN', 'insert'}
                    and row['native_domain_score_bits'] >= 0):
                continue
            key = label+'-'+str(len(examples)+1)
            write(DIRECTORY/(key+'.sheet.json'), grading['sheet'])
            write(DIRECTORY/(key+'.scores.json'), grading['scores'])
            assert calculate_hmmer_search_scores(grading['sheet']) == grading['scores']
            examples.append({'label': label, 'sheet': key+'.sheet.json', 'scores': key+'.scores.json',
                'observation_ref': observation['id'], 'source_ref': source['id'],
                'target': row['target_name'], 'native_domain_score_bits': row['native_domain_score_bits'],
                'paired_positions': row['paired_positions'], 'model_span_positions': row['model_span_positions'],
                'sequence_span_residues': row['sequence_span_residues'],
                'sequence_envelope_residues': row['sequence_envelope_residues'],
                'paired_model_coverage': row['paired_model_coverage'],
                'model_span_coverage': row['model_span_coverage'],
                'paired_sequence_coverage': row['paired_sequence_coverage'],
                'sequence_span_coverage': row['sequence_span_coverage'],
                'sequence_identity_fraction': row['sequence_identity_fraction'],
                'native_accuracy': row['native_accuracy'], 'native_domain_bias_bits': row['native_domain_bias_bits'],
                'posterior_lower_mean': row['posterior_lower_mean'], 'posterior_upper_mean': row['posterior_upper_mean'],
                'saved_sheet_recalculation_equal': True})
write(DIRECTORY/'numerical_examples.json', examples)
print(json.dumps(examples, indent=2))
