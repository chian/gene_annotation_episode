"""Source-bound manual endpoint selections, separate from scientific calculation.

Coordinates and ink establish source support, never biochemical identity or
baseline applicability. This pure reader has no acquisition, model, store,
controller or selected-operation binding. Physical covariance, when supplied,
is already in native-coordinate units; this reader performs no affine unit
conversion. A finite selected later point is not asymptotic completion.

Ink support uses native RGB/L values. RGBA is rendered on fixed opaque white
with nearest-integer 8-bit alpha compositing, and zero-alpha pixels never count
as ink at any threshold. Point RGB is sampled on that same rendered basis.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import hashlib
from io import BytesIO
import json
import math
import warnings

from PIL import Image, UnidentifiedImageError
from .domain import obj, identity, validate_schema, ContractError
from .literature_assay_inputs import _Sources
from .literature_experimental_contracts import ExperimentalContractError

INPUT_VERSION = 'a105_endpoint_signal_selection_v1'
EXTRACTION_VERSION = 'a105_endpoint_signal_inputs_v1'
POINT_ORDER = ('initial', 'baseline_at_addition', 'late')
CONTEXT_FIELDS = ('subject','organism','genotype','construct','preparation','partners',
    'experiment','condition','endpoint','normalization','intended_variable',
    'functional_assertion','correction_discussion','limitations','repetition',
    'experimental_system','expression_host','sampling_window')
RELATIONSHIPS = {
    'axis_scale': ('common_affine','nonlinear','unknown','conflicting'),
    'ordinate_direction': ('increases_upward','increases_downward','unknown','conflicting'),
    'measurement_stage': ('endpoint_amplitude','initial_rate','other','unknown','conflicting'),
    'correction_stage': ('not_applied','already_applied','unknown','conflicting'),
    'baseline_basis': ('source_displayed_extrapolation','matched_control','new_fit','unknown','conflicting'),
    'baseline_applicability': ('supported','explicit_conditional_scenario','unsupported','unknown','conflicting'),
    'fast_component_completion': ('supported','explicit_conditional_scenario','unsupported','unknown','conflicting'),
    'additive_interpretation': ('nonnegative_additive','signed_decomposition','unknown','conflicting'),
    'arrangement': ('single_preparation','replacement','coexistence','not_applicable','unknown','conflicting')}
_COMPONENTS = ('total_amplitude','corrected_amplitude','additional_amplitude','retained_fraction','additional_fraction')
ALL_COMPONENTS = _COMPONENTS + tuple(x+'_variance' for x in _COMPONENTS)
_BASES = ('joint_manual_reading_error','joint_physical_ordinate_estimates')
_TEXT = {'type':'string','minLength':1}
_INT = {'type':'integer','minimum':0}

def _nullable(s): return {'anyOf':[deepcopy(s),{'type':'null'}]}
def _array(s, **kw): return {'type':'array','items':deepcopy(s),**kw}
def _enum(v): return {'enum':list(v)}
def _const(v): return {'const':v}
def _box_schema(): return _array(_INT,minItems=4,maxItems=4)
def _witness_schema(enriched=False):
    return obj({'source_ref':deepcopy(_TEXT),'representation':_enum(('original','text')),
        'start':deepcopy(_INT),'end':{'type':'integer','minimum':1},'quote':deepcopy(_TEXT),
        **({'artifact_ref':deepcopy(_TEXT)} if enriched else {})})
def _interpretation_schema(values,enriched=False):
    return obj({**({'kind':_const('source_interpretation')} if enriched else {}),
        'value':_enum(values),'witnesses':_array(_witness_schema(enriched)),
        'image_regions':_array(_box_schema())})
def _sampling_schema():
    return obj({'image_region':_box_schema(),
        'meaning':_const('finite_selected_late_point_no_physical_time_extracted')})
def _point_schema():
    return obj({'x':deepcopy(_INT),'y':deepcopy(_INT),
        'y_enclosure':_nullable(_array(_INT,minItems=2,maxItems=2)),
        'support_region':_box_schema(),'maximum_rgb':{'type':'integer','minimum':0,'maximum':255},
        'image_witness':obj({'region':_box_schema(),'meaning':_enum(('initial_trace',
            'displayed_baseline_at_addition','selected_late_trace'))}),
        'semantic_witnesses':_array(_witness_schema()),'physical_estimate_owner':_nullable(_witness_schema())})
def endpoint_signal_population_schema():
    context={r:_nullable(_witness_schema()) for r in CONTEXT_FIELDS}
    context['sampling_window']=_nullable(_sampling_schema())
    image=obj({'source_ref':deepcopy(_TEXT),
        'expected_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
        'width':{'type':'integer','minimum':1},'height':{'type':'integer','minimum':1},
        'panel_region':_box_schema(),'image_origin':_enum(('published','synthetic')),
        'points':obj({r:_nullable(_point_schema()) for r in POINT_ORDER})})
    return obj({'version':_const(INPUT_VERSION),'source_ref':deepcopy(_TEXT),
        'source_kind':_enum(('primary_source','retained_extraction','synthetic_fixture')),
        'context':obj(context),'relationships':obj({r:_interpretation_schema(v) for r,v in RELATIONSHIPS.items()}),
        'image':_nullable(image),'covariance_source_ref':_nullable(_TEXT),
        'requested_cells':_array(_enum(ALL_COMPONENTS),uniqueItems=True)})
def _exact_schema():
    return obj({'numerator':{'type':'string','pattern':'^-?[0-9]+$'},
        'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}})
def _error_schema(): return obj({'code':deepcopy(_TEXT),'field':deepcopy(_TEXT)})
def covariance_source_schema():
    return obj({'version':_const('a105_endpoint_signal_covariance_v1'),'basis':_enum(_BASES),
        'primitive_order':_const(list(POINT_ORDER)),
        'primitive_owners':_array(_TEXT,minItems=3,maxItems=3),
        'primitive_units':_const(['native_ordinate_pixel']*3),
        'covariance':_array(_array({'type':'number'},minItems=3,maxItems=3),minItems=3,maxItems=3),
        'variance_status':_enum(('known','estimated','unknown')),
        'origin':_enum(('source_reported','source_derived','synthetic')),
        'provenance_witnesses':_array(_witness_schema()),
        'native_coordinate_basis_witnesses':_array(_witness_schema()),
        'coordinate_units_status':_const('already_in_declared_native_coordinate_units')})
def endpoint_signal_extraction_schema():
    witness=_witness_schema(True)
    context={r:_nullable(obj({'value':deepcopy(_TEXT),'witness':witness})) for r in CONTEXT_FIELDS}
    context['sampling_window']=_nullable(obj({
        'value':_const('finite_selected_late_point_no_physical_time_extracted'),
        'witness':obj({**_sampling_schema()['properties'],'source_ref':deepcopy(_TEXT),
            'artifact_ref':deepcopy(_TEXT),'authentication':_const('source_bytes_and_geometry_only')})}))
    point=obj({'selection':_point_schema(),'coordinate_owner':deepcopy(_TEXT),
        'physical_estimate_owner':_nullable(_TEXT),'x':deepcopy(_INT),'y':deepcopy(_INT),
        'y_enclosure':_nullable(_array(_INT,minItems=2,maxItems=2)),
        'support':obj({'qualifying_pixel_count':deepcopy(_INT),
            'point_rgb':_array(_INT,minItems=3,maxItems=3),
            'authentication':_const('source_bytes_geometry_and_ink_only')}),
        'semantic_witnesses':_array(witness),'physical_owner_witness':_nullable(witness),
        'origin':_enum(('graph_derived_manual','synthetic')),'error':_nullable(_error_schema())})
    source=obj({'source_ref':deepcopy(_TEXT),'representation':_enum(('original','text')),
        'artifact_ref':_nullable(_TEXT),'sha256':_nullable(_TEXT),'error':_nullable(_error_schema())})
    return obj({'version':_const(EXTRACTION_VERSION),'arguments':endpoint_signal_population_schema(),
        'source_ref':deepcopy(_TEXT),'source_kind':_enum(('primary_source','retained_extraction','synthetic_fixture')),
        'context':obj(context),'context_errors':obj({r:_nullable(_error_schema()) for r in CONTEXT_FIELDS}),
        'relationships':obj({r:obj({'interpretation':_nullable(_interpretation_schema(v,True)),
            'error':_nullable(_error_schema())}) for r,v in RELATIONSHIPS.items()}),
        'image':_nullable(obj({'source_ref':deepcopy(_TEXT),'artifact_ref':_nullable(_TEXT),'sha256':_nullable(_TEXT),
            'width':_nullable(_INT),'height':_nullable(_INT),'format':_nullable(_enum(('PNG','JPEG'))),
            'mode':_nullable(_enum(('RGB','RGBA','L'))),'panel_region':_box_schema(),'error':_nullable(_error_schema())})),
        'points':obj({r:obj({'selection':_nullable(_point_schema()),'observation':_nullable(point),
            'error':_nullable(_error_schema())}) for r in POINT_ORDER}),
        'covariance':_nullable(obj({'source_ref':deepcopy(_TEXT),'artifact_ref':_nullable(_TEXT),'sha256':_nullable(_TEXT),
            'model':_nullable(covariance_source_schema()),
            'exact_covariance':_nullable(_array(_array(_exact_schema(),minItems=3,maxItems=3),minItems=3,maxItems=3)),
            'error':_nullable(_error_schema())})),
        'source_artifacts':_array(source),
        'input_origins':_array(_enum(('graph_derived_manual','reported','derived','synthetic')),uniqueItems=True)})

def _fail(code,field): raise ExperimentalContractError(code,field)
def _schema_check(value,schema,field):
    try: validate_schema(value,schema)
    except (ContractError,ValueError,TypeError,OverflowError) as error:
        raise ExperimentalContractError('closed_endpoint_schema_required',field) from error
    def finite(v,p):
        if isinstance(v,float) and not math.isfinite(v): _fail('finite_number_required',p)
        if isinstance(v,dict):
            for k,x in v.items(): finite(x,p+'.'+k)
        elif isinstance(v,list):
            for i,x in enumerate(v): finite(x,f'{p}[{i}]')
    finite(value,field)
def _error(error,field):
    return {'code':str(getattr(error,'code','source_read_failed')),
        'field':str(getattr(error,'field',field))}
def _inside(inner,outer):
    return (outer[0]<=inner[0]<inner[2]<=outer[2] and outer[1]<=inner[1]<inner[3]<=outer[3])
def _geometry(box,outer,field):
    if not _inside(box,outer): _fail('image_region_out_of_bounds',field)
def _prevalidate(args):
    _schema_check(args,endpoint_signal_population_schema(),'arguments')
    image=args['image']
    if image is not None:
        panel=image['panel_region'];_geometry(panel,[0,0,image['width'],image['height']],'image.panel_region')
        for role,p in image['points'].items():
            if p is None: continue
            field='image.points.'+role
            if not panel[0]<=p['x']<panel[2] or not panel[1]<=p['y']<panel[3]: _fail('point_outside_panel',field)
            _geometry(p['support_region'],panel,field+'.support_region')
            _geometry(p['image_witness']['region'],panel,field+'.image_witness')
            if not _inside([p['x'],p['y'],p['x']+1,p['y']+1],p['support_region']): _fail('point_outside_support',field)
            if not _inside([p['x'],p['y'],p['x']+1,p['y']+1],p['image_witness']['region']): _fail('point_outside_witness',field)
            if p['y_enclosure'] is not None and not (panel[1]<=p['y_enclosure'][0]<=p['y']<=p['y_enclosure'][1]<panel[3]):
                _fail('invalid_reading_enclosure',field)
            expected=dict(zip(POINT_ORDER,('initial_trace','displayed_baseline_at_addition','selected_late_trace')))[role]
            if p['image_witness']['meaning']!=expected: _fail('point_role_mismatch',field)
        regions=[v for r in args['relationships'].values() for v in r['image_regions']]
        if args['context']['sampling_window'] is not None: regions.append(args['context']['sampling_window']['image_region'])
        for region in regions: _geometry(region,panel,'image_region')
    elif any(r['image_regions'] for r in args['relationships'].values()) or args['context']['sampling_window'] is not None:
        _fail('image_context_without_image','image')

class _EndpointSources(_Sources):
    def __init__(self,callback): super().__init__(callback);self.artifacts={}
    def source(self,reference,representation):
        key=(reference,representation)
        try:
            source=super().source(reference,representation)
            self.artifacts[key]={'source_ref':reference,'representation':representation,
                'artifact_ref':source['artifact_ref'],'sha256':hashlib.sha256(source['content']).hexdigest(),'error':None}
            return source
        except Exception as error:
            self.artifacts[key]={'source_ref':reference,'representation':representation,
                'artifact_ref':None,'sha256':None,'error':_error(error,'source')}
            raise

def _image(sources,spec):
    record={'source_ref':spec['source_ref'],'artifact_ref':None,'sha256':None,
        'width':None,'height':None,'format':None,'mode':None,'panel_region':deepcopy(spec['panel_region']),'error':None}
    frame=None
    try:
        src=sources.source(spec['source_ref'],'original');raw=src['content']
        record.update(artifact_ref=src['artifact_ref'],sha256=hashlib.sha256(raw).hexdigest())
        if record['sha256']!=spec['expected_sha256']: _fail('image_sha256_mismatch','image')
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as im:
                if im.format not in ('PNG','JPEG'): _fail('unsupported_image_format','image')
                if im.mode not in ('RGB','RGBA','L'): _fail('unsupported_image_mode','image')
                if getattr(im,'n_frames',1)!=1: _fail('single_frame_required','image')
                if im.size!=(spec['width'],spec['height']): _fail('image_dimensions_mismatch','image')
                if im.format=='PNG' and not raw.endswith(b'\x00\x00\x00\x00IEND\xaeB\x60\x82'):
                    _fail('malformed_image','image')
                record.update(width=im.width,height=im.height,format=im.format,mode=im.mode)
                im.verify()
            with Image.open(BytesIO(raw)) as im:
                if im.getexif().get(274,1)!=1: _fail('unsupported_image_orientation','image')
                im.load()
                # Keep alpha until support counting. Dropping it would let an
                # invisible dark pixel authenticate an alleged visible trace.
                frame=im.copy() if im.mode=='RGBA' else im.convert('RGB')
    except (ExperimentalContractError,ContractError,UnidentifiedImageError,OSError,SyntaxError,ValueError,
            Image.DecompressionBombError,Image.DecompressionBombWarning) as error:
        record['error']=_error(error,'image')
    except Exception as error: record['error']=_error(error,'image')
    return record,frame

def _interpretation(sources,value,image):
    witnesses=[sources.witness(w,'relationship.witness') for w in value['witnesses']]
    if value['image_regions'] and (image is None or image['error']): _fail('image_witness_unavailable','relationship')
    identities={(w['source_ref'],w['artifact_ref'],w['representation'],w['start'],w['end']) for w in witnesses}
    identities.update(tuple(region) for region in value['image_regions'])
    required=0 if value['value']=='unknown' else 2 if value['value']=='conflicting' else 1
    if len(identities)<required: _fail('interpretation_witness_required','relationship')
    return {'kind':'source_interpretation','value':value['value'],'witnesses':witnesses,
        'image_regions':deepcopy(value['image_regions'])}

def _point(sources,role,spec,image,frame,image_origin):
    if image['error'] or frame is None: _fail('image_unavailable','points.'+role)
    witnesses=[sources.witness(w,'points.'+role) for w in spec['semantic_witnesses']]
    owner_w=(sources.witness(spec['physical_estimate_owner'],'physical_estimate_owner') if spec['physical_estimate_owner'] else None)
    l,t,r,b=spec['support_region'];pixels=frame.load();threshold=spec['maximum_rgb']
    def rendered(pixel):
        if frame.mode!='RGBA': return pixel
        alpha=pixel[3]
        # Fixed white basis, independent of a viewer's background. Retaining
        # the alpha test also excludes invisible pixels when threshold=255.
        return tuple((c*alpha+255*(255-alpha)+127)//255 for c in pixel[:3])
    count=sum((frame.mode!='RGBA' or pixels[x,y][3]>0) and max(rendered(pixels[x,y]))<=threshold
        for x in range(l,r) for y in range(t,b))
    if count==0: _fail('point_support_ink_unavailable','points.'+role)
    coordinate_owner=identity('endpoint_coordinate',{'source_ref':image['source_ref'],'artifact_ref':image['artifact_ref'],
        'x':spec['x'],'y':spec['y']})
    physical_owner=(identity('endpoint_physical_estimate',owner_w) if owner_w else None)
    return {'selection':deepcopy(spec),'coordinate_owner':coordinate_owner,'physical_estimate_owner':physical_owner,
        'x':spec['x'],'y':spec['y'],'y_enclosure':deepcopy(spec['y_enclosure']),
        'support':{'qualifying_pixel_count':count,'point_rgb':list(rendered(pixels[spec['x'],spec['y']])),
            'authentication':'source_bytes_geometry_and_ink_only'},
        'semantic_witnesses':witnesses,'physical_owner_witness':owner_w,
        'origin':'synthetic' if image_origin=='synthetic' else 'graph_derived_manual','error':None}

def _exact(q):
    q=Fraction(q);return {'numerator':str(q.numerator),'denominator':str(q.denominator)}
def _fraction(q): return Fraction(int(q['numerator']),int(q['denominator']))
def _psd(matrix):
    if any(matrix[i][j]!=matrix[j][i] for i in range(3) for j in range(3)):
        _fail('symmetric_covariance_required','covariance')
    if any(matrix[i][i]<0 for i in range(3)): _fail('positive_semidefinite_covariance_required','covariance')
    if any(matrix[i][i]*matrix[j][j]-matrix[i][j]**2<0 for i in range(3) for j in range(i)):
        _fail('positive_semidefinite_covariance_required','covariance')
    a,b,c=matrix[0];_,d,e=matrix[1];_,_,f=matrix[2]
    if a*d*f+2*b*c*e-a*e*e-d*c*c-f*b*b<0: _fail('positive_semidefinite_covariance_required','covariance')

def _covariance(sources,reference,points):
    record={'source_ref':reference,'artifact_ref':None,'sha256':None,'model':None,'exact_covariance':None,'error':None}
    try:
        src=sources.source(reference,'original');raw=src['content']
        record.update(artifact_ref=src['artifact_ref'],sha256=hashlib.sha256(raw).hexdigest())
        def pairs(items):
            d={}
            for k,v in items:
                if k in d: _fail('duplicate_json_key','covariance')
                d[k]=v
            return d
        def constant(_): _fail('finite_number_required','covariance')
        try:
            model=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_float=Decimal,parse_constant=constant)
        except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as error:
            raise ExperimentalContractError('malformed_covariance_source','covariance') from error
        if not isinstance(model,dict) or 'covariance' not in model:
            _fail('closed_endpoint_schema_required','covariance')
        raw_matrix=model['covariance']
        if (not isinstance(raw_matrix,list) or len(raw_matrix)!=3 or
                any(not isinstance(row,list) or len(row)!=3 for row in raw_matrix)):
            _fail('three_by_three_covariance_required','covariance')
        if any(type(x) not in (int,Decimal) for row in raw_matrix for x in row):
            _fail('finite_number_required','covariance')
        # Decimal preserves source numeric tokens for exact symmetry and PSD.
        matrix=[[Fraction(x) for x in row] for row in model['covariance']]
        projected=deepcopy(model)
        projected['covariance']=[[float(x) for x in row] for row in matrix]
        _schema_check(projected,covariance_source_schema(),'covariance')
        _psd(matrix)
        physical=model['basis']=='joint_physical_ordinate_estimates'
        key='physical_estimate_owner' if physical else 'coordinate_owner'
        owners=[points[r]['observation'][key] if points[r]['observation'] else None for r in POINT_ORDER]
        if any(x is None for x in owners) or owners!=model['primitive_owners']:
            _fail('covariance_owner_mismatch','covariance.primitive_owners')
        for field in ('provenance_witnesses','native_coordinate_basis_witnesses'):
            for w in model[field]: sources.witness(w,'covariance.'+field)
        if model['origin']!='synthetic' and not model['provenance_witnesses']:
            _fail('covariance_provenance_required','covariance')
        if physical and not model['native_coordinate_basis_witnesses']:
            _fail('native_coordinate_basis_witness_required','covariance')
        for i in range(3):
            for j in range(i):
                if owners[i]==owners[j]:
                    if points[POINT_ORDER[i]]['observation']['y']!=points[POINT_ORDER[j]]['observation']['y']:
                        _fail('shared_owner_value_mismatch','covariance')
                    if matrix[i]!=matrix[j] or any(row[i]!=row[j] for row in matrix):
                        _fail('shared_owner_covariance_mismatch','covariance')
        record.update(model=projected,exact_covariance=[[_exact(x) for x in row] for row in matrix])
    except Exception as error: record['error']=_error(error,'covariance')
    return record

def read_endpoint_signal_inputs(arguments, *, read_source):
    """Authenticate selections once. Preserve unrelated partials on dependency errors.

    The host callback authorizes actual received/scoped source bytes and returns
    exactly artifact_ref/content. All scientific meanings remain witnessed
    interpretations. Covariance wire values must already have the declared
    native-coordinate units; no calibration or physical time is inferred.
    """
    _prevalidate(arguments);args=deepcopy(arguments);sources=_EndpointSources(read_source)
    try: sources.source(args['source_ref'],'original')
    except Exception: pass  # Original dependency error remains in source_artifacts.
    image=frame=None
    if args['image'] is not None: image,frame=_image(sources,args['image'])
    context={};errors={};relationships={};points={}
    try:
        for name,value in args['context'].items():
            context[name]=None;errors[name]=None
            if value is None: continue
            try:
                if name=='sampling_window':
                    if image is None or image['error']: _fail('image_witness_unavailable','context.sampling_window')
                    context[name]={'value':value['meaning'],'witness':{**deepcopy(value),'source_ref':image['source_ref'],
                        'artifact_ref':image['artifact_ref'],'authentication':'source_bytes_and_geometry_only'}}
                else:
                    w=sources.witness(value,'context.'+name);context[name]={'value':w['quote'],'witness':w}
            except Exception as error: errors[name]=_error(error,'context.'+name)
        for name,value in args['relationships'].items():
            try: relationships[name]={'interpretation':_interpretation(sources,value,image),'error':None}
            except Exception as error: relationships[name]={'interpretation':None,'error':_error(error,'relationships.'+name)}
        for role in POINT_ORDER:
            spec=args['image']['points'][role] if args['image'] else None
            points[role]={'selection':deepcopy(spec),'observation':None,'error':None}
            if spec is not None:
                try: points[role]['observation']=_point(sources,role,spec,image,frame,args['image']['image_origin'])
                except Exception as error: points[role]['error']=_error(error,'points.'+role)
        covariance=(_covariance(sources,args['covariance_source_ref'],points) if args['covariance_source_ref'] else None)
    finally:
        if frame is not None: frame.close()
    origins=list(dict.fromkeys([p['observation']['origin'] for p in points.values() if p['observation']]))
    if any(x is not None for x in context.values()) and args['source_kind']!='synthetic_fixture': origins.append('reported')
    if covariance and covariance['model'] and covariance['model']['origin'] in ('source_reported','source_derived'):
        origins.append('reported' if covariance['model']['origin']=='source_reported' else 'derived')
    if args['source_kind']=='synthetic_fixture' or covariance and covariance['model'] and covariance['model']['origin']=='synthetic':
        origins.append('synthetic')
    result={'version':EXTRACTION_VERSION,'arguments':args,'source_ref':args['source_ref'],'source_kind':args['source_kind'],
        'context':context,'context_errors':errors,'relationships':relationships,'image':image,'points':points,
        'covariance':covariance,'source_artifacts':list(sources.artifacts.values()),'input_origins':list(dict.fromkeys(origins))}
    return validate_endpoint_signal_extraction(result)

def validate_endpoint_signal_extraction(extraction):
    """Validate detached custody shape/relationships, without source IO or re-reading."""
    _schema_check(extraction,endpoint_signal_extraction_schema(),'extraction')
    args=extraction['arguments'];_prevalidate(args)
    if extraction['source_ref']!=args['source_ref'] or extraction['source_kind']!=args['source_kind']:
        _fail('extraction_source_mismatch','extraction')
    def selected_witness(retained,selected):
        return {k:v for k,v in retained.items() if k!='artifact_ref'}==selected
    for name,entry in extraction['context'].items():
        if entry is None: continue
        selected=args['context'][name]
        if selected is None or extraction['context_errors'][name] is not None:
            _fail('extraction_context_mismatch','context.'+name)
        if name=='sampling_window':
            if (entry['value']!=selected['meaning'] or
                    entry['witness']['image_region']!=selected['image_region']):
                _fail('extraction_context_mismatch','context.'+name)
        elif entry['value']!=selected['quote'] or not selected_witness(entry['witness'],selected):
            _fail('extraction_context_mismatch','context.'+name)
    for name,entry in extraction['relationships'].items():
        value=entry['interpretation']
        if value is not None and (entry['error'] is not None or value['value']!=args['relationships'][name]['value'] or
                value['image_regions']!=args['relationships'][name]['image_regions']):
            _fail('extraction_relationship_mismatch','relationships.'+name)
        if value is not None and ([{k:v for k,v in w.items() if k!='artifact_ref'} for w in value['witnesses']]
                !=args['relationships'][name]['witnesses']):
            _fail('extraction_relationship_mismatch','relationships.'+name)
    for role,entry in extraction['points'].items():
        selected=args['image']['points'][role] if args['image'] else None
        if entry['selection']!=selected: _fail('extraction_point_mismatch','points.'+role)
        p=entry['observation']
        if p is None: continue
        if selected is None or p['selection']!=selected or any(p[k]!=selected[k] for k in ('x','y','y_enclosure')):
            _fail('extraction_point_mismatch','points.'+role)
        if entry['error'] is not None or p['support']['qualifying_pixel_count']<1:
            _fail('extraction_point_mismatch','points.'+role)
        image=extraction['image']
        if image is None or image['error'] is not None or p['coordinate_owner']!=identity('endpoint_coordinate',{
                'source_ref':image['source_ref'],'artifact_ref':image['artifact_ref'],'x':p['x'],'y':p['y']}):
            _fail('extraction_owner_mismatch','points.'+role)
        if ([{k:v for k,v in w.items() if k!='artifact_ref'} for w in p['semantic_witnesses']]
                !=selected['semantic_witnesses']):
            _fail('extraction_point_mismatch','points.'+role)
        owner=p['physical_owner_witness']
        if (owner is None)!=(selected['physical_estimate_owner'] is None):
            _fail('extraction_owner_mismatch','points.'+role)
        if owner is not None and (not selected_witness(owner,selected['physical_estimate_owner']) or
                p['physical_estimate_owner']!=identity('endpoint_physical_estimate',owner)):
            _fail('extraction_owner_mismatch','points.'+role)
        if owner is None and p['physical_estimate_owner'] is not None:
            _fail('extraction_owner_mismatch','points.'+role)
    cov=extraction['covariance']
    if cov and cov['error'] is None:
        if cov['model'] is None or cov['exact_covariance'] is None: _fail('covariance_record_incomplete','covariance')
        matrix=[[_fraction(q) for q in row] for row in cov['exact_covariance']];_psd(matrix)
        basis=cov['model']['basis'];key='physical_estimate_owner' if basis==_BASES[1] else 'coordinate_owner'
        owners=[extraction['points'][r]['observation'][key] if extraction['points'][r]['observation'] else None for r in POINT_ORDER]
        if owners!=cov['model']['primitive_owners']: _fail('covariance_owner_mismatch','covariance')
        if any(float(_fraction(q))!=cov['model']['covariance'][i][j]
                for i,row in enumerate(cov['exact_covariance']) for j,q in enumerate(row)):
            _fail('covariance_exact_projection_mismatch','covariance')
        for i in range(3):
            for j in range(i):
                if owners[i]==owners[j]:
                    if extraction['points'][POINT_ORDER[i]]['observation']['y']!=extraction['points'][POINT_ORDER[j]]['observation']['y']:
                        _fail('shared_owner_value_mismatch','covariance')
                    if matrix[i]!=matrix[j] or any(row[i]!=row[j] for row in matrix):
                        _fail('shared_owner_covariance_mismatch','covariance')
    return deepcopy(extraction)

__all__=['INPUT_VERSION','EXTRACTION_VERSION','POINT_ORDER','CONTEXT_FIELDS','RELATIONSHIPS',
    'endpoint_signal_population_schema','endpoint_signal_extraction_schema','covariance_source_schema',
    'read_endpoint_signal_inputs','validate_endpoint_signal_extraction']
