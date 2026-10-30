"""Independent bounded metadata review; no scientific/runtime acquisition."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
OWNED = HERE.parent / 'a105_partner_operand_information_072'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
seal = json.loads((OWNED / 'SEAL_005.json').read_bytes())
for name, expected in seal['artifact_files'].items():
    assert sha(OWNED / name) == expected, name
actual = {str(p.relative_to(OWNED)) for p in OWNED.rglob('*')
          if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
assert actual == set(seal['artifact_files']) | {'SEAL_005.json'}
for section in ('changed_files', 'read_only_files_unchanged'):
    for name, expected in seal[section].items():
        assert sha(ROOT / name) == expected, name

from gene_annotation_episode.literature_partner_native_inputs import partner_source_population_schema
from gene_annotation_episode.literature_partner_operand_information import partner_source_population_schema_with_information
from gene_annotation_episode.literature_episodes import _population_catalog, LiteratureEpisodes

def additive(before, after):
    if isinstance(before, dict):
        assert isinstance(after, dict) and set(before) <= set(after)
        assert set(after) - set(before) <= {'description'}
        for k, v in before.items():
            additive(v, after[k])
    elif isinstance(before, list):
        assert isinstance(after, list) and len(before) == len(after)
        for a, b in zip(before, after):
            additive(a, b)
    else:
        assert type(before) is type(after) and before == after

bare = partner_source_population_schema()
informed = partner_source_population_schema_with_information()
additive(bare, informed)
catalog = _population_catalog()
baseline = json.loads((OWNED / 'baseline_catalog.json').read_bytes())
assert len(catalog) == len(baseline) == 19
assert [a['name'] for a, b in zip(catalog, baseline) if a != b] == ['literature.partner.source.populate']
for a, b in zip(catalog, baseline):
    if a['name'] == 'literature.partner.source.populate':
        assert a['input_schema'] == informed
        assert {k: v for k, v in a.items() if k != 'input_schema'} == {k: v for k, v in b.items() if k != 'input_schema'}
returns = LiteratureEpisodes(None, rate_population=True).fact_sources('literature')
assert len(returns) == 18 and returns == json.loads((OWNED / 'baseline_returns.json').read_bytes())

patch = ''
for name in ('gene_annotation_episode/literature_partner_operand_information.py',
             'tests/test_literature_partner_operand_information.py',
             'gene_annotation_episode/literature_episodes.py'):
    before = ((OWNED / 'baseline_literature_episodes.py').read_text()
              if name.endswith('/literature_episodes.py') else '')
    patch += ''.join(difflib.unified_diff(before.splitlines(True), (ROOT / name).read_text().splitlines(True),
                    fromfile='a/' + name if before else '/dev/null', tofile='b/' + name))
assert patch == (OWNED / 'exact_additive_patch_004.diff').read_text()
execution = json.loads((OWNED / 'frozen_execution_004.json').read_bytes())
imports = json.loads((OWNED / 'frozen_import_proof_004.json').read_bytes())
assert execution['returncode'] == 0
pin = (OWNED / 'generation_004').resolve()
for name, row in imports['imports'].items():
    p = Path(row['path']).resolve()
    assert p.is_relative_to(pin) and sha(p) == row['sha256'], name
assert '397 passed' in (OWNED / 'frozen_execution_004.txt').read_text()
out = {'scope': 'Description-only metadata acceptance; no model, paper, Store or workflow execution',
       'seal_sha256': sha(OWNED / 'SEAL_005.json'), 'sealed_payloads_checked': len(seal['artifact_files']),
       'exact_patch_rebuilt': True, 'original_values_and_inherited_descriptions_exact': True,
       'operations': len(catalog), 'return_contracts': len(returns),
       'recorded_frozen_tests': 397, 'frozen_import_files_reverified': len(imports['imports']),
       'baseline_limit': 'Task-local baseline reconstructed by reversing assigned changes; no pre-edit capture claimed',
       'accepted': 'Operand information only; scientific model/runtime delivery remains separate'}
with (HERE / 'METADATA_ROOT_RECEIPT_001.json').open('x') as f:
    json.dump(out, f, indent=2); f.write('\n')
print(json.dumps(out))
