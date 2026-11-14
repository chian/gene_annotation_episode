"""Native custody and exact-key projection for selected controlled responses.

This repository owns no scientific choices, model calls, controller observations
or episode loop. Source meanings and numerical results remain separate payloads.
"""
from __future__ import annotations

from copy import deepcopy as cp
import errno
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from jsonschema import Draft202012Validator

from .communication import plain
from .domain import ContractError, canonical, identity
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .literature_ratio_source_storage import LiteratureRatioSourceRepository
from . import literature_controlled_response_inputs as shared
from . import literature_controlled_response_v3_inputs as source
from . import literature_controlled_response_v3_population as population
from . import literature_controlled_response_calculations as arithmetic


PROVIDER = 'literature.a105.controlled_response'
VERSION = 'literature_controlled_response_record_v3'
FACT_VERSION = 'literature_controlled_response_component_fact_v3'
COMPONENTS = (*arithmetic.COMPONENTS, 'local_difference', 'local_variance', 'local_standard_uncertainty')
VIEWS = ('native_raw', 'local_difference', 'local_variance', 'local_standard_uncertainty', 'final', 'conditional')
_PAYLOAD_FIELDS = {'version','selection','extraction','population','component_roster','semantic_bindings','scope_witness_bindings',
    'input_source_ref','input_artifact_ref','direct_input_source_refs','input_source_refs',
    'source_associations','implementation_descriptor','evidence_origin'}


def _sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value).encode()).hexdigest()


def _unique(values):
    return list(dict.fromkeys(values))


def _check(value, schema, code):
    try:
        Draft202012Validator(schema).validate(value)
        canonical(value)
    except Exception as error:
        if not isinstance(error,(ValueError,TypeError)) and error.__class__.__module__.split('.')[0] != 'jsonschema':
            raise
        raise ContractError(code) from error


def controlled_response_population_schema():
    return source.controlled_response_v3_arguments_schema()


def controlled_response_cells_schema():
    return cp(source._schemas()['NATIVE_RETURN_SCHEMA_V3_007'])


def implementation_descriptor(*,evidence_origin='reported_source'):
    if evidence_origin not in ('reported_source','synthetic_fixture'):
        raise ContractError('controlled_native_evidence_profile_invalid')
    names = sorted(set(source._dependencies()) | {
        'literature_controlled_response_storage.py','literature_controlled_response_render.py',
        'literature_controlled_response_v3_population.py','literature_rate_storage.py','literature_ratio_source_storage.py',
        'literature_binding_interaction_render.py','domain.py','state.py','communication.py',
        'episode_bindings.py','episode_receipts.py'})
    return {'version':'controlled_response_native_implementation_v1','provider':PROVIDER,'record_version':VERSION,
            'evidence_origin':evidence_origin,
            'native_schema_sha256':_sha(controlled_response_cells_schema()),
            'modules':{name:_sha(Path(__file__).with_name(name).read_bytes()) for name in names}}


def _registry(extraction):
    result={(role,None):extraction['arms'][role] for role in shared.PRIMITIVE_ORDER}
    result.update({(row['primary_role'],row['reading_key']):row['reading'] for row in extraction['companion_extractions']})
    return result


def _selector_key(selector):
    return selector['role'],selector['reading_key']


def _token(value):
    return quote(value,safe='-._~',encoding='utf-8',errors='strict')


def _raw_key(selector):
    return 'raw:'+selector['role']+(':primary' if selector['reading_key'] is None
                                  else ':companion:'+_token(selector['reading_key']))


def _state(meanings, field, *, common=False):
    records=[row['meanings'][field] if row else None for row in meanings]
    states=[row['resolved_state'] if row else 'unknown' for row in records]
    ids=_unique(row['canonical_id'] for row in records if row and row['resolved_state']=='known' and row['canonical_id'])
    state=('conflicting' if 'conflicting' in states or common and len(ids)>1 else
           'unknown' if not states or 'unknown' in states else 'known')
    return state,ids


def _scope_reference(extraction,witness):
    """A real immutable record for an actual retained scope witness."""
    selected=witness['selection'];locator=witness['canonical_locator']
    authenticated=locator is not None and witness['authentication']!='unavailable'
    if locator is not None:
        source_ref=locator.get('source_ref',locator.get('original_source_ref'))
    elif selected['kind']=='text':source_ref=selected['source_ref']
    else:
        image=next(row for row in extraction['selection']['images'] if row['image_id']==selected['image_id'])
        source_ref=image['original_source_ref']
    label=' '.join(selected['quote'].split()) if authenticated else 'Source witness unavailable'
    if len(label)>512:label=label[:509]+'...'
    anchor=None
    if authenticated and locator['kind']=='text' and len(selected['quote'])<=16000:
        anchor={key:locator[key] for key in ('source_ref','artifact_ref','start','end')}
        anchor['quote']=selected['quote']
    value={'reference_type':'literature_result','source_ref':source_ref,
        'accession':identity('controlled_joint_scope_witness',witness),'label':label,
        'sequence_ref':None,'molecule':None,'length':None,'term_refs':[],'context_refs':[],'anchor':anchor}
    return identity('reference',{'origin':'tool','record':value}),value


def _scope_witnesses(extraction):
    for scope in extraction['joint_scope_extractions']:
        yield from scope['witnesses']
        for name in ('variance_status','model_kind'):yield from scope['requested_model'][name]['witnesses']


