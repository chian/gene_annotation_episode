"""A107 axis instructions, task contexts and finding-progress projection."""
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError

VERSION = 'component_axis_investigation_v1'
NAMES = {'A107': 'Required partner presence and coexpression'}
TASKS = {
    'A107': ('partner_requirements', 'component_identity', 'genome_presence',
        'matched_expression', 'coexpression', 'interaction_distinction', 'target_transfer', 'synthesis'),
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
}

_NATIVE_RETURN_GUIDANCE = (
    'When commissioning a partner_presence_evidence child whose child_tool_info includes '
    'partner.request_expression_hpc or partner.request_detection_hpc, '
    'its closed return schema must include both component_axis_native_component_records '
    'and component_axis_native_execution_records as saved-fact return fields. '
    'Use episode.return_contract for their exact types or select each with a top-level '
    'episode-fact reference; choose the field names and leave host-filled fields out '
    'of initial_report_json. partner_presence_evidence_results carries process metadata. '
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
    from gene_annotation_episode.episodic_workflow.episode_support.findings.partner_presence_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=1))


def task_context(task):
    if task not in TASKS['A107']:
        raise ContractError('component_axis_unknown_task')
    return {'version': VERSION, 'axis': 'A107', 'name': task, 'allowed_tasks': list(TASKS['A107']),
        'scientific_question': INSTRUCTIONS['A107'],
        'communication': 'Scientific descendants retain this evidence axis. Share acquired '
            'findings and specific missing-information needs through shared.*. The shared '
            'parent commissions complementary evidence axes as siblings; consume their '
            'actually delivered records, not their aggregate credit or private sheets.',
        'execution': 'The actual configured tool/resource catalog determines availability. '
            'Use the existing private execution/HPC parent and prediction/execution sisters '
            'for substantial computation; an availability notice, path or job ID is not a '
            'scientific result. Preserve original inputs, scope, software and result receipts. '
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


