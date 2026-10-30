"""Constructed source bytes/pixels, actual reader and separate068 arithmetic.

These are engineering fixtures, not papers, native receipts or model executions.
The immutable069 HAND projections are deliberately not used as source outputs.
"""
from copy import deepcopy as cp
from fractions import Fraction
import errno
import hashlib
import types
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_figure_inputs as graph
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
DESIGN=BASE/'a105_controlled_full_source_design_069'
ROLES=shared.PRIMITIVE_ORDER
CASES=json.loads((DESIGN/'CONSTRUCTED_SOURCE_CASES_001.json').read_text())


class Fixture:
    def __init__(self,index=0):
        self.case=CASES[index]
        self.args=cp(self.case['selection'])
        self.data={s['source_ref']:(s['content_utf8'].encode() if s['content_utf8'] is not None else
            (DESIGN/s['encoded_image_file']).read_bytes()) for s in json.loads((DESIGN/'CONSTRUCTED_SOURCE_ROSTER_001.json').read_text())}
        self.cov_ref=self.args['covariance']['source_ref']
        self.main_ref=self.args['source_ref']
        self.data[self.cov_ref]=self.case['source_covariance_text'].encode()
        self.doc=json.loads(self.case['source_covariance_text'])
        self.calls=[]

    def source(self,reference,representation):
        self.calls.append((reference,representation))
        raw=self.data[reference]
        return {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw}

    def read(self):
        return reader.read_controlled_response_v2_inputs(self.args,read_source=self.source)

    def witness(self,quote,ref=None,tagged=True,start=0):
        ref=ref or self.main_ref
        at=self.data[ref].index(quote.encode(),start)
        w=dict(source_ref=ref,representation='original',start=at,end=at+len(quote.encode()),quote=quote)
        return dict(kind='text',**w) if tagged else w

    def interp(self,value,quote=None):
        return dict(value=value,witnesses=[] if quote is None else [self.witness(quote)])

    def number(self,quote,token):
        at=quote.index(token)
        return dict(witness=self.witness(quote,tagged=False),number_start=at,number_end=at+len(token))

    def append(self,text):
        self.data[self.main_ref]+=('<p>'+text+'</p>\n').encode()

    def covariance(self,mapping=None):
        self.data[self.cov_ref]=(json.dumps(self.doc,indent=2)+'\n').encode()
        labels=list(re.finditer(rb'"label":\s*("(?:[^"\\]|\\.)*")',self.data[self.cov_ref]))
        for role in ROLES:
            b=self.args['covariance']['bindings'][role]
            if mapping is not None:
                index=mapping[ROLES.index(role)]
                if index is None:
                    self.args['covariance']['bindings'][role]=None
                    continue
                if b is None:
                    b=dict(variable_index=index,label_witness=None,
                        owner_witness=cp(self.args['arms'][role]['physical_observation']['canonical_witness']),correspondence=None)
                    self.args['covariance']['bindings'][role]=b
                b['variable_index']=index
            if b is None:continue
            at,end=labels[b['variable_index']].span(1)
            b['label_witness']=dict(source_ref=self.cov_ref,representation='original',start=at,end=end,
                quote=self.data[self.cov_ref][at:end].decode())
            b['correspondence']=dict(value='same',witnesses=[dict(kind='text',**b['label_witness'])])
        for name in ('variance_status','model_kind'):
            self.args[name]=dict(value=self.doc[name],witnesses=[self.witness(json.dumps(self.doc[name]),self.cov_ref)])

    def text_measurement(self,role,text,token,unit='nmol/min'):
        self.append(text)
        self.args['arms'][role]['measurement']=dict(kind='source_literal',literal=dict(status='exact',
            candidates=[self.number(text,token)],fragments=[]),unit=self.witness(unit,tagged=False,start=self.data[self.main_ref].index(text.encode())) if unit else None)

    def roundtrip(self):
        before=cp(self.args)
        extraction=self.read()
        assert self.args==before
        Draft202012Validator(reader._extraction_schema()).validate(extraction)
        assert reader.validate_controlled_response_v2_extraction(self.args,extraction)==extraction
        return extraction,owner.populate_controlled_response_owner(extraction['calculation_inputs'])


def forbidden(*args,**kwargs):
    raise AssertionError('forbidden source/decode/counter/model/sheet operation')


def test_runtime_constructors_equal_all_exact_declarations_and_are_detached():
    for fn,path in ((reader.controlled_response_v2_arguments_schema,DESIGN/'SELECTION_SCHEMA_V2_001.json'),
            (reader._graph_schema,BASE/'a105_controlled_graph_design_061/GRAPH_RESULT_SCHEMA_002.json'),
            (reader._sheet_schema,BASE/'a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json'),
            (reader._extraction_schema,DESIGN/'EXTRACTION_SCHEMA_V2_001.json')):
        actual=fn();assert actual==json.loads(path.read_text());Draft202012Validator.check_schema(actual)
        actual['properties'].clear();assert fn()['properties']
    assert reader.__all__==['controlled_response_v2_arguments_schema','validate_controlled_response_v2_selection',
        'read_controlled_response_v2_inputs','validate_controlled_response_v2_extraction']
    assert shared.__all__==['VERSION','SELECTION_VERSION','COVARIANCE_VERSION','DEPENDENCIES',
        'controlled_response_arguments_schema','validate_controlled_response_selection','read_controlled_response_inputs','validate_controlled_response_extraction']


