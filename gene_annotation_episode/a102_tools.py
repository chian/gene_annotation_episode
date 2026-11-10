"""A102 tools over explicit structures, bounded native jobs and retained sheets.

The registry adds structural capabilities to the ordinary tool map. It owns no
investigation decisions or cross-axis work. All native processing uses the
shared one-job local admission gate and durable prepared handles.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

from .a102_publication import publish_comparison, received_grade
from .a102_scoring import VERSION, digest, feature_sheet, contrast_panel, require
from .a102_structures import MAX_FILE_BYTES, binding_summary, comparison_identity
from .acquisition import AcquisitionError
from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .local_jobs import LocalJobPolicy, run_cancellable_native
from .native_lifecycle import NativeJobHandle, prepare_job, start_prepared, wait_job
from .tools import ToolRegistry


REF={'type':'string','format':'reference'}
REFS={'type':'array','items':REF,'uniqueItems':True}
TEXT={'type':'string','minLength':1}
INTEGER={'type':'integer','minimum':0}
NAMES=('structure.bind','structure.inspect','structure.align','structure.discover',
    'structure.feature_geometry','structure.contrast','structure.reported_comparison','structure.model_request',
    'structure.reference_align','structure.reference_traits','structure.interface_geometry',
    'structure.request_hpc_comparison')


def catalog():
    entries={
        'structure.request_hpc_comparison': {'description': 'Freeze a structural comparison from actually received '
            'model bindings and publish an exact commission for the configured HPC parent, including its '
            'prediction and execution sisters. This operation executes no algorithm and earns no B. '
            'The original collected result is automatically graded when received. A reference-only measured '
            'model requires the explicit target attribution operands; source geometry alone does not transfer.',
            'input_schema': obj({'target_binding_ref': REF,
                'reference_binding_refs': {**REFS, 'minItems': 1, 'maxItems': 32},
                'algorithm': {'enum': ['US-align', 'Foldseek']}, 'primary': {'type': 'boolean'},
                'resource_id': TEXT, 'attribution': {'anyOf': [{'type': 'null'}, obj({
                    'target_ref': REF, 'target_regions': {'type': 'array', 'minItems': 1,
                        'items': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': INTEGER}},
                    'sequence_alignment_ref': {'anyOf': [REF, {'type': 'null'}]}})]}})},
        'structure.bind':{'description':'Bind one explicitly received PDB/mmCIF chain/model to its represented sequence and, for the target, the actual supplied sequence. Retain construct mutations, missing coordinates, native residue identities, model origin and uncertainty. Coordinate mapping performs no sequence-homology investigation. Ambiguous mapping is unavailable; no best chain is silently selected.',
            'input_schema':obj({'file_source_ref':REF,'target_ref':{'anyOf':[REF,{'type':'null'}]},
                'format':{'enum':['pdb_3x_text','pdbx_mmcif_text']},'chain_id':{'type':'string','maxLength':32},
                'model_ordinal':INTEGER,'block_ordinal':INTEGER,'origin':{'enum':['experimental','predicted','supplied_unknown']},
                'origin_witness_refs':REFS,'qualifications':{'type':'array','items':TEXT,'uniqueItems':True}})},
        'structure.inspect':{'description':'Read one received structural binding summary, including origin, actual scope and missing/ambiguous coordinates. This does not grant private coordinate artifacts.',
            'input_schema':obj({'binding_ref':REF})},
        'structure.align':{'description':'Execute pinned US-align structural correspondence discovery on two received bound models. Preserve exact paired CA positions, transform, native metrics and both normalizations. Automatically populate and publish the A102 native grading sheet. Reuse an existing comparison when one already supplies the required evidence.',
            'input_schema':obj({'target_binding_ref':REF,'reference_binding_ref':REF,
                'primary':{'type':'boolean'}})},
        'structure.discover':{'description':'Search a bounded explicit panel of at most 32 received structures with pinned Foldseek global TMalign mode 1 and one CPU. Retain database hash, native columns, map and transform. Complete comparisons receive A102 credit immediately; incomplete leads identify the missing cells for a selected follow-up. This is not an all-PDB database search.',
            'input_schema':obj({'target_binding_ref':REF,'reference_binding_refs':{**REFS,'minItems':1,'maxItems':32},
                'primary':{'type':'boolean'}})},
        'structure.feature_geometry':{'description':'Measure required source-grounded physical feature anchors under a retained comparison scaffold transform, with no feature refit. Features require distinct physical keys and definition witnesses; missing coordinates stay unknown, established incompatibility requires a witness. Automatically populate the separate F and E sheets without changing native B.',
            'input_schema':obj({'comparison_source_ref':REF,'function_ref':REF,'definition_source_refs':REFS,
                'features':{'type':'array','minItems':1,'maxItems':128,'items':obj({
                    'physical_feature_key':TEXT,'state':{'enum':['measure','unresolved','established_absent','established_incompatible']},
                    'target_position':{'anyOf':[INTEGER,{'type':'null'}]},
                    'reference_position':{'anyOf':[INTEGER,{'type':'null'}]},
                    'target_atom':{'anyOf':[TEXT,{'type':'null'}]},'reference_atom':{'anyOf':[TEXT,{'type':'null'}]},
                    'witness_refs':REFS,'reason':TEXT})}})},
        'structure.contrast':{'description':'Compile a source-witnessed function contrast from actually received A102 feature sheets in the same target scope/profile. Max supporting E minus max explicitly incompatible alternative E is separate from controller B. An unexamined alternative pool remains unknown.',
            'input_schema':obj({'target_ref':REF,'function_ref':REF,'supporting_source_refs':REFS,
                'opposing_source_refs':REFS,'incompatibility_witness_refs':REFS})},
        'structure.reported_comparison':{'description':'Retain a structural comparison reported in an actually received external source, including its exact subject, extent and native metric units. Reported literature geometry is separate from a newly executed target comparison and grants no native A102 B.',
            'input_schema':obj({'target_ref':REF,'source_refs':REFS,'description':TEXT,
                'matched_extent':TEXT,'metric_name':{'enum':['RMSD','TM-score','DALI_Z','other']},
                'metric_value':{'type':['number','null']},'metric_unit':TEXT,'transfer_limits':TEXT})},
        'structure.model_request':{'description':'Publish a typed need for a target structural model to the shared parent when retrieval or supplied coordinates are insufficient. Novel-sequence prediction requires an explicit configured remote/API/HPC binding; this port never launches a large local folding job.',
            'input_schema':obj({'target_ref':REF,'reason':TEXT,'available_record_refs':REFS})},
    }
    from .a102_attachments import CHEMICAL_ROLES
    nullable_ref={'anyOf':[REF,{'type':'null'}]}
    entries['structure.reference_align']={'description':'Measure actual Y/Z structural correspondence for an explicitly attributed target X. Y remains a reference model. The host automatically attaches the specific received X/Y native sequence comparison and scoped distance; missing links are parent-facing needs. Reuses an existing native Y/Z alignment when available.',
        'input_schema':obj({'target_ref':REF,'measured_binding_ref':REF,'reference_binding_ref':REF,
            'target_regions':{'type':'array','minItems':1,'items':{'type':'array','items':INTEGER,'minItems':2,'maxItems':2}},
            'sequence_alignment_ref':nullable_ref,'primary':{'type':'boolean'}})}
    entries['structure.reference_traits']={'description':'Attribute explicitly defined traits of reference residues, regions, motifs or discontinuous sites to corresponding target subparts. Uses actual received A101 maps or a native target/reference structural map, never an aggregate axis score. Emits mapped target features and local trait evidence, with unknown cells retained. A geometry constraint stays inferred when no target geometry was measured. Whole-protein function requires an explicit feature-to-whole interpretation.',
        'input_schema':obj({'target_ref':REF,'reference_binding_ref':REF,'sequence_alignment_ref':nullable_ref,
            'comparison_source_ref':nullable_ref,'traits':{'type':'array','minItems':1,'maxItems':128,'items':obj({
                'physical_feature_key':TEXT,'kind':{'enum':['residue_identity','chemical_role','motif','region_identity','geometry_constraint']},
                'reference_positions':{'type':'array','minItems':1,'maxItems':4096,'items':INTEGER,'uniqueItems':True},
                'chemical_role':{'anyOf':[{'enum':list(CHEMICAL_ROLES)},{'type':'null'}]},
                'allowed_symbols':{'anyOf':[{'type':'array','items':TEXT,'minItems':1},{'type':'null'}]},
                'measurement_source_ref':nullable_ref,'definition_source_refs':{**REFS,'minItems':1}})}})}
    entries['structure.interface_geometry']={'description':'Measure source-defined contact constraints between two explicitly received chains in the same coordinate model. Retain actual interchain atom distances and assembly limitations. Automatic per-component attribution requires each target/partner correspondence; one missing partner link leaves only this interface use unresolved.',
        'input_schema':obj({'binding_refs':{'type':'array','items':REF,'minItems':2,'maxItems':2,'uniqueItems':True},
            'target_refs':{'type':'array','items':nullable_ref,'minItems':2,'maxItems':2},
            'contacts':{'type':'array','minItems':1,'maxItems':128,'items':obj({'physical_feature_key':TEXT,
                'left_position':INTEGER,'left_atom':TEXT,'right_position':INTEGER,'right_atom':TEXT,
                'maximum_distance_A':{'type':'number','exclusiveMinimum':0},'definition_source_refs':{**REFS,'minItems':1}})}})}
    entries['structure.reported_comparison']['input_schema']['properties'].update({
        'measured_subject_refs':{'type':'array','items':REF,'minItems':2,'maxItems':2},
        'measured_regions':{'type':'array','items':{'type':'array','items':INTEGER,'minItems':2,'maxItems':2},'minItems':1},
        'target_regions':{'type':'array','items':{'type':'array','items':INTEGER,'minItems':2,'maxItems':2},'minItems':1}})
    return {name:{'resources':'local',**entry} for name,entry in entries.items()}


def _software(path,kind):
    if path is None:return None
    path=Path(path).expanduser().resolve(strict=True)
    require(path.is_file() and os.access(path,os.X_OK),'a102_executable_required',kind=kind)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'version':'20261019' if kind=='US-align' else '941cd33ff0771cd2e3f144e3293e22a2b87e9fda',
        'kind':kind}


class A102ToolRegistry(ToolRegistry):
    def __init__(self,*args,a102_work_directory,usalign_executable=None,foldseek_executable=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.a102_directory=Path(a102_work_directory).resolve()
        require('runs' in self.a102_directory.parts,'a102_disposable_output_requires_runs_directory')
        self.a102_directory.mkdir(parents=True,exist_ok=True)
        self.a102_execution_resources=None
        self.a102_software={'US-align':_software(usalign_executable,'US-align'),
            'Foldseek':_software(foldseek_executable,'Foldseek')}
        self.a102_policy=LocalJobPolicy(min(2 * 1024 ** 3, self.local_job_policy.memory_bytes), min(1024 ** 3, self.local_job_policy.scratch_bytes))
        for sql in [
            'CREATE TABLE IF NOT EXISTS a102_structure_bindings (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS a102_tool_operations (operation_key TEXT PRIMARY KEY,request TEXT NOT NULL,result TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS a102_derived_publications (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL,permitted_use TEXT NOT NULL)',
        ]:self.store.db.execute(sql)

    def as_record(self):
        from .a102_attachments import VERSION as attribution_version
        from .a102_structural_bridge import VERSION as bridge_version
        return {**super().as_record(),'a102_tools':{'version':VERSION,'tool_attribution_version':attribution_version,
            'saved_comparison_bridge_version':bridge_version,
            **({'hpc_resources':deepcopy(self.a102_execution_resources)} if self.a102_execution_resources is not None else {}),
            'software':deepcopy(self.a102_software),
            'directory':str(self.a102_directory),'policy':self.a102_policy.to_dict(),'cpu_threads':1,
            'foldseek_database':'explicit_received_panel_at_most_32','novel_prediction':'shared_parent_explicit_remote_binding_required'}}

    def catalog(self,scope=None):
        entries=super().catalog(scope=scope)
        require(not set(entries)&set(NAMES),'a102_tool_operation_owner_conflict')
        structural=catalog()
        if self.a102_execution_resources is None:structural.pop('structure.request_hpc_comparison')
        return {**entries,**structural}

    def configure_a102_hpc(self,resources):
        selected=plain(resources)
        require(any(row.get('kind')=='pbs_ssh' for row in selected.values()),'a102_configured_hpc_resource_required')
        require(self.a102_execution_resources is None or self.a102_execution_resources==selected,
            'a102_hpc_resource_configuration_changed')
        self.a102_execution_resources=selected

    def operation_resource_limits(self):
        return {'a102_native':{'tool_names':['structure.bind','structure.align','structure.discover','structure.reference_align'],
            'cpu_threads':1,**self.a102_policy.to_dict(),'max_structure_file_bytes':MAX_FILE_BYTES,
            'max_residues_per_chain':4096,'max_foldseek_panel_size':32}}

    def received_attributions(self,context,known):
        from .a102_attachments import refresh
        if context.role not in {'annotation','scientific_process','improvement'}:return [],[]
        if context.role=='scientific_process' and context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id')!='A102':
            return [],[]
        return refresh(self.store,known,plain(context.scope))

    def received_structural_attributions(self,context,known,*,input_authority,hpc_result_reader):
        from .a102_structural_bridge import publish_received_comparisons
        if context.role=='scientific_process' and context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id')!='A102':
            return [],[]
        from .a102_hpc import receive_results
        generated,hpc_needs=receive_results(self.store,context,known,read_result=hpc_result_reader)
        comparisons,needs=publish_received_comparisons(self.store,context,input_authority=input_authority,
            known_record_refs=set(known)|set(generated))
        return list(dict.fromkeys([*generated,*comparisons])),[*hpc_needs,*needs]

    def _reference_request(self,args,comparison_ref):
        from .a102_attachments import request
        return request(self.store,{'operation':'structure.reference_align','target_ref':args['target_ref'],
            'measurement_ref':comparison_ref,'measured_binding_ref':args['measured_binding_ref'],
            'regions':args['target_regions'],'sequence_alignment_ref':args['sequence_alignment_ref']},
            [args['target_ref'],comparison_ref,args['measured_binding_ref'],args['reference_binding_ref'],
                *([args['sequence_alignment_ref']] if args['sequence_alignment_ref'] else [])])

    def publish_a102_comparison_bridge(self,**arguments):
        invocation=self._current_invocation.get()
        if invocation is None:return []
        from .a102_structural_bridge import publish_bridge
        return publish_bridge(self,**arguments,known_record_refs=invocation[0].received_record_refs,
            scope=plain(invocation[0].scope))

    def _received(self,reference,known):
        require(reference in known,'a102_input_not_received',reference=reference)
        return self.store.get(reference)

    def _binding(self,reference,known,scope):
        source=self._received(reference,known)
        row=self.store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(reference,)).fetchone()
        require(row is not None and source.get('provider')=='native.a102.structure_binding'
            and source['origin']=='tool','a102_structure_binding_custody_required')
        body=json.loads(row['body'])
        require(json.loads(self.store.get_artifact(source['artifact_ref']))==binding_summary(body),
            'a102_structure_binding_custody_conflict')
        if body['target_ref'] is not None:
            require(self.store.scope_covers(self.store.coverage(body.get('material_ref') or body['target_ref']),scope),
                'a102_bound_target_outside_scope')
        return body

    def _source(self,provider,body,*,accession=None):
        artifact=self.store.artifact(canonical(body),'application/json')
        operands=[body['target_ref']] if body.get('target_ref') else []
        operands.extend(body.get('definition_source_refs',[]))
        if body.get('comparison_source_ref'):operands.append(body['comparison_source_ref'])
        operands.extend(body.get('binding_refs',[]))
        if body.get('target_refs'):operands.extend(r for r in body['target_refs'] if r)
        operands=[r for r in dict.fromkeys(operands) if self.store.get(r)['record_type'] in {'input','reference','read_subject','feature','product'}]
        return self.store.put('source',{'provider':provider,'accession':accession or digest(body),'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':VERSION,'retrieved_at':None,
            **({'operand_refs':operands} if operands else {})},origin='tool')['id']

    def _derived(self,kind,body):
        source=self._source('native.a102.'+kind,body)
        self.store.db.execute('INSERT OR IGNORE INTO a102_derived_publications VALUES(?,?,?)',
            (source,canonical(body),'a102_scoring'))
        return source

    def _file(self,reference,format,known,invocation):
        self._received(reference,known)
        context,reader,*_=invocation
        delivery,path=reader(context,reference,'source',file_format=format)
        require(delivery.get('failure') is None and path is not None,'a102_structure_file_not_received',
            failure=delivery.get('failure'))
        require(path.stat().st_size<=MAX_FILE_BYTES,'a102_structure_file_size_limit')
        return path,delivery['input']['file']

    def work_directory(self,context,name,arguments,scope):
        request={'name':name,'arguments':arguments,'scope':plain(scope),'run_id':context.run_id,
            'episode_id':context.episode_id}
        return self.a102_directory/digest({'request':request,'software':self.a102_software,
            'policy':self.a102_policy.to_dict()})

    def _job(self,request,directory,*,cancel_event=None):
        directory.mkdir(parents=True,exist_ok=True)
        request_path=directory/'worker-request.json'
        serialized=canonical(request)
        if request_path.exists():require(request_path.read_text()==serialized,'a102_prepared_job_identity_conflict')
        else:request_path.write_text(serialized)
        handle=NativeJobHandle(directory/'native-handle.json')
        if not handle.path.exists():
            temporary=directory/'tmp';temporary.mkdir(exist_ok=True)
            cache=directory/'cache';cache.mkdir(exist_ok=True)
            prepare_job([sys.executable,'-m','gene_annotation_episode.a102_native_worker',str(request_path)],
                cwd=directory,policy=self.a102_policy,handle_path=handle.path,cpu_threads=1,
                env={'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(temporary),'XDG_CACHE_HOME':str(cache),
                    'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
                    'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        start_prepared(handle,cancel_event=cancel_event)
        result=wait_job(handle,cancel_event=cancel_event)
        path=directory/'worker-result.json'
        require(path.exists(),'a102_worker_result_missing')
        value=json.loads(path.read_text())
        require(result.returncode==0 and value['status']=='completed','a102_native_worker_failed',
            failure=value.get('failure'),stderr=result.stderr_path.read_text()[-2048:])
        return value['result'],result.metadata

    async def execute_async(self,name,args,*,scope=None,operation_key=None,permitted_record_refs=None):
        if name not in NAMES:
            return await super().execute_async(name,args,scope=scope,operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            validate_schema(args,catalog()[name]['input_schema'])
            scope=self.store.validate_scope(scope)
            require(type(operation_key) is str and bool(operation_key),'a102_operation_key_required')
            invocation=self._current_invocation.get()
            require(invocation is not None and invocation[2:]==(name,args,operation_key),
                'a102_current_action_binding_required')
            from .episode_return_records import EpisodeReturnRecords
            context=invocation[0]
            EpisodeReturnRecords(self.store,context.run_id,failure_prefix='a102_').authenticate(context)
            known=set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known<=set(context.received_record_refs),'a102_explicit_received_inputs_required')
            request=canonical({'name':name,'arguments':args,'scope':scope,'run_id':context.run_id,
                'episode_id':context.episode_id,'software':self.a102_software,
                'policy':self.a102_policy.to_dict()})
            old=self.store.db.execute('SELECT * FROM a102_tool_operations WHERE operation_key=?',(operation_key,)).fetchone()
            if old:
                require(old['request']==request,'a102_operation_identity_conflict')
                return json.loads(old['result'])
            previous=self.store.db.execute('SELECT result FROM a102_tool_operations WHERE request=? LIMIT 1',
                (request,)).fetchone()
            if previous is not None and name!='structure.request_hpc_comparison':
                result=json.loads(previous['result'])
                result['result']['reused_existing_result']=True
                self.store.db.execute('INSERT INTO a102_tool_operations VALUES(?,?,?)',(operation_key,request,canonical(result)))
                return result
            directory=self.work_directory(context,name,args,scope)
            records=[];native_metadata=None
            if name=='structure.request_hpc_comparison':
                from .a102_hpc import prepare_request,request_body,result_body,commission
                require(self.a102_execution_resources is not None and args['resource_id'] in self.a102_execution_resources,
                    'a102_configured_hpc_resource_required')
                request_ref=prepare_request(self.store,args,context=context,known=known)
                body=request_body(self.store,request_ref)
                native=body['request']['native_request']
                panel=([native['reference']] if native['operation']=='usalign'
                    else [row['binding'] for row in native['references']])
                groups={comparison_identity(native['target'],item) for item in panel}
                reusable={};primary_conflicts=[]
                for reference in sorted(known):
                    prior=received_grade(self.store,reference)
                    if prior is None:continue
                    grade=prior['grade']
                    if grade['primary'] and grade['comparison_group'] in groups:primary_conflicts.append(reference)
                    if (grade['producer']==args['algorithm']
                            and (grade.get('software') or {}).get('version')==body['request']['software_pin']['version']
                            and grade.get('target_binding_ref')==args['target_binding_ref']
                            and grade['reference_ref'] in args['reference_binding_refs']
                            and grade['primary']==args['primary']):
                        reusable.setdefault(grade['reference_ref'],reference)
                retained=[(ref,admission) for ref in known if (admission:=result_body(self.store,ref)) is not None
                    and admission['request_ref']==request_ref and admission['completed']]
                if set(reusable)==set(args['reference_binding_refs']):
                    records=[request_ref,*[reusable[ref] for ref in args['reference_binding_refs']]]
                    result={'request_ref':request_ref,'execution_status':'qualified_comparisons_already_received',
                        'new_execution_requested':False,'scientific_credit':0.}
                elif retained:
                    records=list(dict.fromkeys([request_ref,*[ref for ref,_ in retained],
                        *[ref for _,body in retained for ref in body['comparison_refs']]]))
                    result={'request_ref':request_ref,'execution_status':'already_completed_and_received',
                        'new_execution_requested':False,'scientific_credit':0.}
                else:
                    require(not (args['primary'] and primary_conflicts),'a102_comparison_primary_already_declared',
                        existing_comparison_source_refs=sorted(primary_conflicts),
                        correction='Reuse the received comparisons and request only the remaining references, '
                            'or declare primary=false for a deliberate crosscheck.')
                    from .hpc_commission_sources import publish as publish_commission
                    body=request_body(self.store,request_ref)
                    work=commission(self.store,request_ref,self.a102_execution_resources)
                    commission_ref=publish_commission(self.store,work,scope=scope,resources=self.a102_execution_resources)
                    records=[request_ref,commission_ref]
                    result={'request_ref':request_ref,'commission_source_ref':commission_ref,
                        'hpc_assignment':{'commission_source_ref':commission_ref},
                        'execution_owner':'shared_hpc_parent_with_prediction_and_execution_sisters',
                        'scientific_credit':0.,'new_execution_requested':True,
                        'request_sha256':body['request_sha256']}
            elif name=='structure.bind':
                for ref in args['origin_witness_refs']:self._received(ref,known)
                target=args['target_ref'];sequence=None
                if target is not None:
                    self._received(target,known)
                    require(self.store.subject_molecule(target)=='protein' and
                        self.store.scope_covers(self.store.coverage(target),scope),'a102_supplied_protein_target_required')
                    sequence=self._sequence(target,molecule_model='protein')
                path,file=self._file(args['file_source_ref'],args['format'],known,invocation)
                native_request={'operation':'bind','input_path':str(path),'artifact_ref':file['artifact_ref'],
                    **{k:args[k] for k in ('file_source_ref','target_ref','format','chain_id','model_ordinal','block_ordinal')},
                    'supplied_sequence':sequence,'model_metadata':{'origin':args['origin'],
                        'origin_witness_refs':args['origin_witness_refs'],'qualifications':args['qualifications']}}
                body,native_metadata=await run_cancellable_native(self._job,native_request,directory)
                if target is not None:
                    mapping=self.store.sequence_mapping(target)
                    roots={row['subject_ref'] for row in mapping['path']}
                    require(mapping['units_per_symbol']==1 and len(roots)==1 and all(
                        row['unit']=='aa' and row['strand']=='+' for row in mapping['path']),
                        'a102_original_protein_sequence_mapping_required')
                    positions=[i for row in mapping['path'] for i in range(row['start'],row['end'])]
                    require(len(positions)==len(sequence) and len(set(positions))==len(positions),
                        'a102_original_protein_sequence_mapping_conflict')
                    original=next(iter(roots))
                    body['material_coordinate_to_sequence_mapping']=body['coordinate_to_input_mapping']
                    body['coordinate_to_input_mapping']=[None if p is None else positions[p]
                        for p in body['coordinate_to_input_mapping']]
                    for row in [*body['coordinates'],*body['atoms']]:row['position']=positions[row['position']]
                    for row in body['missing_coordinates']:
                        if row['input_position'] is not None:row['input_position']=positions[row['input_position']]
                    body.update(target_ref=original,material_ref=target,
                        target_scope=[min(positions),max(positions)+1],length=self.store.subject_length(original),
                        original_input_mapping=mapping)
                    body['unrepresented_input_positions']=[positions[p] for p in body['unrepresented_input_positions']]
                    for row in body['mapping_algorithm']['substitutions']:
                        row['material_input_position']=row['input_position']
                        row['input_position']=positions[row['input_position']]
                summary=binding_summary(body)
                ref=self._source('native.a102.structure_binding',summary)
                self.store.db.execute('INSERT OR IGNORE INTO a102_structure_bindings VALUES(?,?)',(ref,canonical(body)))
                records=[ref];result={'binding_ref':ref,**summary}
            elif name=='structure.inspect':
                result={'binding_ref':args['binding_ref'],**binding_summary(self._binding(args['binding_ref'],known,scope))}
            elif name in {'structure.align','structure.discover','structure.reference_align'}:
                borrowed=name=='structure.reference_align'
                if borrowed:
                    self._received(args['target_ref'],known)
                    require(args['target_ref'] in scope['subject_refs'] and self.store.subject_molecule(args['target_ref'])=='protein',
                        'reference_attribution_requires_scoped_protein_target')
                    from .a101_scoring import intervals
                    require(intervals(args['target_regions'],length=self.store.subject_length(args['target_ref']),merge_adjacent=False)==args['target_regions'],
                        'reference_attribution_regions_invalid')
                    self.store.validate_scope({'subject_refs':[args['target_ref']], 'segments':[
                        {'target_ref':args['target_ref'],'start':a,'end':b,'unit':'aa'} for a,b in args['target_regions']]},parent_scope=scope)
                    if args['sequence_alignment_ref']:self._received(args['sequence_alignment_ref'],known)
                query_binding=args['measured_binding_ref'] if borrowed else args['target_binding_ref']
                q=self._binding(query_binding,known,scope)
                require((q['target_ref'] is None) if borrowed else (q['target_ref'] is not None),
                    'reference_model_and_direct_target_bindings_are_distinct')
                if borrowed:q={**q,'target_ref':query_binding}
                kind='US-align' if name=='structure.align' else 'Foldseek'
                if borrowed:kind='US-align'
                software=self.a102_software[kind]
                require(software is not None,'a102_native_software_binding_unavailable',kind=kind)
                require(hashlib.sha256(Path(software['path']).read_bytes()).hexdigest()==software['sha256'],
                    'a102_native_software_identity_changed')
                native_request={'operation':'usalign' if kind=='US-align' else 'foldseek',
                    'target':q,'target_binding_ref':query_binding,
                    'primary':args['primary'],'software':software,'executable':software['path']}
                if kind=='US-align':
                    t=self._binding(args['reference_binding_ref'],known,scope)
                    group=comparison_identity(q,t)
                    for reference in known:
                        received=received_grade(self.store,reference)
                        if received is None:continue
                        prior=received['grade']
                        if (prior['producer']=='US-align' and prior.get('software')==software
                                and prior.get('target_binding_ref')==query_binding
                                and prior['reference_ref']==args['reference_binding_ref']
                                and prior['primary']==args['primary']):
                            outcome={'status':'completed','record_refs':[reference],'changed_record_refs':[],
                                'result':{'reused_existing_comparison':True,'comparisons':[{
                                    'comparison_source_ref':reference,'components':prior['components'],
                                    'function_specific':prior['function_specific'],'native_metrics':prior['native_metrics']}]},
                                'feedback':None}
                            if borrowed:
                                attached=self._reference_request(args,reference)
                                outcome['record_refs'].append(attached)
                                outcome['result'].update(attachment_request_ref=attached,measurement_subject='reference_only')
                            self.store.db.execute('INSERT INTO a102_tool_operations VALUES(?,?,?)',(operation_key,request,canonical(outcome)))
                            return outcome
                        require(not (args['primary'] and prior['primary'] and prior['comparison_group']==group),
                            'a102_comparison_primary_already_declared',existing_comparison_source_ref=reference,
                            correction='Reuse the existing qualified result, or set primary=false for an independent crosscheck.')
                    native_request.update(reference=t,reference_binding_ref=args['reference_binding_ref'],
                        comparison_group=group,variant_ref=digest({'group':group,'algorithm':kind,
                            'software':software,'work_identity':directory.name}))
                else:
                    panel=[{'binding_ref':ref,'binding':self._binding(ref,known,scope)} for ref in args['reference_binding_refs']]
                    manifest=[{'binding_ref':row['binding_ref'],'file_identity':row['binding']['file_identity'],
                        'selection':row['binding']['selection']} for row in panel]
                    native_request.update(references=panel,database_manifest={'entries':manifest,'sha256':digest(manifest)},
                        request_identity=digest({'target':args['target_binding_ref'],'panel':manifest,
                            'software':software,'work_identity':directory.name}))
                native,native_metadata=await run_cancellable_native(self._job,native_request,directory)
                comparisons=[]
                with self.store.transaction():
                    for comparison in native['comparisons']:
                        published=publish_comparison(self.store,comparison)
                        records.append(published['source_ref'])
                        if borrowed:records.append(self._reference_request(args,published['source_ref']))
                        comparisons.append({'comparison_source_ref':published['source_ref'],
                            'comparison_ref':comparison['variant_ref'],'components':published['grade']['components'],
                            'function_specific':published['grade']['function_specific'],
                            'native_metrics':comparison['native_metrics'],'target_model':comparison['target_model'],
                            'reference_model':comparison['reference_model'],'eligible':published['grade']['eligible'],
                            'exclusion':published['grade']['exclusion']})
                    summary={**{k:v for k,v in native.items() if k!='comparisons'},'comparisons':comparisons}
                    if not records or native['leads']:
                        records.append(self._derived('search_summary',summary))
                result=summary
                if borrowed:result.update(measurement_subject='reference_only',target_attribution='automatic_per_measurement_attachment')
            elif name=='structure.reference_traits':
                from .a102_attachments import request as attachment_request
                self._received(args['target_ref'],known)
                require(args['target_ref'] in scope['subject_refs'] and self.store.subject_molecule(args['target_ref'])=='protein',
                    'trait_requires_scoped_protein_target')
                binding=self._binding(args['reference_binding_ref'],known,scope)
                for field in ('sequence_alignment_ref','comparison_source_ref'):
                    if args[field]:self._received(args[field],known)
                keys=[t['physical_feature_key'] for t in args['traits']]
                require(len(set(keys))==len(keys),'duplicate_physical_trait')
                for trait in args['traits']:
                    require(all(p<binding['length'] for p in trait['reference_positions']),'trait_position_outside_reference')
                    require((trait['chemical_role'] is not None) if trait['kind']=='chemical_role' else
                        (trait['chemical_role'] is None or trait['kind']=='geometry_constraint'),'trait_chemical_role_contract')
                    require((trait['allowed_symbols'] is not None)==(trait['kind']=='motif'),'trait_motif_contract')
                    require((trait['measurement_source_ref'] is not None)==(trait['kind']=='geometry_constraint'),'trait_geometry_contract')
                    from .a102_attachments import CHEMICAL_ROLES
                    expected=''.join(binding['sequence'][p] for p in trait['reference_positions'])
                    allowed=([CHEMICAL_ROLES[trait['chemical_role']]]*len(expected) if trait['chemical_role'] is not None
                        else trait['allowed_symbols'] if trait['kind']=='motif' else list(expected))
                    require(len(allowed)==len(expected) and all(a in symbols for a,symbols in zip(expected,allowed,strict=True)),
                        'reference_trait_definition_does_not_hold_on_reference',physical_feature_key=trait['physical_feature_key'])
                    for ref in [*trait['definition_source_refs'],*([trait['measurement_source_ref']] if trait['measurement_source_ref'] else [])]:
                        self._received(ref,known)
                refs=[args['target_ref'],args['reference_binding_ref']]
                refs.extend(args[f] for f in ('sequence_alignment_ref','comparison_source_ref') if args[f])
                for trait in args['traits']:
                    refs.extend(trait['definition_source_refs'])
                    if trait['measurement_source_ref']:refs.append(trait['measurement_source_ref'])
                regions=([[row['start'],row['end']] for row in scope['segments'] if row['target_ref']==args['target_ref']]
                    if scope.get('segments') is not None else [[0,self.store.subject_length(args['target_ref'])]])
                source=attachment_request(self.store,{'operation':name,**args,'target_regions':regions},refs)
                records=[source];result={'attachment_request_ref':source,'trait_level':'target_subpart','whole_function':'requires_explicit_inference'}
            elif name=='structure.interface_geometry':
                result,records=self._interface(args,known,scope)
            elif name=='structure.feature_geometry':
                result,records=self._features(args,known,scope)
            elif name=='structure.contrast':
                result,records=self._contrast(args,known,scope)
            elif name=='structure.reported_comparison':
                self._received(args['target_ref'],known)
                require(bool(args['source_refs']),'a102_reported_comparison_sources_required')
                for ref in args['source_refs']:self._received(ref,known)
                for ref in args.get('measured_subject_refs',[]):self._received(ref,known)
                result={'schema':'a102_reported_comparison_v1',**args,'native_B':None,
                    'status':'reported_subject_and_extent_only','interpretation':'not_freshly_executed_target_geometry'}
                records=[self._derived('reported_comparison',result)]
            else:
                from .shared_information import SharedInformation
                return SharedInformation(self.store,context.run_id).execute(context,'shared.request_information',
                    {'target_ref':args['target_ref'],'question':'A102 needs a target structural model.',
                        'required_information':'Coordinates, original sequence-to-model map, model origin, construct and uncertainty. '
                            'Novel prediction requires an explicitly configured remote/API/HPC resource binding.',
                        'reason':args['reason'],'blocking':True,'available_record_refs':args['available_record_refs']},
                    known_record_refs=known,operation_key=operation_key)
            outcome={'status':'completed','record_refs':records,'changed_record_refs':[],
                'result':result,'feedback':None}
            if native_metadata is not None:outcome['native_execution']=native_metadata
            self.store.db.execute('INSERT INTO a102_tool_operations VALUES(?,?,?)',(operation_key,request,canonical(outcome)))
            return outcome
        except AcquisitionError as error:
            return {'status':'unavailable','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':error.code,'retryable':error.code=='local_resource_busy',
                    'prepared_handle_preserved':True,'operational':error.operational}}
        except (ValueError,KeyError,TypeError) as error:
            return {'status':'invalid','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':str(error),'detail':getattr(error,'detail',{})}}

    def _features(self,args,known,scope):
        self._received(args['comparison_source_ref'],known);self._received(args['function_ref'],known)
        require(self.store.get(args['function_ref'])['record_type'] in {'hypothesis','term'},'a102_function_entity_required')
        require(bool(args['definition_source_refs']),'a102_feature_definition_sources_required')
        for ref in args['definition_source_refs']:self._received(ref,known)
        received=received_grade(self.store,args['comparison_source_ref']);require(received is not None,'a102_native_comparison_required')
        grade=received['grade']
        q=self._binding(grade['target_binding_ref'],known,scope)
        t=self._binding(grade['reference_ref'],known,scope)
        transform=grade['transform'];features=[];physical_anchors=set()
        for feature in args['features']:
            anchor=tuple(feature[key] for key in ('target_position','reference_position','target_atom','reference_atom'))
            if all(value is not None for value in anchor):
                require(anchor not in physical_anchors,'a102_duplicate_physical_feature')
                physical_anchors.add(anchor)
            for ref in feature['witness_refs']:self._received(ref,known)
            row={'physical_feature_key':feature['physical_feature_key'],
                'witness_refs':feature['witness_refs'],'definition':deepcopy(feature)}
            if feature['state']=='measure':
                def select(binding,position,name):
                    return [a for a in binding['atoms'] if a['position']==position and a['atom_name']==name
                        and a['occupancy']!=0]
                qa=select(q,feature['target_position'],feature['target_atom'])
                ta=select(t,feature['reference_position'],feature['reference_atom'])
                if len(qa)!=1 or len(ta)!=1:
                    row.update(state='unresolved',missing_reason='required_atom_missing_or_ambiguous')
                else:
                    xyz=qa[0]['xyz_A'];matrix=transform['rotation'];shift=transform['translation_A']
                    moved=[math.fsum(a*b for a,b in zip(r,xyz,strict=True))+s for r,s in zip(matrix,shift,strict=True)]
                    row.update(state='measured',distance_A=math.dist(moved,ta[0]['xyz_A']),
                        transform_sha256=grade['transform_sha256'],atom_witnesses=[qa[0]['atom_row_key'],ta[0]['atom_row_key']])
            elif feature['state']=='unresolved':row.update(state='unresolved',missing_reason=feature['reason'])
            else:row['state']=feature['state']
            features.append(row)
        sheet=feature_sheet(grade,{'comparison_ref':grade['variant_ref'],'function_ref':args['function_ref'],
            'definition_source_refs':args['definition_source_refs'],'features':features})
        sheet.update(target_ref=grade['target_ref'],target_scope=grade['target_scope'],
            comparison_source_ref=args['comparison_source_ref'],B=grade['components']['B'],
            actual_measured_binding_ref=grade['target_binding_ref'],actual_reference_binding_ref=grade['reference_ref'],
            attachment_required=True,raw_E=sheet['E'])
        source=self._derived('features',sheet)
        from .a102_attachments import refresh,qualified_feature
        additions,_=refresh(self.store,set(known)|{source},scope)
        delivered=list(dict.fromkeys([source,*[ref for ref in additions if ref not in known]]))
        qualified=qualified_feature(self.store,source,sheet,set(known)|set(delivered))
        return {'feature_source_ref':source,**qualified},delivered

    def _interface(self,args,known,scope):
        bindings=[self._binding(ref,known,scope) for ref in args['binding_refs']]
        a,b=bindings
        require(a['file_identity']==b['file_identity'] and a['selection']['model_key']==b['selection']['model_key']
            and a['selection']['data_block']==b['selection']['data_block'] and a['selection']['chain_key']!=b['selection']['chain_key'],
            'interface_requires_distinct_chains_in_same_coordinate_model')
        for target in args['target_refs']:
            if target:
                record=self._received(target,known)
                require(self.store.subject_molecule(target)=='protein' and (target in scope['subject_refs'] or record['record_type']=='reference'),
                    'interface_component_requires_target_or_received_protein_reference')
        rows=[];anchors=set()
        for row in args['contacts']:
            for ref in row['definition_source_refs']:self._received(ref,known)
            anchor=tuple(row[k] for k in ('left_position','left_atom','right_position','right_atom'))
            require(anchor not in anchors,'duplicate_physical_interface_contact');anchors.add(anchor)
            atoms=[[atom for atom in binding['atoms'] if atom['position']==row[side+'_position']
                and atom['atom_name']==row[side+'_atom'] and atom['occupancy']!=0] for side,binding in zip(('left','right'),bindings,strict=True)]
            distance=math.dist(atoms[0][0]['xyz_A'],atoms[1][0]['xyz_A']) if all(len(x)==1 for x in atoms) else None
            rows.append({**row,'distance_A':distance,'kernel':1/(1+max(0,distance-row['maximum_distance_A'])**2) if distance is not None else None})
        result={'schema':'a102_interface_constraint_v1','target_ref':next((t for t in args['target_refs'] if t in scope['subject_refs']),None),
            **args,'contacts':rows,'raw_score':math.fsum(r['kernel'] for r in rows)/len(rows) if all(r['kernel'] is not None for r in rows) else None,
            'assembly_context':'same_coordinate_model_biological_assembly_and_partner_presence_unestablished'}
        source=self._derived('interface_geometry',result)
        return {'interface_source_ref':source,**result},[source]

    def _contrast(self,args,known,scope):
        self._received(args['target_ref'],known);self._received(args['function_ref'],known)
        require(self.store.get(args['function_ref'])['record_type'] in {'hypothesis','term'},'a102_function_entity_required')
        for ref in args['incompatibility_witness_refs']:self._received(ref,known)
        rows=[];refs={}
        for ref in [*args['supporting_source_refs'],*args['opposing_source_refs']]:
            source=self._received(ref,known)
            stored=self.store.db.execute('SELECT * FROM a102_derived_publications WHERE source_ref=?',(ref,)).fetchone()
            require(stored is not None and source.get('provider')=='native.a102.features','a102_received_feature_sheet_required')
            body=json.loads(stored['body'])
            require(json.loads(self.store.get_artifact(source['artifact_ref']))==body and body['target_ref']==args['target_ref'],
                'a102_contrast_target_or_custody_conflict')
            from .a102_attachments import qualified_feature
            body=qualified_feature(self.store,ref,body,known)
            if ref in args['supporting_source_refs']:
                require(body['function_ref']==args['function_ref'],'a102_contrast_support_function_conflict')
            rows.append(body);refs[ref]=body['comparison_ref']
        scopes={canonical(row['target_scope']) for row in rows}
        require(len(scopes)<=1,'a102_contrast_scope_conflict')
        panel=contrast_panel(rows,function_ref=args['function_ref'],
            supporting_refs=[refs[r] for r in args['supporting_source_refs']],
            opposing_refs=[refs[r] for r in args['opposing_source_refs']],
            contrast_witness_refs=args['incompatibility_witness_refs'],
            scope_ref=canonical({'target_ref':args['target_ref'],'regions':json.loads(next(iter(scopes))) if scopes else None}))
        panel.update(target_ref=args['target_ref'],supporting_source_refs=args['supporting_source_refs'],
            opposing_source_refs=args['opposing_source_refs'],contrast_witness_refs=args['incompatibility_witness_refs'])
        source=self._derived('contrast',panel)
        return {'contrast_source_ref':source,**panel},[source]
