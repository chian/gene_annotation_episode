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
        'conflicting':{'type':'boolean'},'association_unresolved':{'type':'boolean'},'unavailable_reason':{'enum':[*ENTRY_REASONS,None]},
        'label_source':_witness(),'group_source':_witness()})
    fields={'label':deepcopy(TEXT),**{name:{'type':'integer','minimum':0} for name in
        ('selected_row_count','known_entry_count','representation_count','point_entry_count')},
        'entry_count':{'type':['integer','null'],'minimum':0},'association_unresolved':{'type':'boolean'},'complete':{'type':'boolean'},
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
            'observed':None if group is None else {k:deepcopy(v) for k,v in group.items() if k!='cells'}}
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
        'observed':_nullable(_group())})
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
        if isinstance(arguments,dict) and arguments.get('version')==GRID_POPULATION:
            return self.grid_projection().populate(context,arguments,operation_key)
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
            by_label={}
            for key,e in unique.items():by_label.setdefault(e['label'],set()).add(key)
            unresolved={key for keys in by_label.values() if len(keys)>1 for key in keys}
            if (group['entry_count']!=(None if unresolved else len(unique)) or group['selected_row_count']!=len(unique)
                    or group['known_entry_count']!=len(set(unique)-unresolved) or group['association_unresolved']!=bool(unresolved)
                    or group['representation_count']!=len(entries)
                    or [e['record_identity'] for e in group['observation_labels']]!=list(unique)
                    or any(e['association_unresolved']!=(e['record_identity'] in unresolved) for e in group['observation_labels'])
                    or group['point_entry_count']!=sum(e['status']=='observed' and not e['conflicting'] and not e['association_unresolved'] for e in group['observation_labels'])):
                raise ContractError('rate_observation_saved_group_binding_mismatch')
        for cell in sheet['cells'].values():
            if ((cell['value'] is None)!=(cell['status']=='unavailable')
                    or (cell['unavailable_reason'] is None)!=(cell['status']=='populated')):
                raise ContractError('rate_observation_saved_cell_binding_mismatch')

    def owned_sheet_refs(self,context):
        """Original selected outputs of this reporting episode, never new work."""
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):return []
        references=[]
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid',
                (self.run_id,context.episode_id)):
            outcome=json.loads(row['outcome'])
            if (outcome.get('status')=='completed'
                    and self.store.get(outcome['result']['sheet_ref']).get('version')==self.record_version
                    and outcome['result']['sheet_ref'] in context.received_record_refs):
                references.append(outcome['result']['sheet_ref'])
        return list(dict.fromkeys(references))

    def available_sheet_refs(self,context):
        """Known own outputs plus exact admitted subsets; storage alone grants none."""
        references=self.owned_sheet_refs(context)
        references.extend(row['sheet_ref'] for row in self.received_cells(context)
            if row['sheet_ref'] in context.received_record_refs)
        return list(dict.fromkeys(references))

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

    def grid_projection(self):
        """A versioned view of the same selected operation; discovery writes none."""
        if not hasattr(self,'_grid_projection'):
            self._grid_projection=LiteratureReportedCurveRepository(self.store,self.run_id)
        return self._grid_projection

    def validate_empty_return_family(self,context):
        if not self._installed(self.operations_table):return
        versions={self.store.get(json.loads(row['outcome'])['result']['sheet_ref']).get('version')
            for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=?',
                (self.run_id,context.episode_id))}
        if self.record_version==VERSION and GRID_RECORD not in versions:return
        if versions and self.record_version not in versions:
            raise ContractError('literature_rate_grid_projection_version_mismatch')


# Explicit reported-curve branch; original v1 schemas and numerical meaning stay separate.
GRID_POPULATION='a105_reported_curve_population_v1'
GRID_RECORD='literature_reported_rate_observation_record_v2'
GRID_NAMESPACE='literature_rate_grid_cells'
GRID_REQUESTED='requested_rate_grid_components'
GRID_VIEW='reported_curve_precision_components'
GRID_SCOPE='source_reported_curve_precision'


def rate_observation_operation_schema():
    from .literature_rate_observation_inputs import reported_rate_grid_population_schema
    from .literature_rate_observation_calculations import reported_curve_precision_request_schema
    return {'type':'object','anyOf':[rate_observation_population_schema(),obj({
        'version':{'const':GRID_POPULATION},'grid':reported_rate_grid_population_schema(),
        'calculation':reported_curve_precision_request_schema()})]}


