"""Finite retained-primary image reader proof, no model/runtime/acquisition."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from gene_annotation_episode import literature_gel_inputs as inputs
from gene_annotation_episode import literature_gel_calculations as calc

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_gel_case_096'
OUT = Path(__file__).resolve().parent
IMAGE_REF = 'retained_primary_figure8_PMC4786714'
TEXT_REF = 'retained_primary_text_PMC4786714'
MAP_REF = 'retained_lane_interpretations_096'
records = {IMAGE_REF: ('artifact_figure8_original', (CASE/'figure8.jpg').read_bytes()),
           TEXT_REF: ('artifact_primary_text_original', (CASE/'primary.txt').read_bytes()),
           MAP_REF: ('artifact_retained_fields_096', (CASE/'EXTRACTION_FIELDS.json').read_bytes())}
assert hashlib.sha256(records[IMAGE_REF][1]).hexdigest() == 'd30e38e432492d114610de90c542ee04bffabb990a46c04331c9bae24fd8c0eb'
primary_lines = records[TEXT_REF][1].splitlines(keepends=True)
def line_witness(first, last):
    start = sum(map(len, primary_lines[:first-1]))
    end = sum(map(len, primary_lines[:last]))
    return {'source_ref':TEXT_REF,'representation':'original','start':start,'end':end,
            'quote':records[TEXT_REF][1][start:end].decode()}
method = line_witness(283,285)
caption = line_witness(341,341)
def meaning(value, witness):
    return {'state':'known','value':value,'witnesses':[deepcopy(witness)]}
def unknown():
    return {'state':'unknown','value':None,'witnesses':[]}
context = {
    'experiment':meaning('IscR gbpA-promoter EMSA, Figure8A',caption),
    'organism':meaning('Vibrio vulnificus',method), 'genotype':unknown(),
    'subject':meaning('IscR',method),
    'construct':meaning('His-tagged IscR expressed using pJK0928',method),
    'system':meaning('In-vitro purified protein and390bp radiolabeled promoter DNA,5nM probe',method),
    'endpoint':meaning('mobility shift of radiolabeled promoter DNA',caption),
    'intended_variable':meaning('same390bp unlabeled DNA competitor concentration at fixed30nM IscR',caption)}
fields=json.loads(records[MAP_REF][1])
lanes=[]
for row in fields['experiment_meanings']['lane_values']:
    lane=row['lane']
    needle=('"lane": '+str(lane)).encode()
    start=records[MAP_REF][1].index(needle, records[MAP_REF][1].index(b'"lane_values"'))
    end=records[MAP_REF][1].index(b'}',start)+1
    witness={'source_ref':MAP_REF,'representation':'original','start':start,'end':end,
             'quote':records[MAP_REF][1][start:end].decode()}
    lanes.append({'lane_id':'lane'+str(lane),'observation_id':'Figure8A_lane'+str(lane),
        'subject':meaning('IscR preparation',method), 'construct':deepcopy(context['construct']),
        'endpoint':deepcopy(context['endpoint']),
        'condition':meaning(f"IscR{row['protein_nM']}nM; same-DNA competitor{row['self_competitor_nM']}nM; probe5nM",witness),
        'control_role':meaning('protein_free' if lane==1 else 'protein_present' if lane<=4 else 'competitor',witness)})
centers=(47,93,140,190,242,291,341,392)
ybands={'upper_shifted':(197,215),'lower_shifted':(219,239),'free':(248,274)}
# These eight complete choices are exactly the MEAN-method subset of096's
# fourteen declared recipes. No median choice is relabeled as mean.
recipes=[('baseline',19,0,(151,190)),('mean_hw17_y0',17,0,(151,190)),
    ('mean_hw17_y2',17,2,(151,190)),('mean_hw19_y2',19,2,(151,190)),
    ('mean_hw21_y0',21,0,(151,190)),('mean_hw21_y2',21,2,(151,190)),
    ('mean_bg174_194',19,0,(174,194)),('mean_bg239_247',19,0,(239,247))]
assignments=[]
for label,hw,ey,bg in recipes:
    rois=[]
    for lane,x in enumerate(centers,1):
        rois.append({'lane_id':'lane'+str(lane),'background':[x-hw,bg[0],x+hw,bg[1]],
            'whole_lane':[x-hw,145,x+hw,278], 'bands':[{'band_id':name,
                'role':'free' if name=='free' else 'shifted','region':[x-hw,y0-ey,x+hw,y1+ey]}
                for name,(y0,y1) in ybands.items()]})
    assignments.append({'assignment_id':label,'lanes':rois})
selection={'version':inputs.VERSION,'image':{'source_ref':IMAGE_REF,'artifact_ref':records[IMAGE_REF][0],
    'byte_sha256':hashlib.sha256(records[IMAGE_REF][1]).hexdigest(),'width':600,'height':937,
    'source_kind':'primary_source'},'context':context,'lanes':lanes,'roi_assignments':assignments}
comparison={'version':calc.COMPARISON_VERSION,'baseline_lane_id':'lane1',
            'protein_lane_id':'lane4','competitor_lane_id':'lane8'}
calls=[]
def read(ref,representation):
    assert representation=='original'
    calls.append([ref,representation])
    artifact,content=records[ref]
    return {'artifact_ref':artifact,'content':content}
extraction=inputs.read_gel_inputs(selection,read_source=read)
sheet=calc.populate_gel_components(extraction,comparison)
baseline=sheet['assignments'][0]
expected_sums=((0,0,100577),(3439,55150,81813),(38473,58516,51687),(41602,34222,31487),
               (21880,69413,78936),(1973,54569,89692),(353,34490,96784),(0,1741,115223))
for actual,wanted in zip(extraction['assignments'][0]['lanes'],expected_sums):
    assert tuple(Fraction(int(b['corrected_signal']['exact']['numerator']),int(b['corrected_signal']['exact']['denominator'])) for b in actual['bands'])==wanted
cell=baseline['cells']['direct_competitor_sensitive_shift']
assert Fraction(int(cell['exact']['numerator']),int(cell['exact']['denominator'])) == Fraction(75824,107311)-Fraction(1741,116964)
assert cell['value']==0.6916968824321723
assert baseline['dependence']['factorization_equal_to_direct'] is True
for name,obj in [('PRIMARY_SELECTION_003.json',selection),('PRIMARY_COMPARISON_003.json',comparison),
                 ('PRIMARY_EXTRACTION_003.json',extraction),('PRIMARY_SHEET_003.json',sheet)]:
    with(OUT/name).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
summary={'origin':'original published JPEG pixels plus source-grounded retained lane interpretation; not author densitometry',
    'primary_text_human_read_lines':[[278,294],[334,348]],'full_paper_read':False,
    'source_calls':calls,'lane_band_sums_all24_exact':True,'mean_assignments':len(assignments),
    'all_original14_variants_reproduced':False,'direct_shift':cell,'cells':baseline['cells'],
    'mean_method_range':sheet['roi_sensitivity']['direct_competitor_sensitive_shift'],
    'sampling_uncertainty':sheet['sampling_uncertainty'],'independent_preparation_count':sheet['independent_preparation_count'],
    'native_episode_execution':False,'actual_model_backed_interpretation':False}
with(OUT/'PRIMARY_VERIFICATION_003.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps({'exact24_band_sums':True,'direct_shift':cell['value'],'mean_assignments':len(assignments),
    'mean_choice_range':sheet['roi_sensitivity']['direct_competitor_sensitive_shift'],'source_calls':calls},indent=2))
