"""Reported comparative signals with explicit conflicting representations.

A signal ratio is a comparability operand, not a molecular activity or an
experimental reliability grade. Visual inputs are retained transcriptions with
original image custody; this adapter does not perform OCR or densitometry.
"""
from __future__ import annotations

from io import BytesIO
import json
import math
import re
from PIL import Image, UnidentifiedImageError

from .communication import plain
from .domain import ContractError, REF, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_ratio_calculations import COMPONENTS, REASONS, populate_relative_signal
from .literature_ratio_reader import read_jats_relative_percent

PROVIDER = 'literature.experimental.relative_signal'
SIGNALS = ('protein_band','transcript_signal','other_reported_signal','unknown')
REFERENCES = ('tagged_wt_complementation','endogenous_wt','other_reported_reference','unknown','conflicting')
ARRANGEMENTS = ('single_preparation','replacement','coexistence','not_applicable','unknown','conflicting')
BINDINGS = {'subject_ref':'reference','variant_ref':'reference','comparison_reference_ref':'reference'}


def ratio_population_schema():
    from .literature_assay_inputs import _witness_schema
    text={'type':'string','minLength':1}
    return obj({'source_ref':REF,'source_kind':{'enum':['primary_jats','synthetic_fixture']},
        **{name:dict(text) for name in ('section_id','subject','variant','reference_literal')},
        'paragraph_index':{'type':'integer','minimum':0},
        'visual_source_refs':{'type':'array','uniqueItems':True,'items':REF},
        'signal_kind':{'enum':list(SIGNALS)},'reference_role':{'enum':list(REFERENCES)},
        'arrangement':{'enum':list(ARRANGEMENTS)},
        'interpretation_witnesses':{'type':'array','items':_witness_schema()}})