def _joint_scope_context(extraction,index):
    scope=extraction['joint_scope_extractions'][index]
    if scope['assignment_index']!=index:raise ContractError('controlled_native_joint_scope_index_mismatch')
    selection=extraction['selection'];nomination=selection['joint_reading_assignments'][index]
    specification=selection['joint_scopes'][index]
    if specification['assignment_index']!=index:raise ContractError('controlled_native_joint_scope_index_mismatch')
    def witness(row):
        ref,_=_scope_reference(extraction,row)
        return {'witness_ref':ref,'authentication':row['authentication'],'attribution':row['attribution']}
    at=0
    def relation(selected):
        nonlocal at
        records=scope['witnesses'][at:at+len(selected['witnesses'])];at+=len(records)
        if len(records)!=len(selected['witnesses']) or any(canonical(r['selection'])!=canonical(w)
                for r,w in zip(records,selected['witnesses'])):
            raise ContractError('controlled_native_scope_witness_association_mismatch')
        return {'selected_value':selected['value'],
            'effective_value':'unknown' if any(r['canonical_locator'] is None for r in records) else selected['value'],
            'witnesses':[witness(r) for r in records]}
    result={'reading_assignment':cp(nomination['assignment']),
        'assignment_admissibility':relation(nomination['admissibility']),
        'effective_admissibility':scope['effective_admissibility']}
    for name in ('normalization','calibration','revision','covariance_scope','model_scope'):
        result[name]=relation(specification[name])
    if at!=len(scope['witnesses']):raise ContractError('controlled_native_scope_witness_association_mismatch')
    result['requested_model']={name:{'selected_value':record['selection']['value'],
        'effective_value':record['effective_value'],'witnesses':[witness(r) for r in record['witnesses']]}
        for name,record in scope['requested_model'].items()}
    result['effective_model']=cp(scope['effective_model'])
    covariance=scope['source_covariance']
    result['covariance_context']=None if covariance is None else {key:cp(covariance[key]) for key in (
        'source_ref','source_validation','projection_state','source_model')}
    return result


def _numeric_locations(extraction):
    """Retain locations of every native numeral that labels must not expand."""
    result=[]
    def span(witness,start=0,end=None):
        if not isinstance(witness,dict) or not all(k in witness for k in ('source_ref','start','quote')):return
        quote=witness['quote'];end=len(quote) if end is None else end
        result.append({'kind':'utf8_span','source_ref':witness['source_ref'],
            'start':witness['start']+len(quote[:start].encode()),'end':witness['start']+len(quote[:end].encode())})
    def walk(value):
        if isinstance(value,dict):
            loc=value.get('source_locator')
            if isinstance(loc,dict) and loc.get('source_ref') and 'start' in loc and 'end' in loc:
                result.append({'kind':'utf8_span','source_ref':loc['source_ref'],'start':loc['start'],'end':loc['end']})
            for prefix in ('number','lower','upper'):
                if prefix+'_start' in value and prefix+'_end' in value:
                    span(value.get('witness'),value[prefix+'_start'],value[prefix+'_end'])
            if value.get('kind')=='image' and value.get('original_source_ref') and 'region' in value:
                result.append({'kind':'image_region','source_ref':value['original_source_ref'],'region':cp(value['region'])})
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    walk(extraction['arms']);walk(extraction['companion_extractions'])
    for reading in _registry(extraction).values():
        if reading:
            uncertainty=reading['reported_uncertainty']
            if uncertainty['confidence_level'] is not None:span(uncertainty['confidence_level']['selection'])
            if reading['graph_details'] is not None:
                image_id=reading['selection']['measurement']['image_id']
                image=next(row for row in extraction['selection']['images'] if row['image_id']==image_id)
                if not any(row['kind']=='image_region' and row['source_ref']==image['original_source_ref'] for row in result):
                    result.append({'kind':'unresolved','source_ref':image['original_source_ref']})
                if image['source_ref']!=image['original_source_ref']:
                    result.append({'kind':'unresolved','source_ref':image['source_ref']})
    # Calibration witnesses can contain source calibration quantities that are
    # not requested arithmetic outputs. Locate their retained lexical numerals;
    # unrelated source labels remain independently bounded by their own spans.
    numeral=re.compile(r'(?<![\w.])[-+−]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?')
    for scope in extraction['joint_scope_extractions']:
        index=scope['assignment_index'];nomination=extraction['selection']['joint_scopes'][index]['calibration']
        for selected in nomination['witnesses']:
            for match in numeral.finditer(selected['quote']):
                if selected['kind']=='text':span(selected,match.start(),match.end())
                else:
                    record=next((w for w in scope['witnesses'] if w['selection']==selected),None)
                    locator=record['canonical_locator'] if record else None
                    if locator is not None:result.append({'kind':'image_region','source_ref':locator['original_source_ref'],
                        'region':cp(locator['region'])})
    # Locate all retained full-N numeric tokens, including unrelated covariance
    # entries that broad labels must not expand. This is retained-text lexical
    # metadata, not source acquisition or a numerical population calculation.
    for item in extraction['covariance_document_scopes']:
        doc=item['document']
        if doc is None:continue
        if doc['raw_text'] is None:
            result.append({'kind':'unresolved','source_ref':doc['source_ref']});continue
        parser=shared._JSON(doc['raw_text'])
        try:parser.load()
        except shared._CovarianceError:
            result.append({'kind':'unresolved','source_ref':doc['source_ref']});continue
        for path in parser.tokens:
            start,end=parser.spans[path]
            result.append({'kind':'utf8_span','source_ref':doc['source_ref'],
                'start':len(doc['raw_text'][:start].encode()),'end':len(doc['raw_text'][:end].encode())})
    return [json.loads(token) for token in sorted(set(canonical(row) for row in result))]


