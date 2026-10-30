"""Recalculate a disk-saved real native sheet with parser/acquisition disabled."""
from pathlib import Path
from unittest.mock import patch
import builtins
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import urllib.request

from gene_annotation_episode import cmalign_inputs
from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores

HERE = Path(__file__).resolve().parent

def main():
    source = HERE/'examples/mapali/sheet.json'
    raw = source.read_bytes()
    sheet = json.loads(raw)
    original = json.dumps(sheet, sort_keys=True, allow_nan=False)
    expected = json.loads((HERE/'examples/mapali/scores.json').read_bytes())
    calls = set()
    def forbidden(*args, **kwargs):
        raise AssertionError('parsing/acquisition/execution disabled during recalculation')
    def profile(frame, event, arg):
        if event == 'call':
            calls.add(frame.f_code.co_filename)
    with patch.object(cmalign_inputs,'populate_cmalign_sheet',forbidden), \
         patch.object(cmalign_inputs,'parse_cmalign_stockholm',forbidden), \
         patch.object(cmalign_inputs,'parse_cmalign_sfile',forbidden), \
         patch.object(cmalign_inputs,'parse_cmalign_insert_file',forbidden), \
         patch.object(cmalign_inputs,'iter_hmmalign_stockholm_records',forbidden), \
         patch.object(cmalign_inputs,'posterior_bin_bounds',forbidden), \
         patch.object(builtins,'open',forbidden), patch.object(io,'open',forbidden), \
         patch.object(socket,'socket',forbidden), patch.object(urllib.request,'urlopen',forbidden), \
         patch.object(subprocess,'Popen',forbidden), patch.object(os,'system',forbidden):
        sys.setprofile(profile)
        try:
            all_scores = calculate_cmalign_scores(sheet)
            new_scores = calculate_cmalign_scores(sheet, parameters={'population':'newly_aligned'})
            inherited_scores = calculate_cmalign_scores(sheet, parameters={'population':'inherited'})
        finally:
            sys.setprofile(None)
    assert all_scores == expected
    assert original == json.dumps(sheet, sort_keys=True, allow_nan=False)
    assert source.read_bytes() == raw
    assert all_scores['sequences'] == new_scores['sequences'] == inherited_scores['sequences']
    proof = {'source':str(source), 'source_sha256_before':hashlib.sha256(raw).hexdigest(),
        'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),
        'saved_all_population_scores_equal':True, 'original_sheet_unchanged':True,
        'blocked_operations':['all cmalign native parsers','Stockholm grammar reader','PP text parser',
            'builtins.open','io.open','socket.socket','urllib.request.urlopen','subprocess.Popen','os.system'],
        'all_sequence_components_retained':len(new_scores['sequences']),
        'selected_counts':{'all':all_scores['summary']['selected_sequence_count'],
            'newly_aligned':new_scores['summary']['selected_sequence_count'],
            'inherited':inherited_scores['summary']['selected_sequence_count']},
        'executed_python_source_files':sorted(calls),
        'model_service_calls':'none: calculator calls only numerical validation, ratios and standard-library copying/JSON validation'}
    (HERE/'SAVED_RECALCULATION_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))

if __name__ == '__main__':
    main()