@pytest.mark.parametrize('index',range(14),ids=[c['name'] for c in CASES])
def test_actual_fourteen_sources_pixels_saved_science_and_separate068(index):
    f=Fixture(index);extraction,sheet=f.roundtrip()
    assert f.calls==shared._reference_closure(f.args)
    assert extraction['covariance']['source_validation']==f.case['source_validation_expected']
    assert extraction['calculation_inputs']['version']=='controlled_response_owner_inputs_v2'
    for role,arm in extraction['arms'].items():
        if arm and arm['graph_details']:
            assert arm['measurement']==arm['graph_details']['measurement']
            assert arm['calculation_operand']['origin']=='synthetic'
            assert arm['graph_details']['operand_projection']['origin']=='graph_derived'
    if index in (0,1,2,3,8,9,10,11,13):
        assert sheet['cells']['controlled_response_difference']['value']==.002 if index not in (10,) else sheet['cells']['controlled_response_difference']['value'] is None
    if index in (0,1,2,3,8):
        assert sheet['cells']['contrast_variance']['value']==3e-7
    if index==9:
        assert extraction['covariance']['projection_state']=='source_invalid'
        assert sheet['cells']['contrast_variance']['value'] is None
    if index in (4,5,10,12):
        assert sheet['cells']['contrast_variance']['value'] is None
    if index in (6,7):
        u=extraction['arms'][ROLES[0]]['reported_uncertainty']
        assert u['effective_unit']['kind']=='graph'
        assert u['canonical']['count']==3
        assert u['canonical']['repetition_basis']=='biological_preparations'
        assert u['canonical']['magnitude']==(.0012 if index==6 else None)
        assert u['canonical']['interval']==([.008,.012] if index==7 else None)
        assert u['canonical']['confidence_level']==(.95 if index==7 else None)
        assert sheet['cells']['contrast_variance']['value']==3e-7
        assert sheet['cells']['source_profile_log_ratio']['value'] is None


@pytest.mark.parametrize('mutation',[
    lambda a:a.update(value=1),lambda a:a['arms'][ROLES[0]]['measurement'].update(value=1),
    lambda a:a['covariance'].update(matrix=[[1]]),lambda a:a['arms'].update(extra=None),
    lambda a:a['arms'][ROLES[3]]['measurement']['bar_selection']['roi'].update(right=0),
    lambda a:a['arms'][ROLES[3]]['measurement']['axis']['scale'].update(status='known',kind=None),
])
def test_bad_selection_rejected_before_callback(mutation):
    f=Fixture();mutation(f.args)
    with pytest.raises(ExperimentalContractError):reader.read_controlled_response_v2_inputs(f.args,read_source=forbidden)


def test_whole_original_closure_scale_only_unused_images_and_late_authorization(monkeypatch):
    f=Fixture()
    extra='source_'+'f'*24;f.data[extra]=f.data[f.args['images'][0]['source_ref']]
    f.args['images'].append(dict(image_id='unused',source_ref=extra,original_source_ref=extra,mapping=None))
    closure=shared._reference_closure(f.args)
    assert any('linear scale' in f.data[ref].decode(errors='ignore') for ref,rep in closure)
    calls=[]
    def denied(ref,rep):
        calls.append((ref,rep))
        if (ref,rep)==closure[-1]:raise ContractError('source_out_of_scope')
        return f.source(ref,rep)
    monkeypatch.setattr(shared,'_Inputs',forbidden)
    with pytest.raises(ContractError,match='source_out_of_scope'):
        reader.read_controlled_response_v2_inputs(f.args,read_source=denied)
    assert calls==closure


@pytest.mark.parametrize('loaded',[{'artifact_ref':'a','content':'text'}, {'artifact_ref':'a','content':bytearray(b'x')},
    {'artifact_ref':'a','content':b'x','extra':1},None])
def test_malformed_callback_never_hidden_by_helper(loaded,monkeypatch):
    monkeypatch.setattr(shared,'_Inputs',forbidden)
    with pytest.raises(ExperimentalContractError):reader.read_controlled_response_v2_inputs(Fixture().args,read_source=lambda *a:loaded)


def test_alias_artifact_conflict_and_unselected_read():
    f=Fixture()
    def alias(ref,rep):
        value=f.source(ref,rep);value['artifact_ref']='one_artifact';return value
    with pytest.raises(ExperimentalContractError,match='artifact_content_conflict'):
        reader.read_controlled_response_v2_inputs(f.args,read_source=alias)
    with shared.open_controlled_response_sources(f.args,read_source=f.source) as context:
        with pytest.raises(ExperimentalContractError,match='unselected_source_read'):context.read_source('source_'+'0'*24,'original')
        with pytest.raises(AttributeError):context.profile='v1'
    assert context.closed and not context.cache and not context.visual.decoded and not context.native.cache


def test_stages_belong_to_context_and_close_after_error():
    f,g=Fixture(1),Fixture(1)
    with shared.open_controlled_response_sources(f.args,read_source=f.source) as a,shared.open_controlled_response_sources(g.args,read_source=g.source) as b:
        science=shared.read_controlled_response_arm_science(a,f.args['arms'][ROLES[0]])
        m=shared.read_controlled_response_text_measurement(a,f.args['arms'][ROLES[0]]['measurement'],endpoint=science['meanings']['endpoint'])
        with pytest.raises(ExperimentalContractError,match='source_stage_context_mismatch'):
            shared.finish_controlled_response_arm(b,science,measurement=m)
    with pytest.raises(ExperimentalContractError,match='source_context_closed'):shared.finish_controlled_response_arm(a,science,measurement=m)