def _context(extraction, dependencies, *, kind, variance='unknown', model='none', pair=None):
    roster=_registry(extraction)
    selectors=dependencies['scientific_readings']
    readings=[roster[_selector_key(s)] for s in selectors]
    endpoint,endpoint_ids=_state(readings,'endpoint',common=True)
    normalization,normalization_ids=_state(readings,'normalization',common=True)
    subject,subject_ids=_state(readings,'subject_construct')
    condition,condition_ids=_state(readings,'condition')
    owner,owner_ids=_state(readings,'physical_observation')
    applications={'condition1':None,'condition0':None}
    if pair is not None:
        applications[pair['condition']]=pair['control_application']
    elif kind in ('final','conditional'):
        roles={s['role'] for s in selectors}
        for name in applications:
            if 'empty_'+name in roles and 'protein_'+name in roles:
                applications[name]=extraction['relationships'][name+'_control_application']['effective_value']
    known_apps=_unique(v for v in applications.values() if v is not None)
    relevant_roles={s['role'] for s in selectors}
    reuse=(extraction['relationships']['control_reference_reuse']['effective_value']
        if all('empty_'+c in relevant_roles for c in applications) else None)
    decisions=[row for row in extraction['reconciliation_decisions'] if row['role'] in relevant_roles]
    representation=('conditional' if kind=='conditional' else
        'unresolved' if any(row['state']!='ready' for row in decisions) else
        'reconciled' if any(len(row['reading_selectors'])>1 for row in decisions) else 'single')
    return {'endpoint_id':endpoint_ids[0] if endpoint=='known' and endpoint_ids else None,
        'normalization_id':normalization_ids[0] if normalization=='known' and normalization_ids else None,
        'subject_construct_ids':subject_ids,'condition_ids':condition_ids,'owner_ids':owner_ids,
        'owner_state':owner,'endpoint_state':endpoint,'normalization_state':normalization,
        'subject_construct_state':subject,'condition_state':condition,
        'control_application':known_apps[0] if len(known_apps)==1 else None,
        'condition_control_applications':applications,'control_reuse':reuse,
        'protein_arrangements':_unique(row['protein_arrangement']['effective_value'] for row in readings if row),
        'variance_status':variance,'model_kind':model,'representation_state':representation,
        'source_kinds':_unique(row['selection']['source_kind'] for row in readings if row),
        'original_origins':_unique(row['calculation_operand']['origin'] for row in readings if row),
        'measurement_methods':_unique('graph' if row['graph_details'] else
            'text' if row['selection']['measurement'] else 'not_selected' for row in readings if row)}


def _unavailable_joint_component(extraction,assignment,component,admissibility):
    """Preserve a nominated scope's absence of a numerical result.

    Scientific selectors describe the actual nomination. Empty evaluated
    numerical dependencies make no claim about a joint calculation, covariance
    cancellation or model fit that was never performed for this scope.
    """
    index=arithmetic.COMPONENTS.index(component)
    roles=([shared.PRIMITIVE_ORDER[index]] if index<4 else
           list(shared.PRIMITIVE_ORDER[:2]) if index==4 else
           list(shared.PRIMITIVE_ORDER[2:]) if index==5 else list(shared.PRIMITIVE_ORDER))
    selectors=[{'role':role,'reading_key':assignment[role]} for role in roles]
    roster=_registry(extraction)
    arms=[roster[_selector_key(selector)] for selector in selectors]
    operands=[arm['calculation_operand'] for arm in arms if arm is not None]
    qualifications=[]
    if any(arm['origin']=='synthetic' for arm in operands):qualifications.append('synthetic_fixture')
    if any(arm['approximate'] for arm in operands):qualifications.append('approximate_source_reading')
    if any(arm['digitization_interval'] is not None for arm in operands):qualifications.append('conditional_digitization')
    cell={'value':None,'lower':None,'upper':None,'relation':'none',
        'approximate':any(arm['approximate'] for arm in operands),'unit':None,'status':'unavailable','origin':None,
        'unavailable_reason':[admissibility+'_joint_applicability'],'formula_code':arithmetic._FORMULAS[index],
        'conditional_on':qualifications,'bound_kind':'none',
        'bound_state':{'lower':'not_applicable','upper':'not_applicable'}}
    dependencies={'scientific_readings':selectors,'numeric_readings':[],'uncertainty_readings':[],
        'covariance_index':None,'covariance_owner_ids':[],'source_variable_indices':[],'model_readings':[],
        'unresolved_readings':[cp(selector) for selector,arm in zip(selectors,arms)
            if arm is None or any(value!='known' for value in arm['calculation_operand']['meaning_statuses'].values())],
        'numeric_fields':[],'full_source_covariance_required':False}
    return cell,dependencies


