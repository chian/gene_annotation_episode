"""Install the reviewed Codon provider and its exact current verification cases."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGING = HERE / 'staging'
PINS = {
    'gene_annotation_episode/bvbrc_codon_tree_inputs.py': '00f915ded5a9d8c259d338c59c7829761a397a781e72b5be72de7f631cab6aa5',
    'gene_annotation_episode/bvbrc_codon_tree_grader.py': '5393d24a52e255fb1d1027082218dadc9165e1f4a0a7f279bc14cb2db82f83be',
}
test_name = 'tests/test_bvbrc_codon_tree_provider.py'
PINS[test_name] = hashlib.sha256((STAGING / test_name).read_bytes()).hexdigest()
goal = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
goal_sha = hashlib.sha256(goal.read_bytes()).hexdigest()
assert goal_sha == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
calc = ROOT / 'gene_annotation_episode/bvbrc_codon_tree_calculators.py'
calc_sha = hashlib.sha256(calc.read_bytes()).hexdigest()
assert calc_sha == 'e8eeab6a379af3cf80b0c92089df13a8c06630abf8baabe04593d94aaab87d54'
prepared = []
for name, pin in PINS.items():
    source, target = STAGING / name, ROOT / name
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == pin and not target.exists(), name
    adaptations = []
    if name == test_name:
        old = b'NATIVE = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24" / "official_example"'
        new = b'NATIVE = STAGING / "verification" / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24" / "official_example"'
        assert data.count(old) == 1
        data = data.replace(old, new)
        adaptations.append('Native fixture path only: actual repository root/verification.')
    prepared.append((source, target, data, pin, adaptations))
receipt = HERE / 'PRODUCTION_CODON_PROVIDER_INSTALLATION_001.json'
assert not receipt.exists()
rows = []
for source, target, data, pin, adaptations in prepared:
    with target.open('xb') as stream:
        stream.write(data)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == pin
    rows.append({'source': str(source), 'source_sha256': pin, 'target': str(target),
                 'target_sha256': hashlib.sha256(data).hexdigest(), 'test_adaptations': adaptations})
with receipt.open('x') as stream:
    json.dump({'scope': 'Installed pure Codon provider; no service/episode completion claim',
               'goal_sha256': goal_sha, 'calculator_sha256': calc_sha, 'files': rows}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'installed': len(rows), 'receipt': str(receipt)}))
