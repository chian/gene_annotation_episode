"""Retain full reader examples; supplied bytes are acquired before pure checks."""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.bvbrc_metacats_input_formats import parse_metacats_input_fasta
from gene_annotation_episode.phylogeny_format_contracts import validate_alignment_document

OUT = Path(__file__).parent
NATIVE = ROOT / 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases'
CASES = ['official_na','aa_two_groups','aa_three_groups','metadata_only_first_group',
         'twelve_groups','native_pair_tail_underflow','all_missing']


def forbidden(*args, **kwargs):
    raise AssertionError('Pure parser/validator attempted acquisition or execution')


def main():
    examples = OUT / 'saved_examples'
    examples.mkdir(exist_ok=True)
    sources = [(name, (NATIVE/name/'original.fasta').read_bytes(),
                str((NATIVE/name/'original.fasta').relative_to(ROOT))) for name in CASES]
    sources.append(('original_hash_distinction',b'>a\n#-A-C-#\n>b\n--C#A--\n',None))
    results = []
    for name, data, path in sources:
        artifact = {'raw_artifact_ref':name, 'source_ref':'retained-input:'+name,
                    'sha256':hashlib.sha256(data).hexdigest()}
        original = deepcopy(artifact)
        with patch.object(builtins,'open',forbidden), patch.object(Path,'open',forbidden), \
             patch.object(Path,'read_bytes',forbidden), patch.object(socket,'socket',forbidden), \
             patch.object(subprocess,'Popen',forbidden):
            parsed = parse_metacats_input_fasta(data,artifact=artifact)
            replay = validate_alignment_document(json.loads(json.dumps(parsed['value'])))
        assert parsed['status']=='ok' and replay==parsed['value'] and artifact==original
        answer = {'input_path':path,'input_bytes_sha256':artifact['sha256'],
                  'input_byte_count':len(data),'parsed':parsed}
        if path is None:
            answer['synthetic_input_text'] = data.decode('ascii')
        destination = examples/(name+'.json')
        with destination.open('x') as f:
            json.dump(answer,f,indent=2,allow_nan=False);f.write('\n')
        rows = replay['rows']
        results.append({'case':name,'path':str(destination.relative_to(ROOT)),
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'rows':replay['observed_row_count'],'columns':replay['observed_column_count'],
            'original_hash_symbols':sum(r['sequence'].count('#') for r in rows),
            'dash_symbols':sum(r['sequence'].count('-') for r in rows),
            'bytes':len(data),'no_io_parse_and_roundtrip_passed':True})
    receipt = {'scope':'Seven retained native-component input FASTAs plus one explicitly synthetic hash/dash example; no new native tool/service execution.',
        'test_evidence':'INPUT_TEST_RESULT_002.json','tests_passed':127,'subtests_passed':9,
        'new_input_tests':25,'initial_test_assertion_failure_retained':'INITIAL_TEST_RESULT_001.json',
        'examples':results,'source_sha256':hashlib.sha256((ROOT/'gene_annotation_episode/bvbrc_metacats_input_formats.py').read_bytes()).hexdigest(),
        'test_sha256':hashlib.sha256((ROOT/'tests/test_bvbrc_metacats_input_formats.py').read_bytes()).hexdigest(),
        'integration_remaining':'Provider ReaderSpec dispatch, metadata association, library and complete child result path remain unfinished.'}
    with (OUT/'INPUT_READER_VERIFICATION_003.json').open('x') as f:
        json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'examples':[{k:r[k] for k in ('case','rows','columns','original_hash_symbols','dash_symbols')} for r in results],
                      'tests_passed':127,'subtests_passed':9},indent=2))


if __name__=='__main__':
    main()
