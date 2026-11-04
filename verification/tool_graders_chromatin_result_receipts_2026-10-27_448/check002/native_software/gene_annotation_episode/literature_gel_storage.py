"""Selected gel custody and exact-key native projections, without an episode loop.

Saved access authenticates the original selected outcome; it does not decode the
image, recount pixels, rerun a numerical calculator or compose model prose.
"""
from __future__ import annotations

from copy import deepcopy as cp
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from jsonschema import Draft202012Validator, ValidationError

from .communication import plain
from .domain import ContractError, canonical, identity
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .literature_ratio_source_storage import LiteratureRatioSourceRepository
from . import literature_gel_inputs as inputs
from . import literature_gel_calculations as calculations
from .literature_gel_native_contracts import (
    PROVIDER, OPERATION, FACT_SOURCE, VERSION, FACT_VERSION, COMPONENTS, VIEWS,
    RAW_COMPONENTS, CORRECTED_COMPONENT, LANE_COMPONENTS, COMPARISON_COMPONENTS,
    LANE_MEANINGS, REQUEST_COMPONENTS, REQUEST_VIEWS, REQUEST_KEYS,
    gel_population_schema, gel_cells_schema, validate_population_arguments,
)


_PAYLOAD_FIELDS={'version','arguments','extraction','sheet','component_roster','meanings','semantic_bindings',
    'input_source_ref','input_artifact_ref','direct_input_source_refs','input_source_refs','source_associations',
    'implementation_descriptor','evidence_origin'}


def _sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value).encode()).hexdigest()


def _unique(values):
    return list(dict.fromkeys(values))


def _check(value,schema,code):
    try:
        Draft202012Validator(schema).validate(value);canonical(value)
    except (ValidationError,ValueError,TypeError) as error:
        raise ContractError(code) from error


def implementation_descriptor(*,evidence_origin='reported_source'):
    if evidence_origin not in ('reported_source','synthetic_fixture'):
        raise ContractError('gel_native_evidence_profile_invalid')
    names=('literature_gel_inputs.py','literature_gel_calculations.py','literature_gel_native_contracts.py',
        'literature_gel_storage.py','literature_gel_render.py','literature_assay_inputs.py',
        'literature_experimental_contracts.py','literature_rate_storage.py','literature_ratio_source_storage.py',
        'literature_binding_interaction_render.py','communication.py','domain.py','state.py',
        'episode_bindings.py','episode_receipts.py')
    return {'version':'gel_native_implementation_v1','provider':PROVIDER,'record_version':VERSION,
        'evidence_origin':evidence_origin,'native_schema_sha256':_sha(gel_cells_schema()),
        'pillow_version':inputs.PILLOW_VERSION,'jsonschema_version':importlib.metadata.version('jsonschema'),
        'modules':{name:_sha(Path(__file__).with_name(name).read_bytes()) for name in names}}


def _token(value):
    return quote(value,safe='-._~',encoding='utf8',errors='strict')


def _witnesses(selection):
    yield from inputs._witnesses(selection)


def _source_pairs(selection):
    return list(dict.fromkeys([(selection['image']['source_ref'],'original')]+
        [(w['source_ref'],w['representation']) for w in _witnesses(selection)]))


def _numeric_locations(extraction):
    image=extraction['selection']['image'];result=[]
    for assignment in extraction['selection']['roi_assignments']:
        for lane in assignment['lanes']:
            for box in [lane['background'],lane['whole_lane'],*[b['region'] for b in lane['bands']]]:
                kind='image_region' if inputs._box_reason(box,image['width'],image['height']) is None else 'unresolved'
                row={'kind':kind,'source_ref':image['source_ref']}
                if kind=='image_region':row['region']=cp(box)
                result.append(row)
    # Gel numerical operands come from these image regions. A numeral inside a
    # scientific context witness (concentration, pH, construct length, etc.) is
    # not thereby an unrequested intensity/calibration operand. Witness/source
    # handles are hidden separately; do not erase returned scientific meanings.
    return [json.loads(row) for row in sorted(set(canonical(v) for v in result))]


def _reference_value(source_ref,accession,label,anchor=None):
    label=' '.join(label.split())
    return {'reference_type':'literature_result','source_ref':source_ref,'accession':accession,
        'label':label if len(label)<=512 else label[:509]+'...','sequence_ref':None,'molecule':None,
        'length':None,'term_refs':[],'context_refs':[],'anchor':anchor}