@pytest.mark.parametrize('error',[FileNotFoundError(errno.ENOENT,'missing'),OSError(errno.EIO,'io'),TimeoutError(errno.ETIMEDOUT,'timeout'),EOFError('truncated')])
def test_original_availability_provenance_and063_boundary(error):
    f=Fixture();image=f.args['images'][0]['source_ref']
    def source(ref,rep):
        if ref==image:raise error
        return f.source(ref,rep)
    x=reader.read_controlled_response_v2_inputs(f.args,read_source=source)
    assert next(s for s in x['sources'] if s['source_ref']==image)['state']=='unavailable'
    assert x['arms'][ROLES[3]]['graph_details']['measurement']['reading_status']=='dependency_unavailable'
    assert x['calculation_inputs']['arms'][ROLES[3]]['status']=='missing'
    assert x['calculation_inputs']['arms'][ROLES[3]]['physical_observation_id']
    assert owner.populate_controlled_response_owner(x['calculation_inputs'])['cells']['controlled_response_difference']['value']==.002
    assert reader.validate_controlled_response_v2_extraction(f.args,x)==x


@pytest.mark.parametrize('error',[PermissionError(errno.EACCES,'scope'),ContractError('unauthorized'),RuntimeError('bug'),OSError(errno.EINVAL,'bad'),OSError('no errno')])
def test_unexpected_provider_errors_propagate(error):
    with pytest.raises(type(error)):
        reader.read_controlled_response_v2_inputs(Fixture().args,read_source=lambda *a:(_ for _ in ()).throw(error))


@pytest.mark.parametrize('upward',[True,False])
@pytest.mark.parametrize('edge',['upper','lower'])
def test_actual_signed_axes_both_terminals(upward,edge):
    f=Fixture();m=f.args['arms'][ROLES[3]]['measurement'];m['terminal_edge']=edge
    if not upward:
        m['axis']['first']['pixel']=0;m['axis']['second']['pixel']=200
    x,sheet=f.roundtrip();p=x['arms'][ROLES[3]]['measurement']['pixel_result']
    nominal=Fraction(319,2) if edge=='upper' else Fraction(399,2)
    expected=20-nominal/10 if upward else nominal/10
    assert shared._fraction(p['native_ordinate'])==expected
    assert p['qualifying_runs']==[{'top':159,'bottom':200}]
    assert x['arms'][ROLES[3]]['calculation_operand']['value']==float(expected)
    assert sheet['cells']['controlled_response_difference']['value']==.002


@pytest.mark.parametrize('variant,status',[('no_pixels','unreadable'),('multiple','ambiguous'),('terminal_clip','unreadable'),('unknown_scale','unsupported'),('defined_U','unsupported'),('unsupported_image','unsupported')])
def test_actual_graph_partials_preserve_science_and_local_work(variant,status):
    f=Fixture();m=f.args['arms'][ROLES[3]]['measurement']
    if variant=='no_pixels':m['bar_selection'].update(rgb_min=[255,0,0],rgb_max=[255,0,0])
    if variant=='multiple':m['bar_selection'].update(rgb_min=[255,255,255],rgb_max=[255,255,255])
    if variant=='terminal_clip':m['bar_selection']['roi']['top']=159
    if variant=='unknown_scale':m['axis']['scale']=dict(status='unknown',kind=None,basis='unresolved',witnesses=[])
    if variant=='defined_U':
        f.append('Plot alternate unit: U/mg.');m['axis']['unit']['candidates']=[f.witness('U/mg')]
    if variant=='unsupported_image':f.data[f.args['images'][0]['source_ref']]=b'not an image'
    x,sheet=f.roundtrip()
    assert x['arms'][ROLES[3]]['measurement']['reading_status']==status
    assert sheet['cells']['controlled_response_difference']['value']==.002
    assert x['arms'][ROLES[3]]['meanings']['physical_observation']['resolved_state']=='known'


@pytest.mark.parametrize('explicit',[False,True])
@pytest.mark.parametrize('wrong',[False,True])
def test_graph_spread_join_with_same_or_explicit_units(explicit,wrong):
    f=Fixture(6);u=f.args['arms'][ROLES[0]]['reported_uncertainty']
    if explicit:
        u['unit']=f.witness('nmol/min',tagged=False)
        u['unit_relationship']=f.interp('explicit_unit','Reported SD: 1.2 nmol/min.')
    if wrong:
        f.append('Other SD: 1.2 uM/min.')
        u['magnitude']=f.number('Other SD: 1.2 uM/min.','1.2')
    x,sheet=f.roundtrip();unc=x['arms'][ROLES[0]]['reported_uncertainty']
    assert unc['canonical']['magnitude']==(None if wrong else .0012)
    assert unc['canonical']['count']==3
    assert sheet['cells']['contrast_variance']['value']==3e-7


def test_absent_scientific_arm_differs_from_present_missing_numeric_arm():
    present=Fixture(1);x,sheet=present.roundtrip();assert sheet['cells']['controlled_response_difference']['value']==.002
    present.args['arms'][ROLES[3]]=None
    present.args['covariance']['bindings'][ROLES[3]]=None
    x,sheet=present.roundtrip();assert x['calculation_inputs']['arms'][ROLES[3]] is None
    assert 'missing_arm' in sheet['cells']['controlled_response_difference']['unavailable_reason']


def test_actual_scientific_control_application_conflict_is_not_numeric_cancellation():
    f=Fixture();a=f.args['relationships']['condition1_control_application'];a['value']='conflicting'
    a['witnesses'].append(f.witness('Only the intended factor differs.'))
    x,s=f.roundtrip();assert s['cells']['controlled_response_difference']['value'] is None
    assert 'conflicting_control_application' in s['cells']['controlled_response_difference']['unavailable_reason']