def _component_rows(extraction, populated, sheet_ref):
    """Mechanical projections only. No source parse or numerical populator."""
    rows=[];roster=_registry(extraction);locations=_numeric_locations(extraction)
    def emit(key,kind,component,cell,dependencies,*,reading=None,assignment=None,pair=None,scope_context=None,
             native=None,uncertainty=None,uncertainty_unit=None,variance='unknown',model='none'):
        rows.append({'version':FACT_VERSION,'sheet_ref':sheet_ref,'component_key':key,
            'kind':kind,'component':component,'reading':cp(reading),'reading_assignment':cp(assignment),
            'pair_key':pair['pair_key'] if pair else None,'cell':cp(cell),'native_reading':cp(native),
            'reported_uncertainty':cp(uncertainty),'reported_uncertainty_unit':uncertainty_unit,'numeric_locations':cp(locations),
            'context':_context(extraction,dependencies,kind=kind,variance=variance,model=model,pair=pair),
            'dependencies':cp(dependencies),'joint_scope_context':cp(scope_context)})
    for raw in populated['local_sheet']['raw']:
        selector=raw['reading'];actual=roster[_selector_key(selector)]
        operand=actual['calculation_operand'] if actual else None
        native=None if operand is None else {k:cp(operand[k]) for k in
            ('value','threshold','relation','approximate','unit','status','origin','digitization_interval','source_observation_id')}
        carrier=actual['reported_uncertainty']['effective_unit'] if actual else None
        unit=carrier.get('record',carrier) if carrier else None
        emit(_raw_key(selector),'native_raw',selector['role']+'_response',raw['cell'],raw['dependencies'],
             reading=selector,native=native,uncertainty=raw['reported_uncertainty'],
             uncertainty_unit=unit['canonical_unit'] if unit and unit['status']=='supported' else None)
    nominations={row['pair_key']:row for row in extraction['component_local_inputs']['pairs']}
    for item in populated['local_sheet']['pairs']:
        pair=nominations[item['pair_key']]
        for name in ('difference','variance','standard_uncertainty'):
            kind='local_'+name
            emit('local:'+_token(item['pair_key'])+':'+name,kind,kind,item[name],item['dependencies'][name],
                 pair=pair,variance=pair['variance_status'] if name!='difference' else 'unknown')
    final=populated['final_sheet']
    if final is not None:
        assignment=extraction['final_projection_basis']['reading_assignment']
        covariance=extraction['covariance']
        scope_context=None
        if extraction['final_projection_basis']['covariance_scope']=='joint':
            scope_index=extraction['final_projection_basis']['scope_index']
            covariance=extraction['joint_scope_extractions'][scope_index]['source_covariance']
            scope_context=_joint_scope_context(extraction,scope_index)
            if scope_context['reading_assignment']!=assignment:raise ContractError('controlled_native_joint_scope_assignment_mismatch')
        for component in arithmetic.COMPONENTS:
            cell=final['cells'][component]
            dependencies=population._dependencies(extraction,final,assignment,component,covariance)
            index=arithmetic.COMPONENTS.index(component)
            emit('final:'+component,'final',component,cell,dependencies,
                 scope_context=scope_context,
                 variance=final['inputs']['variance_status'] if index>=7 else 'unknown',
                 model=final['inputs']['model_kind'] if index>=10 else 'none')
    alternatives={row['scope_index']:row for row in populated['alternatives']}
    for scope in extraction['joint_scope_extractions']:
        assignment_index=scope['assignment_index']
        scope_context=_joint_scope_context(extraction,assignment_index)
        if scope['effective_admissibility']!='compatible':
            assignment=extraction['selection']['joint_reading_assignments'][assignment_index]['assignment']
            for component in arithmetic.COMPONENTS:
                cell,dependencies=_unavailable_joint_component(extraction,assignment,component,scope['effective_admissibility'])
                emit('joint:'+str(assignment_index)+':'+component,'conditional',component,cell,dependencies,
                     assignment=assignment,scope_context=scope_context)
            continue
        alternative=alternatives[assignment_index]
        if alternative['reading_assignment']!=scope_context['reading_assignment']:
            raise ContractError('controlled_native_joint_scope_assignment_mismatch')
        inputs=alternative['sheet']['inputs']
        for item in populated['conditional_components']:
            if item['assignment_index']!=assignment_index:continue
            index=arithmetic.COMPONENTS.index(item['component'])
            emit('joint:'+str(assignment_index)+':'+item['component'],'conditional',item['component'],
                 item['cell'],item['dependencies'],assignment=alternative['reading_assignment'],
                 scope_context=scope_context,
                 variance=inputs['variance_status'] if index>=7 else 'unknown',
                 model=inputs['model_kind'] if index>=10 else 'none')
    _check(rows,controlled_response_cells_schema(),'controlled_native_projection_schema_invalid')
    return rows


