"""Install the exact reviewed S/G handoffs; retain original staging files."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAGING = HERE / 'staging'
PINS = {
    'gene_annotation_episode/bvbrc_phylogeny_common_inputs.py': 'c014f4b510a4f349d55ec3d5255d266417e058a8ab5f8d9cf26fa1b133d32f9d',
    'gene_annotation_episode/bvbrc_phylogeny_common_contracts.py': 'd081167ec5571a728b6ec8a827033c1fd24c58e9d8bd458b9bb28963ee121a04',
    'gene_annotation_episode/bvbrc_phylogeny_common_grader.py': 'ce4095410739cf2e8b1fdc2b97903717be44f6b00c93b4fe7e21abd342a5fb05',
    'gene_annotation_episode/bvbrc_gene_tree_inputs.py': 'f99179802bf2be328e8867f5f1808f139678038883de03269fafe7c792f0cf11',
    'gene_annotation_episode/bvbrc_gene_tree_grader.py': 'f3f382822d3f589295bdde68bb3d2a2e9d07efa59a4468bf82850fdac17d7ac9',
    'tests/test_bvbrc_phylogeny_common.py': '5354fa8af512b7afb71defc9db966b1ebc25f9e69c420e52ee780259320dacce',
    'tests/test_bvbrc_gene_tree_provider.py': '19283e6ed39d5e7a7ca322a9406972093ce2eb8394959bc1e4604c1559d8c7b9',
}
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
GOAL_SHA = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
assert hashlib.sha256(GOAL.read_bytes()).hexdigest() == GOAL_SHA
prepared = []
for name, pin in PINS.items():
    source, target = STAGING / name, ROOT / name
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == pin, name
    assert not target.exists(), name
    adaptations = []
    if name == 'tests/test_bvbrc_gene_tree_provider.py':
        old = b'BOUNDARIES = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"'
        new = b'BOUNDARIES = STAGING / "verification" / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"'
        assert data.count(old) == 1
        data = data.replace(old, new)
        adaptations.append('Native fixture path only: production repository root/verification.')
    if name == 'tests/test_bvbrc_phylogeny_common.py':
        old = b"ROOT = Path('/home/chia/repos/gene_annotation_episode')"
        new = b'ROOT = Path(__file__).resolve().parents[1]'
        assert data.count(old) == 1
        data = data.replace(old, new)
        adaptations.append('Fixture root only: derive actual production repository root.')
    prepared.append((source, target, data, pin, adaptations))
receipt = HERE / 'PRODUCTION_PROVIDER_INSTALLATION_001.json'
assert not receipt.exists()
rows = []
for source, target, data, pin, adaptations in prepared:
    with target.open('xb') as stream:
        stream.write(data)
    rows.append({'source': str(source), 'source_sha256': pin, 'target': str(target),
                 'target_sha256': hashlib.sha256(data).hexdigest(), 'test_adaptations': adaptations})
with receipt.open('x') as stream:
    json.dump({'scope': 'Shared and GeneTree pure providers; no registry, custody or episode integration claim',
               'goal_sha256': GOAL_SHA, 'files': rows}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'installed': len(rows), 'receipt': str(receipt)}))