def test_duplicate_labels_exact_positions_permuted_source_n_more_than_four():
    f=Fixture();f.doc['variables'].append(dict(label='duplicate',unit='widgets',description='unselected fifth row'))
    for row in f.doc['covariance']:row.append(0)
    f.doc['covariance'].append([0,0,0,0,1]);f.covariance()
    x,s=f.roundtrip();assert len(x['covariance']['exact_matrix'])==5;assert s['cells']['contrast_variance']['value']==3e-7
    f.args['covariance']['bindings'][ROLES[2]]['label_witness']=cp(f.args['covariance']['bindings'][ROLES[1]]['label_witness'])
    with pytest.raises(ExperimentalContractError,match='source_label_token_binding_mismatch'):f.read()


@pytest.mark.parametrize('bad',['negative_unused','asymmetric_unused','nonpsd_unused'])
def test_invalid_full_original_C_never_rescued_by_good_AC(bad):
    f=Fixture(1)
    if bad=='negative_unused':f.doc['covariance'][3][3]=-1
    if bad=='asymmetric_unused':f.doc['covariance'][0][3]=.1
    if bad=='nonpsd_unused':f.doc['covariance'][0][3]=f.doc['covariance'][3][0]=5
    f.covariance();x,s=f.roundtrip()
    assert x['covariance']['source_validation']=='invalid'
    assert x['covariance']['calculation_covariance'] is None
    assert s['cells']['controlled_response_difference']['value']==.002
    assert s['cells']['contrast_variance']['value'] is None


def test_owner_alias_full_rows_validated_before_projection_and_both_unit_factors():
    f=Fixture()
    # Bind the same B owner at two different source positions, in differing units.
    f.doc['variables'][3]['unit']='umol/min'
    f.doc['covariance'][0][3]=f.doc['covariance'][3][0]=.00025
    f.doc['covariance'][3][3]=.00000025
    f.covariance(mapping=(2,0,1,3))
    x,s=f.roundtrip();assert x['covariance']['projection_state']=='available'
    assert len(x['covariance']['provided_owner_projection'])==3
    assert s['cells']['contrast_variance']['value']==3e-7
    # A source-full row discrepancy outside the A/C/B least-index marginal.
    f.doc['covariance'][3][3]=.00000026;f.covariance()
    x,s=f.roundtrip();assert x['covariance']['source_validation']=='valid'
    assert x['covariance']['projection_state']=='binding_conflicting'
    assert s['cells']['contrast_variance']['value'] is None


def test_actual_AC_document_and_full_document_partial_bindings_remain_distinct():
    a,sa=Fixture(8).roundtrip();b,sb=Fixture(1).roundtrip()
    assert len(a['covariance']['variables'])==2 and len(b['covariance']['variables'])==4
    assert sa['cells']['contrast_variance']['value']==sb['cells']['contrast_variance']['value']==3e-7
    x,s=Fixture(4).roundtrip();deps=s['contrast_dependencies']
    assert set(deps['required_covariance_owner_ids'])<=set(deps['provided_covariance_owner_ids'])
    assert deps['covariance_state']=='incomplete_active_coverage'
    assert s['cells']['contrast_variance']['value'] is None


def test_actual_provided_owner_unit_incompatibility_is_retained_conflict():
    f=Fixture();f.doc['variables'][0]['unit']='uM/min';f.covariance()
    x,s=f.roundtrip();assert x['covariance']['projection_state']=='binding_conflicting'
    assert s['cells']['controlled_response_difference']['value']==.002
    assert s['cells']['contrast_variance']['value'] is None


@pytest.mark.parametrize('kind',['known','estimated','unselected','no_source_model'])
def test_requested_source_effective_model_scope_and_canceled_graph(kind):
    f=Fixture()
    if kind=='estimated':f.doc['variance_status']='estimated'
    if kind=='no_source_model':f.doc['model_kind']='none'
    f.covariance()
    if kind=='unselected':f.args['model_kind']=f.interp('none')
    x,s=f.roundtrip()
    assert s['contrast_dependencies']['model_active_roles']==[ROLES[0],ROLES[2]]
    assert s['cells']['contrast_variance']['value']==3e-7
    assert (s['cells']['source_profile_log_ratio']['value'] is not None)==(kind=='known')
    if kind=='known':assert s['cells']['source_profile_log_ratio']['value']==pytest.approx(20/3)


def test_no_sd_count_inference_and_exact_source_projection_rounding_limits():
    f=Fixture(6);f.args['covariance']=None;f.args['variance_status']=f.interp('unknown');f.args['model_kind']=f.interp('none')
    x,s=f.roundtrip();assert x['arms'][ROLES[0]]['reported_uncertainty']['canonical']['magnitude']==.0012
    assert s['cells']['contrast_variance']['value'] is None
    f=Fixture(1);raw=f.data[f.cov_ref]
    f.data[f.cov_ref]=raw.replace(b'0.16,',b'0.16000000000000000001,')
    # Bind duplicate labels at their original exact structural positions.
    labels=list(re.finditer(rb'"label":\s*("(?:[^"\\]|\\.)*")',f.data[f.cov_ref]))
    for binding in f.args['covariance']['bindings'].values():
        if binding is None: continue
        at,end=labels[binding['variable_index']].span(1)
        binding['label_witness'].update(start=at,end=end,quote=f.data[f.cov_ref][at:end].decode())
        binding['correspondence']['witnesses']=[dict(kind='text',**binding['label_witness'])]
    for name in ('variance_status','model_kind'):
        f.args[name]['witnesses']=[f.witness(json.dumps(f.doc[name]),f.cov_ref)]
    x,s=f.roundtrip();assert x['covariance']['source_validation']=='valid'
    assert x['effective_model']['model_kind']=='none'
    assert any(d['code']=='source_model_projection_rounding' for d in x['effective_model']['diagnostics'])