def _meaning_specs(extraction):
    """Actual saved interpretations and witnesses; no scientific inference."""
    selected=extraction['selection'];actual={canonical({k:v for k,v in w.items() if k!='artifact_ref'}):w
        for w in extraction['authenticated_witnesses']}
    bindings={};records={}
    def add(value,category,locations,*,preview=False):
        reference=identity('reference',{'origin':'tool','record':value})
        if reference in records and canonical(records[reference])!=canonical(value):
            raise ContractError('gel_native_semantic_binding_conflict')
        records[reference]=value
        bindings[reference]={'record_ref':reference,'category':category,
            'canonical_witness_locations':cp(locations),'label_preview':preview}
        return reference
    def meaning(value,key):
        witness_refs=[];locations=[];full=[]
        for nomination in value['witnesses']:
            witness=actual.get(canonical(nomination))
            if witness is None:raise ContractError('gel_native_witness_binding_mismatch')
            location={k:witness[k] for k in ('source_ref','artifact_ref','start','end')}
            location['kind']='utf8_span';locations.append(location);full.append(witness)
            anchor={k:witness[k] for k in ('source_ref','artifact_ref','start','end','quote')}
            # Store display anchors have a bounded quote field. Authentication
            # and exact full spans remain in the private extraction/binding;
            # a long scientific passage is still a valid reader input.
            record=_reference_value(witness['source_ref'],identity('gel_source_witness',witness),witness['quote'],
                anchor if len(witness['quote'])<=16000 else None)
            witness_refs.append(add(record,'source_witness',[location],preview=len(' '.join(witness['quote'].split()))>512))
        reference=None
        if value['state']=='known':
            if not full:raise ContractError('gel_native_known_meaning_without_witness')
            anchor=None
            # A literal label can have a tighter authenticated location than a
            # broad source passage. Other interpretations keep all witnesses.
            for witness in full:
                if witness['quote'].count(value['value'])==1:
                    start=witness['start']+len(witness['quote'][:witness['quote'].index(value['value'])].encode())
                    anchor={'source_ref':witness['source_ref'],'artifact_ref':witness['artifact_ref'],
                        'start':start,'end':start+len(value['value'].encode()),'quote':value['value']};break
            label_locations=([{'kind':'utf8_span',**{k:anchor[k] for k in ('source_ref','artifact_ref','start','end')}}]
                if anchor is not None else locations)
            record=_reference_value(full[0]['source_ref'],identity('gel_scientific_meaning',{'key':key,'meaning':value,'witnesses':full}),
                value['value'],anchor if anchor is not None and len(anchor['quote'])<=16000 else None)
            # An anchor may belong to a different supporting source.
            if anchor is not None:record['source_ref']=anchor['source_ref']
            reference=add(record,'scientific_meaning',label_locations,preview=len(' '.join(value['value'].split()))>512)
        return {'state':value['state'],'value_ref':reference,'witness_refs':witness_refs}
    global_meanings={name:meaning(selected['context'][name],'global:'+name) for name in inputs.CONTEXT_FIELDS}
    lanes=[]
    for lane in selected['lanes']:
        lanes.append({key:cp(lane[key]) for key in ('lane_id','observation_id')})
        lanes[-1].update({name:meaning(lane[name],'lane:'+_token(lane['lane_id'])+':'+name) for name in LANE_MEANINGS})
    return {'global':global_meanings,'lanes':lanes},bindings,records


def _cell(source_cell):
    value={k:cp(v) for k,v in source_cell.items() if k!='dependencies'}
    value.update(lower=None,upper=None,sensitivity=None)
    return value


def _scalar(value,formula,unit,*,reason=None,exact=None,measured=False):
    if exact is None and value is not None:exact={'numerator':str(value),'denominator':'1'}
    projection=None
    if value is None and exact is not None:
        number=Fraction(int(exact['numerator']),int(exact['denominator']))
        try:
            value=float(number)
            if not math.isfinite(value) or value==0 and number!=0:value=None;projection='numerical_projection_range'
        except OverflowError:projection='numerical_projection_range'
    return {'value':value,'exact':cp(exact),'lower':None,'upper':None,'unit':unit,'formula':formula,
        'status':'unavailable' if exact is None else 'measured' if measured else 'calculated',
        'unavailable_reason':reason,'projection_reason':projection,'qualifications':[],
        'sampling_standard_uncertainty':None,'confidence_interval':None,'sensitivity':None}


