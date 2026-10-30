"""Materialize inspectable sheets/scores and audit isolated recalculation."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode import infernal_search_inputs as inputs
from gene_annotation_episode import infernal_search_grader as grader

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def main():
    output = BASE / 'examples'
    output.mkdir(exist_ok=True)
    sequences = []
    for block in (BASE / 'inputs/tiny.fa').read_text().split('>')[1:]:
        name, *lines = block.splitlines()
        sequence = ''.join(lines)
        sequences.append({'name': name, 'sequence': sequence, 'length': len(sequence)})
    sequences.append({'name': 'no_match', 'sequence': 'A'*160, 'length': 160})
    models = [{'name': 'tRNA5', 'consensus_length': 72}, {'name': 'tRNA5-hand', 'consensus_length': 74}]
    summaries = []
    for table in sorted((BASE / 'native').glob('*/hits.tbl')):
        name = table.parent.name
        receipt = json.loads((table.parent/'receipt.json').read_text())
        command = receipt['command']
        fmt = int(command[command.index('--fmt')+1])
        program = Path(command[0]).name
        operation = {'program': program, 'native_version': '1.1.5',
                     'settings': {'recorded_native_option_argv': command[1:-2]}}
        sheet = inputs.populate_infernal_search_sheet([
            {'artifact_id': name, 'format': 'infernal_tblout', 'table_format': fmt,
             'complete': receipt['returncode'] == 0, 'content': table.read_text()}],
            operation=operation, sequence_metadata=sequences, model_metadata=models)
        scores = grader.calculate_infernal_search_scores(sheet)
        included = grader.calculate_infernal_search_scores(sheet, parameters={'hit_scope': 'included'})
        for suffix, data in [('sheet', sheet), ('scores.reported', scores), ('scores.included', included)]:
            (output/f'{name}.{suffix}.json').write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
        saved = json.loads((output/f'{name}.sheet.json').read_text())
        for artifact in saved['artifacts']:
            artifact['content'] = 'original native text disabled for saved-sheet recalculation'
            artifact['rows'] = []
        def forbidden(*args, **kwargs):
            raise AssertionError('parser, acquisition, subprocess or file I/O during recalculation')
        with patch.object(inputs, 'populate_infernal_search_sheet', forbidden), \
             patch.object(inputs, '_read_artifact', forbidden), \
             patch.object(socket, 'socket', forbidden), \
             patch.object(subprocess, 'Popen', forbidden), \
             patch.object(subprocess, 'run', forbidden), \
             patch.object(Path, 'read_text', forbidden), \
             patch('builtins.open', forbidden):
            assert grader.calculate_infernal_search_scores(saved) == scores
            assert grader.calculate_infernal_search_scores(saved, parameters={'hit_scope': 'included'}) == included
        summaries.append({'name': name, 'program': program, 'table_format': fmt,
            'sheet_status': sheet['status'], 'scores_status': scores['status'],
            'reported_hit_count': len(sheet['hits']), 'included_hit_count': sum(h['inclusion']=='!' for h in sheet['hits']),
            'first_hit_components': scores['hits'][0]['components'] if scores['hits'] else None,
            'aggregates': [{k: g[k] for k in ('sequence_names', 'strand', 'hit_count', 'union_numerator', 'union_denominator', 'union_span_fraction')}
                           for g in scores['sequence_strand_aggregates']],
            'saved_sheet_recalculation_with_disabled_external_paths': 'passed'})
    tree = ast.parse((ROOT/'gene_annotation_episode/infernal_search_grader.py').read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    assert set(imports) <= {'__future__', 'collections', 'copy', 'json', 'math'}
    result = {'generated_utc': datetime.now(timezone.utc).isoformat(),
              'calculator_imports': imports,
              'calculator_model_or_acquisition_imports': [], 'examples': summaries}
    (BASE/'EXAMPLE_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    for name in ('infernal_search_inputs.py','infernal_search_grader.py'):
        p = ROOT/'gene_annotation_episode'/name
        print(name, hashlib.sha256(p.read_bytes()).hexdigest())
    print('Saved-sheet recalculation passed:', len(summaries), 'native cases, two parameters each.')


if __name__ == '__main__':
    main()