def test_detached_validation_no_source_native_parser_decoder_counter_or_populator(monkeypatch):
    f=Fixture(7);x=f.read()
    for module,names in ((shared,['_Context','_Sources','_Inputs','_native_number','_native_unit']),
        (graph,['read_controlled_response_rate_figure','_strict_decode','_count_bar_runs']),
        (owner,['populate_controlled_response_owner'])):
        for name in names:monkeypatch.setattr(module,name,forbidden)
    assert reader.validate_controlled_response_v2_extraction(f.args,x)==x


@pytest.mark.parametrize('mutation',[
    lambda x:x['selection']['arms'][ROLES[0]]['physical_observation'].update(label='tampered'),
    lambda x:x['sources'].pop(),lambda x:x['images'][0].update(original_byte_sha256='0'*64),
    lambda x:x['arms'][ROLES[0]]['reported_uncertainty']['canonical'].update(magnitude=3),
    lambda x:x['arms'][ROLES[0]]['reported_uncertainty'].update(effective_unit=None),
    lambda x:x['covariance']['matrix_tokens'][1].__setitem__(2,'0.04'),
    lambda x:x['covariance']['bindings'][ROLES[0]].update(source_variable_index=0),
    lambda x:x['covariance']['provided_owner_projection'][0].update(source_variable_index=1),
    lambda x:x['effective_model'].update(variance_status='unknown'),
    lambda x:x['calculation_inputs']['arms'][ROLES[0]].update(value=999),
    lambda x:x['arms'][ROLES[3]]['graph_details']['measurement'].update(source_observation_id='fake'),
    lambda x:x['representation_reconciliations'][0].update(net_coefficient=0),
])
def test_saved_meaning_projection_and_full_C_tampering_rejected(mutation):
    f=Fixture(6);x=f.read();mutation(x)
    with pytest.raises(ExperimentalContractError):reader.validate_controlled_response_v2_extraction(f.args,x)


@pytest.mark.parametrize('field',['axis_scale','unit','edge','calibration','image','identity'])
def test_graph_tampering_rejected_even_with_measurement_duplication_updated(field):
    f=Fixture();x=f.read();a=x['arms'][ROLES[3]];g=a['graph_details']
    if field=='axis_scale':g['axis_scale']['effective_kind']='logarithmic'
    if field=='unit':g['measurement']['unit']['exact_scale']['denominator']='1'
    if field=='edge':g['measurement']['pixel_result']['pixel_edge']['nominal']['numerator']='1'
    if field=='calibration':g['measurement']['pixel_result']['axis']['slope']['numerator']='1'
    if field=='image':g['images'][0]['original_byte_sha256']='0'*64
    if field=='identity':g['measurement']['source_observation_id']='controlled_response_graph_'+'0'*64
    a['measurement']=cp(g['measurement'])
    with pytest.raises(ExperimentalContractError):reader.validate_controlled_response_v2_extraction(f.args,x)


def _load(name,path):
    # Immutable historical source is compiled in memory; no bytecode is written
    # into an old pin while evaluating its original implementation.
    module=types.ModuleType(name)
    module.__file__=str(path)
    module.__package__=name.rpartition('.')[0]
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def test_byte_exact_v1_original008_schema_results_partials_errors_callbacks_and_dependencies():
    old=_load('gene_annotation_episode._immutable_source008',BASE/'a105_controlled_response_design_056/implementation_stage_008/final_snapshot_008/gene_annotation_episode/literature_controlled_response_inputs.py')
    tests=_load('_source008_fixture',ROOT/'tests/test_literature_controlled_response_inputs.py')
    assert shared.controlled_response_arguments_schema()==old.controlled_response_arguments_schema()
    assert shared.DEPENDENCIES==old.DEPENDENCIES
    scenarios=[]
    for shared_control in (False,True):
        scenarios.append((tests.Fixture(shared_control),None))
        for error in (EOFError('truncated'),FileNotFoundError(errno.ENOENT,'missing'),OSError(errno.EIO,'io'),
                TimeoutError(errno.ETIMEDOUT,'wait'),PermissionError(errno.EACCES,'scope'),ContractError('scope'),RuntimeError('bug'),OSError('unknown')):
            scenarios.append((tests.Fixture(shared_control),error))
        for kind in ('unknown_unit','clipped','forged','invalidC','unsupportedC','duplicate_label','missing_measurement','null_arm','alias_conflict','sd','ci'):
            f=tests.Fixture(shared_control)
            if kind=='unknown_unit':f.args['arms'][ROLES[0]]['measurement']['unit']=f.witness('widgets/min')
            if kind=='clipped':f.args['arms'][ROLES[0]]['measurement']['literal']['candidates'][0]['number_start']+=1
            if kind=='forged':f.args['arms'][ROLES[0]]['measurement']['literal']['candidates'][0]['witness']['quote']='forged'
            if kind=='invalidC':f.doc['covariance'][0][0]=-1;f.covariance()
            if kind=='unsupportedC':
                f.data[f.cov_ref]=b'unsupported source';f.args['covariance']['bindings']=dict.fromkeys(ROLES)
                f.args['variance_status']=tests.interpretation(f,'unknown');f.args['model_kind']=tests.interpretation(f,'none')
            if kind=='duplicate_label':f.doc['variables'][0]['label']=f.doc['variables'][1]['label']='duplicate';f.covariance()
            if kind=='missing_measurement':f.args['arms'][ROLES[0]]['measurement']=None
            if kind=='null_arm':f.args['arms'][ROLES[0]]=None;f.args['covariance']['bindings'][ROLES[0]]=None
            if kind=='alias_conflict':tests.set_measurement(f,ROLES[3],'Alternate empty mean: 5 nmol/min/mg.','5')
            if kind=='sd':
                u=f.args['arms'][ROLES[0]]['reported_uncertainty'];u.update(statistic=tests.interpretation(f,'sd','Reported SD'),
                    magnitude=f.number('Reported SD: 0.6 nmol/min/mg.','0.6'),unit_relationship=tests.interpretation(f,'same_as_response','nmol/min/mg'))
            if kind=='ci':
                u=f.args['arms'][ROLES[0]]['reported_uncertainty'];u.update(statistic=tests.interpretation(f,'ci','Reported CI'),
                    interval=dict(witness=f.witness('[9, 15]'),lower_start=1,lower_end=2,upper_start=4,upper_end=6),
                    confidence_level=f.witness('95%'),unit_relationship=tests.interpretation(f,'same_as_response','nmol/min/mg'))
            scenarios.append((f,None))
    scenarios += [(tests.defined_unit_fixture(),None),(tests.graph_fixture()[0],None)]
    for fixture,error in scenarios:
        before=cp(fixture.args);outputs=[]
        for module in (old,shared):
            calls=[]
            def source(ref,rep):
                calls.append((ref,rep))
                if error is not None and ref==fixture.main_ref:raise error
                return fixture.source(ref,rep)
            try:
                value=module.read_controlled_response_inputs(fixture.args,read_source=source)
                result=('ok',json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False))
                assert module.validate_controlled_response_extraction(fixture.args,value)==value
            except (ExperimentalContractError,ContractError,OSError,EOFError,RuntimeError) as exc:
                result=(type(exc),getattr(exc,'code',None),getattr(exc,'field',None),str(exc))
            outputs.append((result,calls));assert fixture.args==before
        assert outputs[0]==outputs[1]