class LiteratureRatioRepository(LiteratureRateRepository):
    provider=PROVIDER
    components=COMPONENTS
    record_version='literature_relative_signal_record_v1'
    operations_table='literature_ratio_operations'
    received_table='literature_ratio_received'
    binding_fields=tuple(BINDINGS)

    def _source(self,context,reference):
        if reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        if not self.store.reference_subset([reference],plain(context.scope)):
            raise ContractError('literature_source_outside_scope')
        page = context.assignment if context.role == 'literature_page' else context.assignment.get('page')
        if page:
            pending,seen=[reference],set()
            while pending:
                current=pending.pop()
                if current==page['source_ref']:
                    break
                if current in seen:
                    continue
                seen.add(current)
                if not self.store.reference_subset([current],plain(context.scope)):
                    raise ContractError('literature_source_outside_scope')
                parent=self.store.get(current)
                if parent['record_type']!='source':
                    raise ContractError('literature_source_required')
                pending.extend(parent.get('parent_source_refs',()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        row=self.store.get(reference)
        if row['record_type']!='source':
            raise ContractError('literature_source_required')
        return row

    def populate(self,context,arguments,operation_key):
        from .literature_assay_inputs import _Sources
        if context.run_id!=self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key,str) or not operation_key:
            raise ContractError('operation_key_required')
        args=plain(arguments)
        validate_schema(args,ratio_population_schema())
        signature=canonical({'arguments':args,'scope':plain(context.scope)})
        old=self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id,context.episode_id,operation_key)).fetchone()
        if old:
            if old['signature']!=signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome=json.loads(old['outcome'])
            for ref in self.read(outcome['result']['sheet_ref'])['input_source_refs']:
                self._source(context,ref)
            return outcome
        def read_source(reference,representation):
            row=self._source(context,reference)
            artifact=row['artifact_ref'] if representation=='original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref':artifact,'content':self.store.get_artifact(artifact)}
        source=self._source(context,args['source_ref'])
        try:
            xml=self.store.get_artifact(source['artifact_ref']).decode('utf-8')
        except UnicodeDecodeError as error:
            raise ContractError('literature_utf8_jats_required') from error
        extracted=read_jats_relative_percent({'source_ref':source['id'],'artifact_ref':source['artifact_ref'],
            'xml':xml,'representation':args['source_kind']},section_id=args['section_id'],
            paragraph_index=args['paragraph_index'],expected_subject=args['subject'],
            variant=args['variant'],reference_literal=args['reference_literal'])
        witnesses=_Sources(read_source)
        interpreted=[witnesses.witness(row,f'interpretation_witnesses[{i}]')
                     for i,row in enumerate(args['interpretation_witnesses'])]
        if any(args[name]!='unknown' for name in ('signal_kind','reference_role','arrangement')) and not interpreted:
            raise ContractError('ratio_interpretation_witness_required')
        if any(args[name]=='conflicting' for name in ('reference_role','arrangement')) and len({
                canonical(row) for row in interpreted})<2:
            raise ContractError('ratio_conflict_witnesses_required')
        observations=list(extracted['observations'])
        parents=list(dict.fromkeys([args['source_ref'],*witnesses.references]))
        for ref in args['visual_source_refs']:
            visual=self._source(context,ref)
            try:
                def pairs(items):
                    result={}
                    for key,value in items:
                        if key in result:
                            raise ContractError('retained_visual_duplicate_json_key')
                        result[key]=value
                    return result
                record=json.loads(self.store.get_artifact(visual['artifact_ref']),object_pairs_hook=pairs)
            except (ValueError,UnicodeDecodeError) as error:
                raise ContractError('retained_visual_json_required') from error
            if (not isinstance(record,dict) or set(record)!= {'version','subject','variant','reference','observations'}
                    or record['version']!='relative_visual_signal_v1'
                    or (record['subject'],record['variant'],record['reference'])!=(args['subject'],args['variant'],args['reference_literal'])
                    or not isinstance(record['observations'],list) or not record['observations']):
                raise ContractError('retained_visual_comparison_mismatch')
            parents.append(ref)
            for row in record['observations']:
                expected={'printed_label','reference_printed_label','original_source_ref','original_artifact_ref',
                          'image_region','reference_image_region'}
                if not isinstance(row,dict) or set(row)!=expected:
                    raise ContractError('retained_visual_fields_required')
                original=self._source(context,row['original_source_ref'])
                if (original['artifact_ref']!=row['original_artifact_ref']
                        or original['id'] not in visual.get('parent_source_refs',())):
                    raise ContractError('retained_visual_lineage_mismatch')
                parents.append(original['id'])
                try:
                    with Image.open(BytesIO(self.store.get_artifact(original['artifact_ref']))) as picture:
                        width,height=picture.size
                except (UnidentifiedImageError,OSError,ValueError) as error:
                    raise ContractError('retained_visual_original_image_required') from error
                for name in ('image_region','reference_image_region'):
                    box=row[name]
                    if (not isinstance(box,list) or len(box)!=4 or any(type(x)is not int for x in box)
                            or not 0<=box[0]<box[2]<=width or not 0<=box[1]<box[3]<=height):
                        raise ContractError('retained_visual_region_outside_image')
                numbers=[]
                for name in ('printed_label','reference_printed_label'):
                    token=row[name]
                    if not isinstance(token,str) or not re.fullmatch(r'[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',token):
                        raise ContractError('retained_visual_point_label_required')
                    number=float(token)
                    if not math.isfinite(number) or (number==0 and any(x in '123456789' for x in token.lower().split('e')[0])):
                        raise ContractError('retained_visual_numerical_range')
                    numbers.append(number)
                if numbers[1]<=0:
                    raise ContractError('retained_visual_positive_reference_required')
                ratio=numbers[0]/numbers[1]
                if not math.isfinite(ratio) or ratio==0 and numbers[0]!=0:
                    raise ContractError('retained_visual_numerical_range')
                observations.append({'value':ratio,'origin':'visual_transcription','uncertainty':{
                    'kind':'unreported','magnitude':None,'count':None,'sampling_basis':'unspecified'},
                    'source':{'source_ref':ref,'artifact_ref':visual['artifact_ref'],
                              'representation':'retained_visual_transcription',**row}})
        sheet=populate_relative_signal(observations)
        payload={'version':self.record_version,'input_source_ref':args['source_ref'],
            'input_source_refs':list(dict.fromkeys(parents)),'input_artifact_ref':source['artifact_ref'],
            'sheet':sheet,'comparison':{name:args[name] for name in ('subject','variant','reference_literal',
                'signal_kind','reference_role','arrangement')},'interpretation_witnesses':interpreted,
            'interpretation_kind':'episode_source_interpretation'}
        with self.store.transaction():
            created=[]
            def publish(kind,record):
                candidate=identity(kind,{'origin':'tool','record':record})
                old=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(candidate,)).fetchone()
                row=self.store.put(kind,record,origin='tool',scope=plain(context.scope))
                if old is None:created.append(row['id'])
                return row['id']
            bindings={}
            for name,label in (('subject_ref',args['subject']),('variant_ref',args['variant']),
                               ('comparison_reference_ref',args['reference_literal'])):
                bindings[name]=publish('reference',{'reference_type':'literature_result','source_ref':args['source_ref'],
                    'accession':identity('ratio_label',{'source':args['source_ref'],'role':name,'label':label}),
                    'label':label,'sequence_ref':None,'molecule':None,'length':None,'term_refs':[],'context_refs':[]})
            payload['experimental_bindings']=bindings
            artifact=self.store.artifact(canonical(payload),'application/json')
            request=self.store.artifact(canonical({'run_id':self.run_id,'episode_id':context.episode_id,
                'operation_key':operation_key,'arguments':args}),'application/json')
            sheet_ref=publish('source',{'provider':self.provider,'accession':None,'uri':None,'artifact_ref':artifact,
                'text_ref':artifact,'request_ref':request,'version':self.record_version,'retrieved_at':None,
                'parent_source_refs':payload['input_source_refs']})
            outcome={'status':'completed','operation_ref':identity('operation',{'run_id':self.run_id,
                'episode_id':context.episode_id,'key':operation_key}),'record_refs':[sheet_ref,*bindings.values()],
                'changed_record_refs':created,'result':{'sheet_ref':sheet_ref,'cells':sheet['cells'],
                    'comparison':payload['comparison'],'raw_representation_roster_complete':sheet['candidate_set_complete'],
                    'interpretation_kind':payload['interpretation_kind']},'feedback':None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id,context.episode_id,operation_key,signature,canonical(outcome)))
        return outcome

    def project_cells(self,sheet_refs,*,permitted_record_refs,components=None):
        rows=super().project_cells(sheet_refs,permitted_record_refs=permitted_record_refs,components=components)
        for row in rows:
            saved=self.read(row['sheet_ref'])
            cell=saved['sheet']['cells'][row['component']]
            row.update(value_candidates=cell['value_candidates'],candidate_basis='received_source_representations',
                raw_representation_roster_complete=saved['sheet']['candidate_set_complete'],
                uncertainty_kind='unreported',independent_preparation_count=None,
                source_origins=sorted({item['origin'] for item in saved['sheet']['observations']}),
                interpretation_kind='episode_source_interpretation',
                **{name:saved['comparison'][name] for name in ('signal_kind','reference_role','arrangement')})
        return rows


