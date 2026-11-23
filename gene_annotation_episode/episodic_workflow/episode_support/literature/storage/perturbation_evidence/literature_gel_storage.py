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

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError, canonical, identity
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence import literature_gel_inputs as inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.perturbation_evidence import literature_gel_calculations as calculations
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_gel_native_contracts import PROVIDER, OPERATION, FACT_SOURCE, VERSION, FACT_VERSION, COMPONENTS, VIEWS, RAW_COMPONENTS, CORRECTED_COMPONENT, LANE_COMPONENTS, COMPARISON_COMPONENTS, LANE_MEANINGS, REQUEST_COMPONENTS, REQUEST_VIEWS, REQUEST_KEYS, gel_population_schema, gel_cells_schema, validate_population_arguments


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
    return {'version':'gel_native_implementation','provider':PROVIDER,'record_version':VERSION,
        'evidence_origin':evidence_origin,'native_schema_sha256':_sha(gel_cells_schema()),
        'pillow_version':inputs.PILLOW_VERSION,'jsonschema_version':importlib.metadata.version('jsonschema')}


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
                'background_method':original['background_method']}
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
    received_table='literature_gel_component_received';binding_fields=()

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
                new = not self.store.holds(reference)
                actual=self.store.put(kind,value,origin='tool',scope=plain(context.scope))
                if new:created.append(actual['id'])
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
        return cp(outcome)

    def read(self,sheet_ref):
        record=self._record(sheet_ref,'source')
        if (record['provider']!=PROVIDER or record['origin']!='tool' or record['version']!=VERSION
                or record['artifact_ref']!=record['text_ref'] or not record.get('request_ref')):
            raise ContractError('gel_native_source_required')
        request=self._json(record['request_ref'])
        if (set(request)!={'run_id','episode_id','operation_key','arguments','signature'}
                or request['run_id']!=self.run_id):raise ContractError('gel_native_request_mismatch')
        signature=request['signature'];payload=self._json(record['artifact_ref'])
        if (set(payload)!=_PAYLOAD_FIELDS or payload['version']!=VERSION
                or set(signature)!={'arguments','scope','role','assignment','implementation_descriptor','evidence_origin'}
                or canonical(signature['arguments'])!=canonical(request['arguments'])
                or canonical(payload['arguments'])!=canonical(request['arguments'])
                or canonical(signature['implementation_descriptor'])!=canonical(payload['implementation_descriptor'])
                or signature['evidence_origin']!=payload['evidence_origin']
                or payload['implementation_descriptor']['evidence_origin']!=payload['evidence_origin']
                or record['parent_source_refs']!=payload['input_source_refs']):
            raise ContractError('gel_native_original_outcome_mismatch')
        args=validate_population_arguments(payload['arguments']);self._profile(args)
        if payload['evidence_origin']!=self.evidence_origin:raise ContractError('gel_native_evidence_profile_mismatch')
        context=SimpleNamespace(run_id=self.run_id,episode_id=request['episode_id'],scope=signature['scope'],
            role=signature['role'],assignment=signature['assignment'],received_record_refs=tuple(payload['direct_input_source_refs']))
        pairs,direct,closure=self._sources(context,args['selection'])
        root=self._record(args['selection']['image']['source_ref'],'source')
        if (payload['input_source_ref']!=root['id'] or payload['input_artifact_ref']!=root['artifact_ref']
                or payload['direct_input_source_refs']!=direct or payload['input_source_refs']!=closure
                or [(a['source_ref'],a['representation']) for a in payload['source_associations']]!=pairs):
            raise ContractError('gel_native_original_source_closure_mismatch')
        extraction=payload['extraction'];sheet=payload['sheet']
        # Original payload custody authenticates the saved data.
        # Detached checks never reopen original bytes or recount retained pixels.
        if (canonical(extraction['selection'])!=canonical(args['selection'])
                or canonical(sheet['comparison'])!=canonical(args['comparison'])
                or extraction['extraction_digest']!=inputs._hash(inputs._canonical({k:v for k,v in extraction.items() if k!='extraction_digest'}))
                or sheet['extraction_digest']!=extraction['extraction_digest']
                or sheet['sheet_digest']!=inputs._hash(inputs._canonical({k:v for k,v in sheet.items() if k!='sheet_digest'}))
                or canonical(extraction['sources'])!=canonical(payload['source_associations'])):
            raise ContractError('gel_native_saved_payload_mismatch')
        if extraction['version']!=inputs.EXTRACTION_VERSION or sheet['version']!=calculations.VERSION:
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
        if [r['component_key'] for r in rows]!=payload['component_roster']:
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
        result=[]
        for reference in _unique(sheet_refs):
            if reference not in context.received_record_refs:raise ContractError('literature_sheet_not_received')
            self.read(reference)
            # A sheet another episode populated reaches this one as a received record of the run's shared Store
            # (its reference is in this episode's received records); its saved cells are projected from that Store.
            result.extend(self.project_cells([reference],permitted_record_refs=context.received_record_refs,components=components))
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



__all__=['LiteratureGelRepository','gel_population_schema','gel_cells_schema','implementation_descriptor',
    'PROVIDER','OPERATION','FACT_SOURCE','VERSION','FACT_VERSION','COMPONENTS','VIEWS']
