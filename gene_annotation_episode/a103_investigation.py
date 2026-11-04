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
    schema = obj({'context_summary':{'type':'string','enum':['not_assessed','locus_only','organization_measured',
            'association_measured','no_locus','incomplete_context']},
        'scope_status':{'type':'string','enum':['not_assessed','unresolved','partial','represented']},
        'functional_support':{'type':'string','enum':['not_assessed','system_association','local_trait_evidence',
            'contrast_qualified','contradicted'],
            'description':'Use not_assessed when no explicit functional hypothesis and assessment have been created. '
                'Measured context may still be association_measured and earn credit. system_association, '
                'contrast_qualified and contradicted require actual hypothesis_refs and assessment_refs; '
                'local_trait_evidence requires a qualified fusion with mapped local target features.'},
        'limitations':{'type':'array','uniqueItems':True,'items':{'type':'string','enum':[
            'unmapped_target','reference_context_only','ambiguous_locus','partial_sequence','incomplete_assembly',
            'unexamined_flanks','neighbor_identity_unresolved','source_labels_only','optional_module',
            'related_genome_sampling','unknown_detection_scope','alternatives_unassessed',
            'regulatory_direction_unestablished','exact_chemistry_unestablished','unresolved_primary_variant']}},
        'information_need_refs':refs,
        'hypothesis_refs':{**deepcopy(refs),'items':{'type':'string','format':'reference','x-reference-namespace':'hypothesis'}},
        'assessment_refs':{**deepcopy(refs),'items':{'type':'string','format':'reference','x-reference-namespace':'assessment'}},
        'records':{**deepcopy(refs),'x-source':CONTEXT_RECORD_SOURCE,
            'description':'Actual context measurements, native grades, per-use attachments, local features and received information for parent recomputation.'},
        'context_credit':{'type':'number','x-source':'credit',
            'description':'Host-calculated A103 context progress; not a probability of exact function.'}})
    validate_closed_schema(schema)
    return schema


def initial_report():
    return {'context_summary':'not_assessed','scope_status':'not_assessed','functional_support':'not_assessed',
            'limitations':[],'information_need_refs':[],'hypothesis_refs':[],'assessment_refs':[]}


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
            'communication':'Every scientific descendant remains A103. Share acquired evidence and missing information '
                'through shared.*. The parent commissions A101/A102/A105 or other external investigations as siblings.',
            'native_credit':'Actual context measurements receive native sheets automatically. Locus inventory and neighbor '
                'homology alone do not create context-association scores. Each measurement/use has its own attribution. '
                'Reuse existing measurements and maps; late evidence regrades without another native context job.',
            'reporting':'Use context_summary for measured organization or association. Without actual functional '
                'hypothesis_refs and assessment_refs, keep functional_support=not_assessed; this does not remove '
                'context credit. Local trait evidence requires a qualified mapped fusion. Other functional '
                'interpretations require their explicit context and hypothesis/assessment records.',
            'resources':'Read resource_context.whole_workflow and admission feedback. Its aggregate cap includes Python, provider clients, and all workers. '
                'One small workflow and one provider can run in this Codex window at a time; other windows have independent slots. '
                'Use bounded genomic windows and explicit panels. Large searches require a configured external resource; publish that need.',
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
            'purpose':'Return actual gene-context measurements and their particular target/component/region attribution, bounded interpretation, and shared information needs.',
            'schema_json':json.dumps(schema,allow_nan=False),'initial_report_json':json.dumps(initial,allow_nan=False),
            'assignment':{'selection':selection,'evidence_refs':references,'constraints':deepcopy(constraints or {}),'context':supplied}}


def create_a103_workflow(store,tools,provider,directory,run_id,controller_factory,*,initial_known_record_refs,**options):
    from .a103_credit import A103ContextCredit
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:raise ValueError('a103_numeric_binding_is_host_owned')
    if options.get('episode_record_receipts',True) is not True:raise ValueError('a103_numeric_credit_requires_receipts')
    options['episode_record_receipts'] = True
    scorer = A103ContextCredit()
    if options.get('project_child_credit') is None:
        options['project_child_credit'] = scorer
        options.setdefault('child_credit_binding',scorer.as_record())
    return Workflow(store,tools,provider,directory,run_id,controller_factory,scorer,
        credit_binding=scorer.as_record(),initial_known_record_refs=initial_known_record_refs,**options)


def resolve_report(store,report,*,scope):
    from .a103_credit import A103ContextCredit
    from .a103_publication import received_measurement
    validate_form(report,report_schema(),lambda ref,namespace:
        ref in store.reference_subset([ref],scope) and (namespace is None or store.get(ref)['record_type']==namespace))
    view = A103ContextCredit().read_details(store,scope,known_record_refs=report['records'],details_limit=24,details_offset=0)
    sheets = view['a103_sheet']
    if report['context_summary']=='association_measured' and not any(sheets[k] for k in ('recurrence','fusion','cooccurrence','native_channel')):
        raise ContractError('a103_association_statement_requires_actual_measurement')
    if report['functional_support']=='system_association' and view['credit']<=0:
        raise ContractError('a103_system_statement_requires_qualified_context')
    if report['functional_support'] in {'system_association','contrast_qualified','contradicted'} and not (
            report['hypothesis_refs'] and report['assessment_refs']):
        raise ContractError('a103_function_interpretation_requires_explicit_hypothesis_and_assessment')
    if report['functional_support']=='local_trait_evidence' and not any(
            r['producer_operation']=='context.fusion' and r['score'] is not None for r in view['tool_attachments']):
        raise ContractError('a103_trait_statement_requires_local_feature_attribution')
    if report['functional_support'] in {'contrast_qualified','contradicted'} and not sheets['functional_contrast']:
        raise ContractError('a103_contrast_statement_requires_context_panel')
    if report['functional_support']=='contrast_qualified' and not any(
            r.get('qualified_panel',{}).get('contrast_bounds',[0,1])[0]>0 for r in sheets['functional_contrast']):
        raise ContractError('a103_discriminating_contrast_requires_qualified_separated_bounds')
    return {'receiving_scope_credit':view['credit'],'child_reported_credit':report['context_credit'],
        'context_sheets':sheets,'information_need_refs':report['information_need_refs']}


@dataclass(frozen=True)
class A103ServiceFactory:
    source_directory: str
    tool_retrieval: dict
    additional_descriptors: tuple = ()

    def __call__(self,store,*,run_id,directory,tool_catalog,job_episodes=None,resource_estimator=None,
                 tool_registry=None,**kwargs):
        from .episode_application_services import EpisodeApplicationServices
        from .literature_episodes import LiteratureEpisodes
        from .scientific_process_setup import prepare_scientific_binding
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
        scientific = prepare_scientific_binding(run_directory=directory,source_directory=self.source_directory,
            tool_catalog=tool_catalog,child_roles=('scientific_process','literature'),tool_retrieval=self.tool_retrieval)
        return EpisodeApplicationServices((scientific,LiteratureEpisodes(None).as_record(),*self.additional_descriptors),{})
