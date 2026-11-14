"""Exact original authored phylogeny data; no real producer/custody claim."""
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_bvbrc_phylogeny_bundle_contracts import encode_reference, requested_form_schema
from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_phylogeny_returns import FACT_SOURCES, phylogeny_fact_sources, project_phylogeny_facts
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical, digest

def refs_schema(namespace='source'):
    return {'type': 'object', 'properties': {'refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': 'committed_record_refs'}}, 'required': ['refs'], 'additionalProperties': False}

def selector():
    return {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_artifacts', 'requirements': [{'requirement_id': 'native', 'role': 'native_output', 'required': True, 'declared_format': {'format': 'json', 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}, 'producer_rule_evidence': None, 'exact_object': None}], 'adapter': None, 'requested_schema': refs_schema(), 'supplied_metadata': [], 'supplied_capabilities': []}
MEASUREMENTS, BRANCHES, SITES, MEMBERS, FUNCTIONS, COMPARISONS, REQUIREMENTS, QUALIFICATIONS = FACT_SOURCES
AID = 'selected analysis / α'
TREE = 'artifact_' + 'a' * 64 + '#tree_document/tree/0'
ALIGNMENT = 'artifact_' + 'b' * 64 + '#alignment'

def ref(kind, identifier, aid=AID):
    return encode_reference(kind, aid, identifier)

def slot(name, *, tree=False):
    return {'analysis_id': AID, 'slot_id': name, **({'tree_index': 0} if tree else {})}
SELECTIONS = {'tips': {'metric': 'tree_tip_count', 'analysis_id': AID, 'population_id': 'leaves', 'tree': slot('tree', tree=True)}, 'negative': {'metric': 'literal_row_mean_log2_literal_frequency', 'analysis_id': AID, 'population_id': 'alignment', 'row_index': 0}, 'zero': {'metric': 'site_gap_count', 'analysis_id': AID, 'population_id': 'alignment', 'column_0based': 0}, 'missing': {'metric': 'coverage_original_member_coverage', 'analysis_id': AID, 'population_id': 'alignment', 'row_index': 0, 'input_binding_id': 'input', 'member_id': 'member'}, 'edges': {'metric': 'branch_rows', 'analysis_id': AID, 'population_id': 'leaves', 'tree': slot('tree', tree=True), 'node_indices': [1, 2]}, 'columns': {'metric': 'site_rows', 'analysis_id': AID, 'population_id': 'alignment', 'columns_0based': [0, 1]}, 'members': {'metric': 'family_membership_rows', 'analysis_id': AID, 'family_ids': ['PGF_1']}, 'functions': {'metric': 'function_composition_rows', 'analysis_id': AID, 'population_id': 'function_population'}, 'comparison': {'metric': 'relationship_comparison', 'analysis_id': AID, 'comparison_id': 'organismal'}, 'needs': {'metric': 'missing_requirements'}, 'limitations': {'metric': 'qualifications', 'analysis_id': AID, 'slot_id': 'tree'}}

def fact_form(*sources):
    properties = {'requested_' + str(i): phylogeny_fact_sources()[source]['report_schema'] for i, source in enumerate(sources)}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def content(value, name='supplied'):
    raw = canonical(value).encode()
    sha = hashlib.sha256(raw).hexdigest()
    return {'source_ref': 'source_' + digest([name, sha])[:24], 'artifact_field': 'artifact_ref', 'artifact_ref': 'artifact_' + sha, 'sha256': sha, 'byte_count': len(raw)}

def parameters():
    analysis = {'analysis_id': AID, 'mode': 'core_genome_codon_protein', 'final_alignment_id': slot('alignment'), 'raw_tree_id': slot('tree', tree=True), 'native_engine_slots': [], 'output_role_evidence': [], 'per_family_final_alignment_ids': [], 'explicit_family_matrix_id': None}
    analysis.update({key: None for key in ('partition_document_id', 'supported_tree_id', 'rooted_derivative_tree_id', 'display_tree_id', 'phyloxml_tree_id', 'membership_document_id', 'family_stats_document_id', 'genome_counts_document_id', 'analysis_stats_document_id', 'bootstrap_tree_document_id')})
    calc = {'version': 'codon_tree_components_v1', 'alignment_requests': [{'population_id': 'alignment', 'alphabet': 'dna', 'case_policy': 'literal', 'pairs': [[0, 1]]}], 'tree_requests': [{'population_id': 'leaves', 'branch_unit': 'native_unknown', 'pairs': [[1, 2]]}], 'original_coverage_population_ids': ['alignment'], 'composition_population_ids': ['function_population'], 'taxon_requests': [{'population_id': 'taxonomy', 'rank': 'species'}], 'comparisons': [{'comparison_id': 'organismal', 'gene_tree_id': slot('tree', tree=True), 'organismal_tree_id': slot('tree', tree=True), 'tip_pairs': []}], 'bootstrap_requests': [{'reference_tree_id': slot('tree', tree=True), 'replicate_population_id': 'bootstrap', 'tip_join': {'reference_tree_id': slot('tree', tree=True), 'mappings': []}, 'method': 'rapid_bootstrap'}], 'literal_statistic_population_ids': ['alignment'], 'family_population_requests': [{'family_population_id': 'families', 'genome_population_id': 'genomes'}], 'worst_sequence_population_id': 'families'}
    populations = [{'kind': 'whole_alignment', 'population_id': 'alignment', 'alignment': slot('alignment')}, {'kind': 'whole_tree', 'population_id': 'leaves', 'tree': slot('tree', tree=True)}]
    for kind, pid in (('composition', 'function_population'), ('taxonomy', 'taxonomy'), ('families', 'families'), ('genomes', 'genomes')):
        population = {'population_id': pid, 'evidence': []}
        if kind in {'composition', 'taxonomy'}:
            population.update(unit='feature', member_subjects=[{'kind': 'feature', 'id': 'feature1', 'source_record_id': 'source1'}, {'kind': 'feature', 'id': 'feature2', 'source_record_id': 'source2'}], assignment_completeness='unknown', membership_completeness='complete')
        elif kind == 'families':
            population.update(family_ids=['PGF_1'], stage='selected', completeness='complete')
        else:
            population.update(genome_ids=['genome1'], stage='requested_main', completeness='complete')
        populations.append({'kind': 'explicit', 'population_type': kind, 'population': population})
    populations.append({'kind': 'bootstrap_forest', 'population_id': 'bootstrap', 'forest': slot('tree'), 'expected_replicates': None, 'expected_count_evidence': []})
    return {'version': 'bvbrc_phylogeny_bundle_parameters_v1', 'artifact_selection': [{'analysis_id': AID, 'slot_id': 'tree', 'role': 'raw_tree', 'reader': {'reader': 'newick', 'dialect': 'newick', 'allow_multiple': False}}, {'analysis_id': AID, 'slot_id': 'alignment', 'role': 'final_alignment', 'reader': {'reader': 'aligned_fasta', 'id_rule': 'first_whitespace_token', 'encoding': 'ascii'}}], 'analyses': [{'analysis': analysis, 'population_plans': populations, 'scientific_inputs': None, 'read_parameters': {'source_dialect': 'retained_codon_trees', 'membership_dialect': 'homologs_current', 'family_stats_dialect': None}, 'calculation_parameters': calc}]}

def saved_sheet():
    tree_artifact = {'raw_artifact_ref': TREE.split('#')[0], 'source_ref': 'source_' + 'c' * 24, 'sha256': 'a' * 64}
    alignment_artifact = {'raw_artifact_ref': ALIGNMENT.split('#')[0], 'source_ref': 'source_' + 'd' * 24, 'sha256': 'b' * 64}
    tree = {'tree_id': TREE, 'document_id': TREE.rsplit('/tree/', 1)[0], 'tree_index': 0, 'nodes': [{'node_index': i, 'parent_index': parent, 'child_indices': children, 'branch_length': length} for i, parent, children, length in ((0, None, [1, 4], None), (1, 0, [2, 3], -0.125), (2, 1, [], 0.0), (3, 1, [], 0.2), (4, 0, [5, 6], 0.1), (5, 4, [], 0.3), (6, 4, [], 0.4))]}
    alignment = {'alignment_id': ALIGNMENT, 'artifact': alignment_artifact, 'observed_column_count': 2, 'rows': [{'row_index': 0, 'sequence': 'A-'}, {'row_index': 1, 'sequence': 'AT'}]}
    sheet = {'tool': 'C-L193-CodonTree', 'schema_version': 'bvbrc_codon_tree_sheet_v1', 'mode': 'core_genome_codon_protein', 'documents': {'analyses': [{'analysis_id': AID}], 'store': {'tree_documents': [{'document_id': tree['document_id'], 'artifact': tree_artifact, 'trees': [tree]}], 'phyloxml': [], 'alignments': [alignment], 'native_tables': []}}, 'populations': {'leaves': [{'population_id': 'leaves', 'tree_id': TREE, 'node_indices': [2, 3, 5, 6]}], 'alignments': [{'population_id': 'alignment', 'alignment_id': ALIGNMENT, 'row_indices': [0, 1], 'columns_0based': [0, 1]}], 'composition': [{'population_id': 'function_population', 'member_subjects': [{'id': 'feature1'}, {'id': 'feature2'}]}]}, 'families': [{'family_id': 'PGF_1', 'final_block_indices': [0, 1], 'memberships': [{'representation': 'protein', 'feature_ids': ['feature1']}, {'representation': 'coding_nucleotide', 'feature_ids': ['feature1']}]}], 'genomes': [{'genome_id': 'genome1', 'final_alignment_rows': [{'alignment_id': ALIGNMENT, 'row_index': 0}]}], 'joins': {'functions': [{'function_key': 'enzyme / original label'}], 'function_equivalences': [], 'input_rows': [], 'feature_genomes': [{'feature_id': 'feature1', 'genome_id': 'genome1', 'family_id': 'PGF_1'}], 'family_blocks': [{'family_id': 'PGF_1', 'alignment_id': ALIGNMENT, 'representation': rep, 'member_row_indices': [0]} for rep in ('protein', 'coding_nucleotide')]}, 'missing_requirements': []}
    selections = [{'analysis_id': AID, 'slot_id': sid, 'role': role, 'state': 'resolved', 'artifact_refs': [tree_artifact if sid == 'tree' else alignment_artifact], 'acquisition_receipt_refs': [], 'read_id': sid, 'document_id': doc, 'tree_ids': trees, 'requirement_ids': []} for sid, role, doc, trees in (('tree', 'raw_tree', tree['document_id'], [TREE]), ('alignment', 'final_alignment', ALIGNMENT, []))]
    return {'schema_version': 'bvbrc_phylogeny_sheet_set_v1', 'tool': 'C-L193-CodonTree', 'selections': selections, 'analyses': [{'analysis_id': AID, 'status': 'ok', 'sheet': sheet, 'diagnostics': [], 'missing_requirements': []}]}

def projection(*, selections=None, values=None):
    selections = deepcopy(SELECTIONS if selections is None else selections)
    facts = {'tips': 4, 'negative': -0.5, 'zero': 0, 'missing': None, 'edges': [{'tree_ref': ref('tree', TREE), 'node_index': i, 'split_ref': ref('split', TREE + '/split/2,3') if i == 1 else None, 'length': length, 'length_unit': 'native_unknown', 'support_value': support, 'support_method': 'native_unknown', 'support_scale': 'native_unknown', 'bootstrap_matches': None, 'bootstrap_replicates': None} for i, length, support in ((1, -0.125, 0.0), (2, 0.0, None))], 'columns': [{'alignment_ref': ref('alignment', ALIGNMENT), 'column_0based': i, 'n_rows': 2, 'gap_count': gap, 'canonical_count': 2 - gap, 'ambiguity_count': 0, 'canonical_majority_fraction': 1.0, 'canonical_entropy_bits': 0.0} for i, gap in ((0, 0), (1, 1))], 'members': [{'family_ref': ref('family', 'PGF_1'), 'representation': rep, 'feature_ref': ref('feature', 'feature1'), 'genome_ref': ref('genome', 'genome1'), 'alignment_row_index': 0, 'inclusion_stage': 'final_' + rep} for rep in ('protein', 'coding_nucleotide')], 'functions': [{'population_ref': ref('population', 'function_population'), 'function_ref': ref('function', 'enzyme / original label'), 'assigned_members': 1, 'total_members': 2, 'members_with_recorded_assignment': 1, 'fraction_all': 0.5, 'fraction_recorded': 1.0}], 'comparison': [{'comparison_ref': ref('comparison', 'organismal'), 'matched_tips': 4, 'gene_splits': 1, 'organismal_splits': 1, 'shared_splits': 1, 'rf': 0, 'rf_fraction': 0.0}], 'needs': [], 'limitations': [{'code': 'bvbrc_phylogeny_negative_branch_length', 'phase': 'native_decode', 'severity': 'qualification', 'role_ref': ref('role', 'raw_tree'), 'requirement_refs': []}]}
    facts = {name: deepcopy((values or facts)[name]) for name in selections}
    selected = selector()
    selected.update(endpoint='requested_projection', adapter={'adapter_id': 'bvbrc_codon_tree', 'adapter_version': '1', 'parameters': parameters()}, requested_schema=requested_form_schema(selections))
    sheet = saved_sheet()
    bundle = content({'fixture': 'retained controlled publication'}, 'bundle')
    saved = {'adapter_id': 'bvbrc_codon_tree', 'adapter_version': '1', 'status': 'ok', 'facts': facts, 'sheet_content': content(sheet, 'sheet'), 'components_content': None, 'missing_requirements': [], 'diagnostics': []}
    return ({'version': RESULT_VERSION, 'reference': bundle['source_ref'], 'source_ref': bundle['source_ref'], 'record_refs': [bundle['source_ref']], 'publication': {'bundle_content': bundle, 'result_record_refs': [bundle['source_ref']], 'adapter_result': saved}, 'publication_inputs': {'selector': selected, 'adapter': deepcopy(selected['adapter'])}}, sheet)

def all_facts(body, sheet):
    return project_phylogeny_facts(body, requested_sources=FACT_SOURCES, sheet_set=sheet)

def numbers(facts):
    return {row['field']: row['value'] for row in facts[MEASUREMENTS]}
