"""Create immutable selected integration input, preserving original baselines."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_reported_curve_precision_verification_233'
PIN=OWN/'pin_004'
assert not PIN.exists()
manifest=json.loads((BASE/'PIN_001.json').read_text())['hashes']
overlays=[f'gene_annotation_episode/{n}.py' for n in ('literature_rate_observation_storage','literature_rate_observation_prompt',
 'literature_episodes','communication','literature_numerical_contracts','literature_numerical_return_presentation',
 'literature_experimental_prompt','literature_reference_parent_prompt')]
extras=['tests/test_literature_reported_curve_binding_231.py',
 'research/experimental_scoring_review_2026-10-23/a105_raw_rate_primary_case_164/originals/S1Data.xlsx',
 'research/experimental_scoring_review_2026-10-23/a105_raw_rate_primary_case_164/originals/S1Table.xlsx',
 'research/experimental_scoring_review_2026-10-23/a105_raw_rate_primary_case_164/originals/article.html',
 'verification/literature_reference_evidence_2026-10-25_001/primary_yeag/PMC4664914_original.xml',
 'verification/literature_reference_evidence_2026-10-25_001/primary_yeag/srep17524-f3.jpg',
 *[str((OWN/n).relative_to(ROOT)) for n in ('EXACT_SCHEMA_PROPOSAL_002.json','OLD_V1_BASELINE_001.json')]]
hashes={}
for relative in manifest:
 assert Path(relative).name!='GOAL.md'
 source=(ROOT if relative in overlays else BASE/'pin_001')/relative
 raw=source.read_bytes()
 if relative not in overlays:assert hashlib.sha256(raw).hexdigest()==manifest[relative],relative
 target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 hashes[relative]=hashlib.sha256(raw).hexdigest()
for relative in extras:
 assert relative not in hashes,relative
 raw=(ROOT/relative).read_bytes();target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 hashes[relative]=hashlib.sha256(raw).hexdigest()
old=json.loads((OWN/'OLD_V1_BASELINE_001.json').read_text())
external={str(Path(old['proof_directory'])/'state'/p):h for p,h in old['state_files'].items()}
external.update({str(Path(old['proof_directory'])/p):h for p,h in old['proof_records_sha256'].items()})
for p,h in external.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
result={'version':'reported_curve_binding_pin_v1','base_pin':str(BASE/'PIN_001.json'),'base_count':len(manifest),
 'production_overlays':overlays,'additional_inputs':extras,'hashes':hashes,'external_original_state_dependencies':external,
 'code_claim':'Selected reported-curve integration only; controlled fixtures, no actual model execution; A105 and full goal incomplete.'}
(OWN/'PIN_004.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'pin_files':len(hashes),'overlays':len(overlays),'external_original_state_files':len(external)}))