def _component_rows(payload,sheet_ref):
    selection=payload['arguments']['selection'];extraction=payload['extraction'];sheet=payload['sheet']
    selected_lanes={r['lane_id']:r for r in selection['lanes']}
    extracted={a['assignment_id']:a for a in extraction['assignments']}
    science_lanes={r['lane_id']:r for r in payload['meanings']['lanes']}
    original_assignments={a['assignment_id']:a for a in selection['roi_assignments']}
    assignments={a['assignment_id']:a for a in sheet['assignments']}
    locations=_numeric_locations(extraction);rows=[]
    def wrapped(assignment,deps):
        return [{'assignment_id':assignment,'source_dependency':cp(d)} for d in deps]
    def dep(lane,region,background=None):
        image=selection['image']
        return {'source_ref':image['source_ref'],'artifact_ref':image['artifact_ref'],
            'image_byte_sha256':image['byte_sha256'],'lane_id':lane,'signal_region':cp(region),'background_region':cp(background)}
    def emit(key,view,component,cell,deps,*,assignment=None,lane=None,region=None,band=None):
        numeric_ids=_unique(d['source_dependency']['lane_id'] for d in deps)
        roles={role:sheet['comparison'][role+'_lane_id'] for role in ('baseline','protein','competitor')}
        scientific_ids=(_unique(v for v in roles.values() if v is not None) if view in ('comparison','sensitivity') else numeric_ids)
        if lane is not None and lane not in scientific_ids:scientific_ids.append(lane)
        involved=_unique(d['assignment_id'] for d in deps)
        if assignment is not None and assignment not in involved:involved.append(assignment)
        methods=[]
        for d in deps:
            source=d['source_dependency']
            if source['background_region'] is None:continue
            original=next(r for r in original_assignments[d['assignment_id']]['lanes'] if r['lane_id']==source['lane_id'])
            record={'assignment_id':d['assignment_id'],'lane_id':source['lane_id'],
                'background_method':original.get('background_method','mean'),
                'method_basis':'explicit_v2_nomination' if 'background_method' in original else 'v1_mean_definition'}
            if record not in methods:methods.append(record)
        context={'global':cp(payload['meanings']['global']),'lanes':[cp(science_lanes[i]) for i in scientific_ids],
            'comparison_roles':roles if view in ('comparison','sensitivity') else None,
            'interpretation':cp(sheet['assignments'][0]['scientific_interpretation']) if view in ('comparison','sensitivity') else None,
            **{k:cp(sheet[k]) for k in ('sampling_uncertainty','detector_response_calibration','unimplemented_quantities','independent_preparation_count')},
            'interpretation_basis':extraction['interpretation_basis'],'intensity_meaning':extraction['intensity_meaning']}
        rows.append({'version':FACT_VERSION,'sheet_ref':sheet_ref,'component_key':key,'view':view,'component':component,
            'assignment_id':assignment,'lane_id':lane,'region_kind':region,'band_id':band['band_id'] if band else None,
            'band_role':band['role'] if band else None,'cell':cp(cell),'scientific_context':context,
            'numerical_dependencies':cp(deps),'dependence':[
                {'assignment_id':a,'source_dependence':cp(assignments[a]['dependence'])} for a in involved]
                if view in ('comparison','sensitivity') else [],
            'roi_methods':methods,'origin':sheet['origin'],'numeric_locations':cp(locations)})
    for assignment in sheet['assignments']:
        aid=assignment['assignment_id'];source_assignment=extracted[aid]
        for raw in source_assignment['lanes']:
            lid=raw['lane_id'];base='raw:'+_token(aid)+':'+_token(lid)+':'
            regions=[('background',None,raw['background']),('whole_lane',None,raw['whole_lane'])]
            regions += [('band',b,b['measurement']) for b in raw['bands']]
            for kind,band,measurement in regions:
                stem=base+('band:'+_token(band['band_id']) if band else 'whole' if kind=='whole_lane' else 'background')
                for statistic in RAW_COMPONENTS:
                    unit='pixel_count' if statistic in ('pixel_count','zero_gray_count') else 'display_darkness_sum' if statistic=='sum_darkness' else 'gray_level_sum' if statistic=='sum_gray' else 'gray_level'
                    cell=_scalar(measurement[statistic],'selected_region_'+statistic,unit,
                        reason=measurement['unavailable_reason'],measured=True)
                    emit(stem+':'+statistic,'raw_region',statistic,cell,wrapped(aid,[dep(lid,measurement['region'])]),
                        assignment=aid,lane=lid,region=kind,band=band)
            for band in raw['bands']:
                value=band['corrected_signal']
                cell=_scalar(None,CORRECTED_COMPONENT,'display_darkness_sum',reason=value['unavailable_reason'],exact=value['exact'])
                dependency=dep(lid,band['region'],raw['background']['region'])
                if 'background_method' in raw:dependency['background_method']=raw['background_method']
                emit('corrected:'+_token(aid)+':'+_token(lid)+':'+_token(band['band_id']),'corrected_band',CORRECTED_COMPONENT,
                    cell,wrapped(aid,[dependency]),assignment=aid,lane=lid,region='band',band=band)
        for lane in assignment['lanes']:
            for component in LANE_COMPONENTS:
                source_cell=lane['cells'][component]
                emit('lane:'+_token(aid)+':'+_token(lane['lane_id'])+':'+component,'lane',component,_cell(source_cell),
                    wrapped(aid,source_cell['dependencies']),assignment=aid,lane=lane['lane_id'])
        for component in COMPARISON_COMPONENTS:
            source_cell=assignment['cells'][component]
            emit('comparison:'+_token(aid)+':'+component,'comparison',component,_cell(source_cell),
                wrapped(aid,source_cell['dependencies']),assignment=aid)
    for component in COMPARISON_COMPONENTS:
        sensitivity=sheet['roi_sensitivity'][component]
        info={k:cp(v) for k,v in sensitivity.items() if k not in ('lower','upper')}
        cell=_scalar(None,'explicit_available_assignment_minimum_maximum','display_fraction',
            reason='no_available_values' if sensitivity['status']=='no_available_values' else None)
        cell.update(status='unavailable' if sensitivity['status']=='no_available_values' else 'available_range',
            lower=cp(sensitivity['lower']),upper=cp(sensitivity['upper']),sensitivity=info)
        deps=[d for a in sheet['assignments'] for d in wrapped(a['assignment_id'],a['cells'][component]['dependencies'])]
        emit('sensitivity:'+component,'sensitivity',component,cell,deps)
    _check(rows,gel_cells_schema(),'gel_native_projection_schema_invalid')
    return rows