def _grid_ref(kind):
    return {'type':'string','format':'reference','x-reference-namespace':kind}


def _grid_location_schema():
    return obj({'source_ref':_grid_ref('source'),'artifact_ref':_grid_ref('artifact'),
        'member':deepcopy(TEXT),'cell':{'type':'string','pattern':'^[A-Z]+[1-9][0-9]*$'}})


def rate_grid_cells_schema():
    from .literature_rate_observation_calculations import reported_curve_precision_sheet_schema
    from .literature_rate_observation_inputs import GRID_SOURCE_STATUSES
    cell=deepcopy(reported_curve_precision_sheet_schema()['properties']['cells']['items']['properties'])
    loc=_grid_location_schema()
    label=obj({'display_text':{'type':['string','null']},
        'status':{'enum':['exact_source_label','unrequested_numbers_withheld','numerical_scope_unresolved']},
        'implementation_reason':{'enum':[None,'unrequested_numerical_scope_unresolved']},'location':loc})
    coordinate=obj({'role':{'enum':['point','left','right']},'location':loc,'measurement_key':deepcopy(TEXT),
        'unit':{'enum':['M','mM','uM','nM','unknown']},'status':{'enum':list(GRID_SOURCE_STATUSES)},
        'exact_value':deepcopy(cell['exact_value']),'exact_limit':deepcopy(cell['exact_value']),
        'bound':{'enum':['none','<','>','<=','>=','≤','≥']},'origin':{'enum':['reported','synthetic']}})
    span=obj({'source_ref':_grid_ref('source'),'artifact_ref':_grid_ref('artifact'),
        'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1}})
    props={'sheet_ref':_grid_ref('source'),'evidence_source_ref':_grid_ref('source'),
        'record_version':{'const':GRID_RECORD},'scientific_sheet_version':{'const':'a105_reported_curve_precision_v1'},
        'evaluation_scope':{'const':GRID_SCOPE},'component':deepcopy(TEXT),**cell,'origin':{'const':'derived'},
        'source_context':obj({name:deepcopy(label) for name in ('subject','panel','native_endpoint')}),
        'coordinate_context':_array(coordinate),'sampling':obj({
            'status':{'enum':['supported','stipulated_sensitivity','unknown','conflicting']},
            'assumption':{'enum':['none','iid_reported_curve_vectors']},
            'source_claim':{'enum':['iid_reporting_vectors_supported','not_established','unknown','conflicting']}}),
        'reporting_counts':obj({name:{'type':['integer','null'],'minimum':0} for name in
            ('selected_reporting_entries','available_numeric_entries','selected_concentrations','reporting_curves')}),
        'model_meaning':obj({'fit_model':{'enum':['none','unweighted_positive_km_mm']},
            'estimator':{'enum':['not_applicable','per_reported_curve_fit','mean_of_reported_curve_fits','fit_of_point_means','reported_curve_fit_distribution']},
            'weighting':{'enum':['not_applicable','unweighted']},
            'solver_scope':{'const':'finite_numerical_domain_not_global_certification'}}),
        'scientific_scope':obj({'concentration_basis':{'const':'fixed_reported_concentrations_when_fitted'},
            'precision_basis':{'enum':['not_applicable','descriptive_reported_entries','descriptive_fitted_curve_distribution','conditional_iid_reporting_curve_vectors']},
            'physical_preparation_count':{'type':'null'},'published_estimate_covariance':{'type':'null'},
            'excluded_uncertainty':{'const':'blank_recovery_active_amount_and_concentration_uncertainty_not_propagated'},
            'endpoint_meaning':{'const':'reporter_to_product_meaning_not_resolved_by_precision'},
            'endpoint_relationship':{'enum':['reported_convention_only','supported','unknown','conflicting']}}),
        'host_custody':obj({'context_locations':_array(span),'selected_cell_locations':_array(loc)}),
        'source_kind':{'enum':list(SOURCE_KINDS)}}
    return {**_array(obj(props)),'x-source':GRID_NAMESPACE}


def _grid_selector_keys(components):
    from .literature_rate_observation_calculations import reported_curve_precision_selector_schema
    if not isinstance(components,(list,tuple)):raise ContractError('literature_rate_grid_selectors_required')
    keys=[]
    for choice in components:
        if isinstance(choice,str):
            try:selector=json.loads(choice)
            except (ValueError,TypeError) as error:raise ContractError('literature_rate_grid_selector_invalid') from error
            if canonical(selector)!=choice:raise ContractError('literature_rate_grid_selector_not_canonical')
        else:selector=plain(choice)
        validate_schema(selector,reported_curve_precision_selector_schema())
        key=canonical(selector)
        if key in keys:raise ContractError('literature_rate_grid_selector_duplicate')
        keys.append(key)
    return keys


def _grid_context_selectors(arguments):
    grid=arguments['grid']
    return [w for w in (grid['rate_unit']['witness'],grid['concentration_unit']['witness'],
        *grid['endpoint_relationship']['witnesses'],*grid['curve_sampling']['witnesses'])
        if w is not None and w['kind']=='context_span']


def _grid_location(witness):
    return {key:witness[key] for key in ('source_ref','artifact_ref','member','cell')}


def _grid_scoped_label(witness):
    """Bounded label display, never a reconstruction of a source quotation."""
    import re
    raw=witness['value'] or ''
    # Units, figure labels and supported molecular names are not assay operands.
    visible=re.sub(r'\bFig(?:ure)?\.?\s*[0-9]+[A-Za-z]?', 'figure',raw,flags=re.I)
    visible=re.sub(r'(?:[numµμ]?mol)\s*(?:/\s*min|min\s*(?:\^?\s*[−-]1|⁻¹))','rate unit',visible)
    name=bool(re.fullmatch(r'[A-Z][0-9]+[A-Z](?:/[A-Z][0-9]+[A-Z])*',raw.strip())
        or re.fullmatch(r'[0-9]+(?:,[0-9]+)*-(?:(?:exo|endo|cis|trans|R|S)-)?(?:methyl|hydroxy|oxo|amino|deoxy)-?(?:camphor|uridine)',raw.strip(),re.I)
        or raw.strip()=='P450cam')
    attached=re.compile(r'(?<![A-Za-z])(?:K[_ ]?d|K[_ ]?m|kcat|IC50|EC50|SEM|SD|CV|mean)[_:= ]*[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?(?:[A-Za-zµμ%][A-Za-z0-9µμ%/^−-]*)?',re.I)
    number=re.compile(r'(?<![A-Za-z0-9_.])[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?')
    condition=re.compile(r'(?:pH|dose)[_:= ]*[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)',re.I)
    unit_value=re.compile(r'[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\s*(?:mM|µM|μM|uM|nM|M|percent|%)(?![A-Za-z])')
    unresolved=bool(attached.search(raw) or condition.search(raw) or unit_value.search(raw)
        or not name and number.search(visible))
    return {'display_text':'[Numerical label context withheld; source meaning needs a scoped read.]' if unresolved else raw,
        'status':'numerical_scope_unresolved' if unresolved else 'exact_source_label',
        'implementation_reason':'unrequested_numerical_scope_unresolved' if unresolved else None,
        'location':_grid_location(witness)}


def _grid_row_context(extraction,request,cell):
    """Build once at selected population, not at saved reconstruction."""
    selector=cell['selector'];scope=selector['scope'];args=extraction['original_arguments']
    points=extraction['points'];curves=extraction['curves'];by_cell={p['concentration']['witness']['cell']:p for p in points}
    coordinates=[]
    for field,role in [('concentration_cell','point'),('left_concentration_cell','left'),('right_concentration_cell','right')]:
        if field not in selector:continue
        q=by_cell[selector[field]]['concentration']
        coordinates.append({'role':role,'location':_grid_location(q['witness']),'measurement_key':q['measurement_key'],
            'unit':args['concentration_unit']['code'],**{name:deepcopy(q[name]) for name in ('status','exact_value','exact_limit','bound','origin')}})
    counts=dict.fromkeys(('selected_reporting_entries','available_numeric_entries','selected_concentrations','reporting_curves'))
    if scope=='point':
        entries=by_cell[selector['concentration_cell']]['entries']
        counts.update(selected_reporting_entries=len(entries),available_numeric_entries=sum(e['quantity']['status']=='observed' for e in entries))
    elif scope=='reported_curve_covariance':counts['reporting_curves']=len(curves)
    elif scope in ('curve','estimator','parameter_covariance','sensitivity','variance_term'):
        counts.update(selected_concentrations=len(points),reporting_curves=len(curves))
    estimator=selector.get('estimator','per_reported_curve_fit' if scope=='curve' else 'not_applicable')
    fitted=estimator!='not_applicable' or selector['component'] in ('all_reported_residual_SS','mean_curve_fit_residual_SS_times_curve_count')
    precision=('conditional_iid_reporting_curve_vectors' if cell['model_keys'] else
        'descriptive_fitted_curve_distribution' if estimator=='reported_curve_fit_distribution' else
        'descriptive_reported_entries' if scope in ('point','reported_curve_covariance') else 'not_applicable')
    source_context={name:_grid_scoped_label(extraction['meanings'][field]) for name,field in
        [('subject','subject'),('panel','panel'),('native_endpoint','native_rate_label')]}
    locations=list(dict.fromkeys(canonical(_grid_location(q['witness'])) for p in points for q in
        [p['concentration'],*(e['quantity'] for e in p['entries'])]))
    return {'source_context':source_context,'coordinate_context':coordinates,
        'sampling':{name:args['curve_sampling'][name] for name in ('status','assumption','source_claim')},
        'reporting_counts':counts,'model_meaning':{'fit_model':request['fit_model'],'estimator':estimator,
            'weighting':'unweighted' if fitted and request['fit_model']!='none' else 'not_applicable',
            'solver_scope':'finite_numerical_domain_not_global_certification'},
        'scientific_scope':{'concentration_basis':'fixed_reported_concentrations_when_fitted','precision_basis':precision,
            'physical_preparation_count':None,'published_estimate_covariance':None,
            'excluded_uncertainty':'blank_recovery_active_amount_and_concentration_uncertainty_not_propagated',
            'endpoint_meaning':'reporter_to_product_meaning_not_resolved_by_precision',
            'endpoint_relationship':args['endpoint_relationship']['status']},
        'host_custody':{'context_locations':[deepcopy({k:w[k] for k in ('source_ref','artifact_ref','start','end')})
            for w in extraction['context_witnesses'] if w['kind']=='context_span'],
            'selected_cell_locations':[json.loads(v) for v in locations]},'source_kind':args['source_kind']}


def _project_grid_saved(saved,reference,components):
    selected=_grid_selector_keys(components)
    rows={row['component']:row for row in saved['projected_cells']}
    if any(key not in rows for key in selected):raise ContractError('literature_rate_grid_component_not_selected')
    return [{**deepcopy(rows[key]),'sheet_ref':reference,'evidence_source_ref':saved['input_source_ref']} for key in selected]


class LiteratureReportedCurveRepository(LiteratureRateObservationRepository):
    """Versioned selected scalar view; same operation and ordinary typed receipts."""
    record_version=GRID_RECORD
    received_table='literature_rate_grid_received'

    @staticmethod
    def _components(components):return _grid_selector_keys(components)

    @staticmethod
    def _receipt_files():
        return ('literature_rate_observation_inputs.py','literature_rate_observation_calculations.py',
            'literature_rate_observation_storage.py','literature_rate_observation_prompt.py',
            'literature_rate_storage.py','spreadsheet_tools.py','literature_episodes.py',
            'communication.py','literature_numerical_contracts.py','literature_numerical_return_presentation.py',
            'literature_experimental_prompt.py','literature_reference_parent_prompt.py')

    def _original_implementation(self):
        from pathlib import Path
        return {'version':'reported_curve_original_implementation_v1',
            'files':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in self._receipt_files()}}

    def _all_ancestors(self,scope,references):
        return list(dict.fromkeys(ref for reference in references for ref in self._ancestors(scope,reference)))

    def populate(self,context,arguments,operation_key):
        from .literature_rate_observation_inputs import read_reported_rate_grid
        from .literature_rate_observation_calculations import populate_reported_curve_precision
        if context.run_id!=self.run_id:raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key,str) or not operation_key:raise ContractError('operation_key_required')
        args=plain(arguments);validate_schema(args,rate_observation_operation_schema()['anyOf'][1])
        requested=plain(context.assignment.get(GRID_REQUESTED,[]));self._components(requested)
        if requested!=args['calculation']['requested_components']:raise ContractError('literature_rate_grid_requested_subset_mismatch')
        request={'run_id':self.run_id,'episode_id':context.episode_id,'operation_key':operation_key,
            'arguments':args,'scope':plain(context.scope),'components':requested,'role':context.role,
            'assignment':plain(context.assignment),'received_record_refs':list(context.received_record_refs)}
        signature=canonical(request)
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature']!=signature:raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome']);self.read(outcome['result']['sheet_ref']);return outcome
        source=self._native_source(context,args['grid']['source_ref']);artifact=source['artifact_ref']
        documents=[];context_artifacts=[];direct=[args['grid']['source_ref']]
        for w in _grid_context_selectors(args):
            meta=self._native_source(context,w['source_ref'])
            if w['artifact_ref'] not in (meta['artifact_ref'],meta.get('text_ref')):
                raise ContractError('literature_rate_grid_context_representation_mismatch')
            item={'source_ref':w['source_ref'],'artifact_ref':w['artifact_ref']}
            if item not in context_artifacts:
                context_artifacts.append(item);documents.append({**item,'content':self.store.get_artifact(w['artifact_ref'])})
            if w['source_ref'] not in direct:direct.append(w['source_ref'])
        extraction=read_reported_rate_grid(self.store.get_artifact(artifact),args['grid'],artifact_ref=artifact,context_documents=documents)
        sheet=populate_reported_curve_precision(extraction,args['calculation'])
        rows=[{**deepcopy(cell),**_grid_row_context(extraction,args['calculation'],cell),
            'component':canonical(cell['selector']),'origin':'derived','record_version':GRID_RECORD,
            'scientific_sheet_version':sheet['version'],'evaluation_scope':GRID_SCOPE} for cell in sheet['cells']]
        ancestors=self._all_ancestors(context.scope,direct)
        payload={'version':GRID_RECORD,'input_source_ref':args['grid']['source_ref'],'input_artifact_ref':artifact,
            'direct_input_source_refs':direct,'input_source_refs':ancestors,'context_artifacts':context_artifacts,
            'source_metadata':{r:plain(self._native_provenance(context.scope,r)) for r in ancestors},
            'selection':args,'extraction':extraction,'sheet':sheet,'projected_cells':rows,
            'original_implementation':self._original_implementation()}
        with self.store.transaction():
            self._install();sheet_artifact=self.store.artifact(canonical(payload),'application/json')
            request_ref=self.store.artifact(canonical(request),'application/json')
            value={'provider':PROVIDER,'accession':None,'uri':None,'artifact_ref':sheet_artifact,'text_ref':sheet_artifact,
                'request_ref':request_ref,'version':GRID_RECORD,'retrieved_at':None,'parent_source_refs':ancestors}
            reference=identity('source',{'origin':'tool','record':value})
            existed=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(reference,)).fetchone()
            self.store.put('source',value,origin='tool',scope=plain(context.scope))
            outcome={'status':'completed','operation_ref':identity('operation',{'run_id':self.run_id,'episode_id':context.episode_id,'key':operation_key}),
                'record_refs':[reference],'changed_record_refs':[] if existed else [reference],
                'result':{'sheet_ref':reference,'view':GRID_VIEW,'record_version':GRID_RECORD,
                    'cells':_project_grid_saved(payload,reference,requested)},'feedback':None}
            validate_schema(outcome['result']['cells'],rate_grid_cells_schema())
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return outcome

    def read(self,sheet_ref):
        """Authenticate saved selected state without source bytes, parsers or fitting."""
        import re
        from .literature_rate_observation_inputs import reported_rate_grid_extraction_schema
        from .literature_rate_observation_calculations import reported_curve_precision_sheet_schema
        source=self.store.get(sheet_ref);value={k:v for k,v in source.items() if k not in ('id','record_type','origin')}
        if (source.get('record_type')!='source' or source.get('origin')!='tool' or source.get('provider')!=PROVIDER
                or source.get('version')!=GRID_RECORD or source['text_ref']!=source['artifact_ref']
                or identity('source',{'origin':'tool','record':value})!=sheet_ref):
            raise ContractError('literature_rate_grid_sheet_required')
        request=self._json_artifact(source['request_ref'])
        if (set(request)!={'run_id','episode_id','operation_key','arguments','scope','components','role','assignment','received_record_refs'}
                or request['run_id']!=self.run_id or not all(isinstance(request[n],str) and request[n] for n in ('episode_id','operation_key','role'))
                or request['components']!=request['assignment'].get(GRID_REQUESTED,[])
                or request['components']!=request['arguments']['calculation']['requested_components']):
            raise ContractError('rate_grid_saved_request_mismatch')
        validate_schema(request['arguments'],rate_observation_operation_schema()['anyOf'][1]);keys=self._components(request['components'])
        operation=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,request['episode_id'],request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature']!=canonical(request):raise ContractError('literature_sheet_not_selected_output')
        saved=self._json_artifact(source['artifact_ref'])
        if (set(saved)!={'version','input_source_ref','input_artifact_ref','direct_input_source_refs','input_source_refs','context_artifacts','source_metadata','selection','extraction','sheet','projected_cells','original_implementation'}
                or saved['version']!=GRID_RECORD or saved['selection']!=request['arguments']
                or saved['input_source_ref']!=request['arguments']['grid']['source_ref']
                or saved['input_source_refs']!=source['parent_source_refs']):
            raise ContractError('rate_grid_saved_selection_mismatch')
        args=request['arguments'];data=saved['extraction'];sheet=saved['sheet']
        validate_schema(data,reported_rate_grid_extraction_schema());validate_schema(sheet,reported_curve_precision_sheet_schema())
        if data['original_arguments']!=args['grid'] or sheet['extraction']!=data or sheet['request']!=args['calculation']:
            raise ContractError('rate_grid_saved_sheet_binding_mismatch')
        direct=list(dict.fromkeys([saved['input_source_ref'],*(w['source_ref'] for w in _grid_context_selectors(args))]))
        if (saved['direct_input_source_refs']!=direct or any(r not in request['received_record_refs'] for r in direct)
                or saved['input_source_refs']!=self._all_ancestors(request['scope'],direct)
                or set(saved['source_metadata'])!=set(saved['input_source_refs'])
                or any(canonical(self._native_provenance(request['scope'],r))!=canonical(meta) for r,meta in saved['source_metadata'].items())
                or saved['input_artifact_ref']!=saved['source_metadata'][saved['input_source_ref']]['artifact_ref']):
            raise ContractError('rate_grid_saved_source_binding_mismatch')
        context_artifacts=[]
        for w in _grid_context_selectors(args):
            meta=saved['source_metadata'][w['source_ref']]
            if (w['artifact_ref'] not in (meta['artifact_ref'],meta.get('text_ref'))
                    or not 0<=w['start']<w['end']<=self.store.get(w['artifact_ref'])['size']
                    or w['end']-w['start']!=len(w['quote'].encode())):
                raise ContractError('rate_grid_saved_context_binding_mismatch')
            item={'source_ref':w['source_ref'],'artifact_ref':w['artifact_ref']}
            if item not in context_artifacts:context_artifacts.append(item)
        if context_artifacts!=saved['context_artifacts']:raise ContractError('rate_grid_saved_context_binding_mismatch')
        custody=data['custody']
        if (custody['source_ref']!=saved['input_source_ref'] or custody['artifact_ref']!=saved['input_artifact_ref']
                or 'artifact_'+custody['workbook_sha256']!=saved['input_artifact_ref'] or custody['worksheet']!=args['grid']['worksheet']):
            raise ContractError('rate_grid_saved_custody_mismatch')
        selected_context=[]
        grid=args['grid']
        for w in [grid['rate_unit']['witness'],grid['concentration_unit']['witness'],
                *grid['endpoint_relationship']['witnesses'],*grid['curve_sampling']['witnesses']]:
            if w is not None and w not in selected_context:selected_context.append(w)
        if data['context_witnesses']!=selected_context:raise ContractError('rate_grid_saved_context_binding_mismatch')
        def witness_binding(w,address):
            if (w['cell']!=address or any(w[k]!=v for k,v in custody.items())
                    or w['value_is_formula_cache']!=(w['formula'] is not None)):
                raise ContractError('rate_grid_saved_witness_binding_mismatch')
        curve_cells=list(dict.fromkeys(c['header']['cell'] for c in grid['curves']))
        point_cells=list(dict.fromkeys(p['concentration_cell'] for p in grid['points']))
        if ([c['header']['cell'] for c in data['curves']]!=curve_cells
                or [p['concentration']['witness']['cell'] for p in data['points']]!=point_cells):
            raise ContractError('rate_grid_saved_roster_binding_mismatch')
        for c,address in zip(data['curves'],curve_cells):
            indices=[i for i,choice in enumerate(grid['curves']) if choice['header']['cell']==address]
            witness_binding(c['header'],address)
            if (c['selection_indices']!=indices or any(grid['curves'][i]['header']['expected_text']!=c['header']['value'] for i in indices)
                    or c['curve_key']!=identity('reported_grid_curve',{'artifact_ref':custody['artifact_ref'],'member':custody['member'],'header_cell':address})):
                raise ContractError('rate_grid_saved_curve_binding_mismatch')
        quantities=[]
        for point,address in zip(data['points'],point_cells):
            indices=[i for i,choice in enumerate(grid['points']) if choice['concentration_cell']==address]
            if (point['selection_indices']!=indices or len(point['entries'])!=len(data['curves'])
                    or point['point_key']!=identity('reported_grid_point',{'artifact_ref':custody['artifact_ref'],'member':custody['member'],'concentration_cell':address})):
                raise ContractError('rate_grid_saved_point_binding_mismatch')
            witness_binding(point['concentration']['witness'],address);quantities.append(point['concentration'])
            for entry,curve in zip(point['entries'],data['curves']):
                original_index=curve['selection_indices'][0]
                value_cell=grid['points'][indices[0]]['rate_cells'][original_index]
                if (entry['curve_key']!=curve['curve_key']
                        or entry['representation_key']!=identity('reported_grid_representation',{'source_ref':grid['source_ref'],'point':address,'header':curve['header']['cell']})
                        or any(grid['points'][i]['rate_cells'][j]!=value_cell for i in indices for j in curve['selection_indices'])):
                    raise ContractError('rate_grid_saved_entry_binding_mismatch')
                witness_binding(entry['quantity']['witness'],value_cell);quantities.append(entry['quantity'])
        for q in quantities:
            w=q['witness']
            if (q['measurement_key']!=identity('reported_grid_measurement',{k:w[k] for k in ('artifact_ref','member','cell')})
                    or q['origin']!=('synthetic' if grid['source_kind']=='synthetic_fixture' else 'reported')
                    or (q['status']=='observed')!=(q['exact_value'] is not None)):
                raise ContractError('rate_grid_saved_measurement_binding_mismatch')
        for name,field in [('subject','subject'),('panel','panel'),('native_rate_label','native_rate_label')]:
            w=data['meanings'][name];choice=args['grid'][field]
            if w['cell']!=choice['cell'] or w['value']!=choice['expected_text'] or any(w[k]!=v for k,v in custody.items()):
                raise ContractError('rate_grid_saved_label_binding_mismatch')
        if ([canonical(c['selector']) for c in sheet['cells']]!=keys
                or [c['component'] for c in saved['projected_cells']]!=keys):
            raise ContractError('rate_grid_saved_selector_binding_mismatch')
        pure_fields=set(reported_curve_precision_sheet_schema()['properties']['cells']['items']['properties'])
        for cell,row in zip(sheet['cells'],saved['projected_cells']):
            if ({k:row[k] for k in pure_fields}!=cell or row['component']!=canonical(row['selector'])
                    or row['source_kind']!=args['grid']['source_kind']
                    or row['sampling']!={k:args['grid']['curve_sampling'][k] for k in ('status','assumption','source_claim')}
                    or row['model_meaning']['fit_model']!=args['calculation']['fit_model']
                    or row['scientific_scope']['endpoint_relationship']!=args['grid']['endpoint_relationship']['status']):
                raise ContractError('rate_grid_saved_row_binding_mismatch')
            for name,field in [('subject','subject'),('panel','panel'),('native_endpoint','native_rate_label')]:
                if row['source_context'][name]['location']!=_grid_location(data['meanings'][field]):
                    raise ContractError('rate_grid_saved_display_binding_mismatch')
            selector=cell['selector'];by_point={p['concentration']['witness']['cell']:p for p in data['points']}
            expected_coordinates=[]
            for field,role in [('concentration_cell','point'),('left_concentration_cell','left'),('right_concentration_cell','right')]:
                if field not in selector:continue
                q=by_point[selector[field]]['concentration']
                expected_coordinates.append({'role':role,'location':_grid_location(q['witness']),
                    'measurement_key':q['measurement_key'],'unit':grid['concentration_unit']['code'],
                    **{n:q[n] for n in ('status','exact_value','exact_limit','bound','origin')}})
            if row['coordinate_context']!=expected_coordinates:raise ContractError('rate_grid_saved_coordinate_binding_mismatch')
            if selector['scope']=='point':owners=[e['quantity']['measurement_key'] for e in by_point[selector['concentration_cell']]['entries']]
            elif selector['scope']=='curve':
                ci=curve_cells.index(selector['curve_header_cell'])
                owners=[p['concentration']['measurement_key'] for p in data['points']]+[p['entries'][ci]['quantity']['measurement_key'] for p in data['points']]
            elif selector['scope']=='reported_curve_covariance':
                owners=[e['quantity']['measurement_key'] for address in dict.fromkeys((selector['left_concentration_cell'],selector['right_concentration_cell'])) for e in by_point[address]['entries']]
            else:owners=[p['concentration']['measurement_key'] for p in data['points']]+[e['quantity']['measurement_key'] for p in data['points'] for e in p['entries']]
            if cell['input_measurement_keys']!=list(dict.fromkeys(owners)):
                raise ContractError('rate_grid_saved_ownership_binding_mismatch')
            state=cell['status']
            if (state=='populated' and (cell['value'] is None or cell['conditional_value'] is not None)
                    or state=='conditional_scenario' and (cell['conditional_value'] is None or cell['value'] is not None)
                    or state=='unavailable' and (cell['value'] is not None or cell['conditional_value'] is not None)):
                raise ContractError('rate_grid_saved_value_binding_mismatch')
        receipt=saved['original_implementation']
        if (set(receipt)!={'version','files'} or receipt['version']!='reported_curve_original_implementation_v1'
                or set(receipt['files'])!=set(self._receipt_files())
                or any(type(h) is not str or re.fullmatch('[0-9a-f]{64}',h) is None for h in receipt['files'].values())):
            raise ContractError('rate_grid_saved_original_implementation_mismatch')
        expected={'sheet_ref':sheet_ref,'view':GRID_VIEW,'record_version':GRID_RECORD,
            'cells':_project_grid_saved(saved,sheet_ref,request['components'])}
        validate_schema(expected['cells'],rate_grid_cells_schema())
        outcome=json.loads(operation['outcome'])
        if (outcome.get('status')!='completed' or canonical(outcome.get('result'))!=canonical(expected)
                or outcome.get('record_refs')!=[sheet_ref] or outcome.get('feedback') is not None
                or outcome.get('operation_ref')!=identity('operation',{'run_id':self.run_id,'episode_id':request['episode_id'],'key':request['operation_key']})):
            raise ContractError('rate_grid_saved_outcome_mismatch')
        return saved

    def project_cells(self,sheet_refs,*,permitted_record_refs,components=None):
        result=[]
        if components is not None:self._components(components)
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:raise ContractError('literature_sheet_not_received')
            saved=self.read(reference)
            selected=saved['sheet']['request']['requested_components'] if components is None else components
            result.extend(_project_grid_saved(saved,reference,selected))
        return result

    def fact_cells(self,context,sheet_refs,*,components):
        refs=list(dict.fromkeys(sheet_refs))
        if self.store.reference_subset(refs,plain(context.scope))!=refs:raise ContractError('literature_source_outside_scope')
        return LiteratureRateRepository.fact_cells(self,context,refs,components=self._components(components))

    def selected_sheet_refs(self,context):return self.available_sheet_refs(context)

    def has_work(self,context):return bool(self.available_sheet_refs(context))

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in (
            row['sheet_ref'],row['evidence_source_ref'],
            *(loc['source_ref'] for loc in row['host_custody']['context_locations']))))
