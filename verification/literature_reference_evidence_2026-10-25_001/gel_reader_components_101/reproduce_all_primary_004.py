"""Reproduce all14 declared096 ROI recipes with explicit v2 background methods."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from PIL import Image

from gene_annotation_episode import literature_gel_inputs as inputs
from gene_annotation_episode import literature_gel_calculations as calc

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_gel_case_096'
def load(name):
    return json.loads((OUT/name).read_text())
def fraction(cell):
    return Fraction(int(cell['exact']['numerator']),int(cell['exact']['denominator']))
def write(name,value):
    with(OUT/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
legacy_names=['PRIMARY_SELECTION_003.json','PRIMARY_COMPARISON_003.json','PRIMARY_EXTRACTION_003.json','PRIMARY_SHEET_003.json']
legacy_hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in legacy_names}
selection=load('PRIMARY_SELECTION_003.json')
comparison=load('PRIMARY_COMPARISON_003.json')
reference=load('REFERENCE_096_REPLAY_004.json')
base_rois=selection['roi_assignments'][0]['lanes']
selection['version']=inputs.VERSION_V2
selection['roi_assignments']=[]
assert len(reference['declared_analysis_variants'])==14
for index,variant in enumerate(reference['declared_analysis_variants']):
    opt=variant['options']
    method='median' if opt['median_background'] else 'mean'
    rois=[]
    for base in base_rois:
        center=(base['background'][0]+base['background'][2])//2
        hw=opt['half_width'];ey=opt['expand_y'];bg=opt['background_y']
        bands=[]
        for band in base['bands']:
            box=band['region']
            bands.append({'band_id':band['band_id'],'role':band['role'],
                          'region':[center-hw,box[1]-ey,center+hw,box[3]+ey]})
        rois.append({'lane_id':base['lane_id'],'background_method':method,
            'background':[center-hw,bg[0],center+hw,bg[1]],
            'whole_lane':[center-hw,145,center+hw,278],'bands':bands})
    selection['roi_assignments'].append({'assignment_id':f'original096_variant_{index:02d}_{method}','lanes':rois})
records={'retained_primary_figure8_PMC4786714':('artifact_figure8_original',(CASE/'figure8.jpg').read_bytes()),
         'retained_primary_text_PMC4786714':('artifact_primary_text_original',(CASE/'primary.txt').read_bytes()),
         'retained_lane_interpretations_096':('artifact_retained_fields_096',(CASE/'EXTRACTION_FIELDS.json').read_bytes())}
calls=[]
def read(ref,representation):
    assert representation=='original'
    calls.append([ref,representation])
    artifact,content=records[ref]
    return {'artifact_ref':artifact,'content':content}
extraction=inputs.read_gel_inputs(selection,read_source=read)
sheet=calc.populate_gel_components(extraction,comparison)
checked_band_count=checked_lane_count=0
for actual,selected,variant,result in zip(extraction['assignments'],selection['roi_assignments'],reference['declared_analysis_variants'],sheet['assignments']):
    expected_method='median' if variant['options']['median_background'] else 'mean'
    for lane,expected,calculated in zip(actual['lanes'],variant['rows'],result['lanes']):
        assert lane['background_method']==expected_method
        for band in lane['bands']:
            saved=band['corrected_signal']
            actual_signal=Fraction(int(saved['exact']['numerator']),int(saved['exact']['denominator']))
            expected_signal=expected['bands'][band['band_id']]['corrected_darkness_sum']
            assert abs(float(actual_signal)-expected_signal)<=1e-9
            assert band['measurement']['pixel_count']==expected['bands'][band['band_id']]['pixel_count']
            assert band['measurement']['sum_darkness']==expected['bands'][band['band_id']]['raw_darkness_sum']
            assert band['measurement']['zero_gray_count']==expected['bands'][band['band_id']]['digital_minimum_count']
            checked_band_count+=1
        actual_fraction=fraction(calculated['cells']['shifted_display_fraction'])
        assert abs(float(actual_fraction)-expected['selected_shifted_darkness_fraction'])<=1e-12
        checked_lane_count+=1
    expected_direct=variant['rows'][3]['selected_shifted_darkness_fraction']-variant['rows'][7]['selected_shifted_darkness_fraction']
    assert abs(result['cells']['direct_competitor_sensitive_shift']['value']-expected_direct)<=1e-15
    assert result['dependence']['factorization_equal_to_direct'] is True
baseline_index=next(i for i,v in enumerate(reference['declared_analysis_variants']) if v['options']==reference['baseline_options'])
baseline=sheet['assignments'][baseline_index]
assert baseline['cells']['direct_competitor_sensitive_shift']['value']==0.6916968824321723
sensitivity=sheet['roi_sensitivity']['direct_competitor_sensitive_shift']
lo=float(Fraction(int(sensitivity['lower']['numerator']),int(sensitivity['lower']['denominator'])))
hi=float(Fraction(int(sensitivity['upper']['numerator']),int(sensitivity['upper']['denominator'])))
expected_range=reference['combined_self_competitor_removable_display_shift']['analysis_choice_range_not_sampling_CI']
assert abs(lo-expected_range[0])<=1e-15 and abs(hi-expected_range[1])<=1e-15
write('PRIMARY_SELECTION_V2_004.json',selection)
write('PRIMARY_EXTRACTION_V2_004.json',extraction)
write('PRIMARY_SHEET_V2_004.json',sheet)
# Independent saved-only path: all data loaded before replacing source/decoder
# and public population entrypoints. Check old actual v1 outputs exactly too.
legacy_selection=load('PRIMARY_SELECTION_003.json');legacy_extraction=load('PRIMARY_EXTRACTION_003.json');legacy_sheet=load('PRIMARY_SHEET_003.json')
def forbidden(*_args,**_kwargs):
    raise AssertionError('source IO/decoder/publicreader/publicpopulator forbidden')
inputs.read_gel_inputs=forbidden
inputs._decode=forbidden
calc.populate_gel_components=forbidden
Image.open=forbidden
assert inputs.validate_gel_extraction(legacy_selection,legacy_extraction,
    expected_digest=legacy_extraction['extraction_digest'])==legacy_extraction
assert calc.validate_gel_sheet(legacy_extraction,comparison,legacy_sheet,
    expected_extraction_digest=legacy_extraction['extraction_digest'])==legacy_sheet
assert calc.validate_gel_sheet(extraction,comparison,sheet,
    expected_extraction_digest=extraction['extraction_digest'])==sheet
assert legacy_hashes=={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in legacy_names}
summary={'source':'original096 Figure8A JPEG, exact originalbyteidentity retained',
    'full_paper_read':False,'selected_primary_sections_and_retained_packet':True,
    'own_full_reset':'POST_PAPER_RESET_PROVENANCE_003.json',
    'source_calls':calls,'all14_original_recipes_reproduced':True,
    'checked_lanes':checked_lane_count,'checked_bands':checked_band_count,
    'same_original_pixel_sums_counts_black_occupancies':True,
    'exact_rational_background_order_statistics':True,
    'comparison_against_independent_original096_script':'336 rawband identities/counts exact; corrected double presentation tolerance1e-9;112 f tolerance1e-12;14 direct shifts1e-15',
    'baseline_original_variant_index':baseline_index,'baseline_components':baseline['cells'],
    'complete_available_assignment_range':[lo,hi],'range_kind':'ROI/background choice range, not samplingCI',
    'sampling_standard_uncertainty':None,'independent_preparation_count':None,'molecular_occupancy':None,
    'v1_actual_saved_output_reconstructed_exactly':True,'v1_original_files_preserved':legacy_hashes,
    'v2_saved_output_reconstructed_without_source_decode_publicpopulator':True,
    'expected_digest_custody_basis':'standalone original saved extraction record; native host binding not claimed',
    'native_episode_execution':False,'actual_model_backed_interpretation':False,'annotation_credit':None}
write('PRIMARY_VERIFICATION_004.json',summary)
print(json.dumps({'original_recipes':14,'checked_lanes':checked_lane_count,'checked_bands':checked_band_count,
    'baseline_direct_shift':baseline['cells']['direct_competitor_sensitive_shift']['value'],
    'analysis_choice_range':summary['complete_available_assignment_range'],
    'v1_and_v2_saved_only_reconstruction':True,'source_calls':calls},indent=2))