class LiteratureGelRepository(LiteratureRatioSourceRepository):
    provider=PROVIDER;record_version=VERSION;components=COMPONENTS
    operations_table='literature_gel_operations';received_table='literature_gel_component_received'
    runtime_binding_table='literature_gel_runtime_bindings';binding_fields=()

    def __init__(self,store,run_id,*,evidence_origin='reported_source',expected_descriptor=None):
        implementation_descriptor(evidence_origin=evidence_origin)
        super().__init__(store,run_id,evidence_origin=evidence_origin)
        if expected_descriptor is not None and canonical(expected_descriptor)!=canonical(self.descriptor()):
            raise ContractError('gel_native_implementation_binding_mismatch')

    def descriptor(self):
        return implementation_descriptor(evidence_origin=self.evidence_origin)

    def _profile(self,arguments):
        permitted=({'synthetic_fixture'} if self.evidence_origin=='synthetic_fixture' else {'primary_source','retained_extraction'})
        if arguments['selection']['image']['source_kind'] not in permitted:
            raise ContractError('gel_native_evidence_profile_mismatch')

    def _sources(self,context,selection):
        pairs=_source_pairs(selection);direct=sorted({r for r,_ in pairs})
        for reference in direct:self._source(context,reference)
        closure=list(direct)
        for reference in closure:
            record=self._source(context,reference,direct=False)
            for parent in record.get('parent_source_refs',()):
                self._source(context,parent,direct=False)
                if parent not in closure:closure.append(parent)
        return pairs,direct,closure

    def _bindings(self,extraction,publish=None):
        meanings,bindings,records=_meaning_specs(extraction)
        for reference,value in records.items():
            if publish:
                if publish('reference',value)!=reference:raise ContractError('gel_native_semantic_binding_mismatch')
            else:
                actual=self._record(reference,'reference')
                if canonical({k:v for k,v in actual.items() if k not in ('id','record_type','origin')})!=canonical(value):
                    raise ContractError('gel_native_semantic_binding_mismatch')
        return meanings,bindings

    def populate(self,context,arguments,operation_key):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:raise ContractError('operation_key_required')
        args=validate_population_arguments(arguments);self._profile(args)
        pairs,direct,closure=self._sources(context,args['selection'])
        descriptor=self.descriptor()
        signature=canonical({'arguments':args,'scope':plain(context.scope),'role':context.role,
            'assignment':plain(context.assignment),'implementation_descriptor':descriptor,'evidence_origin':self.evidence_origin})
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone()
        if old:
            if old['signature']!=signature:raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome']);self.read(outcome['result']['sheet_ref']);return cp(outcome)
        def read_source(reference,representation):
            source=self._source(context,reference)
            artifact=source['artifact_ref'] if representation=='original' else source.get('text_ref')
            if artifact is None:raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref':artifact,'content':self._bytes(artifact)}
        extraction=inputs.read_gel_inputs(args['selection'],read_source=read_source)
        sheet=calculations.populate_gel_components(extraction,args['comparison'])
        with self.store.transaction():
            created=[]
            def publish(kind,value):
                reference=identity(kind,{'origin':'tool','record':value})
                old=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(reference,)).fetchone()
                actual=self.store.put(kind,value,origin='tool',scope=plain(context.scope))
                if old is None:created.append(actual['id'])
                return actual['id']
            meanings,bindings=self._bindings(extraction,publish)
            root=self._record(args['selection']['image']['source_ref'],'source')
            payload={'version':VERSION,'arguments':args,'extraction':extraction,'sheet':sheet,'meanings':meanings,
                'semantic_bindings':bindings,'evidence_origin':self.evidence_origin,'component_roster':[],
                'input_source_ref':root['id'],'input_artifact_ref':root['artifact_ref'],
                'direct_input_source_refs':direct,'input_source_refs':closure,
                'source_associations':cp(extraction['sources']),'implementation_descriptor':descriptor}
            rows=_component_rows(payload,'source_'+'0'*24)
            payload['component_roster']=[r['component_key'] for r in rows]
            artifact=self.store.artifact(canonical(payload),'application/json')
            request=self.store.artifact(canonical({'run_id':self.run_id,'episode_id':context.episode_id,
                'operation_key':operation_key,'arguments':args,'signature':json.loads(signature)}),'application/json')
            reference=publish('source',{'provider':PROVIDER,'accession':None,'uri':None,'artifact_ref':artifact,
                'text_ref':artifact,'request_ref':request,'version':VERSION,'retrieved_at':None,'parent_source_refs':closure})
            rows=_component_rows(payload,reference)
            outcome={'status':'completed','operation_ref':identity('operation',{'run_id':self.run_id,
                'episode_id':context.episode_id,'key':operation_key}),
                'record_refs':[reference,*bindings],'changed_record_refs':created,
                'result':{'sheet_ref':reference,'component_keys':payload['component_roster'],'cells':rows,
                    'payload_sha256':_sha(payload)},'feedback':None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return cp(outcome)

    def read(self,sheet_ref):
        record=self._record(sheet_ref,'source')
        if (record['provider']!=PROVIDER or record['origin']!='tool' or record['version']!=VERSION
                or record['artifact_ref']!=record['text_ref'] or not record.get('request_ref')):
            raise ContractError('gel_native_source_required')
        request=self._json(record['request_ref'])
        if (set(request)!={'run_id','episode_id','operation_key','arguments','signature'}
                or request['run_id']!=self.run_id):raise ContractError('gel_native_request_mismatch')
        original=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone()
        if original is None:raise ContractError('literature_sheet_not_selected_output')
        signature=json.loads(original['signature']);outcome=json.loads(original['outcome']);payload=self._json(record['artifact_ref'])
        if (set(payload)!=_PAYLOAD_FIELDS or payload['version']!=VERSION
                or set(signature)!={'arguments','scope','role','assignment','implementation_descriptor','evidence_origin'}
                or canonical(signature)!=canonical(request['signature'])
                or canonical(signature['arguments'])!=canonical(request['arguments'])
                or canonical(payload['arguments'])!=canonical(request['arguments'])
                or canonical(signature['implementation_descriptor'])!=canonical(payload['implementation_descriptor'])
                or signature['evidence_origin']!=payload['evidence_origin']
                or payload['implementation_descriptor']['evidence_origin']!=payload['evidence_origin']
                or outcome['result']['sheet_ref']!=sheet_ref or outcome['result']['payload_sha256']!=_sha(payload)
                or outcome['operation_ref']!=identity('operation',{'run_id':self.run_id,'episode_id':request['episode_id'],'key':request['operation_key']})
                or record['parent_source_refs']!=payload['input_source_refs']):
            raise ContractError('gel_native_original_outcome_mismatch')
        args=validate_population_arguments(payload['arguments']);self._profile(args)
        if payload['evidence_origin']!=self.evidence_origin:raise ContractError('gel_native_evidence_profile_mismatch')
        self._runtime_original(request,signature,outcome)
        context=SimpleNamespace(run_id=self.run_id,episode_id=request['episode_id'],scope=signature['scope'],
            role=signature['role'],assignment=signature['assignment'],received_record_refs=tuple(payload['direct_input_source_refs']))
        pairs,direct,closure=self._sources(context,args['selection'])
        root=self._record(args['selection']['image']['source_ref'],'source')
        if (payload['input_source_ref']!=root['id'] or payload['input_artifact_ref']!=root['artifact_ref']
                or payload['direct_input_source_refs']!=direct or payload['input_source_refs']!=closure
                or [(a['source_ref'],a['representation']) for a in payload['source_associations']]!=pairs):
            raise ContractError('gel_native_original_source_closure_mismatch')
        extraction=payload['extraction'];sheet=payload['sheet']
        # Original payload/outcome/runtime custody authenticates the saved data.
        # Detached checks never reopen original bytes or recount retained pixels.
        if (canonical(extraction['selection'])!=canonical(args['selection'])
                or canonical(sheet['comparison'])!=canonical(args['comparison'])
                or extraction['extraction_digest']!=inputs._hash(inputs._canonical({k:v for k,v in extraction.items() if k!='extraction_digest'}))
                or sheet['extraction_digest']!=extraction['extraction_digest']
                or sheet['sheet_digest']!=inputs._hash(inputs._canonical({k:v for k,v in sheet.items() if k!='sheet_digest'}))
                or canonical(extraction['sources'])!=canonical(payload['source_associations'])):
            raise ContractError('gel_native_saved_payload_mismatch')
        expected_version=inputs.EXTRACTION_VERSION if args['selection']['version']==inputs.VERSION else inputs.EXTRACTION_VERSION_V2
        expected_sheet=calculations.VERSION if expected_version==inputs.EXTRACTION_VERSION else calculations.VERSION_V2
        if extraction['version']!=expected_version or sheet['version']!=expected_sheet:
            raise ContractError('gel_native_saved_version_mismatch')
        for association in payload['source_associations']:
            source=self._record(association['source_ref'],'source')
            artifact=source['artifact_ref'] if association['representation']=='original' else source.get('text_ref')
            if artifact!=association['artifact_ref'] or artifact!='artifact_'+association['byte_sha256']:
                raise ContractError('gel_native_source_association_mismatch')
            self._artifact_metadata(artifact)
        meanings,bindings=self._bindings(extraction)
        if canonical(meanings)!=canonical(payload['meanings']) or canonical(bindings)!=canonical(payload['semantic_bindings']):
            raise ContractError('gel_native_semantic_binding_mismatch')
        rows=_component_rows(payload,sheet_ref)
        if (canonical(rows)!=canonical(outcome['result']['cells'])
                or [r['component_key'] for r in rows]!=payload['component_roster']
                or outcome['result']['component_keys']!=payload['component_roster']
                or outcome['record_refs']!=[sheet_ref,*bindings]):
            raise ContractError('gel_native_original_projection_mismatch')
        return cp(payload)

    def project_cells(self,sheet_refs,*,permitted_record_refs,components):
        if not isinstance(components,(list,tuple)) or any(type(k) is not str for k in components) or len(set(components))!=len(components):
            raise ContractError('gel_native_component_keys_required')
        result=[]
        for reference in _unique(sheet_refs):
            if reference not in permitted_record_refs:raise ContractError('literature_sheet_not_received')
            saved=self.read(reference);roster={r['component_key']:r for r in _component_rows(saved,reference)}
            if any(k not in roster for k in components):raise ContractError('gel_native_component_key_unknown')
            result.extend(cp(roster[k]) for k in components)
        return result

    def requested_component_keys(self,sheet_ref,assignment):
        saved=self.read(sheet_ref);assignment=plain(assignment)
        names=assignment.get(REQUEST_COMPONENTS,[]);views=assignment.get(REQUEST_VIEWS,[])
        for values,allowed in ((names,COMPONENTS),(views,VIEWS)):
            if not isinstance(values,list) or any(type(v) is not str or v not in allowed for v in values) or len(values)!=len(set(values)):
                raise ContractError('gel_native_request_selection_invalid')
        allowed=[r['component_key'] for r in _component_rows(saved,sheet_ref) if r['component'] in names and r['view'] in views]
        keys=assignment.get(REQUEST_KEYS)
        if keys is None:return allowed
        if not isinstance(keys,list) or any(type(k) is not str or k not in allowed for k in keys) or len(keys)!=len(set(keys)):
            raise ContractError('gel_native_requested_key_unresolved')
        return list(keys)

    def validate_returned_values(self,cells,*,permitted_record_refs):
        _check(cells,gel_cells_schema(),'gel_native_cells_schema_invalid')
        keys=[(r['sheet_ref'],r['component_key']) for r in cells]
        if len(keys)!=len(set(keys)):raise ContractError('duplicate_gel_native_cell')
        expected={}
        for reference in _unique(r['sheet_ref'] for r in cells):
            projected=self.project_cells([reference],permitted_record_refs=permitted_record_refs,
                components=[r['component_key'] for r in cells if r['sheet_ref']==reference])
            expected.update({(r['sheet_ref'],r['component_key']):r for r in projected})
        if any(canonical(r)!=canonical(expected[(r['sheet_ref'],r['component_key'])]) for r in cells):
            raise ContractError('gel_native_cell_differs_from_original')

    def fact_cells(self,context,sheet_refs,*,components):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        self.project_cells([],permitted_record_refs=(),components=components)
        received=None;result=[]
        for reference in _unique(sheet_refs):
            if reference not in context.received_record_refs:raise ContractError('literature_sheet_not_received')
            self.read(reference);record=self._record(reference,'source');request=self._json(record['request_ref'])
            if request['episode_id']==context.episode_id:
                self._bind_native_output(context,reference)
                result.extend(self.project_cells([reference],permitted_record_refs=context.received_record_refs,components=components))
            else:
                if received is None:received={(r['sheet_ref'],r['component_key']):r for r in self.received_cells(context)}
                result.extend(cp(received[(reference,k)]) for k in components if (reference,k) in received)
        return result

    def validate_fact_values(self,context,cells):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        self.validate_returned_values(cells,permitted_record_refs=context.received_record_refs)
        for reference in _unique(r['sheet_ref'] for r in cells):
            subset=[r for r in cells if r['sheet_ref']==reference]
            allowed=self.requested_component_keys(reference,context.assignment)
            if any(r['component_key'] not in allowed for r in subset):raise ContractError('gel_native_cell_not_requested')
            expected=self.fact_cells(context,[reference],components=[r['component_key'] for r in subset])
            if canonical(expected)!=canonical(subset):raise ContractError('literature_cell_not_received')

    def semantic_bindings(self,cells):
        self.validate_returned_values(cells,permitted_record_refs=[r['sheet_ref'] for r in cells])
        result={};saved={}
        for row in cells:
            reference=row['sheet_ref']
            if reference not in saved:saved[reference]=self.read(reference)
            context=row['scientific_context']
            meanings=[*context['global'].values(),*[lane[k] for lane in context['lanes'] for k in LANE_MEANINGS]]
            ids=_unique(ref for m in meanings for ref in [m['value_ref'],*m['witness_refs']] if ref is not None)
            target=result.setdefault(reference,{})
            for ref in ids:
                binding=saved[reference]['semantic_bindings'].get(ref)
                if binding is None:raise ContractError('gel_native_semantic_binding_mismatch')
                target[ref]=cp(binding)
        return result

    def cell_record_refs(self,cells):
        bindings=self.semantic_bindings(cells)
        return _unique([*(r['sheet_ref'] for r in cells),*(b['record_ref'] for entries in bindings.values() for b in entries.values()),
            *(d['source_dependency']['source_ref'] for r in cells for d in r['numerical_dependencies']),
            *(loc['source_ref'] for r in cells for loc in r['numeric_locations'])])


    def _runtime_original(self,request,signature,outcome,*,required=False):
        """Inspect the actual original runtime output; never invent a receipt.

        Repository output precedes runtime journal completion. Reads/replay may
        inspect that valid crash interval, but native fact publication requires
        the completed original runtime result and retains its FULL digest.
        """
        key=(self.run_id,request['episode_id'],request['operation_key'])
        bound=(self.store.db.execute(f'SELECT runtime_digest FROM {self.runtime_binding_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',key).fetchone()
            if self._has_table(self.runtime_binding_table) else None)
        prefix=self.run_id+':'+request['episode_id']+':'
        suffix=request['operation_key'][len(prefix):] if request['operation_key'].startswith(prefix) else ''
        valid=(suffix.isascii() and suffix.isdigit() and len(suffix)<=19
               and int(suffix)<=2**63-1 and str(int(suffix))==suffix)
        if not valid:
            if required or bound is not None:raise ContractError('gel_native_original_runtime_required')
            return None
        action=(self.store.db.execute('SELECT action,result FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? AND decision_index=?',(self.run_id,request['episode_id'],int(suffix))).fetchone()
            if self._has_table('runtime_actions') else None)
        if action is None:
            if required or bound is not None:raise ContractError('gel_native_original_runtime_uncommitted')
            return None
        selected=json.loads(action['action'])
        if (set(selected)!={'kind','tool','arguments'} or selected['kind']!='tool'
                or selected['tool']!=OPERATION
                or canonical(selected['arguments'])!=canonical(request['arguments'])):
            raise ContractError('gel_native_original_runtime_mismatch')
        episode=(self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,request['episode_id'])).fetchone() if self._has_table('runtime_episodes') else None)
        if episode is None:raise ContractError('gel_native_original_runtime_episode_unavailable')
        original_request=json.loads(episode['request']);path=json.loads(episode['path'])
        message=original_request.get('message',{})
        if (not path or path[-1][0]!=signature['role'] or canonical(message.get('scope'))!=canonical(signature['scope'])
                or canonical(message.get('episode_assignment',{}))!=canonical(signature['assignment'])):
            raise ContractError('gel_native_original_runtime_context_mismatch')
        if action['result'] is None:
            if required or bound is not None:raise ContractError('gel_native_original_runtime_uncommitted')
            return None
        result=json.loads(action['result'])
        # DecisionSource adds only this legitimate runtime snapshot after the
        # repository commits its tool result. Every other field must be exact.
        tool_portion={name:value for name,value in result.items() if name!='pending_work_after_action'}
        if canonical(tool_portion)!=canonical(outcome):raise ContractError('gel_native_original_runtime_mismatch')
        evidence={'run_id':self.run_id,'episode_id':request['episode_id'],'decision_index':int(suffix),
            'operation_key':request['operation_key'],'action':selected,'result':result,
            'request':original_request,'path':path}
        digest=_sha(evidence)
        if bound is not None and bound['runtime_digest']!=digest:
            raise ContractError('gel_native_original_runtime_digest_mismatch')
        return evidence,digest,bound is not None


    def _bind_native_output(self,context,reference):
        """Bind completed original runtime custody at native fact publication."""
        record=self._record(reference,'source');request=self._json(record['request_ref'])
        operation=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone()
        signature=json.loads(operation['signature']);outcome=json.loads(operation['outcome'])
        evidence,digest,bound=self._runtime_original(request,signature,outcome,required=True)
        if (context.episode_id!=request['episode_id'] or plain(context.path)!=evidence['path']
                or canonical(plain(context.request))!=canonical(evidence['request'])
                or context.role!=signature['role'] or canonical(plain(context.scope))!=canonical(signature['scope'])
                or canonical(plain(context.assignment))!=canonical(signature['assignment'])):
            raise ContractError('gel_native_original_runtime_context_mismatch')
        if bound:return
        if self.store.db.execute('PRAGMA query_only').fetchone()[0]:
            raise ContractError('gel_native_original_runtime_binding_unavailable')
        try:
            with self.store.transaction():
                self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self.runtime_binding_table} '
                    '(run_id TEXT NOT NULL,episode_id TEXT NOT NULL,operation_key TEXT NOT NULL,runtime_digest TEXT NOT NULL,'
                    'PRIMARY KEY(run_id,episode_id,operation_key))')
                self.store.db.execute(f'INSERT OR IGNORE INTO {self.runtime_binding_table} VALUES(?,?,?,?)',
                    (self.run_id,request['episode_id'],request['operation_key'],digest))
                self._runtime_original(request,signature,outcome,required=True)
        except Exception as error:
            if 'readonly' in str(error).lower():
                raise ContractError('gel_native_original_runtime_binding_unavailable') from error
            raise


    def _runtime_evidence(self,context,operation_key):
        rows=self._runtime_delivery_cells(context,operation_key)
        if rows is None:raise ContractError('gel_native_runtime_admission_required')
        index=int(operation_key[len(self.run_id+':'+context.episode_id+':'):].split(':')[0])
        attempt=self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id,context.episode_id,index)).fetchone()
        child=self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,attempt['child_episode_id'])).fetchone()
        parent=self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,context.episode_id)).fetchone()
        if child is None or parent is None or json.loads(child['path'])[:-1]!=json.loads(parent['path']):
            raise ContractError('gel_native_delivery_child_mismatch')
        parent_request=json.loads(parent['request']);child_request=json.loads(child['request'])
        parent_path=json.loads(parent['path']);child_path=json.loads(child['path'])
        message=parent_request['message']
        if (plain(context.path)!=parent_path or context.role!=parent_path[-1][0]
                or plain(context.scope)!=message['scope']
                or plain(context.assignment)!=message.get('episode_assignment',{})):
            raise ContractError('gel_native_delivery_parent_context_mismatch')
        if not self.store.scope_contains(message['scope'],child_request['message']['scope']):
            raise ContractError('gel_native_delivery_child_scope_mismatch')
        # Read the ordinary frozen receipt lineage without installing tables or
        # inventing a manual possession declaration for this new return view.
        if not all(self._has_table(name) for name in ('runtime_receipt_inheritance','runtime_record_receipts')):
            raise ContractError('gel_native_reporting_possession_unavailable')
        receipts=EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store=self.store;receipts.db=self.store.db;receipts.run_id=self.run_id
        child_context=BindingContext(self.run_id,attempt['child_episode_id'],child_path[-1][0],child_path,
            child_request['message']['scope'],child_request['message'].get('episode_assignment',{}),
            child_request,tuple(receipts.known(attempt['child_episode_id'])))
        self.validate_fact_values(child_context,rows)
        evidence={'form':json.loads(attempt['form']),'contract':json.loads(attempt['contract']),
            'child_episode_id':attempt['child_episode_id'],'delivery_ref':attempt['delivery_ref'],
            'child_request':child_request,'parent_request':parent_request,'child_path':child_path,'parent_path':parent_path,
            'parent_episode_id':context.episode_id,'run_id':self.run_id}
        return rows,_sha(evidence)


    def receive_cells(self,context,cells,operation_key):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        with self.store.transaction():
            original,runtime_digest=self._runtime_evidence(context,operation_key)
            if canonical(original)!=canonical(cells):raise ContractError('literature_delivery_binding_mismatch')
            self.validate_returned_values(cells,permitted_record_refs=[r['sheet_ref'] for r in cells])
            self.store.db.execute(f'CREATE TABLE IF NOT EXISTS {self._delivery_table}(run_id TEXT NOT NULL,episode_id TEXT NOT NULL,'
                'operation_key TEXT NOT NULL,cells_digest TEXT NOT NULL,runtime_digest TEXT NOT NULL,PRIMARY KEY(run_id,episode_id,operation_key))')
            old=self.store.db.execute(f'SELECT cells FROM {self.received_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
                (self.run_id,context.episode_id,operation_key)).fetchone()
            bound=self.store.db.execute(f'SELECT cells_digest,runtime_digest FROM {self._delivery_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
                (self.run_id,context.episode_id,operation_key)).fetchone()
            digest=self._delivery_digest(cells)
            if old is not None and (old['cells']!=canonical(cells) or bound is None or bound['cells_digest']!=digest or bound['runtime_digest']!=runtime_digest):
                raise ContractError('literature_delivery_binding_mismatch')
            self.store.db.execute(f'INSERT OR IGNORE INTO {self.received_table} VALUES(?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,canonical(cells)))
            self.store.db.execute(f'INSERT OR IGNORE INTO {self._delivery_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,digest,runtime_digest))


    def received_cells(self,context):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        result=[];seen=set()
        for saved in self.store.db.execute(f'SELECT operation_key,cells FROM {self.received_table} WHERE run_id=? AND episode_id=? ORDER BY rowid',
                (self.run_id,context.episode_id)):
            cells=json.loads(saved['cells']);original,runtime_digest=self._runtime_evidence(context,saved['operation_key'])
            if not self._has_table(self._delivery_table):raise ContractError('literature_delivery_binding_unavailable')
            bound=self.store.db.execute(f'SELECT cells_digest,runtime_digest FROM {self._delivery_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
                (self.run_id,context.episode_id,saved['operation_key'])).fetchone()
            if (bound is None or canonical(original)!=canonical(cells) or bound['cells_digest']!=self._delivery_digest(cells)
                    or bound['runtime_digest']!=runtime_digest):raise ContractError('literature_delivery_binding_mismatch')
            self.validate_returned_values(cells,permitted_record_refs=[r['sheet_ref'] for r in cells])
            for row in cells:
                key=(row['sheet_ref'],row['component_key'])
                if key not in seen:seen.add(key);result.append(cp(row))
        return result


__all__=['LiteratureGelRepository','gel_population_schema','gel_cells_schema','implementation_descriptor',
    'PROVIDER','OPERATION','FACT_SOURCE','VERSION','FACT_VERSION','COMPONENTS','VIEWS']