def test_source_reader_calls_no_sheet_populator_and_rejects_v1_before_io(monkeypatch):
    monkeypatch.setattr(owner,'populate_controlled_response_owner',forbidden)
    assert Fixture().read()['calculation_inputs']['version']=='controlled_response_owner_inputs_v2'
    args=Fixture().args;args['version']='controlled_response_source_selection_v1'
    with pytest.raises(ExperimentalContractError):reader.read_controlled_response_v2_inputs(args,read_source=forbidden)


def test_actual_crop_original_closure_pixels_and_signed_negative_ticks():
    f=Fixture();original=f.args['images'][0]['source_ref'];crop_ref='source_'+'e'*24
    with Image.open(BytesIO(f.data[original])) as frame:
        with frame.crop((0,0,100,210)) as cropped:
            buffer=BytesIO();cropped.save(buffer,format='PNG')
    f.data[crop_ref]=buffer.getvalue()
    f.args['images'][0].update(source_ref=crop_ref,mapping=dict(original_region=[0,0,100,210],colour_conversion='preserve'))
    x,s=f.roundtrip();g=x['arms'][ROLES[3]]['graph_details']
    assert (crop_ref,'original') in f.calls and (original,'original') in f.calls
    assert g['measurement']['pixel_result']['mapped_roi']['region']==[20,10,30,205]
    assert s['cells']['controlled_response_difference']['value']==.002
    f.append('Negative second tick: -20.')
    w=f.witness('-20')
    f.args['arms'][ROLES[3]]['measurement']['axis']['second']['tick']['candidates']=[w]
    x,s=f.roundtrip();p=x['arms'][ROLES[3]]['measurement']['pixel_result']
    assert shared._fraction(p['native_ordinate'])==Fraction('-4.05')
    assert shared._fraction(p['native_bounds']['lower'])==Fraction('-4.15')
    assert shared._fraction(p['native_bounds']['upper'])==Fraction('-3.95')


def test_wrong_actual_crop_pixels_fail_before_scientific_projection():
    f=Fixture();crop='source_'+'d'*24
    buffer=BytesIO();Image.new('RGB',(100,210),'black').save(buffer,format='PNG');f.data[crop]=buffer.getvalue()
    f.args['images'][0].update(source_ref=crop,mapping=dict(original_region=[0,0,100,210],colour_conversion='preserve'))
    with pytest.raises(ExperimentalContractError,match='image_mapping_pixels_mismatch'):f.read()


def test_provided_canceled_owner_C_remains_with_both_missing_mean_units():
    f=Fixture()
    for role in (ROLES[1],ROLES[3]):f.args['arms'][role]['measurement']=None
    x,s=f.roundtrip();assert len(x['covariance']['provided_owner_projection'])==3
    assert all(x['calculation_inputs']['arms'][r]['unit'] is None for r in (ROLES[1],ROLES[3]))
    assert s['cells']['contrast_variance']['value']==3e-7
    assert 'canceled_unit_unknown' in s['cells']['controlled_response_difference']['conditional_on']


def test_nominated_out_of_range_and_wrong_owner_bindings_are_direct_errors():
    f=Fixture();f.args['covariance']['bindings'][ROLES[0]]['variable_index']=99
    with pytest.raises(ExperimentalContractError,match='source_variable_index_out_of_bounds'):f.read()
    f=Fixture();f.args['covariance']['bindings'][ROLES[0]]['owner_witness']=f.witness('Physical B.')
    with pytest.raises(ExperimentalContractError,match='owner_witness_not_in_role'):f.read()


