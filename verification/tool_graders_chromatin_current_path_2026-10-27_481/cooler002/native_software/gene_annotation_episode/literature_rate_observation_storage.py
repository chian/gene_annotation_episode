"""Selected source-cell operation, saved numerical sheet and exact subset custody."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_rate_observation_inputs import (VERSION as INPUT_VERSION, SOURCE_KINDS, TEXT, STATUSES,
    ENTRY_REASONS, label_schema, rate_observation_population_schema, read_rate_observations,
    entry_meaning, validate_selected_layout)
from .literature_rate_observation_calculations import (VERSION as SHEET_VERSION, COMPONENTS,
    REASONS, FORMULAS, QUALIFICATIONS, populate_rate_observation_contrast)

PROVIDER='literature.a105.reported_rate_observations'
VERSION='literature_reported_rate_observation_record_v1'
NAMESPACE='literature_rate_observation_cells'
REQUESTED='requested_rate_observation_components'
VIEW='reported_rate_observation_components'
ALL_REASONS=(*REASONS,*ENTRY_REASONS)


def _array(schema,unique=False):
    return {'type':'array','items':deepcopy(schema),**({'uniqueItems':True} if unique else {})}


def _nullable(schema):
    return {'anyOf':[deepcopy(schema),{'type':'null'}]}


def _exact():
    return _nullable(obj({'numerator':{'type':'string','pattern':'^-?[0-9]+$'},
        'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}}))


def _custody():
    return obj({name:deepcopy(TEXT) for name in ('source_ref','artifact_ref','workbook_sha256','worksheet','member','member_sha256')})


def _witness():
    formula=obj({'text':{'type':['string','null']},'attributes':{'type':'object','additionalProperties':{'type':'string'}}})
    return obj({**_custody()['properties'],'cell':deepcopy(TEXT),'cell_type':deepcopy(TEXT),
        **{name:{'type':['string','null']} for name in ('value','raw_value','style_index','error')},
        'formula':_nullable(formula),'value_is_formula_cache':{'type':'boolean'}})


def _cell():
    return obj({'value':{'type':['number','null']},'unit':deepcopy(TEXT),
        'formula':{'enum':list(dict.fromkeys(FORMULAS.values()))},'origin':{'const':'derived'},
        'status':{'enum':['populated','unavailable']},'unavailable_reason':{'enum':[*ALL_REASONS,None]},
        'source_exact_value':_exact()})


def _entry():
    meaning=obj({name:deepcopy(TEXT) for name in ('source_ref','artifact_ref','worksheet','panel','subject','native_unit','group','observation_label',
        'panel_cell','subject_cell','native_unit_cell','group_cell','label_cell','value_cell')})
    return obj({'record_identity':deepcopy(TEXT),'meaning':meaning,'group':deepcopy(TEXT),'label':deepcopy(TEXT),
        'status':{'enum':list(STATUSES)},'unavailable_reason':{'enum':[*ENTRY_REASONS,None]},
        'bound':{'enum':['none','<','>','<=','>=','≤','≥']},'exact_value':_exact(),
        'origin':{'enum':['reported','synthetic']},
        **{name:_witness() for name in ('group_source','label_source','value_source')}})


def _group(numeric=False):
    observation=obj({'record_identity':deepcopy(TEXT),'label':deepcopy(TEXT),'status':{'enum':list(STATUSES)},
        'conflicting':{'type':'boolean'},'unavailable_reason':{'enum':[*ENTRY_REASONS,None]},
        'label_source':_witness(),'group_source':_witness()})
    fields={'label':deepcopy(TEXT),**{name:{'type':'integer','minimum':0} for name in
        ('entry_count','representation_count','point_entry_count')},'complete':{'type':'boolean'},
        'observation_labels':_array(observation),'limitations':_array({'enum':list(ALL_REASONS)},True)}
    if numeric:
        fields['cells']=obj({name:_cell() for name in ('rate','sample_sd','cv','observed_point_mean','observed_point_sd')})
    return obj(fields)


def _sheet_schema():
    extraction=obj({'version':{'const':INPUT_VERSION},'source_kind':{'enum':list(SOURCE_KINDS)},
        'custody':_custody(),'meanings':obj({name:_witness() for name in ('panel','subject','native_unit')}),
        'entries':_array(_entry()),'grouping':{'const':'unknown'},'physical_conversion':{'const':'unknown'}})
    return obj({'version':{'const':SHEET_VERSION},'axis':{'const':'A105'},
        'scope':{'const':'source_reported_entry_endpoint'},'extraction':extraction,'groups':_array(_group(True)),
        'reference_group':deepcopy(TEXT),'test_group':deepcopy(TEXT),'cells':obj({name:_cell() for name in COMPONENTS}),
        'qualifications':{'const':list(QUALIFICATIONS)},**{name:{'type':'null'} for name in
            ('preparation_count','between_preparation_sd','mean_se','difference_se','corrected_activity','annotation_credit','assay_error_rate')}})


def _project_saved(saved,reference,components):
    sheet=saved['sheet'];data=sheet['extraction']
    groups={}
    for role in ('reference','test'):
        name=sheet[role+'_group']
        group=next((g for g in sheet['groups'] if g['label']==name),None)
        groups[role]={'requested_label':name,'status':'observed' if group else 'not_observed',
            'observed':None if group is None else {k:deepcopy(v) for k,v in group.items() if k!='cells'},
            'observation_labels':[] if group is None else deepcopy(group['observation_labels'])}
    origins=list(dict.fromkeys(e['origin'] for e in data['entries'] if e['group'] in
        (sheet['reference_group'],sheet['test_group'])))
    return [{'sheet_ref':reference,'evidence_source_ref':saved['input_source_ref'],
        'evaluation_scope':'source_reported_rate_observations','component':name,**deepcopy(sheet['cells'][name]),
        'subject':data['meanings']['subject']['value'],'panel':data['meanings']['panel']['value'],
        'source_native_unit':data['meanings']['native_unit']['value'],'source_kind':data['source_kind'],
        'groups':deepcopy(groups),'grouping':'unknown','physical_conversion':'unknown',
        'qualifications':deepcopy(sheet['qualifications']),'input_origins':origins} for name in components]


def rate_observation_cells_schema():
    ref={'type':'string','format':'reference','x-reference-namespace':'source'}
    group=obj({'requested_label':deepcopy(TEXT),'status':{'enum':['observed','not_observed']},
        'observed':_nullable(_group()),'observation_labels':_array(_group()['properties']['observation_labels']['items'])})
    row=obj({'sheet_ref':deepcopy(ref),'evidence_source_ref':deepcopy(ref),
        'evaluation_scope':{'const':'source_reported_rate_observations'},'component':{'enum':list(COMPONENTS)},
        **_cell()['properties'],**{name:deepcopy(TEXT) for name in ('subject','panel','source_native_unit')},
        'source_kind':{'enum':list(SOURCE_KINDS)},'groups':obj({role:deepcopy(group) for role in ('reference','test')}),
        'grouping':{'const':'unknown'},'physical_conversion':{'const':'unknown'},
        'qualifications':{'const':list(QUALIFICATIONS)},'input_origins':_array({'enum':['reported','synthetic']},True)})
    return {**_array(row),'x-source':NAMESPACE}


class LiteratureRateObservationRepository(LiteratureRateRepository):
    """Reuse existing authenticated admission; original XLSX never reread at return."""
    provider,components,record_version=PROVIDER,COMPONENTS,VERSION
    operations_table='literature_rate_observation_operations'
    received_table='literature_rate_observation_received'
    binding_fields=()

    def __init__(self,store,run_id):
        if not isinstance(run_id,str) or not run_id:raise ValueError('explicit_literature_run_required')
        self.store,self.run_id=store,run_id

    def _installed(self,table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store,self.run_id)

    @staticmethod
    def _components(components):
        if (not isinstance(components,(list,tuple)) or any(type(n) is not str or n not in COMPONENTS for n in components)
                or len(set(components))!=len(components)):
            raise ContractError('literature_rate_observation_component_selection_invalid')
        return list(components)

    def _ancestors(self,scope,reference):
        result=[reference]
        for current in result:
            for parent in self._native_provenance(scope,current).get('parent_source_refs',()):
                if parent not in result:result.append(parent)
        return result

    def populate(self,context,arguments,operation_key):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key,str) or not operation_key:raise ContractError('operation_key_required')
        args=plain(arguments);validate_schema(args,rate_observation_population_schema())
        source=self._native_source(context,args['source_ref'])
        requested=self._components(plain(context.assignment.get(REQUESTED,[])))
        request={'run_id':self.run_id,'episode_id':context.episode_id,'operation_key':operation_key,
            'arguments':args,'scope':plain(context.scope),'components':requested}
        signature=canonical(request)
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature']!=signature:raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome']);self.read(outcome['result']['sheet_ref'])
            return outcome
        artifact=source['artifact_ref']
        extraction=read_rate_observations(self.store.get_artifact(artifact),args,artifact_ref=artifact)
        sheet=populate_rate_observation_contrast(extraction,reference_group=args['reference_group'],test_group=args['test_group'])
        validate_schema(sheet,_sheet_schema())
        ancestors=self._ancestors(context.scope,args['source_ref'])
        payload={'version':VERSION,'input_source_ref':args['source_ref'],'input_artifact_ref':artifact,
            'input_source_refs':ancestors,'selection':args,'sheet':sheet}
        with self.store.transaction():
            self._install()
            sheet_artifact=self.store.artifact(canonical(payload),'application/json')
            request_ref=self.store.artifact(canonical(request),'application/json')
            value={'provider':PROVIDER,'accession':None,'uri':None,'artifact_ref':sheet_artifact,'text_ref':sheet_artifact,
                'request_ref':request_ref,'version':VERSION,'retrieved_at':None,'parent_source_refs':ancestors}
            reference=identity('source',{'origin':'tool','record':value})
            existed=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(reference,)).fetchone()
            self.store.put('source',value,origin='tool',scope=plain(context.scope))
            outcome={'status':'completed','operation_ref':identity('operation',{'run_id':self.run_id,'episode_id':context.episode_id,'key':operation_key}),
                'record_refs':[reference],'changed_record_refs':[] if existed else [reference],
                'result':{'sheet_ref':reference,'view':VIEW,'cells':_project_saved(payload,reference,requested)},'feedback':None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return outcome

    def _json_artifact(self,reference):
        content=self.store.get_artifact(reference)
        if 'artifact_'+hashlib.sha256(content).hexdigest()!=reference:
            raise ContractError('rate_observation_saved_artifact_hash_mismatch')
        try:return json.loads(content)
        except (TypeError,ValueError) as error:raise ContractError('rate_observation_saved_json_invalid') from error

    def read(self,sheet_ref):
        """Authenticate original closed saved rows, without scientific IO or math."""
        source=self.store.get(sheet_ref)
        value={k:v for k,v in source.items() if k not in ('id','record_type','origin')}
        if (source.get('record_type')!='source' or source.get('origin')!='tool' or source.get('provider')!=PROVIDER
                or source.get('version')!=VERSION or identity('source',{'origin':'tool','record':value})!=sheet_ref):
            raise ContractError('literature_rate_observation_sheet_required')
        request=self._json_artifact(source['request_ref'])
        if set(request)!={'run_id','episode_id','operation_key','arguments','scope','components'} or request['run_id']!=self.run_id:
            raise ContractError('rate_observation_saved_request_mismatch')
        validate_schema(request['arguments'],rate_observation_population_schema());self._components(request['components'])
        operation=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature']!=canonical(request):raise ContractError('literature_sheet_not_selected_output')
        saved=self._json_artifact(source['artifact_ref'])
        if (set(saved)!={'version','input_source_ref','input_artifact_ref','input_source_refs','selection','sheet'}
                or saved['version']!=VERSION or saved['selection']!=request['arguments']
                or saved['input_source_ref']!=request['arguments']['source_ref'] or saved['input_source_refs']!=source['parent_source_refs']):
            raise ContractError('rate_observation_saved_selection_mismatch')
        validate_schema(saved['sheet'],_sheet_schema());self._validate_saved_bindings(saved,request)
        outcome=json.loads(operation['outcome'])
        expected={'sheet_ref':sheet_ref,'view':VIEW,'cells':_project_saved(saved,sheet_ref,request['components'])}
        if (outcome.get('status')!='completed' or canonical(outcome.get('result'))!=canonical(expected)
                or outcome.get('record_refs')!=[sheet_ref] or outcome.get('feedback') is not None
                or outcome.get('operation_ref')!=identity('operation',{'run_id':self.run_id,'episode_id':request['episode_id'],'key':request['operation_key']})):
            raise ContractError('rate_observation_saved_outcome_mismatch')
        return saved

    def _validate_saved_bindings(self,saved,request):
        args= saved['selection'];sheet=saved['sheet'];data=sheet['extraction'];custody=data['custody']
        original=self._native_provenance(request['scope'],saved['input_source_ref'])
        if (original['artifact_ref']!=saved['input_artifact_ref'] or self._ancestors(request['scope'],saved['input_source_ref'])!=saved['input_source_refs']
                or custody['source_ref']!=saved['input_source_ref'] or custody['artifact_ref']!=saved['input_artifact_ref']
                or 'artifact_'+custody['workbook_sha256']!=saved['input_artifact_ref'] or custody['worksheet']!=args['worksheet']
                or data['source_kind']!=args['source_kind'] or sheet['reference_group']!=args['reference_group'] or sheet['test_group']!=args['test_group']):
            raise ContractError('rate_observation_saved_source_binding_mismatch')
        def check(witness,selector):
            if (any(witness[k]!=v for k,v in custody.items()) or witness['cell']!=selector['cell']
                    or witness['value']!=selector['expected_text'] or witness['formula'] is not None):
                raise ContractError('rate_observation_saved_label_binding_mismatch')
        for name in ('panel','subject','native_unit'):check(data['meanings'][name],args[name])
        validate_selected_layout(args)
        roster=[(g,e) for g in args['groups'] for e in g['observations']]
        if len(roster)!=len(data['entries']):raise ContractError('rate_observation_saved_roster_mismatch')
        for entry,(g,e) in zip(data['entries'],roster):
            check(entry['group_source'],g['label']);check(entry['label_source'],e['label'])
            meaning=entry_meaning(args,saved['input_artifact_ref'],g,e)
            expected_origin='synthetic' if args['source_kind']=='synthetic_fixture' else 'reported'
            if (entry['meaning']!=meaning or entry['group']!=meaning['group'] or entry['label']!=meaning['observation_label']
                    or entry['record_identity']!=identity('source_reported_entry',meaning) or entry['origin']!=expected_origin
                    or entry['value_source']['cell']!=e['value_cell']
                    or any(entry['value_source'][k]!=v for k,v in custody.items())
                    or (entry['exact_value'] is not None)!=(entry['status']=='observed')):
                raise ContractError('rate_observation_saved_entry_binding_mismatch')
        labels=list(dict.fromkeys(e['group'] for e in data['entries']))
        if [g['label'] for g in sheet['groups']]!=labels:raise ContractError('rate_observation_saved_group_binding_mismatch')
        for group in sheet['groups']:
            entries=[e for e in data['entries'] if e['group']==group['label']]
            unique={}
            for entry in entries:unique.setdefault(entry['record_identity'],entry)
            if (group['entry_count']!=len(unique) or group['representation_count']!=len(entries)
                    or [e['record_identity'] for e in group['observation_labels']]!=list(unique)
                    or group['point_entry_count']!=sum(e['status']=='observed' and not e['conflicting'] for e in group['observation_labels'])):
                raise ContractError('rate_observation_saved_group_binding_mismatch')
        for cell in sheet['cells'].values():
            if ((cell['value'] is None)!=(cell['status']=='unavailable')
                    or (cell['unavailable_reason'] is None)!=(cell['status']=='populated')):
                raise ContractError('rate_observation_saved_cell_binding_mismatch')

    def project_cells(self,sheet_refs,*,permitted_record_refs,components=None):
        selected=self._components(COMPONENTS if components is None else components)
        result=[]
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:raise ContractError('literature_sheet_not_received')
            result.extend(_project_saved(self.read(reference),reference,selected))
        return result

    def fact_cells(self,context,sheet_refs,*,components):
        refs=list(dict.fromkeys(sheet_refs))
        if self.store.reference_subset(refs,plain(context.scope))!=refs:raise ContractError('literature_source_outside_scope')
        return super().fact_cells(context,refs,components=components)

    def received_cells(self,context):
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self,context,cells,operation_key):
        with self.store.transaction():
            self._install();return super().receive_cells(context,cells,operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in (row['sheet_ref'],row['evidence_source_ref'])))
