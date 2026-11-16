"""A103-only recursive science with shared-parent information exchange."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError, obj
from .evidence_axis_instructions import validate_instruction_entry
from .scientific_process_library import ScientificProcessLibrary
from .scientific_process_records import SELECTION_VERSION, selector_selection, validate_selection
from .scientific_tool_library import ScientificToolLibrary


VERSION = 'a103_investigation_v1'
CONTEXT_RECORD_SOURCE = 'a103_received_context_records'
TASKS = ('locus_identity','neighborhood_organization','component_attribution','comparative_context',
    'fusion_and_regions','cooccurrence','functional_contrast','synthesis')


def report_schema():
    refs = {'type':'array','items':{'type':'string','format':'reference'},'uniqueItems':True}
    schema = obj({'records':{**deepcopy(refs),'x-source':CONTEXT_RECORD_SOURCE,
            'description':'Actual context measurements, native grades, per-use attachments, local features and received information for parent recomputation.'},
        'context_credit':{'type':'number','x-source':'credit',
            'description':'Host-calculated A103 context progress; not a probability of exact function.'}})
    validate_closed_schema(schema)
    return schema


def initial_report():
    return {}


def context_fact_sources():
    return {CONTEXT_RECORD_SOURCE:{'type':'array',
        'meaning':'Completed own records plus actual received A103 measurements, per-use grades and local target features, including retained evidence; no implicit upstream receipt.',
        'report_schema':{'type':'array','items':{'type':'string','format':'reference'},
            'uniqueItems':True,'x-source':CONTEXT_RECORD_SOURCE}}}


def measurement_report_schema():
    fields=report_schema()['properties']
    return obj({name:deepcopy(fields[name]) for name in ('records','context_credit')})


def resolve_measurement_report(store,report,*,scope):
    from .a103_credit import A103ContextCredit
    validate_form(report,measurement_report_schema(),lambda ref,namespace:
        ref in store.reference_subset([ref],scope))
    credit=A103ContextCredit()(store,scope,known_record_refs=report['records'])['credit']
    if not math.isclose(credit,report['context_credit'],abs_tol=1e-12):
        raise ContractError('a103_returned_measurement_credit_conflict')
    return credit


def received_context_records(store,known,scope,*,committed=()):
    """Return authenticated received context, including prior native work."""
    from .a103_publication import received_measurement
    from .a103_attachments import received_attachments
    known=set(known)
    targets=set(scope['subject_refs'])
    records=(targets | set(committed)) & known
    for ref in known:
        native=received_measurement(store,ref)
        if native is not None and native['body']['target_ref'] in targets:
            records.add(ref)
        source=store.get(ref)
        if ((source.get('provider') or '').startswith('host.a103.hpc_')
                and ref in store.reference_subset([ref],scope)):
            records.add(ref)
    for grade in received_attachments(store,known):
        if grade['target_ref'] not in targets:continue
        records.add(grade['source_ref'])
        for region in grade.get('regions',[]):
            feature=region.get('target_feature_ref')
            if feature in known:records.add(feature)
    return sorted(records)


class A103Subtree:
    def __init__(self,run_directory):
        directory = Path(run_directory)
        self.library = ScientificProcessLibrary(directory/'scientific-process-library')
        self.tools = ScientificToolLibrary(directory/'scientific-tool-library')
        self.axis = self.library.reference('A103')
        entry = validate_instruction_entry(self.library.resolve(self.axis))
        if entry['name']!='Gene context':raise ContractError('a103_gene_context_instructions_required')

    def commission(self,store,*,target_ref,scope,child_tool_info,question,task='synthesis',
                   completeness='unknown',thought_id='P01',evidence_refs=(),constraints=None,
                   context=None,schema=None,initial=None):
        if task not in TASKS:raise ContractError('a103_unknown_context_task')
        if completeness not in {'complete','fragment','unknown'}:raise ContractError('a103_completeness_required')
        if not isinstance(question,str) or not question.strip():raise ContractError('a103_question_required')
        scope = store.validate_scope(plain(scope))
        material = store.get(target_ref)
        if material['record_type'] not in {'input','feature','product','read_subject'} or not store.scope_covers(store.coverage(target_ref),scope):
            raise ContractError('a103_original_material_required')
        references = list(dict.fromkeys([target_ref,*evidence_refs]))
        if set(store.reference_subset(references,scope))!=set(references):raise ContractError('a103_evidence_outside_scope')
        supplied = deepcopy(context or {})
        if 'a103_material' in supplied or 'a103_task' in supplied:raise ContractError('a103_material_context_reserved')
        supplied['a103_material'] = {'version':VERSION,'subject_ref':target_ref,'completeness':completeness,
            'supplied_length':store.subject_length(target_ref),'original_intervals':store.coverage(target_ref)}
        supplied['a103_task'] = {'name':task,'allowed_tasks':list(TASKS),
            'communication':'Every scientific descendant remains A103. Use available shared operations to send '
                'the immediate parent specific missing operands or received evidence relevant to its decision. '
                'That parent chooses within its own investigation options or relays the need upward. '
                'Preserve unmet needs in the typed return; publication starts no response work.',
            'native_credit':'Actual context measurements receive native sheets automatically. Locus inventory and neighbor '
                'homology alone do not create context-association scores. Each measurement/use has its own attribution. '
                'Reuse existing measurements and maps; late evidence regrades without another native context job.',
            'reporting':'Return saved context measurements and their purpose-specific per-use grading. '
                'Native quantities, status, missing inputs and qualifications come from those sheets. '
                'Do not add context_summary, functional_support or a separate report verdict; '
                'system association retains its measured scope rather than becoming exact function.',
            'resources':'Read resource_context.whole_workflow and admission feedback. Its aggregate cap includes Python, provider clients, and all workers. '
                'One small workflow and one provider can run in this Codex window at a time; other windows have independent slots. '
                'Use bounded genomic windows and explicit panels. When context.request_hpc is available, it freezes '
                'received operands for the shared HPC parent and its prediction/execution sisters. Original results '
                'are automatically graded and attributed when received. Reuse qualified received measurements. '
                'Detection inventory reads a completed parent-delivered search; new homology work stays with the shared parent. '
                'Large searches require a configured external resource; publish that need.',
            'interpretation':'Keep target and homolog loci, components, regions, sampling dependence, optional modules and '
                'detection scope explicit. Incomplete sequence is unknown, not absence. System association does not establish exact chemistry, '
                'regulatory direction, physical interaction or indispensable partners.'}
        schema = report_schema() if schema is None else deepcopy(schema)
        validate_closed_schema(schema)
        initial = initial_report() if initial is None else deepcopy(initial)
        validate_form(initial,interpretation_schema(schema),lambda ref,namespace:
            ref in store.reference_subset([ref],scope) and (namespace is None or store.get(ref)['record_type']==namespace))
        tools = self.tools.resolve_tool_info(child_tool_info)
        selection = selector_selection(validate_selection({'version':SELECTION_VERSION,
            'evidence_axis':deepcopy(self.axis),'thought_pattern':self.library.reference(thought_id),'child_tool_info':tools}))
        return {'kind':'episode_child','role':'scientific_process','goal':question,'scope':scope,
            'purpose':'Return saved gene-context measurements and their purpose-specific target/component/region grading, with its exact recorded qualifications and missing inputs; no second report verdict.',
            'schema_json':json.dumps(schema,allow_nan=False),'initial_report_json':json.dumps(initial,allow_nan=False),
            'assignment':{'selection':selection,'evidence_refs':references,'constraints':deepcopy(constraints or {}),'context':supplied}}


def create_a103_workflow(store,tools,provider,directory,run_id,controller_factory,*,initial_known_record_refs,**options):
    from .a103_credit import A103ContextCredit
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:raise ValueError('a103_numeric_binding_is_host_owned')
    if options.get('episode_record_receipts',True) is not True:raise ValueError('a103_numeric_credit_requires_receipts')
    options['episode_record_receipts'] = True
    scorer = A103ContextCredit()
    return Workflow(store,tools,provider,directory,run_id,controller_factory,scorer,
        credit_binding=scorer.as_record(),initial_known_record_refs=initial_known_record_refs,**options)


def resolve_report(store,report,*,scope):
    from .a103_credit import A103ContextCredit
    validate_form(report,report_schema(),lambda ref,namespace:
        ref in store.reference_subset([ref],scope) and (namespace is None or store.get(ref)['record_type']==namespace))
    view = A103ContextCredit().read_details(store,scope,known_record_refs=report['records'],details_limit=24,details_offset=0)
    sheets = view['a103_sheet']
    return {'context_sheets': sheets, 'tool_attachments': view['tool_attachments'],
        'target_sheets': view['target_sheets'],
        'receiving_scope_credit': view['credit'], 'child_reported_credit': report['context_credit'],
        'reporting': 'saved_context_grading; no_separate_function_verdict'}


@dataclass(frozen=True)
class A103ServiceFactory:
    source_directory: str
    tool_retrieval: dict
    additional_descriptors: tuple = ()
    execution_service_factory: object | None = None

    def __call__(self,store,*,run_id,directory,tool_catalog,job_episodes=None,resource_estimator=None,
                 tool_registry=None,**kwargs):
        from .episode_application_services import EpisodeApplicationServices
        from .scientific_process.published_evidence_assessment.episode import create_binding_tree
        from .scientific_process_setup import prepare_scientific_binding
        from .scientific_process.episode import ScientificProcessEpisode
        if self.execution_service_factory is not None:
            from .execution_service_setup import ExecutionServiceFactory
            from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.execution_job_submission.episode import ExecutionEpisode
            from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.execution_progress_assessment.episode import MonitorEpisode
            from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.hpc_work_planning.episode import HPCEpisode
            factory=self.execution_service_factory
            if not isinstance(factory,ExecutionServiceFactory):
                raise TypeError('a103_explicit_execution_service_factory_required')
            execution=factory(store,run_id=run_id,directory=directory,execution_factory=create_execution_bindings,monitor_type=MonitorEpisode,
                hpc_factory=create_hpc_bindings,tool_catalog=tool_catalog,
                tool_registry=tool_registry,job_episodes=job_episodes,resource_estimator=resource_estimator)
            roles=['scientific_process','literature',*ExecutionEpisode.entry_roles, *ExecutionResultsEpisode.entry_roles,*MonitorEpisode.entry_roles]
            if factory.hpc_commissions is not None:
                from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.hpc_work_planning.episode import HPCEpisode
                configure=getattr(tool_registry,'configure_a103_hpc',None)
                if not callable(configure):raise ContractError('a103_hpc_requires_actual_context_tool_registry')
                configure(factory.resources)
                roles.extend(HPCEpisode.entry_roles)
            descriptors=(*execution.episode_binding_descriptors,*self.additional_descriptors)
            ids=[descriptor['binding_id'] for descriptor in descriptors]
            if len(ids)!=len(set(ids)) or {'scientific_process','literature'}.intersection(ids):
                raise ContractError('a103_execution_binding_conflict')
            for descriptor in self.additional_descriptors:roles.extend(descriptor.get('roles',()))
            scientific=prepare_scientific_binding(episode_type=ScientificProcessEpisode,run_directory=directory,source_directory=self.source_directory,
                tool_catalog=tool_registry.catalog() if tool_registry is not None else tool_catalog,
                child_roles=tuple(dict.fromkeys(roles)),tool_retrieval=self.tool_retrieval,
                resource_catalogs=execution.resource_tool_catalogs)
            return EpisodeApplicationServices((scientific,*tuple(binding.as_record() for binding in create_binding_tree(None)),*descriptors),
                execution.role_credit_bindings,execution.job_progress_provider,
                resource_tool_catalogs=execution.resource_tool_catalogs)
        if job_episodes is not None:
            from .assembled_service_setup import bind_assembled_services
            from .composition_information import CONTRACT_INFORMATION_PROFILE
            return bind_assembled_services(store,run_id=run_id,directory=directory,
                job_episodes=job_episodes,resource_estimator=resource_estimator,
                source_directory=self.source_directory,tool_catalog=tool_catalog,tool_registry=tool_registry,
                tool_retrieval=self.tool_retrieval,scientific_child_roles=('scientific_process','literature','launch','monitor','results'),
                handoff_unit=1,acquired_record_unit=1,monitoring_information_unit=1,
                literature_outcome_page_size=8,monitor_outcome_page_size=8,log_window_bytes=128,
                log_roles=('native_text',),scientific_contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        scientific = prepare_scientific_binding(episode_type=ScientificProcessEpisode,run_directory=directory,source_directory=self.source_directory,
            tool_catalog=tool_catalog,child_roles=('scientific_process','literature'),tool_retrieval=self.tool_retrieval)
        return EpisodeApplicationServices((scientific,*tuple(binding.as_record() for binding in create_binding_tree(None)),*self.additional_descriptors),{})

from .scientific_process.episode import create_execution_bindings, create_hpc_bindings

from .scientific_process.execution_result_acquisition.episode import ExecutionEpisode as ExecutionResultsEpisode
