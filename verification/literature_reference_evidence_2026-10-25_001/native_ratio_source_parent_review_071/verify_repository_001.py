"""Root custody-package verification; opens no retained scientific database."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
sys.path.insert(0, str(ROOT))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = BASE / 'a105_visual_signal_repository_071'
new = BASE / 'a105_visual_signal_repository_repair_075'
owned = json.loads((new / 'OWNED_SOURCE_MANIFEST_003.json').read_bytes())
for name, row in owned.items():
    assert sha(ROOT / name) == row['after_sha256']
    assert sha(old / 'pin_006' / name) == row['before_sha256']
patch = ''.join(''.join(difflib.unified_diff((old / 'pin_006' / name).read_text().splitlines(True),
            (ROOT / name).read_text().splitlines(True), fromfile='a/' + name, tofile='b/' + name)) for name in owned)
assert patch == (new / 'OWNED_DELTA_FROM_071006_003.diff').read_text()
checks = {}
for directory, generation in [(old, '006'), (new, '003')]:
    manifest = json.loads((directory / ('ARTIFACT_MANIFEST_' + generation + '.json')).read_bytes())
    for name, row in manifest.items():
        path = ROOT / name
        # Old current-source rows are preserved by their original pin; they are
        # explicitly superseded, not asserted equal to repaired current code.
        if directory == old and name in owned:
            path = old / 'pin_006' / name
        assert sha(path) == row['sha256'], name
    pin_manifest = json.loads((directory / ('PIN_MANIFEST_' + generation + '.json')).read_bytes())
    assert pin_manifest['before'] == pin_manifest['after'] == pin_manifest['frozen']
    for name, expected in pin_manifest['frozen'].items():
        assert sha(directory / ('pin_' + generation) / name) == expected, name
    checks[directory.name] = {'artifact_entries_checked': len(manifest),
        'pin_files_checked': len(pin_manifest['frozen']),
        'artifact_manifest_sha256': sha(directory / ('ARTIFACT_MANIFEST_' + generation + '.json'))}

pure = BASE / 'a105_visual_signal_reader_repair_074'
manifest = json.loads((pure / 'PIN_INPUT_MANIFEST_005.json').read_bytes())
for row in manifest['files']:
    assert sha(pure / 'pin_005' / row['path']) == row['sha256'], row['path']
import_proof = pure / 'pin_005' / pure.relative_to(ROOT) / 'PIN_IMPORT_AND_EXECUTION_005.json'
imports = json.loads(import_proof.read_bytes())
for row in imports['local_imports']:
    p = Path(row['path']).resolve()
    assert p.is_relative_to(pure / 'pin_005') and sha(p) == row['sha256']
assert imports['pytest_exit'] == 0
assert '218 passed' in (pure / 'PIN_RUN_005.log').read_text()

from gene_annotation_episode.literature_ratio_source_storage import ratio_source_cells_schema
decl = BASE / 'visual_signal_parent_review_067/text_locator_declarations_008/RETURN_SCHEMA_008.json'
assert ratio_source_cells_schema() == json.loads(decl.read_bytes())
actual = json.loads((HERE / 'actual_replay_001/ACTUAL_JOINED_OUTPUT_003.json').read_bytes())
readonly = json.loads((HERE / 'actual_replay_001/READONLY_PROOF_003.json').read_bytes())
assert actual['saved_payload']['sheet']['cells']['reported_ratio']['value'] == .64
assert readonly['mode'] == 'ro' and readonly['query_only'] == 1 and readonly['total_changes'] == 0
assert not readonly['source_bytes_read'] and not readonly['decoder_or_population_called']
assert actual['runtime_observations'] == readonly['observation_rows'] == []
assert len(readonly['first_projection']) == 1
assert readonly['first_projection'][0]['component'] == 'reported_ratio'
receipt = {'scope': 'Native repository engineering acceptance; no actual selected episode/C1/C4/model/primary result',
    'packages': checks, 'exact_three_file_delta_reconstructed': True,
    'pure_repair_pin_inputs_checked': len(manifest['files']), 'pure_repair_imports_checked': len(imports['local_imports']),
    'complete_return_schema_matches008': True, 'root_reexecuted_pinned_joined_fixture': True,
    'ratio': .64, 'difference': -.36, 'first_fresh_readonly_total_changes': 0,
    'accepted': 'Native selected custody/storage/projection primitives, original071006 plus repair075',
    'remaining': 'Actual LiteratureEpisode registration, C1/C4 requested-subset delivery, parent use, model execution and wider scientific components'}
with (HERE / 'REPOSITORY_ROOT_RECEIPT_001.json').open('x') as f:
    json.dump(receipt, f, indent=2); f.write('\n')
print(json.dumps(receipt))