@pytest.mark.parametrize('token,code',[('NaN','source_json_nonfinite'),('Infinity','source_json_nonfinite'),('true','source_covariance_shape_invalid')])
def test_strict_original_source_numeric_lexemes_before_any_owner_submatrix(token,code):
    f=Fixture(1)
    # Unprovided B row remains in the actual original source-N document.
    raw=f.data[f.cov_ref].replace(b'0.25,',token.encode()+b',',1)
    f.data[f.cov_ref]=raw
    _reanchor_covariance_tokens(f)
    x,s=f.roundtrip();assert x['covariance']['source_validation']=='invalid'
    assert x['covariance']['diagnostics'][0]['code']==code
    assert s['cells']['controlled_response_difference']['value']==.002
    assert s['cells']['contrast_variance']['value'] is None


def _reanchor_covariance_tokens(f):
    labels=list(re.finditer(rb'"label":\s*("(?:[^"\\]|\\.)*")',f.data[f.cov_ref]))
    for binding in f.args['covariance']['bindings'].values():
        if binding is None:continue
        at,end=labels[binding['variable_index']].span(1)
        binding['label_witness'].update(start=at,end=end,quote=f.data[f.cov_ref][at:end].decode())
        binding['correspondence']['witnesses']=[dict(kind='text',**binding['label_witness'])]
    for name in ('variance_status','model_kind'):
        f.args[name]['witnesses']=[f.witness(json.dumps(f.doc[name]),f.cov_ref)]


def test_numeric_duplicate_keys_source_partial_and_forged_nominations_not_hidden():
    f=Fixture();f.data[f.cov_ref]=f.data[f.cov_ref].replace(b'"covariance":',b'"covariance":[], "covariance":',1)
    _reanchor_covariance_tokens(f)
    x,s=f.roundtrip();assert x['covariance']['diagnostics'][0]['code']=='source_json_duplicate_key'
    assert s['cells']['controlled_response_difference']['value']==.002
    f.args['covariance']['bindings'][ROLES[0]]['label_witness']['quote']='forged'
    with pytest.raises(ExperimentalContractError):f.read()


def test_active_source_censor_and_approximation_keep_component_specific_limits():
    for marker in ('< ','about '):
        f=Fixture();f.text_measurement(ROLES[0],'Alternate A: '+marker+'10 nmol/min.','10')
        x,s=f.roundtrip();a=x['calculation_inputs']['arms'][ROLES[0]]
        assert a['status']==('bound' if marker=='< ' else 'point')
        assert a['approximate']==(marker=='about ')
        assert s['cells']['source_profile_log_ratio']['value'] is None
        if marker=='about ':assert s['cells']['contrast_variance']['value']==3e-7
        else:
            assert s['cells']['controlled_response_difference']['upper']==.002
            assert 'unresolved_censoring_model' in s['cells']['contrast_variance']['unavailable_reason']


def test_full_owner_matrix_permutation_both_unit_factors_and_all_provided_rows():
    f=Fixture(1)
    # A uses nmol/min; C source covariance uses umol/min, both dimensions are
    # retained. V=.16e-6 + .00000020 - 2*.00003*.001 =3e-7.
    f.doc['variables'][1]['unit']='umol/min'
    f.doc['covariance'][1][1]=.00000020
    f.doc['covariance'][1][2]=f.doc['covariance'][2][1]=.00003
    order=[3,2,0,1]
    f.doc['variables']=[f.doc['variables'][i] for i in order]
    f.doc['covariance']=[[f.doc['covariance'][i][j] for j in order] for i in order]
    f.covariance(mapping=(1,None,3,None))
    x,s=f.roundtrip()
    assert x['calculation_inputs']['covariance']['units']==['nmol/min','umol/min']
    assert [p['source_variable_index'] for p in x['covariance']['provided_owner_projection']]==[1,3]
    assert s['cells']['contrast_variance']['value']==3e-7


def test_graph_partial_and_source_covariance_availability_saved_without_source_access():
    f=Fixture();ref=f.cov_ref
    def source(reference,representation):
        if reference==ref:raise EOFError('retained source truncated')
        return f.source(reference,representation)
    x=reader.read_controlled_response_v2_inputs(f.args,read_source=source)
    assert x['covariance']['source_validation']=='unassessed'
    assert x['covariance']['calculation_covariance'] is None
    assert reader.validate_controlled_response_v2_extraction(f.args,x)==x


def test_float_covariance_PSD_projection_failure_is_distinct_from_source_PSD():
    from decimal import Decimal,localcontext
    f=Fixture(1)
    a,b=Fraction('0.100000000000000003'),Fraction('.3')
    # Active source positions are2 and1. Both matter; B/unused rows remain valid.
    matrix=[[Fraction('.25'),0,0,0],[0,b*b,a*b,0],[0,a*b,a*a,0],[0,0,0,Fraction('.1')]]
    with localcontext() as context:
        context.prec=100
        native='['+','.join('['+','.join(str(Decimal(Fraction(v).numerator)/Decimal(Fraction(v).denominator)) for v in row)+']' for row in matrix)+']'
    f.doc['covariance']='MATRIX';f.covariance()
    f.data[f.cov_ref]=f.data[f.cov_ref].replace(b'"MATRIX"',native.encode())
    _reanchor_covariance_tokens(f)
    x,s=f.roundtrip();assert x['covariance']['source_validation']=='valid'
    assert x['covariance']['projection_state']=='precision_invalid'
    assert s['cells']['controlled_response_difference']['value']==.002
    assert s['cells']['contrast_variance']['value'] is None


