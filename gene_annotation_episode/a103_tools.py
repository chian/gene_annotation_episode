"""A103 scientific operations with explicit inputs and shared native admission."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys

from .a103_publication import publish, received_measurement, binding_body
from .a103_scoring import VERSION, MAX_FILE_BYTES, MAX_PANEL, MAX_FLANK_BP, binding_summary, digest, require
from .acquisition import AcquisitionError
from .communication import plain
from .domain import canonical, obj, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .local_jobs import LocalJobPolicy, run_cancellable_native
from .native_lifecycle import NativeJobHandle, prepare_job, start_prepared, wait_job
from .tools import ToolRegistry


REF = {'type':'string','format':'reference'}
NULL_REF = {'anyOf':[REF,{'type':'null'}]}
REFS = {'type':'array','items':REF,'uniqueItems':True}
TEXT = {'type':'string','minLength':1}
INT = {'type':'integer','minimum':0}
NAMES = ('context.bind_locus','reference.neighborhood','context.compare_neighborhoods',
    'context.fusion','context.cooccurrence','context.contrast','context.association_channels','context.detection_inventory',
    'context.request_hpc')


def catalog():
    entries = {
        'context.bind_locus':('Bind an actual supplied GenBank or GFF3+FASTA CDS to its sequence and original genomic record. Preserve ambiguity, translation checks, construct/record identity and whether this file is caller-associated target material or a reference. This alone earns no association credit.',
            obj({'target_ref':REF,'file_source_ref':REF,'accession':TEXT,
                'format':{'enum':['genbank','gff3']},'sequence_source_ref':NULL_REF,
                'genetic_code':{'type':['integer','null'],'minimum':1},
                'selector':{'oneOf':[obj({'locus_tag':TEXT}),obj({'protein_id':TEXT}),obj({'coordinate':INT})]}})),
        'reference.neighborhood':('Measure the actually acquired neighborhood around a received A103 locus binding. Retain native features, gene order, strand, signed gaps/overlaps, regulatory footprints, fetched boundaries and original coordinates. Source product labels remain source annotations. This does not infer an operon or exact function.',
            obj({'binding_ref':REF,'left_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP},
                'right_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP}})),
        'context.compare_neighborhoods':('Measure a declared gene-organization relationship over an explicit panel. Identify actual left/right CDS indices, sampling groups and a fixed relationship definition. Exact component identities or received native alignments qualify each row automatically; unknown rows retain their denominators and bounds. Neighbor homology scores never substitute for a context statistic.',
            obj({'target_ref':REF,'partner_reference_ref':REF,'definition_source_refs':{**REFS,'minItems':1},
                'rows':{'type':'array','minItems':2,'maxItems':MAX_PANEL,'items':obj({
                    'neighborhood_ref':REF,'left_feature_index':INT,'right_feature_index':{'type':['integer','null'],'minimum':0},
                    'sampling_group':TEXT,'right_detection_ref':NULL_REF},
                    required=['neighborhood_ref','left_feature_index','right_feature_index','sampling_group'])},
                'definition':obj({'maximum_gap_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP},
                    'maximum_intervening_genes':{'type':'integer','minimum':0,'maximum':128},
                    'orientation':{'enum':['any','same','convergent','divergent']},
                    'order':{'enum':['any','left_before_right','right_before_left']}})})),
        'context.fusion':('Measure linkage of explicitly attributed nonoverlapping domains/regions within one actual coding product. Each region needs its own received component sequence/map and definition source. Emit local target features when mapped; fused architecture does not automatically establish activities of every domain or the whole protein.',
            obj({'target_ref':REF,'binding_ref':REF,'definition_source_refs':{**REFS,'minItems':1},
                'regions':{'type':'array','minItems':2,'maxItems':16,'items':obj({'start':INT,'end':INT,
                    'component_ref':REF,'alignment_ref':NULL_REF})}})),
        'context.cooccurrence':('Calculate an exact association test from actual admitted detection inventories, with an explicit genome panel. Presence, detection-limited absence and unknown remain distinct. Retain contingency counts, direction, null, sampling groups and correction status; related samples cannot silently count as independent.',
            obj({'target_ref':REF,'left_reference_ref':REF,'right_reference_ref':REF,
                'definition_source_refs':{**REFS,'minItems':1},'rows':{'type':'array','minItems':2,'maxItems':MAX_PANEL,
                    'items':obj({'genome_key':TEXT,'sampling_group':TEXT,'left_detection_ref':REF,'right_detection_ref':REF})}})),
        'context.detection_inventory':('Collect a detection state from an actually completed parent-delivered native phmmer search. Requires the registered parsed-search receipt, actual native output Source, exact searched FASTA Source, component query and measured genomic records. Complete examined CDS coverage permits only detection-limited absence within those records; unexamined sequence or incomplete annotations remain unknown. This port performs no sequence search.',
            obj({'target_ref':REF,'binding_refs':{**REFS,'minItems':1,'maxItems':MAX_PANEL},
                'snapshot_ref':REF,'native_source_ref':REF,'database_source_ref':REF,'component_ref':REF,
                'neighborhood_ref':NULL_REF},required=['target_ref','binding_refs','snapshot_ref','native_source_ref','database_source_ref','component_ref'])),
        'context.contrast':('Compare actual context measurements against explicit alternative relationships. Retain exceptions, paralogs, optional modules and source-grounded incompatibility witnesses. This functional interpretation does not add a second copy of underlying native context credit.',
            obj({'target_ref':REF,'function_ref':REF,'supporting_source_refs':REFS,
                'opposing_source_refs':REFS,'incompatibility_witness_refs':{**REFS,'minItems':1}})),
        'context.association_channels':('Extract native STRING neighborhood/fusion/phylogenetic-profile fields separately from one received complete provider result. Preserve exact endpoints, taxon and version. Combined, expression, experimental and text-mining scores are not A103 channel substitutes.',
            obj({'target_ref':REF,'source_ref':REF,'left_native_id':TEXT,'right_native_id':TEXT,
                'left_reference_ref':REF,'right_actual_ref':REF,'right_reference_ref':REF})),
    }
    from .a103_native_requests import OPERATIONS
    request_schema = {'oneOf':[obj({'operation':{'const':name},'arguments':deepcopy(entries[name][1]),
        'resource_id':TEXT}) for name in OPERATIONS]}
    entries['context.request_hpc'] = ('Freeze an A103 native investigation from actually received genomic records, '
        'locus bindings, panels or completed detector output. Return an exact commission for the configured '
        'HPC parent and its prediction/execution sisters. This operation runs no context calculation or '
        'sequence search. The original received result is automatically graded and attributed. Reuse '
        'received measurements; missing identities and unexamined sequence remain unknown.',request_schema)
    return {name:{'description':description,'resources':'local','input_schema':schema}
            for name,(description,schema) in entries.items()}


class A103ToolRegistry(ToolRegistry):
    def __init__(self,*args,a103_work_directory,target_genomic_sources=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.a103_directory = Path(a103_work_directory).resolve()
        require('runs' in self.a103_directory.parts,'a103_output_requires_runs_directory')
        self.a103_directory.mkdir(parents=True,exist_ok=True)
        self.a103_execution_resources = None
        self.a103_policy = LocalJobPolicy(min(2 * 1024 ** 3, self.local_job_policy.memory_bytes), min(1024 ** 3, self.local_job_policy.scratch_bytes))
        # Caller-supplied material provenance is not an argument a model can set.
        self.a103_target_genomic_sources = deepcopy(target_genomic_sources or {})
        for sql in (
            'CREATE TABLE IF NOT EXISTS a103_bindings (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS a103_operations (operation_key TEXT PRIMARY KEY,request TEXT NOT NULL,result TEXT NOT NULL)',
        ):
            self.store.db.execute(sql)

    def as_record(self):
        return {**super().as_record(),'a103_tools':{'version':VERSION,'directory':str(self.a103_directory),
            'policy':self.a103_policy.to_dict(),'cpu_threads':1,
            **({'hpc_resources':deepcopy(self.a103_execution_resources)} if self.a103_execution_resources is not None else {}),
            'target_genomic_sources':deepcopy(self.a103_target_genomic_sources),'max_panel':MAX_PANEL}}

    def catalog(self,scope=None):
        entries = super().catalog(scope=scope)
        legacy = entries['reference.neighborhood']
        extra = catalog()
        if self.a103_execution_resources is None:extra.pop('context.request_hpc')
        extra['reference.neighborhood']['input_schema'] = {'oneOf':[
            extra['reference.neighborhood']['input_schema'],legacy['input_schema']]}
        return {**entries,**extra}

    def configure_a103_hpc(self,resources):
        selected = plain(resources)
        require(any(row.get('kind')=='pbs_ssh' for row in selected.values()),'a103_configured_hpc_resource_required')
        require(self.a103_execution_resources is None or self.a103_execution_resources==selected,
            'a103_hpc_resource_configuration_changed')
        self.a103_execution_resources = selected

    def received_hpc_attributions(self,context,known,*,hpc_result_reader):
        if context.role=='scientific_process' and context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id')!='A103':
            return [],[]
        from .a103_hpc import receive
        return receive(self,context,known,reader=hpc_result_reader)

    def operation_resource_limits(self):
        parent = getattr(super(),'operation_resource_limits',lambda:{})()
        return {**parent,'a103_native':{'tool_names':[name for name in NAMES if name!='context.request_hpc'],'cpu_threads':1,
            **self.a103_policy.to_dict(),'max_genomic_file_bytes':MAX_FILE_BYTES,
            'max_panel_size':MAX_PANEL,'max_flank_bp':MAX_FLANK_BP}}

    def received_attributions(self,context,known):
        parent = getattr(super(),'received_attributions',None)
        generated,needs = parent(context,known) if parent else ([],[])
        if context.role not in {'annotation','scientific_process','improvement'}:
            return generated,needs
        if context.role=='scientific_process' and context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id')!='A103':
            return generated,needs
        from .a103_attachments import refresh
        more,pending = refresh(self.store,set(known)|set(generated),plain(context.scope))
        return [*generated,*more],[*needs,*pending]

    def _received(self,reference,known):
        require(reference in known,'a103_input_not_received')
        return self.store.get(reference)

    def _target(self,reference,known,scope):
        self._received(reference,known)
        footprint = self.store.coverage(reference)
        require(footprint and self.store.scope_covers(footprint,scope),'a103_target_outside_original_scope')
        roots = {r['target_ref'] for r in footprint}
        require(len(roots)==1,'a103_single_original_target_required')
        target = next(iter(roots))
        regions = [[s['start'],s['end']] for s in footprint]
        return target,regions

    def _file(self,reference,format,known,invocation):
        self._received(reference,known)
        context,reader,*_ = invocation
        delivery,path = reader(context,reference,'source',file_format=format)
        require(delivery.get('failure') is None and path is not None,'a103_genomic_file_not_received')
        require(path.stat().st_size<=MAX_FILE_BYTES,'a103_genomic_file_size_limit')
        return path,delivery['input']['file']

    def work_directory(self,context,name,args,scope):
        return self.a103_directory/digest({'run_id':context.run_id,'episode_id':context.episode_id,
            'name':name,'args':args,'scope':plain(scope),'version':VERSION,'policy':self.a103_policy.to_dict()})

    def _job(self,request,directory,*,cancel_event=None):
        directory.mkdir(parents=True,exist_ok=True)
        path = directory/'worker-request.json'
        serialized = canonical(request)
        if path.exists():
            require(path.read_text()==serialized,'a103_prepared_job_identity_conflict')
        else:
            path.write_text(serialized)
        handle = NativeJobHandle(directory/'native-handle.json')
        if not handle.path.exists():
            temporary,cache = directory/'tmp',directory/'cache'
            temporary.mkdir(exist_ok=True); cache.mkdir(exist_ok=True)
            prepare_job([sys.executable,'-m','gene_annotation_episode.a103_native_worker',str(path)],
                cwd=directory,policy=self.a103_policy,handle_path=handle.path,cpu_threads=1,
                env={'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(temporary),'XDG_CACHE_HOME':str(cache),
                    'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
                    'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        start_prepared(handle,cancel_event=cancel_event)
        result = wait_job(handle,cancel_event=cancel_event)
        out = directory/'worker-result.json'
        require(out.exists(),'a103_native_result_missing')
        value = json.loads(out.read_text())
        require(result.returncode==0 and value['status']=='completed',
            'a103_native_worker_failed:'+canonical(value.get('failure')))
        return value['result'],result.metadata

    def _protein(self,sequence,source,accession):
        artifact = self.store.artifact(sequence,'text/plain')
        return self.store.put('reference',{'reference_type':'protein','source_ref':source,'accession':accession,
            'label':'Actual translated genomic CDS; function unestablished','sequence_ref':artifact,
            'molecule':'protein','length':len(sequence),'term_refs':[],'context_refs':[]},origin='tool')['id']

    async def execute_async(self,name,args,*,scope=None,operation_key=None,permitted_record_refs=None):
        if name not in NAMES or name=='reference.neighborhood' and 'binding_ref' not in args:
            return await super().execute_async(name,args,scope=scope,operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            validate_schema(args,catalog()[name]['input_schema'])
            scope = self.store.validate_scope(scope)
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:]==(name,args,operation_key),
                'a103_current_action_binding_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store,context.run_id,failure_prefix='a103_').authenticate(context)
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known<=set(context.received_record_refs),'a103_explicit_received_inputs_required')
            request = canonical({'run_id':context.run_id,'episode_id':context.episode_id,
                'name':name,'args':args,'scope':scope,'version':VERSION})
            prior = self.store.db.execute('SELECT * FROM a103_operations WHERE operation_key=?',(operation_key,)).fetchone()
            if prior:
                require(prior['request']==request,'a103_operation_identity_conflict')
                return json.loads(prior['result'])
            old = self.store.db.execute('SELECT result FROM a103_operations WHERE request=? LIMIT 1',(request,)).fetchone()
            if old and name!='context.request_hpc':
                outcome = json.loads(old[0])
                outcome['result']['reused_existing_measurement'] = True
                self.store.db.execute('INSERT INTO a103_operations VALUES(?,?,?)',(operation_key,request,canonical(outcome)))
                return outcome
            records,refs = [],[]
            native = None
            directory = self.work_directory(context,name,args,scope)
            if name=='context.request_hpc':
                from .a103_hpc import freeze,commission,existing_local,result_body
                require(self.a103_execution_resources is not None and args['resource_id'] in self.a103_execution_resources,
                    'a103_configured_hpc_resource_required')
                existing = existing_local(self.store,args['operation'],args['arguments'],scope,known)
                if existing:
                    records = existing
                    result = {'execution_status':'qualified_measurement_already_received',
                        'new_execution_requested':False,'scientific_credit':0.}
                else:
                    request_ref,body = freeze(self,args['operation'],args['arguments'],args['resource_id'],
                        context=context,scope=scope,known=known,invocation=invocation)
                    retained = [(ref,admission) for ref in sorted(known)
                        if (admission:=result_body(self.store,ref)) is not None and admission['completed']
                        and admission['logical_work_sha256']==body['logical_work_sha256']
                        and set(admission['measurement_refs'])<=known]
                    if retained:
                        records = list(dict.fromkeys([request_ref,*[ref for ref,_ in retained],
                            *[ref for _,admission in retained for ref in admission['measurement_refs']]]))
                        result = {'request_ref':request_ref,'execution_status':'qualified_measurement_already_received',
                            'new_execution_requested':False,'scientific_credit':0.}
                    else:
                        from .hpc_commission_sources import publish as publish_commission
                        work = commission(body,self.a103_execution_resources)
                        commission_ref = publish_commission(self.store,work,scope=scope,resources=self.a103_execution_resources)
                        records = [request_ref,commission_ref]
                        result = {'request_ref':request_ref,'commission_source_ref':commission_ref,
                            'hpc_assignment':{'commission_source_ref':commission_ref},
                            'execution_owner':'shared_hpc_parent_with_prediction_and_execution_sisters',
                            'new_execution_requested':True,'scientific_credit':0.}
            elif name=='context.bind_locus':
                target,regions = self._target(args['target_ref'],known,scope)
                path,file = self._file(args['file_source_ref'],'genbank_text' if args['format']=='genbank' else 'gff3_text',known,invocation)
                sequence_path = None
                if args['sequence_source_ref'] is not None:
                    sequence_path,_ = self._file(args['sequence_source_ref'],'fasta_text',known,invocation)
                source = self.store.get(args['file_source_ref'])
                original_request = json.loads(self.store.get_artifact(source['request_ref'])) if source.get('request_ref') else None
                if original_request and 'request' in original_request:
                    original_request = original_request['request']
                if original_request and 'params' in original_request:
                    original_request = original_request['params']
                body,native = await run_cancellable_native(self._job,{'operation':'bind',**args,'target_ref':target,
                    'input_path':str(path),'sequence_path':str(sequence_path) if sequence_path else None,
                    'source_request':original_request,'query_sequence':self._sequence(args['target_ref']),
                    'query_molecule':self.store.subject_molecule(args['target_ref'])},directory)
                body.update(target_regions=regions,material_ref=args['target_ref'],
                    supplied_target_genome=args['file_source_ref'] in self.a103_target_genomic_sources.get(target,[]))
                placement = body.get('native_input_placement')
                if placement and placement['state']=='unique' and placement['molecule'] in {'dna','rna'}:
                    mapping = self.store.sequence_mapping(args['target_ref'])
                    require(mapping['units_per_symbol']==1,'a103_original_nucleotide_map_required')
                    positions = [p for part in mapping['path'] for p in
                        (range(part['end']-1,part['start']-1,-1) if part['strand']=='-' else range(part['start'],part['end']))]
                    selected = sorted({positions[p] for a,b in placement['placements'][0]['target_intervals'] for p in range(a,b)})
                    spans = []
                    for p in selected:
                        if spans and p==spans[-1][1]:spans[-1][1]+=1
                        else:spans.append([p,p+1])
                    body['target_regions'] = spans
                if body['selection_status']=='selected' and body['locus']['translation']['status']=='verified':
                    tr = body['locus']['translation']['sequence']
                    protein = self._protein(tr,args['file_source_ref'],body['accession']+'.CDS.'+str(body['locus']['source_feature_index']))
                    body['protein_reference_ref'] = protein
                    records.append(protein)
                binding_ref = publish(self.store,binding_summary(body),[target,args['file_source_ref'],*records])
                self.store.db.execute('INSERT OR IGNORE INTO a103_bindings VALUES(?,?)',(binding_ref,canonical(body)))
                records.append(binding_ref)
                result = {'binding_ref':binding_ref,**binding_summary(body)}
            elif name=='reference.neighborhood':
                binding = binding_body(self.store,args['binding_ref'],known)
                self._target(binding['target_ref'],known,scope)
                body,native = await run_cancellable_native(self._job,{'operation':'neighborhood','binding':binding,
                    'left_bp':args['left_bp'],'right_bp':args['right_bp']},directory)
                body.update(binding_ref=args['binding_ref'],target_regions=binding['target_regions'])
                for row in body['cds']:
                    tr = row['translation']
                    if tr['status']=='verified':
                        protein = self._protein(tr['sequence'],binding['file_source_ref'],binding['accession']+'.CDS.'+str(row['source_feature_index']))
                        row['protein_reference_ref'] = protein
                        records.append(protein)
                source = publish(self.store,body,[args['binding_ref'],*records])
                records.append(source)
                result = {'neighborhood_ref':source,'binding_ref':args['binding_ref'],
                    'accession':body['accession'],'window':body['raw_neighborhood']['window'],
                    'coordinate_mapping':body['raw_neighborhood']['coordinate_mapping'],
                    'cds':[{k:v for k,v in row.items() if k!='translation'} | {
                        'qualifiers':{k:v for k,v in row['qualifiers'].items()
                            if k in {'gene','locus_tag','old_locus_tag','protein_id','product'}},
                        'translation_status':row['translation']['status']} for row in body['cds']],
                    'regulatory_features':body['regulatory_features'],
                    'source_labels_are':body['source_labels_are'],
                    'full_native_detail_source_ref':source}
            elif name=='context.compare_neighborhoods':
                target,regions = self._target(args['target_ref'],known,scope)
                for ref in [args['partner_reference_ref'],*args['definition_source_refs']]:self._received(ref,known)
                rows = []
                for row in args['rows']:
                    self._received(row['neighborhood_ref'],known)
                    measured = received_measurement(self.store,row['neighborhood_ref'])
                    require(measured is not None and measured['body']['schema']=='a103_neighborhood_v1','a103_actual_neighborhood_required')
                    anchor = binding_body(self.store,measured['body']['binding_ref'],known)
                    require(row['left_feature_index']==anchor['locus']['source_feature_index'],'a103_context_left_must_be_bound_focal_locus')
                    selected = {**row,'neighborhood':measured['body']}
                    if row['right_feature_index'] is None:
                        detection_ref = row.get('right_detection_ref')
                        selected['partner_absence_evaluable'] = False
                        if detection_ref is not None:
                            self._received(detection_ref,known)
                            proof = received_measurement(self.store,detection_ref)
                            require(proof is not None and proof['body']['schema']=='a103_detection_v1'
                                and proof['body'].get('neighborhood_ref')==row['neighborhood_ref']
                                and proof['body']['component_ref']==args['partner_reference_ref'],
                                'a103_absence_specific_query_or_neighborhood_conflict')
                            require(proof['body']['present'] is not True,'a103_negative_context_conflicts_with_actual_detection')
                            selected['partner_absence_evaluable'] = proof['body']['present'] is False
                    rows.append(selected)
                body,native = await run_cancellable_native(self._job,{'operation':'compare','rows':rows,'definition':args['definition']},directory)
                body.update(target_ref=target,target_regions=regions,partner_reference_ref=args['partner_reference_ref'],
                    definition_source_refs=args['definition_source_refs'],
                    comparison_group=digest([target,args['partner_reference_ref'],args['definition'],
                        sorted((r['neighborhood_ref'],r['left_feature_index'],r['right_feature_index'],r['sampling_group']) for r in args['rows'])]),
                    comparison_variant=digest(args))
                refs = [args['partner_reference_ref'],*args['definition_source_refs'],*[r['neighborhood_ref'] for r in args['rows']]]
                source = publish(self.store,body,refs); records.append(source)
                result = {'comparison_ref':source,**body}
            elif name=='context.fusion':
                target,regions = self._target(args['target_ref'],known,scope)
                binding = binding_body(self.store,args['binding_ref'],known)
                for ref in [*args['definition_source_refs'],*[r['component_ref'] for r in args['regions']],
                            *[r['alignment_ref'] for r in args['regions'] if r['alignment_ref']]]:
                    self._received(ref,known)
                body,native = await run_cancellable_native(self._job,{'operation':'fusion','binding':binding,'regions':args['regions']},directory)
                body.update(target_ref=target,target_regions=regions,binding_ref=args['binding_ref'],
                    definition_source_refs=args['definition_source_refs'],
                    comparison_group=digest([target,args['binding_ref'],[(r['start'],r['end'],r['component_ref']) for r in args['regions']]]),
                    comparison_variant=digest(args))
                source = publish(self.store,body,[args['binding_ref'],*args['definition_source_refs'],*[r['component_ref'] for r in args['regions']]])
                records.append(source); result = {'fusion_ref':source,**body}
            elif name=='context.detection_inventory':
                from .a103_detection import search_receipt
                target,regions = self._target(args['target_ref'],known,scope)
                metadata,query = search_receipt(self.store,args['snapshot_ref'],args['native_source_ref'],args['component_ref'],known)
                native_path,_ = self._file(args['native_source_ref'],'hmmer3_text',known,invocation)
                database_path,_ = self._file(args['database_source_ref'],'fasta_text',known,invocation)
                bindings = [binding_body(self.store,r,known) for r in args['binding_refs']]
                neighborhood = None
                if args.get('neighborhood_ref'):
                    self._received(args['neighborhood_ref'],known)
                    neighborhood = received_measurement(self.store,args['neighborhood_ref'])
                    require(neighborhood is not None and neighborhood['body']['schema']=='a103_neighborhood_v1'
                        and neighborhood['body']['binding_ref'] in args['binding_refs'],
                        'a103_detection_actual_neighborhood_scope_required')
                    neighborhood = neighborhood['body']
                body,native = await run_cancellable_native(self._job,{'operation':'detection',**args,
                    'native_path':str(native_path),'database_path':str(database_path),'search_metadata':metadata,
                    'bindings':bindings,'query_sequence':query,'neighborhood':neighborhood},directory)
                body.update(target_ref=target,target_regions=regions,binding_refs=args['binding_refs'])
                refs = [args['snapshot_ref'],args['native_source_ref'],args['database_source_ref'],args['component_ref'],*args['binding_refs']]
                source = publish(self.store,body,refs);records.append(source)
                result = {'detection_ref':source,**body}
            elif name=='context.cooccurrence':
                target,regions = self._target(args['target_ref'],known,scope)
                rows = []
                for ref in [args['left_reference_ref'],args['right_reference_ref'],*args['definition_source_refs']]: self._received(ref,known)
                for row in args['rows']:
                    states = []
                    for field,component in (('left_detection_ref',args['left_reference_ref']),('right_detection_ref',args['right_reference_ref'])):
                        self._received(row[field],known)
                        detection = received_measurement(self.store,row[field])
                        require(detection is not None and detection['body']['schema']=='a103_detection_v1', 'a103_actual_detection_inventory_required')
                        proof = detection['body']
                        require(proof['genome_key']==row['genome_key'] and proof['component_ref']==component,'a103_detection_operand_conflict')
                        states.append(proof['present'])
                    rows.append({**row,'left_present':states[0],'right_present':states[1]})
                body,native = await run_cancellable_native(self._job,{'operation':'cooccurrence','rows':rows},directory)
                refs = [r[f] for r in args['rows'] for f in ('left_detection_ref','right_detection_ref')]
                body.update(target_ref=target,target_regions=regions,detection_refs=refs,
                    left_reference_ref=args['left_reference_ref'],right_reference_ref=args['right_reference_ref'],
                    definition_source_refs=args['definition_source_refs'],detection_scope='actual_received_detection_inventories',
                    comparison_group=digest([target,args['left_reference_ref'],args['right_reference_ref'],
                        sorted(r['genome_key'] for r in rows)]),comparison_variant=digest(args))
                source = publish(self.store,body,[*refs,*args['definition_source_refs']]); records.append(source)
                result = {'cooccurrence_ref':source,**body}
            elif name=='context.contrast':
                target,regions = self._target(args['target_ref'],known,scope)
                from .a103_attachments import received_attachments
                grades = {r['measurement_ref']:r for r in received_attachments(self.store,known)}
                refs = [args['function_ref'],*args['supporting_source_refs'],*args['opposing_source_refs'],*args['incompatibility_witness_refs']]
                for ref in refs:self._received(ref,known)
                selected = [*args['supporting_source_refs'],*args['opposing_source_refs']]
                require(all(r in grades and grades[r]['target_ref']==target for r in selected),'a103_contrast_requires_received_qualified_context')
                support = max((grades[r]['score'] or 0 for r in args['supporting_source_refs']),default=0.)
                oppose = max((grades[r]['score'] or 0 for r in args['opposing_source_refs']),default=0.)
                body = {'schema':'a103_contrast_v1','producer_operation':name,'target_ref':target,'target_regions':regions,
                    **{k:deepcopy(v) for k,v in args.items() if k!='target_ref'},
                    'supporting_context':support,'opposing_context':oppose,'contrast':max(0.,support-oppose),
                    'controller_credit':None,'interpretation':'explicit_functional_contrast; no_new_independent_context_measurement'}
                source = publish(self.store,body,refs); records.append(source); result = {'contrast_ref':source,**body}
            else:
                result,records = self._channels(args,known,scope)
            outcome = {'status':'completed','record_refs':list(dict.fromkeys(records)),
                'changed_record_refs':[],'result':result,'feedback':None}
            if native is not None:outcome['native_execution'] = native
            self.store.db.execute('INSERT INTO a103_operations VALUES(?,?,?)',(operation_key,request,canonical(outcome)))
            return outcome
        except AcquisitionError as error:
            return {'status':'unavailable','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':error.code,'retryable':error.code=='local_resource_busy',
                    'prepared_handle_preserved':(error.operational or {}).get('prepared_handle_preserved',True),'operational':error.operational}}
        except (ValueError,KeyError,TypeError,StopIteration) as error:
            return {'status':'invalid','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':str(error),'detail':getattr(error,'detail',{})}}

    def _channels(self,args,known,scope):
        from .a103_channels import publish_channels
        target,regions = self._target(args['target_ref'],known,scope)
        for ref in [args['source_ref'],args['left_reference_ref'],args['right_actual_ref'],args['right_reference_ref']]:
            self._received(ref,known)
        return publish_channels(self.store,{**args,'target_ref':target,'target_regions':regions})
