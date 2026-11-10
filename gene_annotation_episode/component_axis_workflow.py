"""Independent A107/A110 commissions over existing science/execution services."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .component_axis_reports import initial_report, report_schema
from .domain import ContractError
from .evidence_axis_instructions import validate_instruction_entry
from .scientific_process_library import ScientificProcessLibrary
from .scientific_process_records import SELECTION_VERSION, selector_selection, validate_selection
from .scientific_tool_library import ScientificToolLibrary


VERSION = 'component_axis_investigation_v1'
NAMES = {'A107': 'Required partner presence and coexpression',
    'A110': 'Biochemical feasibility and chemical/resource accounting'}
TASKS = {
    'A107': ('partner_requirements', 'component_identity', 'genome_presence',
        'matched_expression', 'coexpression', 'interaction_distinction', 'target_transfer', 'synthesis'),
    'A110': ('reaction_identity', 'stoichiometric_accounting', 'electron_accounting',
        'cofactor_regeneration', 'resource_feasibility', 'conditional_energetics',
        'prediction_contrast', 'target_transfer', 'synthesis'),
}
_AXIS_INSTRUCTIONS = {
    'A107': 'Investigate which components a possible function genuinely requires and whether '
        'they are present and expressed in the relevant genome, organism and conditions. Start '
        'from the supplied material and question; a candidate annotation is not required. '
        'Choose requirement experiments, genomic detection or matched expression analysis '
        'according to that question and the actual supplied observations. These investigations '
        'can be useful separately. Source-table expression measurements and descriptive '
        'relationships can be calculated before functional partnership or molecular '
        'correspondence is established; retain those unknowns as limitations on biological '
        'application. An expression table is not an omission/addback experiment. '
        'For direct inspection of supplied tables or genomic sources, select the actual '
        'source.read/source.locate capabilities as part of the fixed child toolset. Native '
        'request and qualification operations do not grant those readers. When delegating '
        'source inspection, request the exact table identifiers, conditions and selection '
        'operands needed by the subsequent investigation as well as their provenance. '
        'Discover requirements from actual sources and preserve the assayed subject, partner '
        'identity, construct, endpoint and conditions. Use literature.partner.populate or '
        'literature.partner.source.populate through the configured literature child for the '
        'existing omission/addback components. Return requested literature_partner_cells, '
        'including useful partial and unavailable components. These measurements describe '
        'condition-specific dependence; they do not themselves establish physiological presence '
        'or computational coexpression. Use partner.requirement_evidence for a retained '
        'source-backed requires/partner_dependence finding and its exact received native '
        'components. Original experimental role references are not sequence operands. '
        'Use partner.source_identity_evidence for a received source declaration identifying '
        'a particular role, its actual protein sequence and selected experiment. Keep '
        'the original role and sequence reference separate; attach the saved identity '
        'to the particular requirement use and that requirement to the relevant detection '
        'or expression use. A name or accession alone leaves construct identity unresolved. '
        'Supplied reference sequences can use the ordinary material readers and '
        'sequence.view to retain an explicit processing model and original bytes. '
        'A processing model is not biological identity proof; the source declaration '
        'and its particular native correspondence still need qualification. '
        'Share missing sequence/construct/experiment records as specific parent needs. '
        'Use partner.component_correspondence for its particular actual/reference '
        'peptide or selected region, and partner.detection_evidence for an authenticated '
        'detector inventory. These operations retain native data and cannot invent required '
        'function, physiological context or whole-genome absence. Genomic operations in this '
        'registry use context.request_hpc and the existing shared HPC service. '
        'When a pinned phmmer deployment is configured, partner.request_detection_hpc '
        'runs the actual query against an admitted CDS FASTA and applies the original '
        'scoped detector to selected admitted GenBank records on that allocation. '
        'This returns its own authenticated profile, not a legacy parsed-search receipt '
        'or an A101 family score. Preserve uncertain translation/coverage and scoped '
        'native inclusion; use partner.detection_evidence for particular qualification. '
        'For an admitted declared expression table, use partner.request_expression_hpc for '
        'a single component (right_feature_id=null) or matched sample pairs. Preserve raw '
        'values, reported censor bounds, source detection criteria and descriptive Pearson '
        'correlation of complete point pairs. Threshold comparisons require the declared '
        'matching scale, normalization, calibration condition and source controls. A '
        'below-limit result is not gene absence. Use '
        'partner.expression_evidence separately for each measured feature and particular '
        'target or component. A measured RNA feature needs actual nucleotide identity and '
        'a retained native encoding/product link before a protein correspondence is useful. '
        'For gene-ID-level RNA data, use partner.expression_locus_evidence with an actual '
        'received genomic binding and declared sample reference genomes. That operation '
        'can project its public verified translation into an explicit biological reference; '
        'it does not reopen a private reference or verify the sample genotype/isoform. '
        'Preserve native quantity/normalization, missing pairs, declared organism and '
        'biological-unit dependence. This route does not infer a detection threshold, '
        'sampling significance, protein abundance or activity from transcript measurements. '
        'Read actual component/detection records when delivered '
        'by the shared parent. Presence, scoped detection-limited absence, unexamined sequence '
        'and ambiguous identity are different outcomes. Match expression and coexpression to '
        'the actual samples, conditions, component identities and measurement scope. Source '
        'labels, generic expression in another organism and physical interaction are not '
        'substitutes for required-partner presence or demonstrated function. Preserve the '
        'particular correspondence needed for a whole molecule, region, residue or site; do '
        'not replace local feature coordinates with a whole-protein score. A protein feature '
        'can reuse its received parent alignment through explicit forward protein-coordinate '
        'paths; missing parent frames are a specific information need. Do '
        'not transfer an experimental requirement just from a family label or axis score.',
    'A110': 'Investigate whether a possible reaction or pathway is chemically sustainable '
        'under its declared conditions. Start from the supplied material and biological question; '
        'discover or obtain specific reaction leads through legitimate sources and parent exchange. '
        'For direct source inspection, include the actual source.read/source.locate '
        'capabilities when selecting the fixed child toolset. Native request and '
        'qualification operations do not implicitly grant source readers. '
        'Identify chemical entities, compartments, stoichiometric coefficients, reaction direction '
        'and alternatives before interpreting feasibility. Keep atom/charge bookkeeping, electron '
        'flow, cofactor and carrier regeneration, usable resource constraints and conditional '
        'energetics distinguishable. Rhea, ChEBI and KEGG source records retain their native '
        'direction, identity and qualification; a database equation does not establish physiological '
        'direction or activity. Use literature.reaction.populate or '
        'literature.reaction.source.populate through the configured literature '
        'child for the existing reaction-prediction/resource components; retain their exact '
        'measurement scale, source meanings, native uncertainty and missing reasons. Return '
        'literature_reaction_cells and, when supported, literature_reaction_semantic_cells. '
        'Do not turn instrument signals into molar amounts, a product-pair ratio into substrate '
        'consumption, or steady-state FBA into thermodynamic feasibility. Repeated source views '
        'retain their original measurement identities. A regenerated carrier is not necessarily '
        'consumed once per turnover. Unknown formula, charge, resource, mapping or energetic '
        'prerequisite stays unknown. Use chemistry.request_accounting_hpc for an admitted '
        'declared chemical panel: exact equation residuals, explicit electron terms, declared '
        'pathway/carrier accounting and conditional chemical-standard-state Gibbs components. '
        'The declared weighted pathway energy is the sum of step energies at one matching '
        'physical condition, not evidence that each step is favorable or physically coupled. '
        'Unsupported formula/energetic conventions remain explicit; qualified chemical '
        'energetics requires the corresponding equation, identity and physical prerequisites. '
        'For received public Rhea and ChEBI records, chemistry.prepare_reference_accounting '
        'can assemble a source panel from exact participant identities and source fields '
        'for the existing HPC accounting operation. Missing source records remain specific '
        'parent needs; source balance assertions and the actual native calculation are '
        'different evidence. Source preparation supplies no physical conditions or activity. '
        'Use chemistry.reaction_evidence for a particular reaction-reference and molecular '
        'application; source interpretations and received sequence/region maps remain separate '
        'from the chemical calculation. For already saved experimental reaction-ratio, '
        'prediction or resource-model components, use chemistry.experimental_reaction_evidence '
        'with the actual sheet and selected component names. That independent path can retain '
        'source quantities and explicit unresolved application before obtaining a biological '
        'reaction reference, an accounting panel or a protein map. Qualify ratio/prediction '
        'and resource-model uses separately, retaining the source model definitions and '
        'actual assayed subject. Neither a sheet handle nor a protein map supplies unreceived '
        'cells or converts a resource model into a protein measurement. Original assay roles '
        'are not sequence operands: chemistry.source_identity_evidence can retain a received '
        'source declaration linking one original role to an actual protein and experiment. '
        'Select that saved identity for the particular molecular use; preserve unknown '
        'construct identity and share missing records with the parent. Protein features preserve their local coordinates '
        'and received parent-to-feature paths for a particular native correspondence. Keep '
        'missing parent frames and conflicting residue maps explicit and separate '
        'from chemical opposition. If a pinned remote FBA deployment is configured, '
        'chemistry.request_flux_balance_hpc uses the original driver, readers and calculations '
        'on the shared HPC service and returns only the selected projection. Do not count '
        'a remote worksheet path/digest as a receipt for other cells. Feasibility alone does '
        'not demonstrate molecular activity.',
}

_NATIVE_RETURN_GUIDANCE = (
    'When commissioning a scientific_process child whose child_tool_info includes '
    'partner.request_expression_hpc, partner.request_detection_hpc, '
    'chemistry.request_accounting_hpc or chemistry.request_flux_balance_hpc, '
    'its closed return schema must include both component_axis_native_component_records '
    'and component_axis_native_execution_records as saved-fact return fields. '
    'Use episode.return_contract for their exact types or select each with a top-level '
    'episode-fact reference; choose the field names and leave host-filled fields out '
    'of initial_report_json. scientific_process_results carries process metadata. '
    'Preparation or unavailable work can return empty component arrays and its saved '
    'execution findings. This custody requirement does not require a job to succeed.'
)

_SOURCE_COMMIT_GUIDANCE = (
    'Each text-derived source_content observation requires its own observations[].anchor. '
    'Select the actual source_ref, artifact_ref and zero-based half-open UTF-8 '
    'start/end from a received source.read window or source.locate match. The host '
    'retrieves and stores the exact quotation within the original reasoning action. '
    'For source.locate, use its artifact_ref together with the selected match '
    'witness source_ref/start/end. '
    'A source_subjects[].anchor does not populate observations[].anchor; retain the '
    'observation\'s own source and measured subjects. After a partial commit, reuse the '
    'successful aliases or saved record IDs and their actual witnesses when correcting '
    'rejected rows; successful rows remain committed. These source commitments are '
    'separate from the automatically projected numerical components.'
)
INSTRUCTIONS = {axis: instruction+' '+_NATIVE_RETURN_GUIDANCE+' '+_SOURCE_COMMIT_GUIDANCE
    for axis, instruction in _AXIS_INSTRUCTIONS.items()}


def finding_progress():
    from .investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=1))


def task_context(axis, task):
    if axis not in TASKS or task not in TASKS[axis]:
        raise ContractError('component_axis_unknown_task')
    return {'version': VERSION, 'axis': axis, 'name': task, 'allowed_tasks': list(TASKS[axis]),
        'scientific_question': INSTRUCTIONS[axis],
        'communication': 'Scientific descendants retain this evidence axis. Share acquired '
            'findings and specific missing-information needs through shared.*. The shared '
            'parent commissions complementary evidence axes as siblings; consume their '
            'actually delivered records, not their aggregate credit or private sheets.',
        'execution': 'The actual configured tool/resource catalog determines availability. '
            'Use the existing shared execution/HPC parent and prediction/execution sisters '
            'for substantial computation; an availability notice, path or job ID is not a '
            'scientific result. Preserve original inputs, scope, software and result receipts. '
            'The original ordinary flux-balance adapter remains local-only. The new '
            'chemistry.request_flux_balance_hpc bridge is available only with caller-configured '
            'pinned remote software; availability is not an executed deployment check. These '
            'axis registries expose no local heavy FBA fallback. '
            'Publish missing execution capability to the shared parent. Read the actual '
            'whole-workflow CPU/RAM/process bounds and admission feedback.',
        'reporting': 'Return retained scientific findings and exact requested numerical cells '
            'with their source, biological scope, dependence and limitations. The receiver '
            'automatically projects its current scoring sheets from actual admitted cells, '
            'native graders and per-use qualifications. No synthesis child, finalize action '
            'or model-written conclusion is required to make an existing result count. Selected path '
            'evidence and correspondence references are interpretations, not automatic transfer '
            'proofs. Controller progress uses retained findings and remains separate from '
            'scientific component values. No new combined scientific scalar is defined.'}


class ComponentAxisSubtree:
    AXIS = None

    def __init__(self, run_directory):
        directory = Path(run_directory)
        if self.AXIS not in NAMES:
            raise ContractError('component_axis_concrete_subtree_required')
        self.library = ScientificProcessLibrary(directory/'scientific-process-library')
        self.tools = ScientificToolLibrary(directory/'scientific-tool-library')
        self.axis = self.library.reference(self.AXIS)
        entry = validate_instruction_entry(self.library.resolve(self.axis))
        if entry['name'] != NAMES[self.AXIS]:
            raise ContractError('component_axis_matching_instructions_required')

    def commission(self, store, *, target_ref, scope, child_tool_info, question,
                   task='synthesis', completeness='unknown', thought_id='P01',
                   evidence_refs=(), constraints=None, context=None, schema=None, initial=None):
        selected_task = task_context(self.AXIS, task)
        if not isinstance(question, str) or not question.strip():
            raise ContractError('component_axis_question_required')
        if completeness not in {'complete', 'fragment', 'unknown'}:
            raise ContractError('component_axis_completeness_required')
        scope = store.validate_scope(plain(scope))
        material = store.get(target_ref)
        if material['record_type'] not in {'input', 'feature', 'product', 'read_subject'} or not (
                store.scope_covers(store.coverage(target_ref), scope)):
            raise ContractError('component_axis_original_material_required')
        references = list(dict.fromkeys([target_ref, *evidence_refs]))
        if set(store.reference_subset(references, scope)) != set(references):
            raise ContractError('component_axis_evidence_outside_scope')
        supplied = plain(context or {})
        reserved = (self.AXIS.lower()+'_material', self.AXIS.lower()+'_task')
        if any(key in supplied for key in reserved):
            raise ContractError('component_axis_original_context_reserved')
        supplied[reserved[0]] = {'version': VERSION, 'subject_ref': target_ref,
            'molecule': store.subject_molecule(target_ref), 'supplied_length': store.subject_length(target_ref),
            'completeness': completeness, 'original_intervals': store.coverage(target_ref)}
        supplied[reserved[1]] = selected_task
        schema = report_schema(self.AXIS) if schema is None else deepcopy(schema)
        validate_closed_schema(schema)
        initial = initial_report(self.AXIS) if initial is None else deepcopy(initial)
        validate_form(initial, interpretation_schema(schema), lambda ref, namespace:
            ref in store.reference_subset([ref], scope)
            and (namespace is None or store.get(ref)['record_type'] == namespace))
        selection = selector_selection(validate_selection({'version': SELECTION_VERSION,
            'evidence_axis': deepcopy(self.axis), 'thought_pattern': self.library.reference(thought_id),
            'child_tool_info': self.tools.resolve_tool_info(child_tool_info)}))
        return {'kind': 'episode_child', 'role': 'scientific_process', 'goal': question, 'scope': scope,
            'purpose': 'Return the particular scientific findings, native numerical components, '
                'target/partner/feature correspondence and unresolved parent information needs.',
            'schema_json': json.dumps(schema, allow_nan=False),
            'initial_report_json': json.dumps(initial, allow_nan=False),
            'assignment': {'selection': selection, 'evidence_refs': references,
                'constraints': plain(constraints or {}), 'context': supplied}}


@dataclass(frozen=True)
class ComponentAxisServiceFactory:
    source_directory: str
    tool_retrieval: dict
    execution_service_factory: object | None = None
    additional_descriptors: tuple = ()
    literature_configuration: dict | None = None
    AXIS = None

    def as_record(self):
        return {'version': VERSION, 'axis': self.AXIS, 'source_directory': self.source_directory,
            'tool_retrieval': plain(self.tool_retrieval),
            'execution_service_factory': (self.execution_service_factory.as_record()
                if self.execution_service_factory is not None else None),
            'additional_descriptors': plain(self.additional_descriptors),
            'literature_configuration': plain(self.literature_configuration or {})}

    def __call__(self, store, *, run_id, directory, tool_catalog, tool_registry=None,
                 job_episodes=None, resource_estimator=None, **kwargs):
        from .episode_application_services import EpisodeApplicationServices
        from .literature_episodes import LiteratureEpisodes
        from .scientific_process_setup import prepare_scientific_binding
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        from .a102_structural_catalog import prepare_catalog
        if self.AXIS not in NAMES:
            raise ContractError('component_axis_concrete_service_factory_required')
        configuration = plain(self.literature_configuration or {})
        if configuration.get('rate_population', True) is not True:
            raise ContractError('component_axis_numerical_readers_required')
        if configuration.get('a106_intervention') or configuration.get('a108_context_evidence'):
            raise ContractError('component_axis_conflicting_literature_axis_configuration')
        configuration['rate_population'] = True
        configuration.setdefault('contract_information_profile', CONTRACT_INFORMATION_PROFILE)
        literature = LiteratureEpisodes(None, **configuration).as_record()
        directory = Path(directory)
        frozen = directory/'scientific-process-library'
        source = Path(self.source_directory)
        if (frozen/'index.json').is_file():
            library = ScientificProcessLibrary(frozen)
            if any(row['option_ref']['option_id'] == 'A111' for row in library.headers()):
                raise ContractError('component_axis_new_work_requires_merged_catalog')
        else:
            index = json.loads((source/'index.json').read_text())
            if any(row['id'] == 'A111' for row in index['entries']):
                # Reuse the existing shared catalog migration; no structural
                # scientific work or cross-axis child is commissioned here.
                source = prepare_catalog(source, directory/'component-axis-catalog')
        descriptors = tuple(self.additional_descriptors)
        roles = ['scientific_process', 'literature']
        credit, progress_provider, catalogs = {}, None, None
        if self.execution_service_factory is not None:
            from .execution_service_setup import ExecutionServiceFactory
            from .execution_episodes import ExecutionEpisodes
            from .episode_monitoring import MonitorEpisodes
            factory = self.execution_service_factory
            if not isinstance(factory, ExecutionServiceFactory):
                raise TypeError('component_axis_explicit_execution_service_factory_required')
            execution = factory(store, run_id=run_id, directory=directory,
                tool_catalog=tool_catalog, tool_registry=tool_registry, job_episodes=job_episodes,
                resource_estimator=resource_estimator)
            descriptors = (*execution.episode_binding_descriptors, *descriptors)
            credit, progress_provider = execution.role_credit_bindings, execution.job_progress_provider
            catalogs = execution.resource_tool_catalogs
            roles.extend((*ExecutionEpisodes.entry_roles, *MonitorEpisodes.entry_roles))
            if factory.hpc_commissions is not None:
                from .hpc_episodes import HPCEpisodes
                roles.extend(HPCEpisodes.entry_roles)
        elif job_episodes is not None:
            raise ContractError('component_axis_jobs_require_explicit_execution_service_factory')
        ids = [row['binding_id'] for row in descriptors]
        if len(ids) != len(set(ids)) or {'scientific_process', 'literature'}.intersection(ids):
            raise ContractError('component_axis_service_binding_conflict')
        for descriptor in self.additional_descriptors:
            roles.extend(descriptor.get('roles', ()))
        restrict = getattr(tool_registry, 'restrict_resource_tool_catalogs', None)
        if callable(restrict):
            catalogs = restrict(catalogs)
        scientific = prepare_scientific_binding(run_directory=directory, source_directory=source,
            tool_catalog=tool_registry.catalog() if tool_registry is not None else tool_catalog,
            child_roles=tuple(dict.fromkeys(roles)), tool_retrieval=self.tool_retrieval,
            resource_catalogs=catalogs, contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        return EpisodeApplicationServices((scientific, literature, *descriptors), credit,
            progress_provider, resource_tool_catalogs=catalogs)


def create_workflow(axis, store, tools, provider, directory, run_id, controller_factory,
                    *, initial_known_record_refs, **options):
    from .runtime import Workflow
    from .inprocess_replay import VERSION as INPROCESS_COMPLETION_ORDER
    factory = options.get('episode_service_factory')
    if not isinstance(factory, ComponentAxisServiceFactory) or factory.AXIS != axis:
        raise ContractError('component_axis_matching_service_factory_required')
    if any(key in options for key in ('project_credit', 'credit_binding',
            'project_child_credit', 'child_credit_binding')):
        raise ContractError('component_axis_progress_binding_is_host_owned')
    if options.get('episode_record_receipts', True) is not True:
        raise ContractError('component_axis_numerical_receipts_required')
    progress = finding_progress()
    options['episode_record_receipts'] = True
    if options.get('execution_binding') is None:
        if options.get('inprocess_completion_order', INPROCESS_COMPLETION_ORDER) != INPROCESS_COMPLETION_ORDER:
            raise ContractError('component_axis_original_completion_order_required')
        options['inprocess_completion_order'] = INPROCESS_COMPLETION_ORDER
    return Workflow(store, tools, provider, directory, run_id, controller_factory,
        progress, credit_binding=progress.as_record(),
        initial_known_record_refs=initial_known_record_refs, **options)