class LiteratureControlledResponseRepository(LiteratureRatioSourceRepository):
    provider=PROVIDER;record_version=VERSION;components=COMPONENTS
    operations_table='literature_controlled_response_operations'
    received_table='literature_controlled_response_component_received'
    runtime_binding_table='literature_controlled_response_runtime_bindings'
    binding_fields=()

    def __init__(self,store,run_id,*,evidence_origin='reported_source',expected_descriptor=None):
        # Reuse only read-only-safe table installation/custody primitives.
        implementation_descriptor(evidence_origin=evidence_origin)
        super().__init__(store,run_id,evidence_origin=evidence_origin)
        if expected_descriptor is not None and canonical(expected_descriptor)!=canonical(self.descriptor()):
            raise ContractError('controlled_native_implementation_binding_mismatch')

    def descriptor(self):
        return implementation_descriptor(evidence_origin=self.evidence_origin)

    def _profile_selection(self,selection):
        """Bind the caller-declared execution profile, not publication truth."""
        arms=[*selection['arms'].values(),*[row['reading'] for row in selection['companion_readings']]]
        permitted=({'synthetic_fixture'} if self.evidence_origin=='synthetic_fixture'
                   else {'primary_source','retained_extraction'})
        if any(arm is not None and arm['source_kind'] not in permitted for arm in arms):
            raise ContractError('controlled_native_evidence_profile_mismatch')

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
            if required or bound is not None:raise ContractError('controlled_native_original_runtime_required')
            return None
        action=(self.store.db.execute('SELECT action,result FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? AND decision_index=?',(self.run_id,request['episode_id'],int(suffix))).fetchone()
            if self._has_table('runtime_actions') else None)
        if action is None:
            if required or bound is not None:raise ContractError('controlled_native_original_runtime_uncommitted')
            return None
        selected=json.loads(action['action'])
        if (set(selected)!={'kind','tool','arguments'} or selected['kind']!='tool'
                or selected['tool']!='literature.controlled_response.source_v3.populate'
                or canonical(selected['arguments'])!=canonical(request['arguments'])):
            raise ContractError('controlled_native_original_runtime_mismatch')
        episode=(self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,request['episode_id'])).fetchone() if self._has_table('runtime_episodes') else None)
        if episode is None:raise ContractError('controlled_native_original_runtime_episode_unavailable')
        original_request=json.loads(episode['request']);path=json.loads(episode['path'])
        message=original_request.get('message',{})
        if (not path or path[-1][0]!=signature['role'] or canonical(message.get('scope'))!=canonical(signature['scope'])
                or canonical(message.get('episode_assignment',{}))!=canonical(signature['assignment'])):
            raise ContractError('controlled_native_original_runtime_context_mismatch')
        if action['result'] is None:
            if required or bound is not None:raise ContractError('controlled_native_original_runtime_uncommitted')
            return None
        result=json.loads(action['result'])
        # DecisionSource adds only this legitimate runtime snapshot after the
        # repository commits its tool result. Every other field must be exact.
        tool_portion={name:value for name,value in result.items() if name!='pending_work_after_action'}
        if canonical(tool_portion)!=canonical(outcome):raise ContractError('controlled_native_original_runtime_mismatch')
        evidence={'run_id':self.run_id,'episode_id':request['episode_id'],'decision_index':int(suffix),
            'operation_key':request['operation_key'],'action':selected,'result':result,
            'request':original_request,'path':path}
        digest=_sha(evidence)
        if bound is not None and bound['runtime_digest']!=digest:
            raise ContractError('controlled_native_original_runtime_digest_mismatch')
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
            raise ContractError('controlled_native_original_runtime_context_mismatch')
        if bound:return
        if self.store.db.execute('PRAGMA query_only').fetchone()[0]:
            raise ContractError('controlled_native_original_runtime_binding_unavailable')
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
                raise ContractError('controlled_native_original_runtime_binding_unavailable') from error
            raise

    def _sources(self,context,selection):
        pairs=shared._reference_closure(selection)
        direct=sorted({ref for ref,representation in pairs})
        for ref in direct:self._source(context,ref)
        closure=list(direct)
        for ref in closure:
            record=self._source(context,ref,direct=False)
            for parent in record.get('parent_source_refs',()):
                self._source(context,parent,direct=False)
                if parent not in closure:closure.append(parent)
        return pairs,direct,closure

    def _bindings(self,extraction,publish=None):
        result={}
        for reading in _registry(extraction).values():
            if reading is None:continue
            for category,meaning in reading['meanings'].items():
                cid=meaning['canonical_id'];w=meaning['canonical_witness']
                if meaning['resolved_state']!='known' or cid is None or w is None:continue
                locator=w['canonical_locator'];selected=w['selection']
                raw=selected.get('quote',selected.get('text','source-bound '+category))
                label=' '.join(raw.split())
                if len(label)>512:label=label[:509]+'...'
                anchor=None
                if locator and locator['kind']=='text' and 'quote' in selected and len(selected['quote'])<=16000:
                    anchor={k:locator[k] for k in ('source_ref','artifact_ref','start','end')}
                    anchor['quote']=selected['quote']
                value={'reference_type':'literature_result','source_ref':locator.get('source_ref',locator.get('original_source_ref')),
                    'accession':cid,'label':label,'sequence_ref':None,'molecule':None,'length':None,
                    'term_refs':[],'context_refs':[],'anchor':anchor}
                reference=identity('reference',{'origin':'tool','record':value})
                if publish:assert publish('reference',value)==reference
                else:
                    actual=self._record(reference,'reference')
                    if canonical({k:v for k,v in actual.items() if k not in ('id','record_type','origin')})!=canonical(value):
                        raise ContractError('controlled_native_semantic_binding_mismatch')
                row=result.setdefault(cid,{'canonical_id':cid,'category':category,'record_ref':reference,
                    'canonical_witness_location':cp(locator),'meanings':[]})
                if row['record_ref']!=reference:raise ContractError('controlled_native_semantic_binding_conflict')
                if canonical(meaning) not in {canonical(v) for v in row['meanings']}:row['meanings'].append(cp(meaning))
        return result

    def _scope_bindings(self,extraction,publish=None):
        result={}
        for witness in _scope_witnesses(extraction):
            reference,value=_scope_reference(extraction,witness)
            if publish:
                if publish('reference',value)!=reference:raise ContractError('controlled_native_scope_binding_mismatch')
            else:
                actual=self._record(reference,'reference')
                if canonical({k:v for k,v in actual.items() if k not in ('id','record_type','origin')})!=canonical(value):
                    raise ContractError('controlled_native_scope_binding_mismatch')
            row={'record_ref':reference,'category':'joint_scope_witness',
                'canonical_witness_location':cp(witness['canonical_locator']),'witness':cp(witness)}
            if reference in result and result[reference]!=row:raise ContractError('controlled_native_scope_binding_mismatch')
            result[reference]=row
        return result

    def populate_v3(self,context,arguments,operation_key):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:raise ContractError('operation_key_required')
        args=source.validate_controlled_response_v3_selection(plain(arguments))
        self._profile_selection(args)
        pairs,direct,closure=self._sources(context,args)
        descriptor=self.descriptor()
        signature=canonical({'arguments':args,'scope':plain(context.scope),'role':context.role,
                             'assignment':plain(context.assignment),'implementation_descriptor':descriptor,
                             'evidence_origin':self.evidence_origin})
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone()
        if old:
            if old['signature']!=signature:raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome']);self.read(outcome['result']['sheet_ref']);return outcome
        associations=[]
        def read_source(ref,representation):
            record=self._source(context,ref)
            artifact=record['artifact_ref'] if representation=='original' else record.get('text_ref')
            associations.append({'source_ref':ref,'representation':representation,'artifact_ref':artifact,
                                 'sha256':artifact.removeprefix('artifact_') if artifact else None})
            if artifact is None:raise FileNotFoundError(errno.ENOENT,'selected representation unavailable')
            data=self._bytes(artifact)
            return {'artifact_ref':artifact,'content':data}
        extraction=source.read_controlled_response_v3_inputs(args,read_source=read_source)
        populated=population.populate_controlled_response_v3(extraction)
        with self.store.transaction():
            created=[]
            def publish(kind,value):
                ref=identity(kind,{'origin':'tool','record':value})
                old=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(ref,)).fetchone()
                actual=self.store.put(kind,value,origin='tool',scope=plain(context.scope))
                if old is None:created.append(ref)
                return actual['id']
            bindings=self._bindings(extraction,publish)
            scope_bindings=self._scope_bindings(extraction,publish)
            # Roster keys do not depend on sheet_ref; the real sheet reference
            # is inserted only into the immutable selected outcome projection.
            roster=_component_rows(extraction,populated,'source_'+'0'*24)
            payload={'version':VERSION,'selection':args,'extraction':extraction,'population':populated,
                'evidence_origin':self.evidence_origin,
                'component_roster':[row['component_key'] for row in roster],'semantic_bindings':bindings,
                'scope_witness_bindings':scope_bindings,
                'input_source_ref':args['source_ref'],'input_artifact_ref':self._record(args['source_ref'],'source')['artifact_ref'],
                'direct_input_source_refs':direct,'input_source_refs':closure,'source_associations':associations,
                'implementation_descriptor':descriptor}
            artifact=self.store.artifact(canonical(payload),'application/json')
            request=self.store.artifact(canonical({'run_id':self.run_id,'episode_id':context.episode_id,
                'operation_key':operation_key,'arguments':args,'signature':json.loads(signature)}),'application/json')
            sheet_ref=publish('source',{'provider':PROVIDER,'accession':None,'uri':None,'artifact_ref':artifact,
                'text_ref':artifact,'request_ref':request,'version':VERSION,'retrieved_at':None,'parent_source_refs':closure})
            rows=_component_rows(extraction,populated,sheet_ref)
            outcome={'status':'completed','operation_ref':identity('operation',{'run_id':self.run_id,
                'episode_id':context.episode_id,'key':operation_key}),
                'record_refs':[sheet_ref,*_unique(row['record_ref'] for row in [*bindings.values(),*scope_bindings.values()])],
                'changed_record_refs':created,'result':{'sheet_ref':sheet_ref,'projection_status':extraction['projection_status'],
                'component_keys':payload['component_roster'],'cells':rows,'payload_sha256':_sha(payload)},'feedback':None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return cp(outcome)

    def populate(self,context,arguments,operation_key):
        return self.populate_v3(context,arguments,operation_key)

    def read(self,sheet_ref):
        record=self._record(sheet_ref,'source')
        if (record['provider']!=PROVIDER or record['origin']!='tool' or record['version']!=VERSION
                or record['text_ref']!=record['artifact_ref'] or not record.get('request_ref')):
            raise ContractError('controlled_native_source_required')
        request=self._json(record['request_ref'])
        if (set(request)!={'run_id','episode_id','operation_key','arguments','signature'}
                or request['run_id']!=self.run_id):raise ContractError('controlled_native_request_mismatch')
        operation=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone()
        if operation is None:raise ContractError('literature_sheet_not_selected_output')
        outcome=json.loads(operation['outcome']);payload=self._json(record['artifact_ref'])
        signature=json.loads(operation['signature'])
        if (set(payload)!=_PAYLOAD_FIELDS or payload['version']!=VERSION
                or canonical(signature)!=canonical(request['signature'])
                or canonical(signature['arguments'])!=canonical(request['arguments'])
                or canonical(payload['selection'])!=canonical(request['arguments'])
                or canonical(signature['implementation_descriptor'])!=canonical(payload['implementation_descriptor'])
                or signature.get('evidence_origin')!=payload['evidence_origin']
                or payload['implementation_descriptor'].get('evidence_origin')!=payload['evidence_origin']
                or outcome['result']['sheet_ref']!=sheet_ref or outcome['result']['payload_sha256']!=_sha(payload)
                or outcome['operation_ref']!=identity('operation',{'run_id':self.run_id,'episode_id':request['episode_id'],'key':request['operation_key']})
                or record['parent_source_refs']!=payload['input_source_refs']):
            raise ContractError('controlled_native_original_outcome_mismatch')
        if set(signature)!={'arguments','scope','role','assignment','implementation_descriptor','evidence_origin'}:
            raise ContractError('controlled_native_original_request_invalid')
        if payload['evidence_origin']!=self.evidence_origin:
            raise ContractError('controlled_native_evidence_profile_mismatch')
        self._profile_selection(payload['selection'])
        fingerprints=payload['extraction']['implementation_dependencies']['expected_module_fingerprints']
        if any(payload['implementation_descriptor']['modules'].get(name)!=pin for name,pin in fingerprints.items()):
            raise ContractError('controlled_native_source_implementation_binding_mismatch')
        self._runtime_original(request,signature,outcome)
        # Recheck the ORIGINAL authorized source/page/scope closure against
        # immutable records only. Scientific source bytes remain unopened.
        context=SimpleNamespace(run_id=self.run_id,episode_id=request['episode_id'],
            scope=signature['scope'],role=signature['role'],assignment=signature['assignment'],
            received_record_refs=tuple(payload['direct_input_source_refs']))
        pairs,direct,closure=self._sources(context,payload['selection'])
        original=self._record(payload['selection']['source_ref'],'source')
        if (payload['input_source_ref']!=payload['selection']['source_ref']
                or payload['input_artifact_ref']!=original['artifact_ref']
                or payload['direct_input_source_refs']!=direct or payload['input_source_refs']!=closure
                or [(a['source_ref'],a['representation']) for a in payload['source_associations']]!=pairs):
            raise ContractError('controlled_native_original_source_closure_mismatch')
        source.validate_controlled_response_v3_extraction(payload['selection'],payload['extraction'])
        _check(payload['population'],source._schemas()['POPULATION_SCHEMA_V3_007'],'controlled_native_population_schema_invalid')
        bindings=self._bindings(payload['extraction'])
        if canonical(bindings)!=canonical(payload['semantic_bindings']):raise ContractError('controlled_native_semantic_binding_mismatch')
        scope_bindings=self._scope_bindings(payload['extraction'])
        if canonical(scope_bindings)!=canonical(payload['scope_witness_bindings']):raise ContractError('controlled_native_scope_binding_mismatch')
        for association in payload['source_associations']:
            original=self._record(association['source_ref'],'source')
            artifact=original['artifact_ref'] if association['representation']=='original' else original.get('text_ref')
            if (artifact!=association['artifact_ref'] or
                    (artifact is None and association['sha256'] is not None) or
                    (artifact is not None and artifact!='artifact_'+association['sha256'])):
                raise ContractError('controlled_native_source_association_mismatch')
            if artifact is not None:self._artifact_metadata(artifact)
        expected=_component_rows(payload['extraction'],payload['population'],sheet_ref)
        if (canonical(expected)!=canonical(outcome['result']['cells'])
                or [row['component_key'] for row in expected]!=payload['component_roster']
                or outcome['result']['component_keys']!=payload['component_roster']):
            raise ContractError('controlled_native_original_projection_mismatch')
        return cp(payload)

    def project_cells(self,sheet_refs,*,permitted_record_refs,components):
        if not isinstance(components,(list,tuple)) or any(type(k) is not str for k in components) or len(set(components))!=len(components):
            raise ContractError('controlled_native_component_keys_required')
        result=[]
        for ref in _unique(sheet_refs):
            if ref not in permitted_record_refs:raise ContractError('literature_sheet_not_received')
            saved=self.read(ref)
            roster={row['component_key']:row for row in _component_rows(saved['extraction'],saved['population'],ref)}
            if any(key not in roster for key in components):raise ContractError('controlled_native_component_key_unknown')
            result.extend(cp(roster[key]) for key in components)
        return result

    def requested_component_keys(self,sheet_ref,assignment):
        saved=self.read(sheet_ref);assignment=plain(assignment)
        names=assignment.get('requested_controlled_response_components',[])
        views=assignment.get('requested_controlled_response_views',[])
        for values,allowed in ((names,COMPONENTS),(views,VIEWS)):
            if not isinstance(values,list) or any(type(v) is not str or v not in allowed for v in values) or len(set(values))!=len(values):
                raise ContractError('controlled_native_request_selection_invalid')
        rows=_component_rows(saved['extraction'],saved['population'],sheet_ref)
        allowed=[row['component_key'] for row in rows if row['component'] in names and row['kind'] in views]
        keys=assignment.get('requested_controlled_response_component_keys')
        if keys is None:return allowed
        if not isinstance(keys,list) or len(set(keys))!=len(keys) or any(type(k) is not str or k not in allowed for k in keys):
            raise ContractError('controlled_native_requested_key_unresolved')
        return list(keys)

    def validate_returned_values(self,cells,*,permitted_record_refs):
        _check(cells,controlled_response_cells_schema(),'controlled_native_cells_schema_invalid')
        seen=set();expected={}
        for row in cells:
            key=(row['sheet_ref'],row['component_key'])
            if key in seen:raise ContractError('duplicate_controlled_native_cell')
            seen.add(key)
        for ref in _unique(row['sheet_ref'] for row in cells):
            projected=self.project_cells([ref],permitted_record_refs=permitted_record_refs,
                components=[r['component_key'] for r in cells if r['sheet_ref']==ref])
            expected.update({(r['sheet_ref'],r['component_key']):r for r in projected})
        if any(canonical(row)!=canonical(expected[(row['sheet_ref'],row['component_key'])]) for row in cells):
            raise ContractError('controlled_native_cell_differs_from_original')

    def fact_cells(self,context,sheet_refs,*,components):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        self.project_cells([],permitted_record_refs=(),components=components)
        received=None;result=[]
        for ref in _unique(sheet_refs):
            if ref not in context.received_record_refs:raise ContractError('literature_sheet_not_received')
            saved=self.read(ref)
            record=self._record(ref,'source');request=self._json(record['request_ref'])
            if request['episode_id']==context.episode_id:
                self._bind_native_output(context,ref)
                result.extend(self.project_cells([ref],permitted_record_refs=context.received_record_refs,components=components))
            else:
                if received is None:received={(r['sheet_ref'],r['component_key']):r for r in self.received_cells(context)}
                result.extend(cp(received[(ref,key)]) for key in components if (ref,key) in received)
        return result

    def validate_fact_values(self,context,cells):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        self.validate_returned_values(cells,permitted_record_refs=context.received_record_refs)
        for ref in _unique(row['sheet_ref'] for row in cells):
            subset=[row for row in cells if row['sheet_ref']==ref]
            allowed=self.requested_component_keys(ref,context.assignment)
            if any(row['component_key'] not in allowed for row in subset):raise ContractError('controlled_native_cell_not_requested')
            expected=self.fact_cells(context,[ref],components=[row['component_key'] for row in subset])
            if canonical(expected)!=canonical(subset):raise ContractError('literature_cell_not_received')

    def _runtime_evidence(self,context,operation_key):
        rows=self._runtime_delivery_cells(context,operation_key)
        if rows is None:raise ContractError('controlled_native_runtime_admission_required')
        index=int(operation_key[len(self.run_id+':'+context.episode_id+':'):].split(':')[0])
        attempt=self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id,context.episode_id,index)).fetchone()
        child=self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,attempt['child_episode_id'])).fetchone()
        parent=self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id,context.episode_id)).fetchone()
        if child is None or parent is None or json.loads(child['path'])[:-1]!=json.loads(parent['path']):
            raise ContractError('controlled_native_delivery_child_mismatch')
        parent_request=json.loads(parent['request']);child_request=json.loads(child['request'])
        parent_path=json.loads(parent['path']);child_path=json.loads(child['path'])
        message=parent_request['message']
        if (plain(context.path)!=parent_path or context.role!=parent_path[-1][0]
                or plain(context.scope)!=message['scope']
                or plain(context.assignment)!=message.get('episode_assignment',{})):
            raise ContractError('controlled_native_delivery_parent_context_mismatch')
        if not self.store.scope_contains(message['scope'],child_request['message']['scope']):
            raise ContractError('controlled_native_delivery_child_scope_mismatch')
        # Read the ordinary frozen receipt lineage without installing tables or
        # inventing a manual possession declaration for this new return view.
        if not all(self._has_table(name) for name in ('runtime_receipt_inheritance','runtime_record_receipts')):
            raise ContractError('controlled_native_reporting_possession_unavailable')
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

    def semantic_bindings(self,cells):
        self.validate_returned_values(cells,permitted_record_refs=[r['sheet_ref'] for r in cells])
        result={};saved_by_ref={}
        for row in cells:
            context=row['context'];ids=_unique([context['endpoint_id'],context['normalization_id'],
                *context['subject_construct_ids'],*context['condition_ids'],*context['owner_ids']])
            if row['sheet_ref'] not in saved_by_ref:saved_by_ref[row['sheet_ref']]=self.read(row['sheet_ref'])
            saved=saved_by_ref[row['sheet_ref']]
            target=result.setdefault(row['sheet_ref'],{})
            for cid in ids:
                if cid is not None and cid in saved['semantic_bindings']:
                    binding=saved['semantic_bindings'][cid]
                    target[cid]={k:cp(binding[k]) for k in ('record_ref','category','canonical_witness_location')}
            scope=row['joint_scope_context']
            if scope is not None:
                relations=[scope['assignment_admissibility'],*[scope[name] for name in (
                    'normalization','calibration','revision','covariance_scope','model_scope')],*scope['requested_model'].values()]
                for relation in relations:
                    for witness in relation['witnesses']:
                        ref=witness['witness_ref'];binding=saved['scope_witness_bindings'].get(ref)
                        if binding is None:raise ContractError('controlled_native_scope_binding_mismatch')
                        target[ref]={k:cp(binding[k]) for k in ('record_ref','category','canonical_witness_location')}
        return result

    def cell_record_refs(self,cells):
        bindings=self.semantic_bindings(cells)
        return _unique([*(row['sheet_ref'] for row in cells),
            *(entry['record_ref'] for sheet in bindings.values() for entry in sheet.values()),
            *(row['joint_scope_context']['covariance_context']['source_ref'] for row in cells
                if row['joint_scope_context'] is not None and row['joint_scope_context']['covariance_context'] is not None)])


__all__=['LiteratureControlledResponseRepository','controlled_response_population_schema',
         'controlled_response_cells_schema','implementation_descriptor','COMPONENTS','VIEWS','PROVIDER']
