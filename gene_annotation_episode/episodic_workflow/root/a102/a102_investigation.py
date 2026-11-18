"""Compose A102-only scientific tasks using the existing recursive episodes."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError, obj
from .evidence_axis_instructions import validate_instruction_entry
from .structural_homology_evidence_library import StructuralHomologyEvidenceLibrary
from .structural_homology_evidence_records import SELECTION_VERSION, selector_selection, validate_selection
from .scientific_tool_library import ScientificToolLibrary
VERSION = 'a102_investigation_v1'
TASKS = ('model_inventory', 'target_model_correspondence', 'structural_discovery', 'native_comparison', 'functional_feature_geometry', 'functional_contrast', 'reference_attribution', 'local_trait_attribution', 'interface_constraints', 'synthesis')

def report_schema():
    refs = {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'uniqueItems': True}
    schema = obj({'records': {**deepcopy(refs), 'x-source': 'committed_record_refs', 'description': 'Actual received and committed sources, bound maps and automatically graded structural results for the parent to recompute.'}, 'structural_credit': {'type': 'number', 'x-source': 'credit', 'description': 'Host-calculated A102 native correspondence B; not a function probability.'}})
    validate_closed_schema(schema)
    return schema

def initial_report():
    return {}

class A102Subtree:

    def __init__(self, run_directory):
        directory = Path(run_directory)
        self.library = StructuralHomologyEvidenceLibrary(directory / 'scientific-process-library')
        self.tools = ScientificToolLibrary(directory / 'scientific-tool-library')
        self.axis = self.library.reference('A102')
        entry = validate_instruction_entry(self.library.resolve(self.axis))
        if entry['name'] != 'Structural homology':
            raise ContractError('a102_structural_homology_instructions_required')

    def selection(self, *, child_tool_info, thought_id='P01'):
        tools = self.tools.resolve_tool_info(child_tool_info)
        return selector_selection(validate_selection({'version': SELECTION_VERSION, 'evidence_axis': deepcopy(self.axis), 'thought_pattern': self.library.reference(thought_id), 'child_tool_info': tools}))

    def commission(self, store, *, target_ref, scope, completeness, child_tool_info, question, task='synthesis', thought_id='P01', evidence_refs=(), constraints=None, context=None, schema=None, initial=None):
        if task not in TASKS:
            raise ContractError('a102_unknown_structural_task')
        if completeness not in {'complete', 'fragment', 'unknown'}:
            raise ContractError('a102_material_completeness_required')
        if type(question) is not str or not question.strip():
            raise ContractError('a102_question_required')
        scope = store.validate_scope(plain(scope))
        target = store.get(target_ref)
        if target['record_type'] not in {'input', 'feature', 'product', 'read_subject'} or store.subject_molecule(target_ref) != 'protein' or (not store.scope_covers(store.coverage(target_ref), scope)):
            raise ContractError('a102_material_outside_scope_or_not_protein')
        references = list(dict.fromkeys([target_ref, *evidence_refs]))
        if set(store.reference_subset(references, scope)) != set(references):
            raise ContractError('a102_evidence_outside_scope')
        supplied = deepcopy(context or {})
        if 'a102_material' in supplied or 'a102_task' in supplied:
            raise ContractError('a102_material_context_reserved')
        supplied['a102_material'] = {'version': VERSION, 'subject_ref': target_ref, 'supplied_length': store.subject_length(target_ref), 'completeness': completeness, 'original_intervals': store.coverage(target_ref)}
        supplied['a102_task'] = {'name': task, 'allowed_tasks': list(TASKS), 'communication': 'Publish both acquired information and missing-information requests to the shared parent. The parent may commission other evidence axes as siblings. Every scientific descendant here remains A102.', 'native_credit': 'Native geometry automatically earns B. Missing functional features do not erase it. Reference-only measurements require their particular target attribution. Local trait evidence stays attached to subparts. F, E and function contrast remain separate. Reuse an existing qualified alignment; follow up only for missing cells.', 'resources': 'Use current resource_context and actual admission results; one small local job at a time. Novel folding and external DALI jobs require an explicit configured remote/API/HPC resource.', 'interpretation': 'Preserve origin, construct, target mapping, matched extent, confidence and uncertainty. A fold match or subunit match cannot establish exact function, substrate or whole-complex activity.'}
        schema = report_schema() if schema is None else deepcopy(schema)
        validate_closed_schema(schema)
        initial = initial_report() if initial is None else deepcopy(initial)
        validate_form(initial, interpretation_schema(schema), lambda ref, namespace: ref in store.reference_subset([ref], scope) and (namespace is None or store.get(ref)['record_type'] == namespace))
        return {'kind': 'episode_child', 'role': 'structural_homology_evidence', 'goal': question, 'scope': scope, 'purpose': 'Return structural correspondence and its actual maps and native grades, qualified functional comparisons, and unresolved shared information needs.', 'schema_json': json.dumps(schema, allow_nan=False), 'initial_report_json': json.dumps(initial, allow_nan=False), 'assignment': {'selection': self.selection(child_tool_info=child_tool_info, thought_id=thought_id), 'evidence_refs': references, 'constraints': deepcopy(constraints or {}), 'context': supplied}}

def create_a102_workflow(store, tools, provider, directory, run_id, controller_factory, *, initial_known_record_refs, **options):
    from .a102_credit import A102StructuralCredit
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:
        raise ValueError('a102_root_numeric_binding_is_host_owned')
    if options.get('episode_record_receipts', True) is not True:
        raise ValueError('a102_numeric_credit_requires_episode_receipts')
    scorer = A102StructuralCredit()
    options['episode_record_receipts'] = True
    return Workflow(store, tools, provider, directory, run_id, controller_factory, scorer, credit_binding=scorer.as_record(), initial_known_record_refs=initial_known_record_refs, **options)

def resolve_report(store, report, *, scope):
    """Validate a default typed return and resolve its actually delivered sheets."""
    from .a102_credit import A102StructuralCredit
    from .a102_publication import received_grade
    scope = store.validate_scope(plain(scope))
    validate_form(report, report_schema(), lambda ref, namespace: ref in store.reference_subset([ref], scope) and (namespace is None or store.get(ref)['record_type'] == namespace))
    native = [row for ref in report['records'] if (row := received_grade(store, ref)) is not None]
    projection = A102StructuralCredit().read_details(store, scope, known_record_refs=report['records'], details_limit=24, details_offset=0)
    return {'native_comparisons': native, 'functional_sheets': projection['functional_sheets'], 'tool_attachments': projection['tool_attachments'], 'target_sheets': projection['target_sheets'], 'child_reported_credit': report['structural_credit'], 'receiving_scope_credit': projection['credit'], 'reporting': 'saved_native_and_per_use_grading; no_separate_function_verdict'}

@dataclass(frozen=True)
class A102ServiceFactory:
    """Bind the recursive science/literature roles, plus explicit execution ports."""
    source_directory: str
    tool_retrieval: dict
    additional_descriptors: tuple = ()
    additional_role_credit_bindings: dict | None = None
    job_progress_provider: object | None = None
    resource_tool_catalogs: dict | None = None

    def __call__(self, store, *, run_id, directory, tool_catalog, job_episodes=None, resource_estimator=None, tool_registry=None):
        from .episode_application_services import EpisodeApplicationServices
        from .structural_homology_evidence.published_evidence_assessment.episode import create_binding_tree
        from .structural_homology_evidence_setup import prepare_scientific_binding
        from .structural_homology_evidence.episode import StructuralHomologyEvidenceEpisode
        child_roles = ('structural_homology_evidence', 'literature')
        descriptors = list(self.additional_descriptors)
        role_bindings = dict(self.additional_role_credit_bindings or {})
        progress = self.job_progress_provider
        resource_catalogs = deepcopy(self.resource_tool_catalogs)
        if tool_registry is not None:
            from types import SimpleNamespace
            from .a102_resources import A102ResourceAdapter, A102ResourceCredit, A102ProgressProvider
            from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.resource_work_submission.episode import ResourceEpisode
            from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_progress_assessment.episode import MonitorEpisode
            from .a102_progress_reader import SavedProgressReader
            adapter = A102ResourceAdapter(tool_registry, store, run_id)
            resources = create_resource_bindings(None, resource_adapters=(adapter,))
            monitor = MonitorEpisode(None)
            descriptors.extend([*(resource.as_record() for resource in resources), monitor.as_record()])
            operational = A102ResourceCredit(adapter)
            role_bindings.update({role: {'definition': operational.as_record(), 'project': operational} for resource in resources for role in resource.roles})
            information = monitor.information_credit(SavedProgressReader(store, run_id), information_unit=1)
            role_bindings['monitor'] = {'definition': information.as_record(), 'project': information}
            progress = A102ProgressProvider(adapter)
            child_roles += ('launch', 'monitor', 'results')
            contracts = {entry['name']: {**entry, 'resources': 'local'} for role in ('launch_local', 'results') for entry in adapter.catalog(SimpleNamespace(role=role))}
            resource_catalogs = {**(resource_catalogs or {}), 'local': list(contracts.values())}
        for descriptor in self.additional_descriptors:
            child_roles += tuple((r for r in descriptor.get('roles', ()) if r not in child_roles))
        scientific = prepare_scientific_binding(episode_type=StructuralHomologyEvidenceEpisode, run_directory=directory, source_directory=self.source_directory, tool_catalog=tool_catalog, child_roles=child_roles, tool_retrieval=self.tool_retrieval, resource_catalogs=resource_catalogs)
        return EpisodeApplicationServices((scientific, *tuple((binding.as_record() for binding in create_binding_tree(None))), *descriptors), role_bindings, progress, resource_tool_catalogs=resource_catalogs)
from .resource_binding_tree import create_resource_bindings
