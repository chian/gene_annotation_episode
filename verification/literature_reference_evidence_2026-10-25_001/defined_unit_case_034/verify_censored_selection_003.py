"""Additive mechanical correction; preserve all previous case034 files unchanged.

Uses already reviewed assignments and exact run024 source bytes. No new source
interpretation, model, workflow, database mutation or production correction.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
PIN = BASE / 'literature_model_run_030/pin_001'
INPUT = BASE / 'literature_model_run_024/pin_001/inputs'
sys.path.insert(0, str(PIN))
from gene_annotation_episode.literature_rate_native_inputs import read_rate_source_inputs, validate_native_selection
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_experimental_contracts import validate_rate_extraction

sha = lambda data: hashlib.sha256(data).hexdigest()

def write_new(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    # Include the permanent old manifest and every existing file, not only its
    # listed entries. All old files must remain byte-identical after this run.
    before = {str(path.relative_to(OUT)): sha(path.read_bytes())
              for path in OUT.rglob('*') if path.is_file()}
    manifest_hash = sha((PIN / 'SOURCE_MANIFEST.json').read_bytes())
    assert manifest_hash == '2616012239523f24d41ce1c9d04d08ab7bd6c75ee7f1e10943172e39b090c2df'
    metadata = json.loads((INPUT / 'SOURCE_INPUT_METADATA.json').read_bytes())
    original = (INPUT / 'PRIMARY_PMC_001.html').read_bytes()
    text = (INPUT / 'PRIMARY_ARTICLE_TEXT_001.txt').read_bytes()
    assert sha(original) == metadata['sources'][0]['original']['sha256']
    assert sha(text) == metadata['sources'][0]['text']['sha256']
    old = json.loads((OUT / 'CENSORED_SELECTION_002.json').read_bytes())
    new = deepcopy(old)
    label = old['arms']['test']['label']
    assert label['quote'] == 'Fd + Hyd − crotonyl-CoA'
    # The reviewed label already binds the physical row. Select the actual
    # adjacent source text and exclude only '<' from the numerical token;
    # the unchanged reader independently observes and preserves that qualifier.
    row_text = label['quote'] + '\n<0.01'
    start = label['start']
    end = start + len(row_text.encode('utf-8'))
    assert text[start:end] == row_text.encode('utf-8')
    witness = {**label, 'start': start, 'end': end, 'quote': row_text}
    token_start = row_text.index('<') + 1
    new['arms']['test']['rate']['number'] = {
        'witness': witness, 'number_start': token_start, 'number_end': len(row_text)}
    restored = deepcopy(new)
    restored['arms']['test']['rate']['number'] = old['arms']['test']['rate']['number']
    assert restored == old  # Only the stale numeric selector is corrected.
    write_new('CENSORED_SELECTION_003.json', new)
    # Re-read the saved selection itself; do not verify a different in-memory
    # object later mutated after publication.
    retained = json.loads((OUT / 'CENSORED_SELECTION_003.json').read_bytes())
    assert retained == new

    accesses = []
    def read_source(reference, representation):
        assert reference == retained['source_ref']
        content = {'original': original, 'text': text}[representation]
        accesses.append({'source_ref': reference, 'representation': representation,
                         'artifact_ref': 'artifact_' + sha(content)})
        return {'artifact_ref': 'artifact_' + sha(content), 'content': content}

    extraction = read_rate_source_inputs(retained, read_source=read_source)
    assert validate_rate_extraction(extraction) == extraction
    validate_native_selection(retained, extraction)
    rows = {row['arm']: row for row in extraction['rows']}
    model = extraction['native_context']['model']
    sheet = populate_rate_contrast(extraction, reference_arm='reference', test_arm='test',
        reference_condition=rows['reference']['condition'],
        test_condition=rows['test']['condition'], dependence=model['dependence']['value'],
        observation_model=model['observation_model']['value'])
    test = sheet['cells']['test_rate']
    assert rows['test']['source']['number']['raw_number'] == '0.01'
    assert rows['test']['status'] == 'censored' and rows['test']['bound'] == 'lt'
    assert test['value'] is None and test['threshold'] == .01 and test['bound'] == 'lt'
    assert test['unavailable_reason'] == 'censored_measurement'
    assert sheet['cells']['reference_rate']['value'] == 7
    for name in ('rate_difference', 'retained_fraction', 'fractional_decrease'):
        assert sheet['cells'][name]['value'] is None
        assert sheet['cells'][name]['unavailable_reason'] == 'censored_measurement'
    write_new('CENSORED_VERIFICATION_003.json', {'selection_filename': 'CENSORED_SELECTION_003.json',
        'selection_sha256': sha((OUT / 'CENSORED_SELECTION_003.json').read_bytes()),
        'extraction': extraction, 'sheet': sheet})
    imported = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if path and name.startswith('gene_annotation_episode'):
            path = Path(path).resolve()
            assert path.is_relative_to(PIN)
            imported.append({'module': name, 'path': str(path), 'sha256': sha(path.read_bytes())})
    for name, digest in before.items():
        assert sha((OUT / name).read_bytes()) == digest, name
    correction = (
        '# Additive correction 003: retained censored selector\n\n'
        'The parent identified a preservation defect: verify_original_source.py saved '
        'CENSORED_SELECTION_002.json before replacing the test rate-number selector. '
        'That file retains the corrected crotonyl-CoA-omission label and intended change '
        'but still selects the Hyd 0.1 operand. It does not reproduce the reported '
        'censored result. The historical script, selector, reports and manifests remain unchanged.\n\n'
        'CENSORED_SELECTION_003.json changes only arms.test.rate.number, binding the '
        'already reviewed omission row and its actual <0.01 source text. The new '
        'mechanical verification reloads that saved file before invoking unchanged '
        'pin030. It reproduces test_rate value=null, threshold=0.01, bound=lt and '
        'unavailable_reason=censored_measurement; rate_difference, retained_fraction '
        'and fractional_decrease remain unavailable. The source reference rate is7. '
        'No new scientific interpretation, model, workflow, observation, production '
        'edit, live-state mutation or historical rewrite occurred.\n\n'
        'CENSORED_VERIFICATION_003.json contains the exact saved selection hash, '
        'extraction and calculated sheet. CENSORED_HASH_RECEIPT_003.json records '
        'original source/pin/import hashes and verifies every pre-existing case034 '
        'file is byte-identical. The old FILE_MANIFEST.json is preserved, not refreshed.\n')
    with (OUT / 'ADDITIVE_CORRECTION_003.md').open('x') as stream:
        stream.write(correction)
    added = ['CENSORED_SELECTION_003.json', 'CENSORED_VERIFICATION_003.json',
             'ADDITIVE_CORRECTION_003.md', 'verify_censored_selection_003.py']
    write_new('CENSORED_HASH_RECEIPT_003.json', {
        'status': 'passed', 'utc': datetime.now(timezone.utc).isoformat(),
        'selection_reloaded_from_disk_before_verification': True,
        'only_corrected_path': 'arms.test.rate.number',
        'old_selector_does_not_reproduce_censor_result': True,
        'pin_manifest_sha256': manifest_hash,
        'source_original_sha256': sha(original), 'source_text_sha256': sha(text),
        'source_accesses': accesses, 'imports': imported,
        'preserved_preexisting_file_hashes': before,
        'all_preexisting_files_unchanged': True,
        'new_files': [{'path': name, 'sha256': sha((OUT / name).read_bytes()),
                       'size': (OUT / name).stat().st_size} for name in added]})
    for name, digest in before.items():
        assert sha((OUT / name).read_bytes()) == digest, name
    print(json.dumps({'status': 'passed', 'selection_reloaded': True,
        'test_rate': {'value': test['value'], 'threshold': test['threshold'], 'bound': test['bound']},
        'point_contrast': sheet['cells']['rate_difference']['value'],
        'preexisting_files_preserved': len(before), 'imported_pin_files': len(imported)}))

if __name__ == '__main__':
    main()
