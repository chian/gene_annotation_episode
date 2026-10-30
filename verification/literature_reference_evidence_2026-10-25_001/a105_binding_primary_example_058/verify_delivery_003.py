"""Verify sealed delivery without any reader, calculator, provider or Episode."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = {
    'literature_binding_interaction_inputs.py': 'd17ad5095cb08c2da8c51210544c2fd22871e8fddbaade689ee7809e82a95f92',
    'literature_binding_visual_inputs.py': '8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718',
    'literature_binding_interaction_calculations.py': 'ac7ea12c105e16df5085942090ec8e3f96c618b4f5866283325c46c92804b432',
    'literature_binding_interaction_storage.py': '0dd5b0bbee30809560a1b39715c05c493c38d94581bbd255ebcbcdee2f6b749e',
    'literature_binding_interaction_validation.py': 'f8bae57a55bc7417acd83788a9082b8f0b7c9298f84cb7c0a9482f2f59673ebc',
    'literature_binding_interaction_render.py': '8f721dc277d444ce051117f94c03e6e7f016f40c6f3318db49348ccf5f316b3c',
    'literature_episodes.py': 'e38bd88b71abea93e71a119098b9e0b0c6106c52dca1762ec1871121fd52236a',
    'episode_services.py': '5a40cfd781b089b03122c47629d85960e3bcd0d6dd5b5bcd9e95aaaefbb4754f',
    'literature_experimental_prompt.py': '77f177c6339b8872a910d6fbfcd38fc13b296fb33f7efbede44cfb8da49f6b3a',
}

def load(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest = load(HERE / 'MANIFEST_003.json')
    for name, row in manifest['files'].items():
        path = HERE / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    current = {str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file()}
    assert current-set(manifest['excluded']) == set(manifest['files'])
    proposal = load(HERE / 'MANIFEST_001.json')
    for name, row in proposal['files'].items():
        path = HERE / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    for name, row in load(HERE / 'SOURCE_IDENTITIES_001.json').items():
        original = HERE.parent / 'a105_binding_case_042' / name
        assert sha(original) == row['sha256']
        assert sha(HERE / 'pin_003/inputs' / name) == row['sha256']
    for name, expected in FROZEN.items():
        assert sha(HERE / 'pin_003/gene_annotation_episode' / name) == expected, name
        assert sha(HERE.parents[2] / 'gene_annotation_episode' / name) == expected, name
    saved = load(HERE / 'run_003/SAVED_EXTRACTION_AND_CALCULATION.json')
    identities = {value for item in saved for value in item['calculation']['physical_fit_ids'].values()}
    assert len(identities) == 6
    assert load(HERE / 'AUDIT_003.json')['passed']
    assert load(HERE / 'provider_permission_run_004/RECEIPT.json')['passed']
    assert load(HERE / 'EXIT_RUN_002.json')['exit_code'] != 0
    assert load(HERE / 'EXIT_RUN_003.json')['exit_code'] == 0
    receipt = {'passed': True, 'files_verified': len(manifest['files']),
        'manifest_sha256': sha(HERE / 'MANIFEST_003.json'), 'original_proposal_unchanged': True,
        'original_primary_packet_unchanged': True, 'accepted_native_hashes_exact': len(FROZEN),
        'six_physical_fits_across_eight_role_slots': True, 'failed002_preserved_fresh003_passed': True,
        'selected_provider_formatting_distinguished_from_original_C4_derived_permission': True,
        'actual_configured_model_science_claimed': False}
    with (HERE / 'FINAL_VERIFY_003.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
