"""Recheck the seven effective saved examples after the partial-row correction."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('examples001', HERE / 'write_calculator_examples_001.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
manifest = json.loads((HERE / 'EXAMPLES_001/manifest.json').read_text())
cases = []
for item in manifest['cases']:
    folder = HERE / ('EXAMPLES_002' if item['case'] == 'twelve_groups' else 'EXAMPLES_001')
    prefix = item['case']
    example = json.loads((folder / (prefix + '-inputs.json')).read_text())
    expected = json.loads((folder / (prefix + '-answer.json')).read_text())
    before = json.dumps(example, sort_keys=True)
    with patch('builtins.open', old.forbidden), patch.object(Path, 'open', old.forbidden), \
            patch.object(Path, 'read_bytes', old.forbidden), patch.object(Path, 'read_text', old.forbidden), \
            patch.object(socket, 'socket', old.forbidden), patch.object(subprocess, 'Popen', old.forbidden), \
            patch('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', old.forbidden):
        assert old.calculate(example) == expected
        assert json.dumps(example, sort_keys=True) == before
    cases.append({'case': prefix, 'effective_inputs': str((folder / (prefix + '-inputs.json')).relative_to(old.ROOT)),
                  'exact_saved_answer_equal': True, 'inputs_unchanged': True})
receipt = {'scope': 'Final pure functions on saved examples; no parser, service or native program',
    'cases': cases, 'all_passed': True,
    'source_files': [old.bound(old.ROOT / 'gene_annotation_episode' / (name + '.py'))[1]
        for name in ('bvbrc_alignment_values', 'bvbrc_metacats_calculators', 'bvbrc_metacats_calculation_contracts')]}
old.save(HERE / 'SAVED_REPLAY_FINAL_003.json', receipt)
print(json.dumps({'replayed': len(cases), 'exact_equal': True, 'all_acquisition_disabled': True}))
