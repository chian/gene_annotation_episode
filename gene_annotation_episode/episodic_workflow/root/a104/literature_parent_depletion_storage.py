"""Selected XLSX parent-depletion section of the one A105 worksheet.

The source is parsed and arithmetic is performed only at the selected action.
Cold reads validate committed identities and project saved cells without
opening the workbook or rerunning the parser/calculator.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_parent_depletion_inputs import parent_depletion_population_schema, read_parent_depletion_inputs
from .literature_parent_depletion_calculations import COMPONENTS, populate_parent_depletion_components
from .literature_rate_storage import LiteratureRateRepository

PROVIDER='literature.a105.parent_depletion_population'
VERSION='literature_parent_depletion_record_v1'
NAMESPACE='literature_parent_depletion_cells'
REQUESTED='requested_parent_depletion_components'


def parent_depletion_cells_schema():
    ref={'type':'string','format':'reference','x-reference-namespace':'source'}
    artifact={'type':'string','format':'reference','x-reference-namespace':'artifact'}
    text={'type':'string'}
    return {'type':'array','x-source':NAMESPACE,'items':obj({
        'sheet_ref':ref,'evidence_source_ref':ref,'workbook_artifact_ref':artifact,
        'component':{'type':'string','enum':list(COMPONENTS)},'evaluation_scope':{'type':'string','const':'finite_parent_compound_removal'},
        'value':{'type':'number'},'exact_decimal':text,'unit':{'type':'string','const':'fraction'},
        'status':{'type':'string','const':'point'},'origin':{'type':'string','enum':['reported','calculated']},
        'formula':text,'compound':text,'submix':text,'time_hours':{'type':'integer','minimum':0},
        'sheet_name':text,'row_number':{'type':'integer','minimum':1},
        'source_cell_addresses':{'type':'array','minItems':1,'maxItems':2,'items':text},
        'input_measurement_keys':{'type':'array','minItems':1,'maxItems':2,'items':text},
        'shared_active_observation_key':text,
        'normalization_status':{'type':'string','const':'source_relative_removal_denominator_raw_values_unavailable'},
        'repetition_basis':{'type':'string','const':'unknown'},'active_control_covariance':{'type':'string','const':'unknown'},
        'equal_mutant_protein_amount':{'type':'string','const':'unknown'},
        'product_identity_for_studied_enzyme':{'type':'string','const':'unknown'},
        'reported_sd_of_difference':{'type':'null'},'standard_error_of_difference':{'type':'null'},
        'difference_uncertainty_status':{'type':'string','const':'joint_replication_and_covariance_unknown'},
        'product_coupling_factor':{'type':'null'},'annotation_credit':{'type':'null'}})}


def _rows(saved, sheet_ref, components):
    e,s=saved['extraction'],saved['sheet']
    return [{'sheet_ref':sheet_ref,'evidence_source_ref':e['source_ref'],
        'workbook_artifact_ref':saved['input_artifact_ref'],
        'component':component,'evaluation_scope':s['evaluation_scope'],
        **deepcopy(s['cells'][component]),
        'compound':e['compound'],'submix':e['submix'],'time_hours':e['time_hours'],
        'sheet_name':e['sheet_name'],'row_number':e['row_number'],
        'shared_active_observation_key':s['shared_active_observation_key'],
        'normalization_status':e['normalization_status'],'repetition_basis':e['repetition_basis'],
        'active_control_covariance':e['active_control_covariance'],
        'equal_mutant_protein_amount':e['equal_mutant_protein_amount'],
        'product_identity_for_studied_enzyme':e['product_identity_for_studied_enzyme'],
        'product_coupling_factor':s['product_coupling_factor'],'annotation_credit':s['annotation_credit']}
        for component in components]


class LiteratureParentDepletionRepository(LiteratureRateRepository):
    provider=PROVIDER
    components=COMPONENTS
    record_version=VERSION
    operations_table='literature_parent_depletion_operations'
    received_table='literature_parent_depletion_received'
    binding_fields=()

    def __init__(self,store,run_id):
        if not isinstance(run_id,str) or not run_id: raise ValueError('explicit_literature_run_required')
        self.store,self.run_id=store,run_id

    def _installed(self,table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store,self.run_id)

    def populate(self,context,arguments,operation_key):
        if context.run_id!=self.run_id: raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key,str) or not operation_key: raise ContractError('operation_key_required')
        args=plain(arguments);validate_schema(args,parent_depletion_population_schema())
        request={'run_id':self.run_id,'episode_id':context.episode_id,'operation_key':operation_key,
            'arguments':args,'scope':plain(context.scope)}
        signature=canonical(request)
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature']!=signature: raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome']);self.read(outcome['result']['sheet_ref'])
            self._native_source(context,args['source_ref'])
            return outcome
        source=self._native_source(context,args['source_ref'])
        raw=self.store.get_artifact(source['artifact_ref'])
        extraction=read_parent_depletion_inputs(args,raw)
        sheet=populate_parent_depletion_components(extraction)
        payload={'version':VERSION,'input_source_ref':args['source_ref'],'input_artifact_ref':source['artifact_ref'],
            'selection':args,'extraction':extraction,'sheet':sheet}
        with self.store.transaction():
            self._install()
            artifact=self.store.artifact(canonical(payload),'application/json')
            request_ref=self.store.artifact(canonical(request),'application/json')
            record={'provider':PROVIDER,'accession':None,'uri':None,'artifact_ref':artifact,
                'text_ref':artifact,'request_ref':request_ref,'version':VERSION,'retrieved_at':None,
                'parent_source_refs':[args['source_ref']]}
            sheet_ref=identity('source',{'origin':'tool','record':record})
            exists=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(sheet_ref,)).fetchone()
            self.store.put('source',record,origin='tool',scope=plain(context.scope))
            rows=_rows(payload,sheet_ref,COMPONENTS)
            validate_schema(rows,parent_depletion_cells_schema())
            outcome={'status':'completed','operation_ref':identity('operation',{
                'run_id':self.run_id,'episode_id':context.episode_id,'key':operation_key}),
                'record_refs':[sheet_ref],'changed_record_refs':[] if exists else [sheet_ref],
                'result':{'sheet_ref':sheet_ref,'cells':rows},'feedback':None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return outcome

    def _artifact_json(self,reference):
        raw=self.store.get_artifact(reference)
        if reference!='artifact_'+sha256(raw).hexdigest(): raise ContractError('parent_depletion_saved_hash_mismatch')
        try: value=json.loads(raw)
        except (UnicodeDecodeError,json.JSONDecodeError) as error:
            raise ContractError('parent_depletion_saved_json_required') from error
        if not isinstance(value,dict): raise ContractError('parent_depletion_saved_object_required')
        return value

    def read(self,sheet_ref):
        source=self.store.get(sheet_ref)
        if source.get('record_type')!='source' or source.get('origin')!='tool' or source.get('provider')!=PROVIDER or source.get('version')!=VERSION:
            raise ContractError('parent_depletion_sheet_required')
        record={k:v for k,v in source.items() if k not in ('id','record_type','origin')}
        if identity('source',{'origin':'tool','record':record})!=sheet_ref:
            raise ContractError('parent_depletion_saved_source_identity_mismatch')
        request=self._artifact_json(source['request_ref'])
        if request.get('run_id')!=self.run_id or set(request)!={'run_id','episode_id','operation_key','arguments','scope'}:
            raise ContractError('parent_depletion_saved_selection_mismatch')
        original_scope=self.store.validate_scope(request['scope'])
        self._native_provenance(original_scope,sheet_ref)
        operation=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature']!=canonical(request):
            raise ContractError('parent_depletion_saved_operation_mismatch')
        outcome=json.loads(operation['outcome']);saved=self._artifact_json(source['artifact_ref'])
        validate_schema(saved['selection'],parent_depletion_population_schema())
        if (set(saved)!={'version','input_source_ref','input_artifact_ref','selection','extraction','sheet'}
                or saved['version']!=VERSION or saved['selection']!=request['arguments']
                or saved['input_source_ref']!=request['arguments']['source_ref']
                or saved['extraction']['source_ref']!=saved['input_source_ref']
                or saved['extraction']['workbook_sha256']!=saved['selection']['expected_sha256']
                or source['parent_source_refs']!=[saved['input_source_ref']]
                or self._native_provenance(original_scope,saved['input_source_ref'])['artifact_ref']!=saved['input_artifact_ref']
                or outcome.get('status')!='completed' or outcome.get('result',{}).get('sheet_ref')!=sheet_ref
                or outcome.get('operation_ref')!=identity('operation',{'run_id':self.run_id,
                    'episode_id':request['episode_id'],'key':request['operation_key']})):
            raise ContractError('parent_depletion_saved_selection_mismatch')
        rows=_rows(saved,sheet_ref,COMPONENTS)
        validate_schema(rows,parent_depletion_cells_schema())
        if canonical(rows)!=canonical(outcome['result']['cells']):
            raise ContractError('parent_depletion_saved_cells_mismatch')
        return saved

    def project_cells(self,sheet_refs,*,permitted_record_refs,components=None):
        selected=COMPONENTS if components is None else components
        if not isinstance(selected,(list,tuple)) or len(set(selected))!=len(selected) or any(c not in COMPONENTS for c in selected):
            raise ContractError('parent_depletion_component_selection_invalid')
        rows=[]
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs: raise ContractError('literature_sheet_not_received')
            rows.extend(_rows(self.read(ref),ref,selected))
        return rows

    def received_cells(self,context):
        return super().received_cells(context) if self._installed(self.received_table) else []

    def available_sheet_refs(self,context):
        refs=[]
        for ref in context.received_record_refs:
            try: row=self.store.get(ref)
            except (LookupError,ContractError): continue
            if row.get('record_type')=='source' and row.get('provider')==PROVIDER and row.get('version')==VERSION:
                self.read(ref);refs.append(ref)
        return list(dict.fromkeys(refs))

    def receive_cells(self,context,cells,operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context,cells,operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in
            (row['sheet_ref'],row['evidence_source_ref'],row['workbook_artifact_ref'])))


__all__=['PROVIDER','VERSION','NAMESPACE','REQUESTED','COMPONENTS',
    'LiteratureParentDepletionRepository','parent_depletion_cells_schema']