def test_source_C_underflow_and_reported_CI_rounding_keep_true_partial_ranges():
    f=Fixture(1)
    f.data[f.cov_ref]=f.data[f.cov_ref].replace(b'0.16,',b'1e-500,')
    # Preserve PSD: remove source A/C covariance, not its diagonal failure.
    f.data[f.cov_ref]=f.data[f.cov_ref].replace(b'0.03',b'0.0')
    _reanchor_covariance_tokens(f)
    x,s=f.roundtrip();assert x['covariance']['source_validation']=='valid'
    assert x['covariance']['projection_state']=='numeric_range'
    assert s['cells']['controlled_response_difference']['value']==.002
    f=Fixture(7)
    quote='Reported narrow CI: [0.10000000000000000001, 0.10000000000000000002] nmol/min.'
    f.append(quote);u=f.args['arms'][ROLES[0]]['reported_uncertainty']
    lower,upper='0.10000000000000000001','0.10000000000000000002'
    u['interval']=dict(witness=f.witness(quote,tagged=False),lower_start=quote.index(lower),lower_end=quote.index(lower)+len(lower),
        upper_start=quote.index(upper),upper_end=quote.index(upper)+len(upper))
    x,s=f.roundtrip();u=x['arms'][ROLES[0]]['reported_uncertainty']
    assert u['interval']['raw_values']==[lower,upper]
    assert u['canonical']['interval'] is None
    assert any(d['code']=='source_numeric_range' for d in u['diagnostics'])
    assert x['arms'][ROLES[0]]['measurement']['pixel_result']['native_bounds']


def test_saved_graph_partial_status_cannot_be_promoted_or_rewritten():
    f=Fixture();f.args['arms'][ROLES[3]]['measurement']['bar_selection'].update(rgb_min=[255,0,0],rgb_max=[255,0,0])
    x=f.read();a=x['arms'][ROLES[3]];g=a['graph_details']
    g['measurement']['reading_status']='unsupported';g['operand_projection']['status']='unsupported'
    a['measurement']=cp(g['measurement'])
    with pytest.raises(ExperimentalContractError,match='saved_graph_status_mismatch'):
        reader.validate_controlled_response_v2_extraction(f.args,x)


def test_reported_CI_printed_unit_conflict_is_not_graph_pixel_uncertainty():
    f=Fixture(7);quote='Reported alternate CI: [8, 12] uM/min at 95% confidence.'
    f.append(quote);u=f.args['arms'][ROLES[0]]['reported_uncertainty']
    u['interval']=dict(witness=f.witness(quote,tagged=False),lower_start=quote.index('8'),lower_end=quote.index('8')+1,
        upper_start=quote.index('12'),upper_end=quote.index('12')+2)
    x,s=f.roundtrip();unc=x['arms'][ROLES[0]]['reported_uncertainty']
    assert unc['interval']['values']==[8,12]
    assert unc['canonical']['interval'] is None
    assert any(d['code']=='source_uncertainty_unit_conflicting' for d in unc['diagnostics'])
    assert s['cells']['contrast_variance']['value']==3e-7


def test_original_v1_facades_do_not_admit_new_profile_or_perform_its_IO():
    f=Fixture()
    with pytest.raises(ExperimentalContractError,match='controlled_selection_schema_invalid'):
        shared.read_controlled_response_inputs(f.args,read_source=forbidden)
    x=f.read()
    with pytest.raises(ExperimentalContractError,match='controlled_selection_schema_invalid'):
        shared.validate_controlled_response_extraction(f.args,x)


def test_request_object_key_order_does_not_reassign_scientific_owner_roles():
    f=Fixture();original=f.read()
    f.args['arms']={role:f.args['arms'][role] for role in reversed(ROLES)}
    x=f.read()
    assert x['calculation_inputs']==original['calculation_inputs']
    assert x['representation_reconciliations']==original['representation_reconciliations']
    assert reader.validate_controlled_response_v2_extraction(f.args,x)==x


@pytest.mark.parametrize('order',['original','canonical','reversed'])
@pytest.mark.parametrize('index',[0,1,6,7,9,12])
def test_JSON_object_order_has_no_scientific_or_saved_validation_semantics(order,index):
    def reorder(value):
        if isinstance(value,dict):
            keys=list(value)
            if order=='canonical':keys=sorted(keys)
            if order=='reversed':keys.reverse()
            return {k:reorder(value[k]) for k in keys}
        if isinstance(value,list):return [reorder(v) for v in value]
        return value
    f=Fixture(index);first=f.read();original_sheet=owner.populate_controlled_response_owner(first['calculation_inputs'])
    args=reorder(f.args);x=reader.read_controlled_response_v2_inputs(args,read_source=f.source)
    assert x['calculation_inputs']==first['calculation_inputs']
    assert x['representation_reconciliations']==first['representation_reconciliations']
    assert owner.populate_controlled_response_owner(x['calculation_inputs'])==original_sheet
    assert reader.validate_controlled_response_v2_extraction(args,reorder(x))==reorder(x)
    assert reader.validate_controlled_response_v2_extraction(args,reorder(first))==reorder(first)


@pytest.mark.parametrize('dependency',['root','covariance','scale','image'])
def test_unavailable_source_science_retains_specific_partial_through_canonical_saved_JSON(dependency):
    f=Fixture(7)
    refs={'root':f.main_ref,'covariance':f.cov_ref,'image':f.args['images'][0]['source_ref'],
        'scale':f.args['arms'][ROLES[3]]['measurement']['axis']['scale']['witnesses'][0]['source_ref']}
    def source(ref,rep):
        if ref==refs[dependency]:raise EOFError('retained dependency unavailable')
        return f.source(ref,rep)
    x=reader.read_controlled_response_v2_inputs(f.args,read_source=source)
    saved=json.loads(json.dumps(x,sort_keys=True));args=json.loads(json.dumps(f.args,sort_keys=True))
    assert reader.validate_controlled_response_v2_extraction(args,saved)==saved
    assert owner.populate_controlled_response_owner(x['calculation_inputs'])['cells']['protein_condition0_response']['value']==(.008 if dependency!='root' else None)
