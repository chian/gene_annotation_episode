"""Compose A102-only scientific tasks using the existing recursive episodes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError, obj
from .evidence_axis_instructions import validate_instruction_entry
from .scientific_process_library import ScientificProcessLibrary
from .scientific_process_records import SELECTION_VERSION, selector_selection, validate_selection
from .scientific_tool_library import ScientificToolLibrary


VERSION='a102_investigation_v1'
TASKS=('model_inventory','target_model_correspondence','structural_discovery','native_comparison',
    'functional_feature_geometry','functional_contrast','reference_attribution','local_trait_attribution',
    'interface_constraints','synthesis')


def legacy_report_schema():
    """Historical model-verdict contract; new commissions use saved grading."""
    refs={'type':'array','items':{'type':'string','format':'reference'},'uniqueItems':True}
    schema=obj({'structural_summary':{'type':'string','enum':['not_assessed','native_geometry_retained','partial_geometry','no_model','no_informative_match']},
        'scope_status':{'type':'string','enum':['not_assessed','unresolved','partial','represented']},
        'functional_support':{'type':'string','enum':['not_assessed','fold_only','local_trait_evidence','feature_qualified','contrast_qualified','contradicted']},
        'limitations':{'type':'array','items':{'type':'string','enum':['predicted_target','predicted_reference',
            'construct_difference','missing_coordinates','partial_match','ambiguous_mapping','unresolved_primary_variant',
            'no_model','no_informative_match','function_features_unassessed','alternatives_unassessed',
            'native_software_unbound','subunit_scope','fragment_input','unknown_full_length']},'uniqueItems':True},
        'information_need_refs':refs,
        'records':{**deepcopy(refs),'x-source':'committed_record_refs',
            'description':'Actual received and committed sources, bound maps and automatically graded structural results for the parent to recompute.'},
        'structural_credit':{'type':'number','x-source':'credit',
            'description':'Host-calculated A102 native correspondence B; not a function probability.'}})
    validate_closed_schema(schema)
    return schema


def report_schema():
    original = legacy_report_schema()['properties']
    schema = obj({name: deepcopy(original[name]) for name in ('records', 'structural_credit')})
    validate_closed_schema(schema)
    return schema


def initial_report():
    return {}


class A102Subtree:
    def __init__(self,run_directory):
        directory=Path(run_directory)
        self.library=ScientificProcessLibrary(directory/'scientific-process-library')
        self.tools=ScientificToolLibrary(directory/'scientific-tool-library')
        self.axis=self.library.reference('A102')
        entry=validate_instruction_entry(self.library.resolve(self.axis))
        if entry['name']!='Structural homology':raise ContractError('a102_structural_homology_instructions_required')

    def selection(self,*,child_tool_info,thought_id='P01'):
        tools=self.tools.resolve_tool_info(child_tool_info)
        return selector_selection(validate_selection({'version':SELECTION_VERSION,
            'evidence_axis':deepcopy(self.axis),'thought_pattern':self.library.reference(thought_id),
            'child_tool_info':tools}))

    def commission(self,store,*,target_ref,scope,completeness,child_tool_info,question,
                   task='synthesis',thought_id='P01',evidence_refs=(),constraints=None,
                   context=None,schema=None,initial=None):
        if task not in TASKS:raise ContractError('a102_unknown_structural_task')
        if completeness not in {'complete','fragment','unknown'}:raise ContractError('a102_material_completeness_required')
        if type(question) is not str or not question.strip():raise ContractError('a102_question_required')
        scope=store.validate_scope(plain(scope));target=store.get(target_ref)
        if (target['record_type'] not in {'input','feature','product','read_subject'}
                or store.subject_molecule(target_ref)!='protein'
                or not store.scope_covers(store.coverage(target_ref),scope)):
            raise ContractError('a102_material_outside_scope_or_not_protein')
        references=list(dict.fromkeys([target_ref,*evidence_refs]))
        if set(store.reference_subset(references,scope))!=set(references):raise ContractError('a102_evidence_outside_scope')
        supplied=deepcopy(context or {})
        if 'a102_material' in supplied or 'a102_task' in supplied:raise ContractError('a102_material_context_reserved')
        supplied['a102_material']={'version':VERSION,'subject_ref':target_ref,
            'supplied_length':store.subject_length(target_ref),'completeness':completeness,
            'original_intervals':store.coverage(target_ref)}
        supplied['a102_task']={'name':task,'allowed_tasks':list(TASKS),
            'communication':'Publish both acquired information and missing-information requests to the shared parent. '
                'The parent may commission other evidence axes as siblings. Every scientific descendant here remains A102.',
            'native_credit':'Native geometry automatically earns B. Missing functional features do not erase it. '
                'Reference-only measurements require their particular target attribution. Local trait evidence stays attached to subparts. '
                'F, E and function contrast remain separate. Reuse an existing qualified alignment; follow up only for missing cells.',
            'resources':'Use current resource_context and actual admission results; one small local job at a time. '
                'Novel folding and external DALI jobs require an explicit configured remote/API/HPC resource.',
            'interpretation':'Preserve origin, construct, target mapping, matched extent, confidence and uncertainty. '
                'A fold match or subunit match cannot establish exact function, substrate or whole-complex activity.'}
        schema=report_schema() if schema is None else deepcopy(schema);validate_closed_schema(schema)
        initial=initial_report() if initial is None else deepcopy(initial)
        validate_form(initial,interpretation_schema(schema),lambda ref,namespace:
            ref in store.reference_subset([ref],scope) and (namespace is None or store.get(ref)['record_type']==namespace))
        return {'kind':'episode_child','role':'scientific_process','goal':question,'scope':scope,
            'purpose':'Return structural correspondence and its actual maps and native grades, qualified functional comparisons, and unresolved shared information needs.',
            'schema_json':json.dumps(schema,allow_nan=False),'initial_report_json':json.dumps(initial,allow_nan=False),
            'assignment':{'selection':self.selection(child_tool_info=child_tool_info,thought_id=thought_id),
                'evidence_refs':references,'constraints':deepcopy(constraints or {}),'context':supplied}}


def create_a102_workflow(store,tools,provider,directory,run_id,controller_factory,*,initial_known_record_refs,**options):
    from .a102_credit import A102StructuralCredit
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:raise ValueError('a102_root_numeric_binding_is_host_owned')
    if options.get('episode_record_receipts',True) is not True:raise ValueError('a102_numeric_credit_requires_episode_receipts')
    scorer=A102StructuralCredit();options['episode_record_receipts']=True
    return Workflow(store,tools,provider,directory,run_id,controller_factory,scorer,
        credit_binding=scorer.as_record(),initial_known_record_refs=initial_known_record_refs,**options)


def resolve_report(store,report,*,scope):
    """Validate a default typed return and resolve its actually delivered sheets."""
    from .a102_credit import A102StructuralCredit
    from .a102_publication import received_grade
    scope=store.validate_scope(plain(scope))
    legacy = 'structural_summary' in report
    validate_form(report,legacy_report_schema() if legacy else report_schema(),lambda ref,namespace:
        ref in store.reference_subset([ref],scope) and (namespace is None or store.get(ref)['record_type']==namespace))
    native=[row for ref in report['records'] if (row:=received_grade(store,ref)) is not None]
    if legacy and report['structural_summary']=='native_geometry_retained' and not native:
        raise ContractError('a102_native_geometry_statement_requires_native_records')
    projection=A102StructuralCredit().read_details(store,scope,known_record_refs=report['records'],
        details_limit=24,details_offset=0)
    features=projection['functional_sheets']['features'];panels=projection['functional_sheets']['contrasts']
    if not legacy:
        return {'native_comparisons': native, 'functional_sheets': projection['functional_sheets'],
            'tool_attachments': projection['tool_attachments'],
            'target_sheets': projection['target_sheets'],
            'child_reported_credit': report['structural_credit'],
            'receiving_scope_credit': projection['credit'],
            'reporting': 'saved_native_and_per_use_grading; no_separate_function_verdict'}
    support=report['functional_support']
    if support=='fold_only' and not projection['credit']>0:
        raise ContractError('a102_fold_statement_requires_eligible_native_correspondence')
    if support=='feature_qualified' and not any(row['E'] is not None and row['E']>0 for row in features):
        raise ContractError('a102_feature_statement_requires_received_feature_sheet')
    if support=='local_trait_evidence' and not any(row['score'] is not None
            for row in projection['functional_sheets']['traits']):
        raise ContractError('a102_local_trait_statement_requires_received_trait_sheet')
    if support=='contrast_qualified' and not any(row['A102_f'] is not None and row['A102_f']>0 for row in panels):
        raise ContractError('a102_contrast_statement_requires_received_contrast_sheet')
    if support=='contradicted' and not any(any(feature['state'] in {'established_absent','established_incompatible'}
            for feature in row['features']) for row in features):
        raise ContractError('a102_contradiction_requires_grounded_incompatible_feature')
    return {'native_comparisons':native,'functional_sheets':projection['functional_sheets'],
        'tool_attachments':projection['tool_attachments'],'target_sheets':projection['target_sheets'],
        'child_reported_credit':report['structural_credit'],'receiving_scope_credit':projection['credit'],
        'information_need_refs':list(report['information_need_refs'])}


@dataclass(frozen=True)
class A102ServiceFactory:
    """Bind the recursive science/literature roles, plus explicit execution ports."""
    source_directory: str
    tool_retrieval: dict
    additional_descriptors: tuple=()
    additional_role_credit_bindings: dict|None=None
    job_progress_provider: object|None=None
    resource_tool_catalogs: dict|None=None

    def __call__(self,store,*,run_id,directory,tool_catalog,job_episodes=None,resource_estimator=None,tool_registry=None):
        from .episode_application_services import EpisodeApplicationServices
        from .literature_episodes import LiteratureEpisodes
        from .scientific_process_setup import prepare_scientific_binding
        child_roles=('scientific_process','literature')
        descriptors=list(self.additional_descriptors)
        role_bindings=dict(self.additional_role_credit_bindings or {})
        progress=self.job_progress_provider
        resource_catalogs=deepcopy(self.resource_tool_catalogs)
        if tool_registry is not None:
            from types import SimpleNamespace
            from .a102_resources import A102ResourceAdapter,A102ResourceCredit,A102ProgressProvider
            from .resource_episodes import ResourceEpisodes
            from .episode_monitoring import MonitorEpisodes
            from .episode_progress_credit import ProgressInformationCredit
            from .assembled_service_setup import _SavedProgressReader
            adapter=A102ResourceAdapter(tool_registry,store,run_id)
            resource=ResourceEpisodes(None,resource_adapters=(adapter,))
            descriptors.extend([resource.as_record(),MonitorEpisodes(None).as_record()])
            operational=A102ResourceCredit(adapter)
            role_bindings.update({role:{'definition':operational.as_record(),'project':operational} for role in resource.roles})
            information=ProgressInformationCredit(_SavedProgressReader(store,run_id),information_unit=1)
            role_bindings['monitor']={'definition':information.as_record(),'project':information}
            progress=A102ProgressProvider(adapter)
            child_roles+=('launch','monitor','results')
            contracts={entry['name']:{**entry,'resources':'local'} for role in ('launch_local','results')
                for entry in adapter.catalog(SimpleNamespace(role=role))}
            resource_catalogs={**(resource_catalogs or {}),'local':list(contracts.values())}
        for descriptor in self.additional_descriptors:
            child_roles+=tuple(r for r in descriptor.get('roles',()) if r not in child_roles)
        scientific=prepare_scientific_binding(run_directory=directory,source_directory=self.source_directory,
            tool_catalog=tool_catalog,child_roles=child_roles,tool_retrieval=self.tool_retrieval,
            resource_catalogs=resource_catalogs)
        return EpisodeApplicationServices((scientific,LiteratureEpisodes(None).as_record(),*descriptors),
            role_bindings,progress,resource_tool_catalogs=resource_catalogs)
