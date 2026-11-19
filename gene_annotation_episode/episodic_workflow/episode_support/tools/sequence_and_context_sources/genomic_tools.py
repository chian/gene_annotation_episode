"""Private A107 genomic presence input preparation and HPC receipt publication."""
from contextvars import ContextVar
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.genomic_tables import RESULTS
from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.scoring import VERSION, MAX_FILE_BYTES, MAX_PANEL, MAX_FLANK_BP, digest, require
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.partner_presence_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.tools import ToolRegistry

REF = {'type':'string','format':'reference'}
NULL_REF = {'anyOf':[REF,{'type':'null'}]}
REFS = {'type':'array','items':REF,'uniqueItems':True}
TEXT = {'type':'string','minLength':1}
INT = {'type':'integer','minimum':0}

def catalog():
    entries = {
        'context.bind_locus':('Bind an actual supplied GenBank or GFF3+FASTA CDS to its sequence and original genomic record. Preserve ambiguity, translation checks, construct/record identity and whether this file is caller-associated target material or a reference. This alone earns no association credit.',
            obj({'target_ref':REF,'file_source_ref':REF,'accession':TEXT,
                'format':{'enum':['genbank','gff3']},'sequence_source_ref':NULL_REF,
                'genetic_code':{'type':['integer','null'],'minimum':1},
                'selector':{'oneOf':[obj({'locus_tag':TEXT}),obj({'protein_id':TEXT}),obj({'coordinate':INT})]}})),
        'reference.neighborhood':('Measure the actually acquired neighborhood around a received locus binding. Retain native features, gene order, strand, signed gaps/overlaps, regulatory footprints, fetched boundaries and original coordinates. Source product labels remain source annotations. This does not infer an operon or exact function.',
            obj({'binding_ref':REF,'left_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP},
                'right_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP}})),
        'context.detection_inventory':('Collect a detection state from an actually completed parent-delivered native phmmer search. Requires the registered parsed-search receipt, actual native output Source, exact searched FASTA Source, component query and measured genomic records. Complete examined CDS coverage permits only detection-limited absence within those records; unexamined sequence or incomplete annotations remain unknown. This port performs no sequence search.',
            obj({'target_ref':REF,'binding_refs':{**REFS,'minItems':1,'maxItems':MAX_PANEL},
                'snapshot_ref':REF,'native_source_ref':REF,'database_source_ref':REF,'component_ref':REF,
                'neighborhood_ref':NULL_REF},required=['target_ref','binding_refs','snapshot_ref','native_source_ref','database_source_ref','component_ref'])),
    }
    from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.genomic_requests import OPERATIONS
    request_schema = {'oneOf':[obj({'operation':{'const':name},'arguments':deepcopy(entries[name][1]),
        'resource_id':TEXT}) for name in OPERATIONS]}
    entries['context.request_hpc'] = ('Freeze an A107 genomic presence investigation from actually received genomic records, '
        'locus bindings, examined neighborhoods or completed detector output. Return an exact commission for the configured '
        'HPC parent and its prediction/execution sisters. This operation runs no context calculation or '
        'sequence search. The original received result is automatically graded and attributed. Reuse '
        'received measurements; missing identities and unexamined sequence remain unknown.',request_schema)
    return {name:{'description':description,'resources':'local','input_schema':schema}
            for name,(description,schema) in entries.items()}


class A107GenomicToolRegistry(ToolRegistry):
    def __init__(self,*args,a107_genomic_work_directory,target_genomic_sources=None,**kwargs):
        super().__init__(*args,**kwargs)
        # The acting episode of the current tool action: (ActionInvocation, received-input reader, name, arguments, operation key).
        self._current_invocation = ContextVar('a107_action_invocation', default=None)
        self.a107_genomic_directory = Path(a107_genomic_work_directory).resolve()
        require('runs' in self.a107_genomic_directory.parts,'a103_output_requires_runs_directory')
        self.a107_genomic_directory.mkdir(parents=True,exist_ok=True)
        self.a107_genomic_execution_resources = None
        self.a107_genomic_policy = LocalJobPolicy(min(2 * 1024 ** 3, self.local_job_policy.memory_bytes), min(1024 ** 3, self.local_job_policy.scratch_bytes))
        # Caller-supplied material provenance is not an argument a model can set.
        self.a107_target_genomic_sources = deepcopy(target_genomic_sources or {})

    def as_record(self):
        return {**super().as_record(),'a107_genomic_tools':{'version':VERSION,'directory':str(self.a107_genomic_directory),
            'policy':self.a107_genomic_policy.to_dict(),'cpu_threads':1,
            **({'hpc_resources':deepcopy(self.a107_genomic_execution_resources)} if self.a107_genomic_execution_resources is not None else {}),
            'target_genomic_sources':deepcopy(self.a107_target_genomic_sources),'max_panel':MAX_PANEL}}

    def catalog(self, scope=None):
        entries = super().catalog(scope=scope)
        if self.a107_genomic_execution_resources is not None:
            entries['context.request_hpc'] = catalog()['context.request_hpc']
        return entries

    def configure_a107_genomic_hpc(self,resources):
        selected = plain(resources)
        require(any(row.get('kind')=='pbs_ssh' for row in selected.values()),'a103_configured_hpc_resource_required')
        require(self.a107_genomic_execution_resources is None or self.a107_genomic_execution_resources==selected,
            'a103_hpc_resource_configuration_changed')
        self.a107_genomic_execution_resources = selected

    def received_hpc_attributions(self, context, known, *, hpc_result_reader):
        if context.role != 'partner_presence_evidence':
            return [], []
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc import receive
        return receive(self, context, known, reader=hpc_result_reader)

    def operation_resource_limits(self):
        parent = getattr(super(), 'operation_resource_limits', lambda: {})()
        return {**parent, 'a107_genomic_request': {'tool_names': ['context.request_hpc'],
            'cpu_threads': 1, 'max_genomic_file_bytes': MAX_FILE_BYTES,
            'max_panel_size': MAX_PANEL, 'max_flank_bp': MAX_FLANK_BP}}

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
        return self.a107_genomic_directory/digest({'run_id':context.run_id,'episode_id':context.episode_id,
            'name':name,'args':args,'scope':plain(scope),'version':VERSION,'policy':self.a107_genomic_policy.to_dict()})

    def _protein(self,sequence,source,accession):
        artifact = self.store.artifact(sequence,'text/plain')
        return self.store.put('reference',{'reference_type':'protein','source_ref':source,'accession':accession,
            'label':'Actual translated genomic CDS; function unestablished','sequence_ref':artifact,
            'molecule':'protein','length':len(sequence),'term_refs':[],'context_refs':[]},origin='tool')['id']

    async def execute_async(self,name,args,*,scope=None,operation_key=None,permitted_record_refs=None):
        if name != 'context.request_hpc':
            return await super().execute_async(name,args,scope=scope,operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            validate_schema(args,catalog()[name]['input_schema'])
            scope = self.store.validate_scope(scope)
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:]==(name,args,operation_key),
                'a103_current_action_binding_required')
            context = invocation[0]
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known<=set(context.received_record_refs),'a103_explicit_received_inputs_required')
            request = canonical({'run_id':context.run_id,'episode_id':context.episode_id,
                'name':name,'args':args,'scope':scope,'version':VERSION})
            from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc import freeze,commission,existing_local,result_body
            require(self.a107_genomic_execution_resources is not None and args['resource_id'] in self.a107_genomic_execution_resources,
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
                    from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_commission_sources import publish as publish_commission
                    work = commission(body,self.a107_genomic_execution_resources)
                    commission_ref = publish_commission(self.store,work,scope=scope,resources=self.a107_genomic_execution_resources)
                    records = [request_ref,commission_ref]
                    result = {'request_ref':request_ref,'commission_source_ref':commission_ref,
                        'hpc_assignment':{'commission_source_ref':commission_ref},
                        'new_execution_requested':True,'scientific_credit':0.}
            outcome = {'status':'completed','record_refs':list(dict.fromkeys(records)),
                'changed_record_refs':[],'result':result,'feedback':None}
            self.store.table(RESULTS).put({"request":request,"result":canonical(outcome)})
            return outcome
        except AcquisitionError as error:
            return {'status':'unavailable','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':error.code,'retryable':error.code=='local_resource_busy',
                    'prepared_handle_preserved':(error.operational or {}).get('prepared_handle_preserved',True),'operational':error.operational}}
        except (ValueError,KeyError,TypeError,StopIteration) as error:
            return {'status':'invalid','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'code':str(error),'detail':getattr(error,'detail',{})}}
