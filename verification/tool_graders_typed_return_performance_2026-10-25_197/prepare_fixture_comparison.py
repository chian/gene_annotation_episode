"""Copy exact frozen candidate and only the five tests' retained input closure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
SOURCE = OWN / 'candidate'
DESTINATION = OWN / 'fixture_comparison_candidate'
assert not DESTINATION.exists()
expected = json.loads((OWN / 'source_after.json').read_text())
assert len(expected) == 1053

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert {name: digest(SOURCE / name) for name in expected} == expected
DESTINATION.mkdir()
for name in expected:
    destination = DESTINATION / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / name, destination)
assert {name: digest(DESTINATION / name) for name in expected} == expected

msa = 'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples/dna/'
meta = 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases/aa_two_groups/'
fixtures = {msa + name: 'msa_native_fixture(dna)' for name in ('output.afa', 'foma.table', 'cons.fasta')}
fixtures.update({meta + name: 'meta_native_fixture(aa_two_groups)' for name in (
    'RECEIPT.json', 'original.fasta', 'metadata.tsv', 'output/comparison.txt',
    'output/comparison-chisqTable.tsv', 'output/comparison-mcTable.tsv',
    'output/retained_raw/comparison-chisqTable.txt', 'output/retained_raw/comparison-mcTable.txt')})
fixtures.update({
    'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/EXAMPLES_001/aa_two_groups-inputs.json': 'meta_native_fixture(aa_two_groups)',
    'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples/combined_native-inputs.json': 'xmfa_native_fixture(False)',
    'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples/combined.xmfa': 'xmfa_native_fixture(False)',
    'cases/gene_001/target.faa': 'MinhashRun.__init__ supplied sequence',
})
assert len(fixtures) == 15
provenance = []
receipt = json.loads((ROOT / meta / 'RECEIPT.json').read_text())
for name, route in fixtures.items():
    assert name not in expected
    original = ROOT / name
    raw = original.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    relative_meta = name.removeprefix(meta)
    if name.startswith(meta) and relative_meta in receipt['files']:
        assert receipt['files'][relative_meta] == {'sha256': sha, 'bytes': len(raw)}
    destination = DESTINATION / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    assert digest(original) == digest(destination) == sha
    expected[name] = sha
    provenance.append({'path': name, 'origin': str(original), 'sha256': sha,
        'bytes': len(raw), 'required_by': route, 'existing_retained_bytes': True})
assert {name: digest(SOURCE / name) for name in json.loads((OWN / 'source_after.json').read_text())} == json.loads((OWN / 'source_after.json').read_text())
assert {name: digest(DESTINATION / name) for name in expected} == expected
(OWN / 'fixture_comparison_manifest.json').write_text(json.dumps(expected, indent=2, sort_keys=True) + '\n')
(OWN / 'fixture_comparison_sources.json').write_text(json.dumps({
    'created_at': datetime.now(timezone.utc).isoformat(), 'source': str(SOURCE),
    'destination': str(DESTINATION), 'original_manifest': str(OWN / 'source_after.json'),
    'original_manifest_sha256': digest(OWN / 'source_after.json'),
    'unchanged_original_paths': 1053, 'supplemental_fixture_paths': provenance,
    'supplemental_bytes': sum(item['bytes'] for item in provenance),
    'running_candidate_unchanged': True}, indent=2) + '\n')
print(json.dumps({'copied_unchanged_paths': 1053, 'new_fixture_paths': len(fixtures),
    'new_fixture_bytes': sum(item['bytes'] for item in provenance), 'total_paths': len(expected)}))
