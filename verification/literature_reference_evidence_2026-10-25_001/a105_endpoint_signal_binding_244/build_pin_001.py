"""Immutable joined test input: baseline231 plus only owned approved overlays."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
BASE=OWN.parent/'a105_reported_curve_binding_231'
PIN=OWN/'pin_001'
assert not PIN.exists()
baseline=json.loads((BASE/'PIN_004.json').read_text())
owned=['literature_figure_storage','literature_episodes','communication','literature_numerical_contracts',
    'literature_numerical_return_presentation','literature_experimental_prompt','literature_reference_parent_prompt',
    'literature_endpoint_signal_storage','literature_endpoint_signal_render']
overlay={f'gene_annotation_episode/{name}.py' for name in owned}
overlay.update(f'gene_annotation_episode/literature_endpoint_signal_{name}.py' for name in ('inputs','calculations','prompt'))
overlay.update(['tests/test_literature_endpoint_signal_binding_244.py','tests/test_literature_endpoint_signal_components_241.py'])
extras=set()
pure=OWN.parent/'a105_endpoint_signal_components_241'
for row in json.loads((pure/'implementation_005/MANIFEST_003.json').read_text())['files']:
    if row['path'].startswith('research/') or row['path'].endswith('.json') and row['path'].startswith('verification/'):
        extras.add(row['path'])
extras.update(str((OWN/name).relative_to(ROOT)) for name in
    ('EXACT_SCHEMAS_002.json','PAIRED_SELECTED_INPUT_002.json','PAIRED_SELECTED_OUTPUT_002.json'))
hashes={}
for relative in set(baseline['hashes'])|overlay|extras:
    assert Path(relative).name!='GOAL.md'
    source=ROOT/relative if relative in overlay|extras else BASE/'pin_004'/relative
    raw=source.read_bytes()
    if relative not in overlay|extras:
        assert hashlib.sha256(raw).hexdigest()==baseline['hashes'][relative],relative
    target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    hashes[relative]=hashlib.sha256(raw).hexdigest()
result={'version':'endpoint_signal_joined_pin_v1','base_pin':str(BASE/'PIN_004.json'),
    'production_owned':sorted(overlay-{x for x in overlay if x.startswith('tests/')}),
    'test_overlays':sorted(x for x in overlay if x.startswith('tests/')),'additional_data':sorted(extras),
    'hashes':dict(sorted(hashes.items())),'status':'immutable_inputs_not_test_result',
    'private_provider_payloads_inspected':False,'goal_authority_copied_or_changed':False}
(OWN/'PIN_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'files':len(hashes),'pin':str(PIN)}))
