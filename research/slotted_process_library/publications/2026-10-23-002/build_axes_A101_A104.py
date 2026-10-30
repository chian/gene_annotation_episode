"""A101–A104 native evidence-axis definitions, using preserved case sources.

No target evidence is created, no operation is invented, and no scoring formula,
weight or cutoff is supplied. Run once; existing publication files are retained.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.evidence_axis_contracts import validate_evidence_axis_entry


PUBLICATION = Path(__file__).resolve().parent
REPO = PUBLICATION.parents[3]
ORIGINAL = REPO/'verification/scientific_support_slot_candidates_2026-10-22_002/candidate002'


def measurement(metric_id, name, field, kinds, units, direction, requirements, limits, *, recorded=None):
    return {'metric_id': metric_id, 'name': name, 'native_field': field,
        'observation_kinds': kinds, 'units': units, 'direction': direction,
        'method_requirements': requirements, 'comparison_limits': limits,
        'binding': {'kind': 'recorded_measurement' if recorded else 'unbound',
                    'measurement_name': recorded, 'json_pointer': None}}


def criterion(criterion_id, question, evidence, met, not_met, unknown, *, metrics=(), test=None):
    return {'criterion_id': criterion_id, 'question': question,
        'required_metric_ids': list(metrics), 'required_evidence': evidence,
        'outcomes': {'met': met, 'not_met': not_met, 'unknown': unknown}, 'deterministic_test': test}


SEQUENCE_METHOD = [
    'The actual comparison identifies query and comparator, sequence or profile boundaries, program and the parameters relevant to this statistic.',
    'Preserve the actual source record, reported numeric bound or uncertainty, search space and database/model identity when supplied; missing method details remain unknown.']
SEQUENCE_LIMIT = [
    'A sequence statistic measures the reported correspondence, not a probability that a particular function is correct.',
    'Do not compare or average unlike methods, configurations, search spaces or native scales without an explicitly supplied calibration; no calibration is defined here.']
STRUCTURE_METHOD = [
    'An actual selected structural comparison identifies the compared structures, experimental or predicted origin, chains, aligned regions and method-specific statistic.',
    'Preserve the actual atom/residue selection, superposition or normalization convention and available uncertainty.']
STRUCTURE_LIMIT = [
    'A global fold match does not establish substrate specificity or the presence of a particular catalytic or recognition feature.',
    'No structural-comparison extractor is claimed by an unbound binding. Missing native numbers stay unavailable, not zero; prediction confidence is not a structural-homology score.']


AXES = {
 'A101': {
  'name': 'Sequence homology',
  'description': 'Native sequence correspondence and explicit characterization-to-target transfer criteria for the annotation evidence axis.',
  'native_measurements': [
   measurement('alignment_score', 'Native alignment score', 'alignment_score', ['alignment', 'comparison'], ['native_alignment_score'], 'higher', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['Raw alignment scores require the same scoring scheme and meaningful sequence-span comparison.'], recorded='alignment_score'),
   measurement('bitscore', 'Native sequence or profile bit score', 'bitscore', ['alignment', 'profile_match', 'comparison'], ['bit'], 'higher', SEQUENCE_METHOD, SEQUENCE_LIMIT, recorded='bitscore'),
   measurement('evalue', 'Native expected random-match count', 'evalue', ['alignment', 'profile_match', 'comparison'], ['expected_random_matches'], 'lower', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['An E-value depends on the searched space. A reported bound remains a bound; do not replace it with an invented exact zero.'], recorded='evalue'),
   measurement('identity_fraction', 'Identity within the reported alignment', 'identity_fraction', ['alignment', 'comparison'], ['fraction'], 'target_dependent', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['Preserve the denominator and aligned region. High identity over a short or irrelevant region does not establish transfer of the candidate property.'], recorded='identity_fraction'),
   measurement('query_coverage', 'Native query coverage', 'query_coverage', ['alignment', 'profile_match', 'comparison'], ['fraction'], 'target_dependent', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['Identify which sequence is the query; do not confuse matched-domain coverage with whole-protein coverage.'], recorded='query_coverage'),
   measurement('comparator_coverage', 'Native comparator coverage', 'target_coverage', ['alignment', 'profile_match', 'comparison'], ['fraction'], 'target_dependent', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['The alignment method’s target is the comparator, which is not automatically the gene being annotated. Preserve that orientation.'], recorded='target_coverage'),
   measurement('profile_model_score', 'Native profile-model score', 'model_score', ['profile_match'], ['native_model_score'], 'higher', SEQUENCE_METHOD,
    SEQUENCE_LIMIT+['Model scores depend on the model and configuration; one model’s raw score is not another model’s functional confidence.'], recorded='model_score')],
  'judgment_criteria': [
   criterion('native_correspondence_recorded', 'Is the target-to-homolog sequence correspondence supported by an actual native-scored comparison?',
    ['target_sequence', 'identified_comparator', 'native_scored_correspondence'],
    'An actual comparison identifies the target and comparator and reports at least one native alignment, search or profile statistic with the matched region and interpretable method context.',
    'The cited comparison demonstrably concerns another sequence pair, or the claimed match is outside the regions actually compared.',
    'No native-scored correspondence, sequence identity, matched-region information or necessary method context has been received. Different programs need not all report the same statistics.'),
   criterion('comparator_property_characterized', 'What measured comparator property is proposed to transfer to the target?',
    ['characterized_source_subject', 'experimental_property', 'experimental_conditions'],
    'The source identifies the assayed homolog and the proposed property as an actual experimental result under stated conditions, rather than only an inherited annotation.',
    'The source actually assigns another property or its controlled results contradict the characterization being claimed.',
    'The relevant characterization, assayed subject, controls or conditions have not been established from received evidence.'),
   criterion('claim_relevant_features_correspond', 'Does the observed sequence correspondence include the features needed for the particular annotation claim?',
    ['native_scored_correspondence', 'characterization_feature_requirements', 'target_feature_comparison'],
    'The actual matched region includes the source-supported features relevant to the claimed property, and no received feature comparison contradicts that transfer at the stated specificity.',
    'A source-required feature is demonstrably absent or incompatible in the target, or the cited match excludes the region needed for the claimed transfer.',
    'The property’s relevant features, their target mapping or the informative alignment region are not established. A global similarity number alone leaves this criterion unknown.'),
   criterion('specificity_not_overtransferred', 'Does the proposed annotation stay within the property actually supported by the homolog comparison?',
    ['proposed_target_hypothesis', 'characterized_source_subject', 'specificity_comparison'],
    'The claim is bounded to the family, reaction, substrate or role that the comparison actually supports; received specificity-changing or counterexample evidence has been retained in that boundary.',
    'The target is assigned a specific substrate, reaction or physiological role despite received discriminating evidence that rejects that transfer, or broad family similarity is presented as its specific experimental proof.',
    'The evidence does not discriminate the claimed specificity from alternatives, or relevant specificity comparisons have not been received.')],
  'qualitative_grading': [],
  'transfer_chain': {
   'source_subject': 'Identify the experimentally characterized homolog and the sequence/profile comparator; retain any difference between them.',
   'source_property': 'Retain the actual measured property, controls and conditions separately from the sequence statistic.',
   'correspondence': 'Link the actual sequence comparison, matched span and function-relevant features to the gene being annotated.',
   'target_hypothesis': 'Identify the candidate target property and supported specificity; family membership is distinct from exact chemistry or native role.',
   'limitations': 'Retain incomplete coverage, changed recognition features, source conditions and shared evidence dependencies. The assay and alignment form a chain rather than two independent experiments.'}},
 'A102': {
  'name': 'Structural homology',
  'description': 'Native structural correspondence measures and feature-specific criteria for transferring a characterized homolog property.',
  'native_measurements': [
   measurement('structural_similarity_score', 'Method-reported structural similarity score', None, ['structure_match', 'comparison'], ['native_structural_similarity_score'], 'higher', STRUCTURE_METHOD,
    STRUCTURE_LIMIT+['Use this descriptor only for a method whose native statistic increases with the reported structural correspondence. Do not relabel a lower-is-better distance.']),
   measurement('aligned_structure_rmsd', 'RMSD over the actual aligned atoms or residues', 'RMSD', ['structure_match', 'comparison'], ['angstrom'], 'lower', STRUCTURE_METHOD,
    STRUCTURE_LIMIT+['A small RMSD over a short fragment is not a full-length match. Preserve matched extent and selections; flexible regions and missing atoms affect the comparison.']),
   measurement('aligned_structure_residues', 'Native count of structurally aligned residues', None, ['structure_match', 'comparison'], ['residue'], 'target_dependent', STRUCTURE_METHOD,
    STRUCTURE_LIMIT+['A residue count is matched extent, not calibrated evidence of functional equivalence.']),
   measurement('structural_alignment_coverage', 'Native reported structural-alignment coverage', None, ['structure_match', 'comparison'], ['fraction', 'percent'], 'target_dependent', STRUCTURE_METHOD,
    STRUCTURE_LIMIT+['Retain the program’s stated denominator and units; do not silently change percentages to fractions or combine them across methods.'])],
  'judgment_criteria': [
   criterion('structural_comparison_quantified', 'Is the structural correspondence supported by an actual native comparison and its matched extent?',
    ['target_structure_or_model', 'comparator_structure_or_model', 'native_structural_comparison'],
    'An actual comparison identifies both structures and reports a method-specific native correspondence measure and the region or extent compared.',
    'The cited calculation uses another structure pair or a different region than the claimed match.',
    'No actual native comparison, identified structure pair or matched extent is available. A structure prediction’s confidence does not substitute for this comparison.'),
   criterion('structure_origin_retained', 'Are experimental constraints and predicted or modeled origins correctly distinguished?',
    ['structure_origin', 'construct_chain_assembly', 'structural_uncertainty'],
    'Each compared structure is identified as experimentally constrained/refined or predicted/docked/simulated, and the available construct, assembly and uncertainty limits are retained.',
    'A wholly predicted or docked state is presented as an experimental structure, or a ligand/contact interpretation is asserted beyond the cited experimental constraints.',
    'The relevant structure origin, construct/assembly identity or uncertainty needed for the comparison is not available.'),
   criterion('functional_geometry_corresponds', 'Do the structures share the machinery relevant to the specific candidate property?',
    ['native_structural_comparison', 'characterized_comparator_property', 'functional_site_or_architecture_comparison'],
    'The actual comparison supports correspondence of the source-characterized catalytic, recognition or partner architecture needed for the stated target property.',
    'A source-required catalytic or recognition feature is demonstrably missing or incompatible, or the match is limited to an architecture unrelated to the claimed property.',
    'Only global fold similarity is known, or the functional feature/region and its correspondence have not been established.'),
   criterion('structural_transfer_bounded', 'Does structural transfer preserve the distinction between architecture and measured function?',
    ['proposed_target_hypothesis', 'characterized_comparator_property', 'functional_transfer_limits'],
    'The proposed annotation is limited to the correspondence and characterized property actually supported, with model origin and observed specificity differences retained.',
    'Fold or contact compatibility is presented as measured target chemistry, affinity, transport or native necessity despite the absent corresponding functional observation.',
    'The relevant comparator characterization or information distinguishing the claimed target property from structural compatibility is missing.')],
  'qualitative_grading': [],
  'transfer_chain': {
   'source_subject': 'Identify the structurally compared homolog and the subject on which function was experimentally characterized.',
   'source_property': 'Retain the experimentally supported comparator property separately from a global fold label or modeled ligand.',
   'correspondence': 'Preserve actual matched chains, regions, native structural measures and correspondence of relevant functional machinery.',
   'target_hypothesis': 'State the target property supported by that correspondence at its justified specificity.',
   'limitations': 'Retain predicted origin, incomplete alignments, changed active-site features and shared-source dependencies. A102 structural correspondence differs from A111 experimental structural-state evidence.'}},
 'A103': {
  'name': 'Gene context',
  'description': 'Native genomic-context association measures, identified neighboring genes and explicit criteria linking organization to the candidate annotation.',
  'native_measurements': [
   measurement('gene_context_association_score', 'Native genomic-context association score', None, ['context', 'context_measurement', 'comparison'], ['native_context_association_score'], 'target_dependent',
    ['An actual context-analysis result names the compared gene families, organism inventory, native statistic, method, detection scope and relevant configuration.',
     'Retain the method’s own scale/direction and whether the statistic concerns neighborhood, fusion, cooccurrence or another explicitly measured relationship.'],
    ['No native context-score extractor is currently claimed by this unbound descriptor. Genomic adjacency or a prose impression is not relabeled as this score.',
     'Shared ancestry, related genome sampling, incomplete assemblies and homolog-detection limits can affect the observed association.']),
   measurement('gene_context_association_pvalue', 'Native reported context-association significance', None, ['context_measurement', 'comparison'], ['p_value'], 'lower',
    ['The actual context test reports its statistic, null model, tested set and whether this value is adjusted for multiple comparisons.'],
    ['Do not invent a significance cutoff or call an unadjusted value adjusted. A reported association significance is not a probability of the candidate function.']),
   measurement('neighbor_identification_bitscore', 'Native homology bit score identifying a relevant neighbor', 'bitscore', ['alignment', 'profile_match', 'comparison'], ['bit'], 'higher',
    SEQUENCE_METHOD+['The scored query is the particular neighboring component being identified; preserve its genomic relationship to the gene being annotated.'],
    SEQUENCE_LIMIT+['A neighbor-identification score supports that identity, not the target gene’s function by itself.'], recorded='bitscore'),
   measurement('neighbor_identification_evalue', 'Native homology E-value identifying a relevant neighbor', 'evalue', ['alignment', 'profile_match', 'comparison'], ['expected_random_matches'], 'lower',
    SEQUENCE_METHOD+['The scored query is the actual neighboring gene product and comparator under examination.'],
    SEQUENCE_LIMIT+['A native neighbor match and a genomic-context association are separate linked facts, not interchangeable scores.'], recorded='evalue')],
  'judgment_criteria': [
   criterion('context_scope_identified', 'Does the context evidence refer to the relevant gene and actual genome or assembly?',
    ['target_genomic_location', 'genome_or_assembly_scope', 'gene_organization_observation'],
    'The evidence identifies the target locus and actual neighboring or fused genes, with their observed orientation/spacing or fusion organization in the relevant genome/assembly.',
    'The claimed arrangement belongs to another locus, organism or assembly, or the received coordinates/organization contradict the stated relationship.',
    'The target locus, relevant genomic region, assembly scope or actual organization has not been established.'),
   criterion('associated_components_identified', 'Are the genes used to interpret the context actually identified with their uncertainty?',
    ['neighbor_identity_evidence', 'source_component_function', 'detection_scope'],
    'The neighboring components and the function used in the contextual inference have source-grounded identity evidence, including actual native homology or characterization where available.',
    'A key neighbor has a demonstrated incompatible identity or property, or an unsupported copied annotation is presented as experimental characterization of that component.',
    'The relevant neighbor identity, characterized role or detection scope is not established; an unannotated region is not a supported absent gene.'),
   criterion('organization_supports_claimed_relationship', 'Does the actual organization support the particular functional relationship being assigned?',
    ['gene_organization_observation', 'source_component_function', 'context_comparison_or_native_association'],
    'The observed organization and actual comparison/association bear on a named pathway, component or regulatory relationship compatible with the candidate annotation, retaining nonuniversal arrangements.',
    'The received contextual comparison contradicts the claimed relationship, or a relationship to an unrelated neighboring system is presented as support for the proposed role.',
    'Only adjacency without a supported component relationship is available, or an informative context comparison/native association has not been received.'),
   criterion('context_claim_not_overstated', 'Is the contextual conclusion bounded to what organization and component evidence establish?',
    ['proposed_target_hypothesis', 'context_comparison_or_native_association', 'context_dependence_limits'],
    'The annotation retains that context may support association or participation without demonstrating exact chemistry, direction of regulation or indispensable partner dependence.',
    'Nonspecific adjacency, related-genome repetition or an unexamined missing region is presented as independent proof of a specific reaction or a universally required component.',
    'The evidence needed to distinguish contextual association from the more specific target claim, or the relevant detection/assembly limit, is unavailable.')],
  'qualitative_grading': [],
  'transfer_chain': {
   'source_subject': 'Identify the actual target locus, genomic region and neighboring components; references remain evidence subjects rather than new annotation targets.',
   'source_property': 'Retain the independently supported properties of the neighboring components or associated pathway.',
   'correspondence': 'Connect their actual genomic organization and native association/identification measurements to the proposed relationship.',
   'target_hypothesis': 'Identify the target’s proposed participation, partner relationship or bounded role that this context supports.',
   'limitations': 'Preserve incomplete assemblies, uncertain gene detection, optional modules, unlinked relevant homologs and shared ancestry; native context data and its interpretation remain distinct.'}},
 'A104': {
  'name': 'Evolutionary history and phylogenetic placement',
  'description': 'Native tree/placement support and explicit clade, organism-history and outlier-explanation criteria for annotation evidence.',
  'native_measurements': [
   measurement('clade_support', 'Native support for the relevant branch or placement', None, ['comparison', 'context', 'context_measurement'], ['percent', 'probability', 'native_support_unit'], 'higher',
    ['An actual tree or placement result identifies homologs, the alignment, model/method, relevant branch and the reported support statistic.',
     'Retain whether the quantity is bootstrap support, posterior support or another actual statistic and preserve its native scale.'],
    ['No tree-support extractor is claimed by this unbound descriptor. A nearest-hit score or distribution list is not branch support.',
     'Different support statistics and gene/sample sets are not automatically comparable or independent.']),
   measurement('placement_branch_length', 'Native branch length or placement distance', None, ['comparison', 'context_measurement'], ['substitutions_per_site', 'native_branch_length_unit'], 'target_dependent',
    ['An actual phylogenetic result identifies the target placement, relevant branches, native distance definition and model.'],
    ['A long branch or outlying placement is not automatically a functional contradiction or proof of horizontal transfer. Missing taxa, paralogs and tree uncertainty remain alternatives.']),
   measurement('gene_species_congruence_statistic', 'Native gene-versus-organism history comparison', None, ['comparison', 'context_measurement'], ['native_congruence_statistic'], 'target_dependent',
    ['An actual comparison specifies the gene tree, organismal history, taxon mapping and its native congruence/reconciliation statistic.'],
    ['Do not invent a universal tree-congruence score, infer an unmeasured transfer event or silently equate duplication/loss with horizontal transfer.'])],
  'judgment_criteria': [
   criterion('phylogeny_actually_reconstructed', 'Does the evidence provide an actual relevant phylogenetic analysis?',
    ['homolog_taxon_inventory', 'alignment_and_tree_method', 'actual_tree_or_placement'],
    'The received result identifies homologs/taxa, method and an actual tree or placement for the relevant target and comparators, retaining the reported uncertainty.',
    'A nearest sequence hit or a presence/absence list is presented as a reconstructed tree, or the cited tree does not include the target/comparison claimed.',
    'No actual relevant tree/placement, homolog sampling, method or necessary taxon mapping has been received.'),
   criterion('placement_matches_characterized_clade', 'Is the target placed in a functionally characterized clade relevant to the candidate annotation?',
    ['actual_tree_or_placement', 'characterized_clade_members', 'target_clade_assignment'],
    'The actual topology/placement locates the target among source-characterized members bearing the candidate property, with the reported branch/placement uncertainty and exceptions retained.',
    'The actual placement lies in a characterized clade with an incompatible property, or an asserted target membership is contradicted by the cited topology.',
    'The relevant members’ functions, target membership or placement support are unresolved; clustering by label alone does not settle the candidate property.'),
   criterion('organism_history_congruence_examined', 'Does the inferred gene history fit the organismal evolutionary context?',
    ['actual_tree_or_placement', 'organism_history', 'paralog_and_sampling_context'],
    'The received gene/organism comparison is compatible with the expected history at the assessed scope, with relevant duplication, loss and sampling alternatives retained.',
    'A received comparison demonstrates incongruence or an outlying placement inconsistent with the claimed unqualified vertical-history interpretation.',
    'The organismal history, gene-tree comparison, paralog identity or informative sampling is absent or too uncertain to decide.'),
   criterion('hgt_outlier_explanation', 'If horizontal transfer is proposed, is there a source-grounded explanation for the outlying placement?',
    ['outlying_gene_placement', 'possible_source_context', 'recipient_context', 'independent_transfer_evidence_or_alternative'],
    'The proposed transfer explanation is consistent with the actual outlying placement, a plausible source/recipient relationship and independent received context or sequence/genomic support, while unresolved alternatives are retained.',
    'Received placement, source/recipient context or independent evidence contradicts the proposed transfer explanation; shared environment alone is treated as proof despite that contradiction.',
    'Transfer has not been established as a relevant alternative, the source/recipient context is missing, or placement/alternative explanations remain insufficiently constrained.')],
  'qualitative_grading': [{
   'criterion_id': 'hgt_outlier_explanation', 'kind': 'hgt_environment_explanation',
   'reason_no_native_metric': 'Native tree support and congruence are retained above. The biological plausibility of a particular transfer explanation from source/recipient environments and other evidence has no universal native numerical statistic; the user explicitly permitted a pseudo-grader for this explanation.',
   'ordered_levels': [
    {'code': 'contradicted', 'meaning': 'Received biological or sequence/genomic evidence contradicts the stated transfer explanation.'},
    {'code': 'plausible_only', 'meaning': 'Source/recipient circumstances are compatible with transfer, but independent evidence does not distinguish it from retained alternatives.'},
    {'code': 'corroborated', 'meaning': 'The explanation is compatible with the outlying placement and source/recipient circumstances and has independent received supporting evidence; retain remaining uncertainty.'}]}],
  'transfer_chain': {
   'source_subject': 'Identify the actual gene/homolog sequences and taxa represented in the phylogenetic comparison.',
   'source_property': 'Retain the experimentally characterized clade-member properties separately from copied labels or occurrence patterns.',
   'correspondence': 'Connect the target’s actual tree placement to those members and compare gene history with organismal history, preserving native reported support.',
   'target_hypothesis': 'Identify the candidate function supported or challenged by that placement, and separately identify any proposed transfer explanation.',
   'limitations': 'Retain taxon sampling, paralog identity, duplication/loss, tree uncertainty and environmental/source limits. A biological explanation grade is not a replacement for tree evidence or an invented numeric weight.'}}
}


def main():
    originals = {path.stem: json.loads(path.read_text()) for path in (ORIGINAL/'entries').glob('A*.json')}
    selections = {key: [(key, i) for i in range(len(originals[key]['evidence']))]
                  for key in ('A101', 'A102', 'A103')}
    selections['A104'] = [('A101', 14), ('A103', 5)] + [('A104', i) for i in range(5)]
    crosswalk = []
    for axis_id, content in AXES.items():
        evidence = [deepcopy(originals[key]['evidence'][i]) for key, i in selections[axis_id]]
        entry = validate_evidence_axis_entry({'entry_version': 'evidence_axis_entry_v1',
            'id': axis_id, 'slot': 'evidence_axis', **content, 'evidence': evidence})
        destination = PUBLICATION/'entries'/f'{axis_id}.json'
        with destination.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
        for new_index, (original_id, original_index) in enumerate(selections[axis_id]):
            path = ORIGINAL/'entries'/f'{original_id}.json'
            crosswalk.append({'axis_id': axis_id, 'evidence_index': new_index,
                'original_path': str(path.relative_to(REPO)),
                'original_file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'original_pointer': f'/evidence/{original_index}',
                'meaning': ('Actual tree/clade observation' if axis_id == 'A104' and new_index < 2 else
                    'Retained source observation and inspection limits; no new numerical result or primary-source verification')})
    with (PUBLICATION/'SOURCE_CROSSWALK_A101_A104.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps({'meaning': 'Exact row ancestry; source reuse does not create independent support.',
            'rows': crosswalk}, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
