"""Reconstruct authored001-003 revisions and retain actual current004 source bytes.

Earlier pytest logs already exist. Inverse edits are recorded here explicitly;
these are reconstructed code receipts, not claims of contemporaneous snapshots.
"""
from pathlib import Path
import hashlib,json
P=Path(__file__).parent;R=P.parents[1]
paths=['gene_annotation_episode/literature_measurement_comparison_inputs.py','gene_annotation_episode/literature_measurement_comparison_calculations.py','gene_annotation_episode/literature_measurement_comparison_prompt.py','tests/test_literature_measurement_comparison_components_258.py']
versions={4:{p:(R/p).read_text() for p in paths}}
v3=versions[3]=dict(versions[4]);ip=paths[0];cp=paths[1];tp=paths[3]
v3[ip]=v3[ip].replace("    value['reasons']=_merge(value['reasons'])\n",'').replace("    effective = unit if unc['unit_relationship']['value']=='same_as_estimate' else None\n","    effective = unit\n").replace("        if unc['unit_relationship']['value'] in ('same_as_estimate','explicit_unit'): effective = explicit\n","        effective = explicit\n").replace("    if args['optical'] is not None and not args['optical']['sign_support']:_fail('interpretation_witness_required','optical.sign_support')\n",'')
line="    result.update({k:deepcopy(data[k]) for k in ('roles','owner_keys','units','dependency_keys','variance_status','origin','systematic_coverage','derivation')})\n"
v3[ip]=v3[ip].replace(line,'').replace("    if any(quantities[r] is None or quantities[r]['canonical_exact'] is None for r in roles):",line+"    if any(quantities[r] is None or quantities[r]['canonical_exact'] is None for r in roles):")
v3[tp]=v3[tp].replace("        if val.startswith(('< ','> ')): a+=2;val=val[2:]\n",'')
v2=versions[2]=dict(v3);v2[cp]=v2[cp].replace("reasons=_reasons() if reasons is None else _merge(reasons)","reasons=_reasons() if reasons is None else deepcopy(reasons)").replace("'model_keys':list(dict.fromkeys(models))","'model_keys':list(models)")
v1=versions[1]=dict(v2);v1[ip]=v1[ip].replace(', _interpret as _native_interpret','').replace('return _native_interpret(value, sources, field)',"return _interpretation(value, (value['value'],), sources, field)")
manifest=[]
for n,files in versions.items():
 out=P/f'pytest_attempt_{n:03d}_code'
 rows=[]
 for name,text in files.items():
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
  rows.append({'path':name,'sha256':hashlib.sha256(text.encode()).hexdigest()})
 manifest.append({'attempt':n,'code_snapshot':'actual_current_tested_bytes' if n==4 else 'reconstructed_by_recorded_inverse_authored_edits','files':rows})
(P/'INITIAL_ATTEMPT_CODE_RECEIPTS_004.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Initial four attempt source receipts retained; reconstructed001-003 are labelled explicitly.')
