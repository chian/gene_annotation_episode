"""Save focused complete requested facts from final serialized provider examples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode import bvbrc_alignment_bundle_contracts as contracts
from gene_annotation_episode import bvbrc_alignment_bundle_projection as projection

OUT=Path(__file__).resolve().parent
BASE=OUT/'saved_examples_012'
records=[]
for name in ('msa_dna','msa_reference','msa_original_coverage','msa_composition','msa_trees',
             'metacats_aa_two_groups','metacats_aa_three_groups','metacats_native_pair_tail_underflow',
             'msa_xmfa','msa_xmfa_missing_sources','synthetic_cross_analysis'):
    path=BASE/(name+'.inputs.json')
    args=json.loads(path.read_text())
    fields={k:deepcopy(v['x-alignment-fact']) for k,v in args['requested_form']['properties'].items()}
    aid=args['parameters']['analyses'][0]['analysis']['analysis_id']
    if name=='msa_dna':
        fields={k:v for k,v in fields.items() if k in ('native_score','collection:msa_entropy')}
        fields['native_score']['row_index']=1
        fields['collection:msa_entropy']['columns_0based']=[1,2]
    elif name.startswith('metacats_'):
        fields={k:v for k,v in fields.items() if k.startswith('collection:') or '|cramers_v' in k or '|total_variation' in k or '|minimum_expected' in k or '|cells_below_5' in k or '|cell_denominator' in k}
        if name=='metacats_aa_two_groups':
            for v in fields.values():
                if v['kind']=='group_counts':
                    v['columns_0based']=[1];v['symbols']=['A','C']
                elif v['kind']=='measurement' and 'column_0based' in v['selector']:
                    v['selector']['column_0based']=1
        if name=='metacats_native_pair_tail_underflow':
            slot=next(s for s in args['parameters']['artifact_selection'] if s['reader']['reader']=='metacats_raw_r' and s['reader']['kind']=='pairwise')
            fields['observed_pair_p']={'kind':'native_measurement','analysis_id':aid,'table':{'analysis_id':aid,'slot_id':slot['slot_id']},'row_index':1,'field':{'kind':'p_value'}}
    elif name=='synthetic_cross_analysis':
        fields={'cross_family':fields['cross_family']}
    args['requested_form']=contracts.requested_form_schema(fields,provider=args['provider'])
    facts=projection.project_requested_facts(**args)
    assert projection.validate_projected_facts(facts,**args)==facts
    if name=='metacats_aa_two_groups':
        for basis in ('native','biological'):
            assert facts[basis+':comparison:effects|cramers_v']['value']==1.0
            assert facts[basis+':comparison:effects|cramers_v']['numerator']==12.000000000000002
            assert facts[basis+':comparison:effects|cramers_v']['denominator']==12.0
            assert facts[basis+':comparison:effects|total_variation']['value']==1.0
    records.append({'name':name,'full_input_path':str(path.relative_to(ROOT)),
        'full_input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'requested_form':args['requested_form'],'facts':facts})
(OUT/'WORKED_EXAMPLES_017.json').write_text(json.dumps({'basis':'Exact saved cells; no scientific formula recalculated. Full inputs retain provider provenance; synthetic commissioning does not establish live custody.','examples':records},indent=2,allow_nan=False)+'\n')
print(json.dumps({'examples':len(records),'selected_fields':sum(len(r['facts']) for r in records)}))
