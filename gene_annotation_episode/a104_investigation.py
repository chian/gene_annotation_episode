"""A104-only recursive science with shared-parent evidence and HPC requests."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .communication import plain, validate_closed_schema, validate_form, interpretation_schema
from .domain import obj, ContractError
from .a104_hpc import require
from .scientific_process_library import ScientificProcessLibrary
from .scientific_process_records import SELECTION_VERSION, selector_selection, validate_selection
from .scientific_tool_library import ScientificToolLibrary
from .evidence_axis_instructions import validate_instruction_entry


VERSION = 'a104_evolutionary_investigation_v1'
RECORD_SOURCE = 'a104_received_evolutionary_records'
TASKS = ('panel_identity', 'alignment_suitability', 'family_phylogeny', 'target_placement',
         'characterized_clades', 'organismal_history', 'paralog_discrimination',
         'robustness', 'synthesis')


def parent_generation_schema(frame, schema):
    """Offer waits to this example's parent only for real pending work.

    This narrows model generation, not the recorded action contract or numerical
    continuation. Historical waits remain replayable. The operational HPC
    specialization owns its actual allocation monitoring and is unaffected.
    """
    state = frame.get('fields', frame)
    pending = state.get('pending_work')
    if not isinstance(pending, dict) or pending.get('items') != []:
        return schema
    result = deepcopy(schema)
    nodes = [result, *result.get('properties', {}).get('response', {}).get('anyOf', [])]
    for node in nodes:
        selection = node.get('properties', {}).get('selection', {})
        if 'anyOf' in selection:
            selection['anyOf'] = [branch for branch in selection['anyOf']
                if (branch.get('properties', {}).get('kind', {}).get('const') != 'wait'
                    and branch.get('properties', {}).get('kind', {}).get('enum') != ['wait'])]
    return result


def legacy_report_schema():
    """Historical model-verdict contract; new commissions use saved grading."""
    refs = {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'uniqueItems': True}
    return obj({'phylogeny_status': {'type': 'string', 'enum': ['not_assessed', 'execution_pending',
        'native_trees_received', 'placement_measured', 'histories_compared', 'partial', 'uninformative']},
        'function_scope': {'type': 'string', 'enum': ['not_assessed', 'specificity_unresolved',
            'reference_clade_qualified', 'mixed_function_clade', 'contradicted']},
        'history_interpretation': {'type': 'string', 'enum': ['not_assessed', 'compatible_at_examined_scope',
            'discordant_cause_unresolved', 'duplication_loss_requires_further_work', 'local_scope_only', 'topology_unresolved']},
        'limitations': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': [
            'partial_input', 'region_only', 'uncharacterized_references', 'mixed_functions', 'missing_taxa',
            'paralog_mapping', 'unresolved_branches', 'rooting_unestablished', 'organismal_reference_proxy',
            'phylogenetic_outlier', 'mobile_family_scope', 'native_execution_pending',
            'missing_A105_characterization', 'alternative_models_unassessed', 'restricted_taxon_scope']}},
        'information_need_refs': deepcopy(refs),
        'hypothesis_refs': {**deepcopy(refs), 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'}},
        'assessment_refs': {**deepcopy(refs), 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}},
        'records': {**deepcopy(refs), 'x-source': RECORD_SOURCE,
            'description': 'Actual received native tree measurements, per-use grades, retained phylogenies and shared needs; no implicit upstream receipt.'},
        'phylogenetic_credit': {'type': 'number', 'x-source': 'credit',
            'description': 'Host-calculated native evolutionary investigation progress. Branch support is not functional confidence.'}})


def report_schema():
    original = legacy_report_schema()['properties']
    schema = obj({name: deepcopy(original[name]) for name in ('records', 'phylogenetic_credit')})
    validate_closed_schema(schema)
    return schema


def initial_report():
    return {}


def fact_sources():
    return {RECORD_SOURCE: {'type': 'array', 'meaning': 'Completed own records and actual received A104 native evidence and grades.',
        'report_schema': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                          'uniqueItems': True, 'x-source': RECORD_SOURCE}}}


def received_records(store, known, scope, *, committed=()):
    known = set(known)
    result = set(committed) & known
    for reference in known:
        record = store.get(reference)
        provider = record.get('provider', '')
        if provider.startswith(('native.a104.', 'host.a104.')) or provider in {'episode.shared_information', 'host.hpc.commission'}:
            result.add(reference)
        elif record['record_type'] == 'observation' and record['origin'] == 'tool' and record['source_ref'] in known \
                and store.get(record['source_ref']).get('provider', '').startswith('native.a104.'):
            result.add(reference)
    return sorted(result)


def resolve_report(store, report, *, scope):
    from .a104_credit import A104EvolutionaryCredit
    from .a104_publication import received_measurement
    legacy = 'phylogeny_status' in report
    validate_form(report, legacy_report_schema() if legacy else report_schema(), lambda reference, namespace:
        reference in store.reference_subset([reference], scope)
        and (namespace is None or store.get(reference)['record_type'] == namespace))
    view = A104EvolutionaryCredit().read_details(store, scope, known_record_refs=report['records'],
                                                details_limit=128, details_offset=0)
    require(math.isclose(report['phylogenetic_credit'], view['credit'], abs_tol=1e-12), 'a104_report_numeric_credit_conflict')
    if not legacy:
        return {'receiving_scope_credit': view['credit'], 'child_reported_credit': report['phylogenetic_credit'],
            'evolutionary_sheets': view['a104_sheet'], 'tool_attachments': view['tool_attachments'],
            'target_sheets': view['target_sheets'],
            'reporting': 'saved_native_tree_and_per_use_grading; no_separate_history_or_function_verdict'}
    measurements = [value for reference in report['records'] if (value := received_measurement(store, reference)) is not None]
    placements = [value for value in measurements if value['grade']['kind'] == 'placement']
    histories = [value['body'] for value in measurements if value['grade']['kind'] == 'history_comparison']
    if report['phylogeny_status'] == 'native_trees_received':
        from .a104_hpc import native_body
        require(any(native_body(store, reference) is not None for reference in report['records']),
                'a104_native_tree_statement_requires_received_original_execution')
    if report['phylogeny_status'] == 'placement_measured':
        require(placements, 'a104_placement_statement_requires_native_measurement')
    if report['phylogeny_status'] == 'histories_compared':
        require(histories, 'a104_history_statement_requires_actual_two_tree_comparison')
    if report['history_interpretation'] == 'compatible_at_examined_scope':
        require(any(row['raw_value'] is not None and row['comparison']['rf']['value'] == 0 for row in histories),
                'a104_history_agreement_requires_supported_native_comparison')
    if report['history_interpretation'] == 'discordant_cause_unresolved':
        require(any(row['comparison']['rf']['value'] is not None and row['comparison']['rf']['value'] > 0
                    for row in histories),
                'a104_discordance_statement_requires_native_comparison')
    characterized = [row['sheets']['reference_characterization'] for row in view['tool_attachments']
                     if 'reference_characterization' in row['sheets']]
    if report['function_scope'] == 'reference_clade_qualified':
        require(any(row['all_sampled_references_have_one_observed_activity'] for row in characterized),
                'a104_function_clade_requires_exact_characterized_reference_links')
    if report['function_scope'] == 'mixed_function_clade':
        require(any(row['status'] == 'mixed_characterized_functions' for row in characterized),
                'a104_mixed_function_statement_requires_characterized_members')
    if report['function_scope'] in {'reference_clade_qualified', 'contradicted'}:
        require(report['hypothesis_refs'] and report['assessment_refs'], 'a104_function_statement_requires_explicit_hypothesis_and_assessment')
        hypotheses = {reference: store.get(reference) for reference in report['hypothesis_refs']}
        assessments = [store.get(reference) for reference in report['assessment_refs']]
        require(all(any(set(store.roots(subject)) & set(scope['subject_refs']) for subject in row['subject_refs'])
                    for row in hypotheses.values()), 'a104_function_hypothesis_requires_original_target')
        relation = 'strengthens' if report['function_scope'] == 'reference_clade_qualified' else 'weakens'
        require(any(row['hypothesis_ref'] in hypotheses and row['relation'] == relation for row in assessments),
                'a104_function_statement_requires_corresponding_assessment_relation')
    return {'receiving_scope_credit': view['credit'], 'child_reported_credit': report['phylogenetic_credit'],
            'evolutionary_sheets': view['a104_sheet'], 'tool_attachments': view['tool_attachments'],
            'target_sheets': view['target_sheets'], 'information_need_refs': report['information_need_refs']}


class A104Subtree:
    def __init__(self, directory):
        directory = Path(directory)
        self.library = ScientificProcessLibrary(directory/'scientific-process-library')
        self.tools = ScientificToolLibrary(directory/'scientific-tool-library')
        self.axis = self.library.reference('A104')
        entry = validate_instruction_entry(self.library.resolve(self.axis))
        require(entry['name'] == 'Evolutionary history and phylogenetic placement', 'a104_published_instructions_required')

    def commission(self, store, *, target_ref, scope, child_tool_info, question, task='synthesis',
                   evidence_refs=(), context=None, constraints=None, thought_id='P01', completeness='unknown', schema=None, initial=None):
        require(task in TASKS and completeness in {'complete', 'fragment', 'unknown'}, 'a104_declared_scientific_task_required')
        require(isinstance(question, str) and question.strip(), 'a104_scientific_question_required')
        scope = store.validate_scope(plain(scope))
        target = store.get(target_ref)
        require(target['record_type'] in {'input', 'feature', 'product', 'read_subject'}
                and store.coverage(target_ref) and store.scope_covers(store.coverage(target_ref), scope),
                'a104_original_material_required')
        references = list(dict.fromkeys([target_ref, *evidence_refs]))
        require(set(store.reference_subset(references, scope)) == set(references), 'a104_evidence_outside_scope')
        supplied = deepcopy(context or {})
        require(not {'a104_material', 'a104_task'} & set(supplied), 'a104_material_context_reserved')
        supplied['a104_material'] = {'subject_ref': target_ref, 'completeness': completeness,
            'original_intervals': store.coverage(target_ref), 'supplied_length': store.subject_length(target_ref)}
        supplied['a104_task'] = {'name': task, 'allowed_tasks': list(TASKS),
            'ownership': 'Every scientific descendant remains A104. Use available shared operations to send '
                'the immediate parent specific sequence-identification or experimental-characterization needs '
                'and relevant received evidence. That parent chooses within its own investigation options '
                'or relays the need upward. Publication starts no response work; retain unmet needs in the typed return.',
            'resources': 'Use the exact shared HPC request for MUSCLE, IQ-TREE and bootstrap work. '
                'The operational hpc child may execute the exact received commission_source_ref. '
                'It is the shared execution service, not another biological evidence axis. '
                'Publish its request and receipts to the annotation parent. '
                'Do not substitute a local inference job. Read whole-workflow CPU/RAM/concurrency information, '
                'including Python and provider processes. One workflow per Codex window.',
            'credit': 'Actual native target placement, family-versus-organismal comparison, and experimentally '
                'qualified native clade composition are separate bounded progress coordinates. Acquisition, job submission, alignment inventory, prose and nearest-hit '
                'identity alone do not supply these measurements. Grading runs automatically on publication or receipt; '
                'episode.credit only reads it. Use retained results without rerunning their native algorithms.',
            'measurement': 'Inspect the native tips and splits, measure informative target placement, and compare '
                'the actual histories at an explicit shared taxon/copy scope. Keep paralogs, fragments, marker-reference '
                'assumptions, model/branch uncertainty and omitted taxa. A root in a stored representation is not ancestry.',
            'interpretation': 'Native support is phylogenetic support. Uncharacterized members cannot make a '
                'single-function clade. A mixed-function clade cannot identify a narrow activity. Discordance alone '
                'does not establish horizontal transfer. Preserve specificity and historical cause as unresolved '
                'when their evidence is missing; share those needs while other scientific work remains.'}
        selected_schema = report_schema() if schema is None else deepcopy(schema)
        selected_initial = initial_report() if initial is None else deepcopy(initial)
        validate_closed_schema(selected_schema)
        validate_form(selected_initial, interpretation_schema(selected_schema), lambda ref, namespace:
            ref in store.reference_subset([ref], scope) and (namespace is None or store.get(ref)['record_type'] == namespace))
        tools = self.tools.resolve_tool_info(child_tool_info)
        selection = selector_selection(validate_selection({'version': SELECTION_VERSION, 'evidence_axis': deepcopy(self.axis),
            'thought_pattern': self.library.reference(thought_id), 'child_tool_info': tools}))
        return {'kind': 'episode_child', 'role': 'scientific_process', 'goal': question, 'scope': scope,
            'purpose': 'Return saved evolutionary measurements and their purpose-specific per-use grading, with exact recorded qualifications and missing inputs; no second history or function verdict.',
            'schema_json': json.dumps(selected_schema, allow_nan=False), 'initial_report_json': json.dumps(selected_initial, allow_nan=False),
            'assignment': {'selection': selection, 'evidence_refs': references, 'constraints': deepcopy(constraints or {}), 'context': supplied}}


@dataclass(frozen=True)
class A104ServiceFactory:
    source_directory: str
    tool_retrieval: dict
    execution_resources: dict
    hpc_commissions: dict
    shared_execution_memory: dict | None = None

    def as_record(self):
        return {'version': VERSION, 'source_directory': self.source_directory, 'tool_retrieval': deepcopy(self.tool_retrieval),
                'execution_resources': deepcopy(self.execution_resources), 'hpc_commissions': deepcopy(self.hpc_commissions),
                'shared_execution_memory': deepcopy(self.shared_execution_memory)}

    def __call__(self, store, *, run_id, directory, tool_catalog, tool_registry=None, **kwargs):
        from .episode_application_services import EpisodeApplicationServices
        from .scientific_process_setup import prepare_scientific_binding
        from .literature_episodes import LiteratureEpisodes
        from .execution_service_setup import ExecutionServiceFactory
        from .execution_memory import ExecutionMemory
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        execution_factory = ExecutionServiceFactory(self.execution_resources, {}, 1., 1., .01,
            hpc_commissions=self.hpc_commissions,
            shared_execution_memory=self.shared_execution_memory or ExecutionMemory.configured().as_record())
        execution = execution_factory(store, run_id=run_id, directory=directory,
            tool_catalog=tool_catalog, tool_registry=tool_registry)
        science = prepare_scientific_binding(run_directory=directory, source_directory=self.source_directory,
            tool_catalog=tool_catalog, child_roles=('scientific_process', 'literature', 'hpc'),
            tool_retrieval=self.tool_retrieval, resource_catalogs=execution.resource_tool_catalogs,
            contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        literature = LiteratureEpisodes(None, rate_population=True, compiled_assay_population=True,
            assay_grading_population=True, contract_information_profile=CONTRACT_INFORMATION_PROFILE).as_record()
        return EpisodeApplicationServices((science, literature, *execution.episode_binding_descriptors),
            execution.role_credit_bindings, execution.job_progress_provider,
            resource_tool_catalogs=execution.resource_tool_catalogs)
