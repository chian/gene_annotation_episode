"""Source240/238 numerical custody plus explicitly SYNTHETIC design contrasts.

No provider/model traffic, selected delivery, runtime controller or final credit
is exercised. Frozen paper coordinates are manual readings, not physical data.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from gene_annotation_episode.literature_endpoint_signal_inputs import (
    POINT_ORDER, endpoint_signal_population_schema, endpoint_signal_extraction_schema,
    covariance_source_schema, read_endpoint_signal_inputs, validate_endpoint_signal_extraction,
)
from gene_annotation_episode.literature_endpoint_signal_calculations import (
    COMPONENTS, FORMULAS, MEANINGS, endpoint_signal_sheet_schema, populate_endpoint_signal,
)
from gene_annotation_episode.literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

ROOT=Path(__file__).resolve().parents[1]
OWN=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241'
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238'
ORACLE=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_contributor_review_240/SHARED_UNCERTAINTY_ORACLE_001.json'

def _load(name): return json.loads((OWN/name).read_text())
def _source(content): return {'artifact_ref':'artifact_'+hashlib.sha256(content).hexdigest(),'content':content}
def _paper():
    args=_load('EXAMPLE_INPUT_002.json')
    blobs={('source_kaster_primary','original'):(CASE/'originals/primary.html').read_bytes(),
        ('source_kaster_primary','text'):(CASE/'originals/primary_text.txt').read_bytes(),
        ('source_kaster_original_figure4','original'):(CASE/'originals/figure4.jpg').read_bytes()}
    return args,blobs

def _callback(blobs,calls=None):
    def read(ref,rep):
        if calls is not None: calls.append((ref,rep))
        return _source(blobs[ref,rep])
    return read

def _read(args,blobs): return read_endpoint_signal_inputs(args,read_source=_callback(blobs))
def _cells(sheet): return {r['component']:r for r in sheet['cells']}
def _q(cell,field='exact_value'):
    value=cell[field]
    return None if value is None else Fraction(int(value['numerator']),int(value['denominator']))
def _covq(v): return Fraction(int(v['numerator']),int(v['denominator']))

def _synthetic(ys=(10,4,2), *, direction='increases_downward'):
    """Controlled synthetic raster and interpretation, never a published finding."""
    args,blobs=_paper()
    im=Image.new('RGB',(512,512),'black');stream=BytesIO();im.save(stream,format='PNG');im.close()
    raw=stream.getvalue();blobs[('synthetic_image','original')]=raw
    args['source_kind']='synthetic_fixture'
    args['image'].update(source_ref='synthetic_image',expected_sha256=hashlib.sha256(raw).hexdigest(),
        width=512,height=512,panel_region=[0,0,512,512],image_origin='synthetic')
    for role,y in zip(POINT_ORDER,ys):
        p=args['image']['points'][role]
        p.update(x=30,y=y,y_enclosure=[y,y],support_region=[28,max(0,y-1),33,y+2])
        p['image_witness']['region']=list(p['support_region'])
    args['relationships']['ordinate_direction']['value']=direction
    for r in ('baseline_applicability','fast_component_completion'):
        args['relationships'][r]['value']='supported'
    return args,blobs

def _attach_covariance(args,blobs,matrix, *, basis='joint_manual_reading_error',origin='synthetic',status='known'):
    initial=_read(args,blobs)
    field='physical_estimate_owner' if basis=='joint_physical_ordinate_estimates' else 'coordinate_owner'
    owners=[initial['points'][r]['observation'][field] for r in POINT_ORDER]
    wire={'version':'a105_endpoint_signal_covariance_v1','basis':basis,'primitive_order':list(POINT_ORDER),
        'primitive_owners':owners,'primitive_units':['native_ordinate_pixel']*3,'covariance':matrix,
        'variance_status':status,'origin':origin,'provenance_witnesses':[],
        'native_coordinate_basis_witnesses':([args['context']['condition']] if basis=='joint_physical_ordinate_estimates' else []),
        'coordinate_units_status':'already_in_declared_native_coordinate_units'}
    args['covariance_source_ref']='synthetic_covariance'
    blobs['synthetic_covariance','original']=json.dumps(wire).encode()
    return wire

def test_exact_reviewed_contracts_constants_and_full_task():
    for name,fn in [('INPUT',endpoint_signal_population_schema),('EXTRACTION',endpoint_signal_extraction_schema),
            ('SHEET',endpoint_signal_sheet_schema),('COVARIANCE',covariance_source_schema)]:
        assert fn()==_load(name+'_SCHEMA_002.json')
    constants=_load('CELL_CONSTANTS_002.json')
    assert FORMULAS==constants['FORMULAS'] and MEANINGS==constants['MEANINGS']
    assert ENDPOINT_SIGNAL_TASK==(OWN/'PROMPT_CONSTANT_PLAN_001.txt').read_text().strip()
    assert len(ENDPOINT_SIGNAL_TASK.split('\n\n'))==7
    assert 'supplied sequence, selected contents or snippets' in ENDPOINT_SIGNAL_TASK


def test_original_source_exact_manual_reading_and_shared_enclosure():
    args,blobs=_paper();saved=deepcopy(args);calls=[]
    extraction=read_endpoint_signal_inputs(args,read_source=_callback(blobs,calls))
    sheet=populate_endpoint_signal(extraction);cells=_cells(sheet)
    assert args==saved and extraction==sheet['input_snapshot']
    assert cells['total_amplitude']['value']==142
    for name,value in [('corrected_amplitude',131),('additional_amplitude',11),('retained_fraction',131/142),('additional_fraction',11/142)]:
        assert cells[name]['value'] is None and cells[name]['conditional_value']==value
        assert cells[name]['status']=='conditional_scenario'
    f=cells['retained_fraction']
    assert _q(f,'conditional_exact_value')==Fraction(131,142)
    assert _q(f,'exact_lower')==Fraction(128,143) and _q(f,'exact_upper')==Fraction(67,71)
    assert _q(cells['additional_fraction'],'exact_lower')==Fraction(4,71)
    assert _q(cells['additional_fraction'],'exact_upper')==Fraction(15,143)
    assert Fraction(128,145)!=_q(f,'exact_lower')  # Invalid independent numerator/denominator division.
    assert [extraction['points'][r]['observation']['support']['point_rgb'] for r in POINT_ORDER]==[[41]*3,[131]*3,[38]*3]
    assert extraction['covariance'] is None and sheet['joint_propagation'] is None
    assert all(cells[n]['value'] is None and cells[n]['conditional_value'] is None for n in COMPONENTS[5:])
    assert '∼0.6' in extraction['context']['correction_discussion']['value']
    assert extraction['context']['expression_host'] is None
    assert extraction['relationships']['arrangement']['interpretation']['value']=='coexistence'
    assert extraction['context']['sampling_window']['value']=='finite_selected_late_point_no_physical_time_extracted'
    assert 'physical_covariance_unreported' in f['qualifications']
    # The same original bytes were authenticated; no external source or arbitrary numerical argument.
    assert len(calls)==3
    raw=blobs['source_kaster_primary','text']
    for field in ('subject','organism','partners','experiment','endpoint','condition','experimental_system'):
        w=extraction['context'][field]['witness']
        assert 21082<=w['start']<w['end']<=21658
        assert raw[w['start']:w['end']].decode()==w['quote']

@pytest.mark.parametrize('mutation,code',[
    ('extra_scientific_value','closed_endpoint_schema_required'),('outside','point_outside_panel'),
    ('enclosure','invalid_reading_enclosure'),('role','point_role_mismatch')])
def test_invalid_selections_fail_before_source_callbacks(mutation,code):
    args,blobs=_paper()
    if mutation=='extra_scientific_value': args['amplitude']=142
    elif mutation=='outside':args['image']['points']['initial']['x']=999
    elif mutation=='enclosure':args['image']['points']['initial']['y_enclosure']=[40,38]
    else:args['image']['points']['initial']['image_witness']['meaning']='selected_late_trace'
    calls=[]
    with pytest.raises(ExperimentalContractError) as error:
        read_endpoint_signal_inputs(args,read_source=_callback(blobs,calls))
    assert error.value.code==code and calls==[]

@pytest.mark.parametrize('bad,expected', [('hash','image_sha256_mismatch'),('dimensions','image_dimensions_mismatch'),('decode','source_read_failed')])
def test_image_dependency_failure_preserves_context(bad,expected):
    args,blobs=_paper()
    if bad=='hash':args['image']['expected_sha256']='0'*64
    elif bad=='dimensions':args['image']['width']=480
    else:
        raw=b'not an image';blobs['source_kaster_original_figure4','original']=raw
        args['image']['expected_sha256']=hashlib.sha256(raw).hexdigest()
    extraction=_read(args,blobs)
    assert extraction['image']['error']['code']==expected
    assert extraction['context']['subject']['value'].startswith('MvhADG/HdrABC')
    assert all(c['status']=='unavailable' for c in populate_endpoint_signal(extraction)['cells'])


def test_missing_baseline_and_bad_local_witness_preserve_total():
    args,blobs=_paper();args['image']['points']['baseline_at_addition']=None
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert cells['total_amplitude']['value']==142 and cells['retained_fraction']['status']=='unavailable'
    args,blobs=_paper();args['image']['points']['baseline_at_addition']['semantic_witnesses'][0]['quote']='bad quote'
    extraction=_read(args,blobs)
    assert extraction['points']['baseline_at_addition']['error']['code']=='source_quote_mismatch'
    assert _cells(populate_endpoint_signal(extraction))['total_amplitude']['value']==142

@pytest.mark.parametrize('name,value,reason',[
    ('axis_scale','nonlinear','axis_scale_unestablished'),('axis_scale','unknown','axis_scale_unestablished'),
    ('ordinate_direction','unknown','ordinate_direction_unresolved'),
    ('baseline_applicability','unknown','baseline_applicability_unresolved'),
    ('baseline_applicability','unsupported','baseline_applicability_unresolved'),
    ('baseline_applicability','conflicting','baseline_applicability_unresolved'),
    ('fast_component_completion','unknown','fast_component_completion_unresolved'),
    ('correction_stage','already_applied','correction_already_applied'),
    ('measurement_stage','initial_rate','measurement_stage_not_endpoint')])
def test_applicability_and_double_correction_guards(name,value,reason):
    args,blobs=_paper();args['relationships'][name]['value']=value
    if value=='conflicting':args['relationships'][name]['image_regions'].append([60,30,210,190])
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert cells['retained_fraction']['status']=='unavailable'
    assert reason in cells['retained_fraction']['unavailable_reasons']
    if name not in ('axis_scale','ordinate_direction','measurement_stage'):
        assert cells['total_amplitude']['value']==142
    assert extraction['points']['initial']['observation']['y']==39


def test_signed_out_of_domain_and_zero_denominator_are_not_clamped():
    args,blobs=_synthetic((10,14,2));cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert cells['corrected_amplitude']['value']==-4 and cells['retained_fraction']['value']==-.5
    assert cells['additional_fraction']['value']==1.5
    assert 'nonnegative_additive_model_incompatible' in cells['retained_fraction']['qualifications']
    args,blobs=_synthetic((10,4,10));cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert cells['total_amplitude']['value']==0 and cells['corrected_amplitude']['value']==6
    assert 'zero_total_amplitude' in cells['retained_fraction']['unavailable_reasons']


def test_denominator_reading_enclosure_crossing_zero_and_missing_bounds_preserve_point():
    args,blobs=_synthetic((10,4,2));args['image']['points']['late']['y_enclosure']=[1,12]
    cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert cells['retained_fraction']['value']==.75 and cells['retained_fraction']['lower'] is None
    assert 'reading_denominator_contains_zero' in cells['retained_fraction']['unavailable_reasons']
    args['image']['points']['late']['y_enclosure']=None
    cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert cells['retained_fraction']['value']==.75 and 'reading_enclosure_unreported' in cells['retained_fraction']['unavailable_reasons']


def test_independent_shared_uncertainty_oracle_and_joint_output():
    oracle=json.loads(ORACLE.read_text());args,blobs=_synthetic()
    _attach_covariance(args,blobs,oracle['synthetic_joint_covariance'])
    sheet=populate_endpoint_signal(_read(args,blobs));cells=_cells(sheet)
    assert cells['total_amplitude_variance']['value']==20
    assert cells['corrected_amplitude_variance']['value']==11
    assert cells['additional_amplitude_variance']['value']==21
    assert _q(cells['retained_fraction_variance'])==Fraction(59,256)
    assert _q(cells['retained_fraction_variance'])!=Fraction(89,256)
    assert cells['retained_fraction_variance']['exact_value']=={k:v for k,v in oracle['exact_results']['retained_fraction_variance'].items() if k!='decimal'}
    joint=sheet['joint_propagation']['exact_covariance']
    assert _covq(joint[1][2])==-6 and _covq(joint[1][0])==5
    assert _q(cells['additional_fraction_variance'])==Fraction(59,256)
    assert 'physical_covariance_unreported' in cells['retained_fraction_variance']['qualifications']
    assert 'synthetic_covariance_model' in cells['retained_fraction_variance']['qualifications']

@pytest.mark.parametrize('scale,shift,direction',[(3,20,'increases_downward'),(-2,100,'increases_upward')])
def test_common_affine_ordinate_and_covariance_invariance(scale,shift,direction):
    ys=[scale*q+shift for q in (10,4,2)]
    args,blobs=_synthetic(ys,direction=direction)
    matrix=[[scale*scale*v for v in row] for row in ((4,1,0),(1,9,2),(0,2,16))]
    _attach_covariance(args,blobs,matrix)
    cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert _q(cells['retained_fraction'])==Fraction(3,4)
    assert _q(cells['retained_fraction_variance'])==Fraction(59,256)
    assert cells['total_amplitude']['value']==abs(scale)*8

@pytest.mark.parametrize('mutation,code',[
    ('owner','covariance_owner_mismatch'),('units','closed_endpoint_schema_required'),
    ('basis','closed_endpoint_schema_required'),('asymmetry','symmetric_covariance_required'),
    ('indefinite','positive_semidefinite_covariance_required'),('duplicate','duplicate_json_key')])
def test_bad_covariance_preserves_native_cells(mutation,code):
    args,blobs=_synthetic();wire=_attach_covariance(args,blobs,[[4,1,0],[1,9,2],[0,2,16]])
    if mutation=='owner':wire['primitive_owners'][0]='wrong_owner'
    elif mutation=='units':wire['primitive_units'][0]='absorbance'
    elif mutation=='basis':wire['coordinate_units_status']='convert_from_absorbance'
    elif mutation=='asymmetry':wire['covariance']=[[10**18,10**17,0],[10**17+1,10**18,0],[0,0,1]]
    elif mutation=='indefinite':wire['covariance']=[[1,2,0],[2,1,0],[0,0,1]]
    raw=json.dumps(wire)
    if mutation=='duplicate':raw=raw.replace('"origin": "synthetic"','"origin": "synthetic", "origin": "source_reported"')
    blobs['synthetic_covariance','original']=raw.encode()
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert extraction['covariance']['error']['code']==code
    assert cells['total_amplitude']['value']==8 and cells['retained_fraction']['value']==.75
    assert cells['retained_fraction_variance']['value'] is None

@pytest.mark.parametrize('matrix', [[[0,0,0],[0,0,0],[0,0,0]],[[1,1,1],[1,1,1],[1,1,1]]])
def test_explicit_zero_or_singular_covariance_is_preserved(matrix):
    args,blobs=_synthetic();_attach_covariance(args,blobs,matrix)
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert extraction['covariance']['error'] is None
    assert cells['retained_fraction_variance']['value']==0


def test_unknown_covariance_status_does_not_imply_independence():
    args,blobs=_synthetic();_attach_covariance(args,blobs,[[4,1,0],[1,9,2],[0,2,16]],status='unknown')
    cells=_cells(populate_endpoint_signal(_read(args,blobs)))
    assert cells['retained_fraction']['value']==.75
    assert cells['retained_fraction_variance']['value'] is None
    assert 'covariance_status_unknown' in cells['retained_fraction_variance']['unavailable_reasons']


def test_synthetic_physical_block_already_native_units_requires_actual_owners_and_basis():
    args,blobs=_synthetic()
    # Three different source-backed owner witnesses are controlled scenario declarations.
    for r,field in zip(POINT_ORDER,('subject','condition','experiment')):
        args['image']['points'][r]['physical_estimate_owner']=args['context'][field]
    _attach_covariance(args,blobs,[[4,1,0],[1,9,2],[0,2,16]],basis='joint_physical_ordinate_estimates')
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert extraction['covariance']['error'] is None
    v=cells['retained_fraction_variance']
    assert _q(v)==Fraction(59,256) and v['uncertainty_basis']=='joint_physical_ordinate_estimates'
    assert 'synthetic_covariance_model' in v['qualifications'] and 'synthetic' in v['input_origins']
    wire=json.loads(blobs['synthetic_covariance','original']);wire['native_coordinate_basis_witnesses']=[]
    blobs['synthetic_covariance','original']=json.dumps(wire).encode()
    assert _read(args,blobs)['covariance']['error']['code']=='native_coordinate_basis_witness_required'


def test_requested_subset_order_and_pure_calculator_immutability():
    args,blobs=_paper();args['requested_cells']=['retained_fraction','total_amplitude']
    extraction=_read(args,blobs);snapshot=deepcopy(extraction)
    assert [c['component'] for c in populate_endpoint_signal(extraction)['cells']]==args['requested_cells']
    assert extraction==snapshot
    extraction['points']['initial']['observation']['y']=40
    with pytest.raises(ExperimentalContractError,match='extraction_point_mismatch'):
        validate_endpoint_signal_extraction(extraction)

@pytest.mark.parametrize('raw,code',[(b'{','malformed_covariance_source'),(b'[]','closed_endpoint_schema_required'),
    (b'{"covariance": [[1,2]]}','three_by_three_covariance_required'),
    (b'{"covariance": [[NaN,0,0],[0,1,0],[0,0,1]]}','finite_number_required'),
    (b'{"covariance": [[true,0,0],[0,1,0],[0,0,1]]}','finite_number_required')])
def test_malformed_covariance_has_specific_partial_error(raw,code):
    args,blobs=_synthetic();args['covariance_source_ref']='bad_covariance';blobs['bad_covariance','original']=raw
    extraction=_read(args,blobs)
    assert extraction['covariance']['error']['code']==code
    assert _cells(populate_endpoint_signal(extraction))['retained_fraction']['value']==.75


def test_missing_ink_preserves_unrelated_points_and_context():
    args,blobs=_paper()
    p=args['image']['points']['baseline_at_addition']
    p.update(x=100,y=100,y_enclosure=[100,100],support_region=[100,100,102,102],maximum_rgb=0)
    p['image_witness']['region']=[100,100,102,102]
    extraction=_read(args,blobs)
    assert extraction['points']['baseline_at_addition']['error']['code']=='point_support_ink_unavailable'
    assert _cells(populate_endpoint_signal(extraction))['total_amplitude']['value']==142


def test_same_physical_owner_cannot_have_different_values_or_covariance_rows():
    args,blobs=_synthetic()
    witness=args['context']['condition']
    for r in POINT_ORDER:args['image']['points'][r]['physical_estimate_owner']=witness
    _attach_covariance(args,blobs,[[1,1,1],[1,1,1],[1,1,1]],basis='joint_physical_ordinate_estimates')
    assert _read(args,blobs)['covariance']['error']['code']=='shared_owner_value_mismatch'
    args,blobs=_synthetic((10,10,2))
    for r in POINT_ORDER[:2]:args['image']['points'][r]['physical_estimate_owner']=witness
    args['image']['points']['late']['physical_estimate_owner']=args['context']['subject']
    _attach_covariance(args,blobs,[[1,0,0],[0,1,0],[0,0,1]],basis='joint_physical_ordinate_estimates')
    assert _read(args,blobs)['covariance']['error']['code']=='shared_owner_covariance_mismatch'


def test_detached_owner_and_context_tampering_rejected():
    args,blobs=_paper();extraction=_read(args,blobs)
    extraction['points']['initial']['observation']['coordinate_owner']='borrowed_owner'
    with pytest.raises(ExperimentalContractError,match='extraction_owner_mismatch'):
        populate_endpoint_signal(extraction)
    extraction=_read(args,blobs);extraction['context']['subject']['value']='borrowed_subject'
    with pytest.raises(ExperimentalContractError,match='extraction_context_mismatch'):
        populate_endpoint_signal(extraction)


def _replace_synthetic_image(args,blobs,image):
    stream=BytesIO();image.save(stream,format='PNG');image.close();raw=stream.getvalue()
    blobs['synthetic_image','original']=raw
    args['image']['expected_sha256']=hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('alpha,threshold,supported',[(0,180,False),(0,255,False),
    (64,180,False),(74,180,False),(75,180,True),(128,180,True),(255,180,True)])
def test_rgba_visible_support_uses_white_rendering_and_excludes_zero_alpha(alpha,threshold,supported):
    args,blobs=_synthetic()
    _replace_synthetic_image(args,blobs,Image.new('RGBA',(512,512),(0,0,0,alpha)))
    for p in args['image']['points'].values():p['maximum_rgb']=threshold
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert extraction['image']['mode']=='RGBA' and extraction['image']['error'] is None
    assert extraction['context']['subject'] is not None
    if supported:
        for entry in extraction['points'].values():
            assert entry['observation']['support']['point_rgb']==[255-alpha]*3
            assert entry['observation']['support']['qualifying_pixel_count']==15
        assert cells['total_amplitude']['value']==8 and cells['retained_fraction']['value']==.75
    else:
        assert all(entry['observation'] is None and entry['error']['code']=='point_support_ink_unavailable'
            for entry in extraction['points'].values())
        assert all(c['status']=='unavailable' for c in cells.values())


def test_rgba_partial_alpha_rgb_compositing_rounds_consistently_at_threshold():
    args,blobs=_synthetic()
    # Over white, this becomes (128,127,127), not the raw (1,0,0).
    _replace_synthetic_image(args,blobs,Image.new('RGBA',(512,512),(1,0,0,128)))
    for p in args['image']['points'].values():p['maximum_rgb']=127
    extraction=_read(args,blobs)
    assert all(p['observation'] is None for p in extraction['points'].values())
    for p in args['image']['points'].values():p['maximum_rgb']=128
    extraction=_read(args,blobs)
    assert all(p['observation']['support']['point_rgb']==[128,127,127] for p in extraction['points'].values())
    assert _cells(populate_endpoint_signal(extraction))['retained_fraction']['value']==.75


@pytest.mark.parametrize('mode,color,expected',[('RGB',(41,51,61),[41,51,61]),
    ('L',41,[41,41,41]),('RGBA',(41,51,61,255),[41,51,61])])
def test_rgb_l_and_opaque_rgba_native_readings_are_unchanged(mode,color,expected):
    args,blobs=_synthetic()
    _replace_synthetic_image(args,blobs,Image.new(mode,(512,512),color))
    extraction=_read(args,blobs)
    assert extraction['image']['mode']==mode
    assert all(p['observation']['support']['point_rgb']==expected for p in extraction['points'].values())
    assert _cells(populate_endpoint_signal(extraction))['retained_fraction']['value']==.75


def test_invisible_rgba_baseline_preserves_visible_initial_and_later_partials():
    args,blobs=_synthetic()
    image=Image.new('RGBA',(512,512),(0,0,0,255))
    # Use a non-overlapping baseline selection for this controlled case.
    p=args['image']['points']['baseline_at_addition'];p['x']=60
    p['support_region']=[58,3,63,6];p['image_witness']['region']=[58,3,63,6]
    for x in range(58,63):
        for y in range(3,6):image.putpixel((x,y),(0,0,0,0))
    _replace_synthetic_image(args,blobs,image)
    extraction=_read(args,blobs);cells=_cells(populate_endpoint_signal(extraction))
    assert extraction['points']['baseline_at_addition']['error']['code']=='point_support_ink_unavailable'
    assert extraction['points']['initial']['observation'] is not None
    assert extraction['points']['late']['observation'] is not None
    assert extraction['context']['subject'] is not None
    assert cells['total_amplitude']['value']==8 and cells['retained_fraction']['status']=='unavailable'
