"""Independent242 arithmetic after root's recorded complete post-paper reset.

No raw preparation values, physical IDs, calibration or joint covariance are
invented. All mean-precision and interval calculations are explicit scenarios.
"""
from copy import deepcopy
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import math
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242'
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast

assert json.loads((HERE/'RESET_COMPLETE_003.json').read_text())['postpaper_reset_complete']
manifest=json.loads((CASE/'MANIFEST_001.json').read_text())
for entry in manifest['files']:
    raw=(CASE/entry['path']).read_bytes()
    assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],entry['path']
text=(CASE/'sources/elife-06181-v2.txt').read_bytes()
pdf=(CASE/'sources/elife-06181-v2.pdf').read_bytes()
selection=json.loads((CASE/'source_selection.json').read_text())

def witness(start_phrase,end_phrase):
    start=text.index(start_phrase.encode())
    end=text.index(end_phrase.encode(),start)+len(end_phrase.encode())
    return {'source_ref':selection['source_ref'],'representation':'text',
        'start':start,'end':end,'quote':text[start:end].decode()}

full_footnote=witness('#The mutant was expressed in two independent enzyme preparations',
    'measurements for the independent preparations.')
conditions=witness('Activity measurements were performed in 0.1 M MOPS','MgCl2 was excluded.')
purification=witness('WT and mutant AP were purified from a fusion construct',
    'C-terminal end of AP.')
enriched=deepcopy(selection)
operand=enriched['numerator']
operand['context'].update(preparation=full_footnote,conditions=conditions,experimental_system=purification)
for field in ('statistic','repetition_basis'):
    operand['uncertainty'][field]['witnesses']=[deepcopy(full_footnote)]
operand['uncertainty']['count']['witness']=deepcopy(full_footnote)

def source(ref,representation):
    assert ref==selection['source_ref']
    raw=pdf if representation=='original' else text
    return {'artifact_ref':'sha256_'+hashlib.sha256(raw).hexdigest(),'content':raw}

extraction=read_kinetic_inputs(enriched,read_source=source)
row=extraction['operands']['numerator']
x=Q(row['number']['raw_number']);s=Q(row['uncertainty']['magnitude']['raw_number'])
n=row['uncertainty']['canonical']['count']
assert (x,s,n)==(Q(31,10),Q(1,10),2)
assert row['uncertainty']['canonical']['repetition_basis']=='biological_preparations'
scale=Q(60,10**6)
assert row['unit']['canonical_unit']=='uM^-1min^-1'
assert row['canonical_value']==float(x*scale)
assert row['uncertainty']['canonical']['magnitude']==float(s*scale)
assert row['measurement_identity'] is None
sheet=populate_kinetic_contrast(extraction['calculation_inputs'])
assert sheet['model'] is None and sheet['cells']['source_profile_log_ratio']['value'] is None
assert 'mean_se' not in sheet['cells']
assert n==2 and sheet['independent_preparation_count'] is None
# Native exact printed operands, never reversal of a rounded canonical float.
relative_sd=s/abs(x)
scenario_variance=s*s/n
scenario_se=math.sqrt(float(scenario_variance))
t95_df1=1/math.tan(math.pi/40)
halfwidth=t95_df1*scenario_se
assert relative_sd==Q(1,31) and scenario_variance==Q(1,200)
assert math.isclose(scenario_se,0.07071067811865475)
assert math.isclose(t95_df1,12.7062047361747)
assert math.isclose(halfwidth,0.89846435320937)
assert math.isclose(scenario_se/float(x),math.sqrt(float(scenario_variance/(x*x))))
assert scenario_variance*scale*scale==Q(9,500000000000)

test_line=next(line for line in text.decode().splitlines()
    if line.strip().startswith('D101A/E322Y/K328A '))
match=re.search(r'D101A/E322Y/K328A\s+([0-9.]+) \(([0-9.]+)\)',test_line)
assert match and '#' not in test_line.split()[0]
y,sy=map(Q,match.groups())
assert (y,sy)==(Q(11,10),Q(1,10))
assert x-y==2 and y/x==Q(11,31) and 1-y/x==Q(20,31)
report={'status':'passed','source_packet_files_verified':len(manifest['files']),
    'source_values':{'reported_estimate_native':str(x),'reported_sd_native':str(s),
        'physical_preparation_count':n,'native_unit':'M^-1 s^-1',
        'relative_reported_sd':str(relative_sd),'relative_reported_sd_decimal':float(relative_sd)},
    'conditional_mean_precision':{'variance_native_squared':str(scenario_variance),
        'standard_error_native':scenario_se,'relative_standard_error':scenario_se/float(x),
        'variance_canonical_squared':str(scenario_variance*scale*scale),
        'conditions':['one estimate per independent preparation for this SD',
            'common-mean finite-variance IID preparation estimates',
            'ordinary sample-SD denominator n-1','printed summaries treated as nominal operands'],
        'source_estimator_hierarchy_complete':False,'ordinary_unconditional_value':None},
    'illustrative_conditional_interval':{'proposed_confidence_level':0.95,'df':n-1,
        't_multiplier':t95_df1,'halfwidth':halfwidth,'lower':float(x)-halfwidth,'upper':float(x)+halfwidth,
        'additional_conditions':['normal preparation estimates','reported central estimate is their equal-weight arithmetic mean'],
        'source_established_normality':False,'source_explicit_mean_label':False,
        'ordinary_unconditional_interval':None},
    'separately_assayed_K328A_contrast':{'reference_minus_test':str(x-y),
        'test_over_reference':str(y/x),'fractional_decrease':str(1-y/x),
        'test_physical_preparation_count':None,'cross_construct_covariance':None,
        'difference_standard_error':None,'source_SD_test':str(sy),
        'existing_kinetic_pair_route':'requires same molecule/construct; must not falsely mark different variants identical'},
    'existing_interface_findings':{'kinetic_reader_extracts_count_SD':True,
        'kinetic_parameter_return_schema_already_permits_count_SD':True,
        'kinetic_calculator_single_summary_mean_precision_cells':False,
        'raw_rate_reader_requires_real_rows_and_does_not_accept_catalytic_efficiency_dimension':True,
        'basic_SD_over_sqrt_n_math_exists_in_rate_calculators':True},
    'calibration_recovery':None,'active_fraction_uncertainty':None,'assay_error_probability':None,
    'annotation_credit':None,'selected_episode_run':False,'actual_model_execution':False}
outputs={'ROOT_PRECISION_CHECK_004.json':report,'ROOT_ENRICHED_SELECTION_004.json':enriched,
    'ROOT_ENRICHED_EXTRACTION_004.json':extraction,'ROOT_CONTEXT_WITNESSES_004.json':
        {'complete_preparation_footnote':full_footnote,'conditions_with_E322Y_exception':conditions,
            'purification_construct_not_proof_of_assayed_tag_status':purification}}
for name,value in outputs.items():
    with (HERE/name).open('x') as handle:json.dump(value,handle,indent=2,ensure_ascii=False);handle.write('\n')
print(json.dumps({'status':'passed','source_files':len(manifest['files']),
    'reported_x':str(x),'reported_sd':str(s),'physical_preparations':n,
    'conditional_se':scenario_se,'illustrative_interval':report['illustrative_conditional_interval'],
    'no_unconditional_mean_interval_claimed':True}))
