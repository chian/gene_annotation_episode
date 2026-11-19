"""A110 axis question, task names and finding-progress policy for the head subtree."""
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import ContractError

VERSION = 'component_axis_investigation_v1'
NAMES = {'A110': 'Biochemical feasibility and chemical/resource accounting'}
TASKS = {
    'A110': ('reaction_identity', 'stoichiometric_accounting', 'electron_accounting',
        'cofactor_regeneration', 'resource_feasibility', 'conditional_energetics',
        'prediction_contrast', 'target_transfer', 'synthesis'),
}
_AXIS_INSTRUCTIONS = {
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
    'When commissioning a biochemical_feasibility_evidence child whose child_tool_info includes '
    'chemistry.request_accounting_hpc or chemistry.request_flux_balance_hpc, '
    'its closed return schema must include both component_axis_native_component_records '
    'and component_axis_native_execution_records as saved-fact return fields. '
    'Use episode.return_contract for their exact types or select each with a top-level '
    'episode-fact reference; choose the field names and leave host-filled fields out '
    'of initial_report_json. biochemical_feasibility_evidence_results carries process metadata. '
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


def scientific_guidance():
    """The A110 head's own investigation guidance: the axis question and the descendant relationship."""
    return INSTRUCTIONS['A110'] + '\n\nScientific descendants remain A110. Use available shared operations for specific parent information needs or useful received findings. The immediate parent chooses within its own options or relays the need upward; publication does not commission work or promise a reply. Preserve named scientific components separately from controller progress.\n\n'


def finding_progress():
    from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=1))


def task_context(task):
    if task not in TASKS['A110']:
        raise ContractError('component_axis_unknown_task')
    return {'version': VERSION, 'axis': 'A110', 'name': task, 'allowed_tasks': list(TASKS['A110']),
        'scientific_question': INSTRUCTIONS['A110'],
        'communication': 'Scientific descendants retain this evidence axis. Share acquired '
            'findings and specific missing-information needs through shared.*. The shared '
            'parent commissions complementary evidence axes as siblings; consume their '
            'actually delivered records, not their aggregate credit or private sheets.',
        'execution': 'The actual configured tool/resource catalog determines availability. '
            'Use the existing private execution/HPC parent and prediction/execution sisters '
            'for substantial computation; an availability notice, path or job ID is not a '
            'scientific result. Preserve original inputs, scope, software and result receipts. '
            'The original ordinary flux-balance adapter remains local-only. The new '
            'chemistry.request_flux_balance_hpc bridge is available only with caller-configured '
            'pinned remote software; availability is not an executed deployment check. These '
            'axis registries expose no local heavy FBA fallback. '
            'Publish missing execution capability to the shared parent. Read the actual '
            'whole-workflow CPU/RAM bounds and admission feedback.',
        'reporting': 'Return retained scientific findings and exact requested numerical cells '
            'with their source, biological scope, dependence and limitations. The receiver '
            'automatically projects its current scoring sheets from actual admitted cells, '
            'native graders and per-use qualifications. No synthesis child, finalize action '
            'or model-written conclusion is required to make an existing result count. Selected path '
            'evidence and correspondence references are interpretations, not automatic transfer '
            'proofs. Controller progress uses retained findings and remains separate from '
            'scientific component values. No new combined scientific scalar is defined.'}