def ratio_cells_schema():
    reference={'type':'string','format':'reference','x-reference-namespace':'source'}
    properties={'sheet_ref':dict(reference),'evidence_source_ref':dict(reference),
        'component':{'type':'string','enum':list(COMPONENTS)},'value':{'type':['number','null']},
        'value_candidates':{'type':'array','uniqueItems':True,'items':{'type':'number'}},
        'candidate_basis':{'type':'string','enum':['received_source_representations']},
        'raw_representation_roster_complete':{'type':'boolean'},
        'unit':{'type':['string','null'],'enum':['fraction','dimensionless',None]},
        'status':{'type':'string','enum':['populated','conflicting','unavailable']},
        'origin':{'type':'string','enum':['reported','synthetic','visual_transcription','derived','proposed']},
        'unavailable_reason':{'type':['string','null'],'enum':[None,*REASONS]},
        'conditional_on':{'type':'array','items':{'type':'string','enum':['source_interpretation']}},
        'uncertainty_kind':{'type':'string','enum':['unreported']},
        'independent_preparation_count':{'type':['integer','null'],'minimum':0},
        'source_origins':{'type':'array','uniqueItems':True,'items':{'type':'string','enum':['reported','synthetic','visual_transcription']}},
        'interpretation_kind':{'type':'string','enum':['episode_source_interpretation']},
        'signal_kind':{'type':'string','enum':list(SIGNALS)},'reference_role':{'type':'string','enum':list(REFERENCES)},
        'arrangement':{'type':'string','enum':list(ARRANGEMENTS)}}
    for name,namespace in BINDINGS.items():
        properties[name]={'type':['string','null'],'format':'reference','x-reference-namespace':namespace}
    return {'type':'array','items':obj(properties),'x-source':'literature_ratio_cells'}
