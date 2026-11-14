"""Dispatch shared arithmetic over a validated, saved provider sheet.

No acquisition, byte parsing, executable invocation, resource choice, or score
aggregation occurs here. Individual shared components retain their populations.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

from . import phylogeny_calculators as calc
from . import phylogeny_calculation_contracts as c
from . import bvbrc_phylogeny_common_contracts as v
from .bvbrc_phylogeny_common_contracts import validate_shared_fields


def _merge_requirements(*collections):
    merged = {}
    for collection in collections:
        for row in collection:
            v._requirement(row)
            key = row['requirement_id']
            v._require(key not in merged or merged[key] == row, 'requirement_meaning_conflict')
            merged[key] = deepcopy(row)
    return list(merged.values())


def _parameters(parameters):
    v._shape(parameters, v.COMMON_PARAMETER_KEYS, 'common_parameters_shape_invalid'); v._json(parameters)
    for key in v.COMMON_PARAMETER_KEYS:
        c.sequence(parameters[key], stored=True)
    for key in ('original_coverage_population_ids', 'composition_population_ids'):
        c.strings(parameters[key])
    for row in parameters['alignment_requests']:
        v._shape(row, ('population_id', 'alphabet', 'case_policy', 'pairs'), 'alignment_request_shape_invalid'); c.text(row['population_id'])
        v._require(row['alphabet'] in ('dna', 'rna', 'protein', 'unknown') and row['case_policy'] in ('uppercase', 'literal'), 'alignment_request_invalid'); c.sequence(row['pairs'], stored=True)
    for row in parameters['tree_requests']:
        v._shape(row, ('population_id', 'branch_unit', 'pairs'), 'tree_request_shape_invalid'); c.text(row['population_id']); c.sequence(row['pairs'], stored=True)
        v._require(row['branch_unit'] in c.BRANCH_UNITS, 'tree_request_unit_invalid')
    for row in parameters['bootstrap_requests']:
        v._shape(row, ('reference_tree_id', 'replicate_population_id', 'tip_join', 'method'), 'bootstrap_request_shape_invalid'); c.text(row['reference_tree_id']); c.text(row['replicate_population_id'])
        v._require(row['method'] in ('rapid_bootstrap', 'rell_bootstrap'), 'bootstrap_request_method_invalid')
    for row in parameters['taxon_requests']:
        v._shape(row, ('population_id', 'rank'), 'taxon_request_shape_invalid'); c.text(row['population_id']); c.text(row['rank'])
    for row in parameters['comparisons']:
        v._shape(row, ('comparison_id', 'gene_tree_id', 'organismal_tree_id', 'tip_pairs'), 'comparison_request_shape_invalid')
        for key in ('comparison_id', 'gene_tree_id', 'organismal_tree_id'):
            c.text(row[key])
        c.sequence(row['tip_pairs'], stored=True)
    for key, identity in (('alignment_requests', 'population_id'), ('tree_requests', 'population_id'), ('comparisons', 'comparison_id')):
        v._unique(parameters[key], identity)
    for key in ('taxon_requests', 'bootstrap_requests'):
        v._require(len({repr(row) for row in parameters[key]}) == len(parameters[key]), 'duplicate_calculation_request')


def _coverage(sheet, alignment, population, members):
    supplied = []
    seen = set()
    for join in sheet['joins']['input_rows']:
        if join['alignment_id'] != alignment['alignment_id'] or join['row_index'] not in population['row_indices']:
            continue
        key = join['row_index'], join['input_binding_id'], join['member_id']
        if key in seen:
            continue
        seen.add(key); fact = members[(join['input_binding_id'], join['member_id'])]
        supplied.append({'row': {'alignment_id': alignment['alignment_id'], 'row_index': join['row_index']},
            'member': {'input_binding_id': join['input_binding_id'], 'member_id': join['member_id']},
            'original_length': fact['length'], 'original_sequence_sha256': fact['sequence_sha256'],
            'evidence': ([deepcopy(fact['evidence'])] if fact['evidence'] is not None else []) + deepcopy(join['evidence'])})
    missing_rows = set(population['row_indices']) - {r['row']['row_index'] for r in supplied}
    if missing_rows:
        requirement = c.requirement(c.scope(population['population_id']), 'original_residue_map_required', source_refs=[alignment['artifact']['source_ref']])
        # The member is unknown; inventing a MemberRef merely to fill a row
        # would assert an unsupported biological association.
        return {'population_id': population['population_id'], 'alignment_id': alignment['alignment_id'], 'rows': [],
                'missing_requirements': [requirement], 'diagnostics': [c.diagnostic('original_member_associations_incomplete')]}
    correspondences = deepcopy([row for row in sheet['joins']['residues'] if row['alignment_id'] == alignment['alignment_id'] and row['row_index'] in population['row_indices']])
    incomplete = False
    for row in correspondences:
        interval, member = row['original_interval_0based_half_open'], row['original_member']
        if interval is None or member is None:
            continue
        fact = members[(member['input_binding_id'], member['member_id'])]
        unknown = fact['molecule'] in (None, 'unknown', 'mixed')
        if fact['molecule'] in ('dna', 'rna'):
            unknown |= row['strand'] == 'unknown'
        if interval[1] - interval[0] == 3:
            unknown |= row['translation_table'] is None or row['transformation_id'] is None
        if unknown:
            # The original asserted interval remains in the saved sheet. It
            # cannot establish validated coverage under unknown molecular units.
            row['original_interval_0based_half_open'] = None; incomplete = True
    result = calc.original_member_coverage(alignment, population=population, members=tuple(supplied), correspondences=tuple(correspondences))
    if incomplete:
        result['diagnostics'].append({'code': 'bvbrc_phylogeny_original_coordinate_metadata_incomplete', 'phase': 'association',
            'path': '/joins/residues', 'severity': 'qualification', 'evidence_refs': [alignment['artifact']['source_ref']]})
    return result


def _bootstrap_method_evidenced(sheet, request, reference):
    # An explicit method request cannot rename an unknown native experiment.
    methods = {r['method'] for r in sheet['support_observations'] if r['tree_id'] == reference['tree_id'] and r['method'] != 'native_unknown'}
    if methods:
        return None if methods == {request['method']} else 'bootstrap_method_conflict'
    analysis = sheet['documents']['analyses'][0]
    selected_trees = {analysis[k] for k in analysis if k.endswith('tree_id') and analysis[k] is not None}
    if reference['tree_id'] not in selected_trees or not analysis['output_role_evidence']:
        return 'bootstrap_method_unresolved'
    linked = [r for r in sheet['read_outcomes'] if r['reader']['reader'] == 'raxml_run_log' and r['status'] != 'invalid' and set(r['observation_ids']) & set(analysis['native_engine_observation_ids'])]
    commands = {r['command_id']: r for r in sheet['observed_run']['commands']}
    expected_mode = 'a' if request['method'] == 'rapid_bootstrap' else 'D'
    modes = set()
    for engine in sheet['observed_run']['engines']:
        if engine['name'] != 'raxml' or engine['version'] is None or not (engine['version_location'] or engine['version_evidence']):
            continue
        for cid in engine['command_ids']:
            command = commands[cid]; argv = command['argv']
            if command['origin'] == 'observed' and command['role'] in ('inference', 'bootstrap') and argv and command['location'] is not None and any(command['location']['artifact'] == r['artifact'] for r in linked):
                modes |= {argv[i + 1] for i, token in enumerate(argv[:-1]) if token == '-f' and argv[i + 1] in ('a', 'D')}
    if modes == {expected_mode}:
        return None
    return 'bootstrap_method_conflict' if modes else 'bootstrap_method_unresolved'


def _bootstrap_join(request, reference, population, trees):
    """Reject identity contradictions even when method metadata is missing."""
    join = request['tip_join']; v._shape(join, ('reference_tree_id', 'mappings'), 'bootstrap_join_shape_invalid')
    v._require(join['reference_tree_id'] == reference['tree_id'], 'bootstrap_reference_conflict')
    c.sequence(join['mappings'], stored=True); seen = set()
    reference_tips = {n['node_index'] for n in reference['nodes'] if not n['child_indices']}
    for mapping in join['mappings']:
        v._shape(mapping, ('replicate_tree_id', 'pairs'), 'bootstrap_mapping_shape_invalid')
        tid = mapping['replicate_tree_id']; c.text(tid)
        v._require(tid in population['tree_ids'] and tid not in seen, 'bootstrap_mapping_identity_conflict'); seen.add(tid)
        c.sequence(mapping['pairs'], stored=True); left, right = set(), set()
        replicate_tips = {n['node_index'] for n in trees[tid]['nodes'] if not n['child_indices']}
        for pair in mapping['pairs']:
            v._shape(pair, ('reference_node_index', 'replicate_node_index'), 'bootstrap_pair_shape_invalid')
            a, b = pair['reference_node_index'], pair['replicate_node_index']; c.integer(a); c.integer(b)
            v._require(a in reference_tips and b in replicate_tips, 'bootstrap_terminal_reference_conflict')
            v._require(a not in left and b not in right, 'bootstrap_join_not_injective'); left.add(a); right.add(b)


def _alignment_alphabet(sheet, population, requested, index):
    """Resolve a homogeneous alphabet from exact supplied scientific context.

    A calculation parameter never supplies this context. The sheet contains
    one primary analysis, so its observed settings apply only to that primary
    alignment. Exact partition columns and checked input-member joins can
    independently establish the selected population's molecular unit.
    """
    if requested == 'unknown':
        return 'unknown', None
    aid = population['alignment_id']; analysis = index['analysis']
    primary = analysis.get('aligned_document_id', analysis.get('final_alignment_id'))
    settings = {r['value'] for r in sheet['observed_run']['settings']
                if aid == primary and r['name'] == 'alphabet' and r['origin'] == 'observed'
                and r['value'] is not None and (r['location'] is not None or r['evidence'])}
    if len(settings) > 1:
        return 'unknown', 'observed_alphabet_conflict'
    interpretations = set(settings) - {'unknown', 'mixed'}
    mixed = 'mixed' in settings
    partition_id = analysis.get('partition_document_id')
    if aid == primary and partition_id is not None:
        document = index['documents'][partition_id]
        selected = set(population['columns_0based']); covered = set(); partition_types = set(); overlap = set()
        protein_models = {'DAYHOFF', 'DCMUT', 'JTT', 'MTREV', 'WAG', 'RTREV', 'CPREV', 'VT', 'BLOSUM62',
                          'MTMAM', 'LG', 'MTART', 'MTZOA', 'PMB', 'HIVB', 'HIVW', 'JTTDCMUT', 'FLU',
                          'STMTREV', 'LG4M', 'LG4X'}
        for partition in document['partitions']:
            cols = selected & set(partition['columns_0based'])
            if not cols:
                continue
            overlap |= covered & cols; covered |= cols
            token = partition['model_token']
            if token in ('DNA', 'RNA'):
                partition_types.add(token.lower())
            elif token in protein_models or token.endswith('F') and token[:-1] in protein_models:
                partition_types.add('protein')
            else:
                partition_types.add('unknown')
        if document['completeness'] == 'complete' and selected and covered == selected and not overlap:
            if len(partition_types) == 1 and 'unknown' not in partition_types:
                interpretations |= partition_types
                mixed = False  # Exact homogeneous selection of a mixed matrix.
            elif len(partition_types - {'unknown'}) > 1:
                mixed = True
    selected_rows = set(population['row_indices'])
    row_types = {}
    transforms = {t['transformation_id']: t for t in sheet['joins']['transformations']}
    for row in sheet['joins']['input_rows']:
        if row['alignment_id'] != aid or row['row_index'] not in selected_rows:
            continue
        member = index['members'][(row['input_binding_id'], row['member_id'])]
        transform = transforms.get(row['transformation_id'])
        same_unit = transform is None or transform['kind'] in ('header_tokenization', 'duplicate_suffix', 'amino_acid_J_to_X', 'selected_segment', 'end_trim', 'concatenate')
        if member['evidence'] is not None and row['evidence'] and same_unit and member['molecule'] in ('dna', 'rna', 'protein'):
            row_types.setdefault(row['row_index'], set()).add(member['molecule'])
        else:
            row_types.setdefault(row['row_index'], set()).add('unknown')
    if selected_rows and set(row_types) == selected_rows:
        member_types = set().union(*row_types.values())
        if len(member_types) == 1 and 'unknown' not in member_types:
            interpretations |= member_types
        elif len(member_types - {'unknown'}) > 1:
            mixed = True
    if len(interpretations) > 1:
        return 'unknown', 'observed_alphabet_conflict'
    if not mixed and interpretations == {requested}:
        return requested, None
    return 'unknown', 'requested_alphabet_unverified'


def calculate_common_components(sheet: dict, *, provider: Literal['gene_tree', 'codon_tree'], parameters: dict) -> dict:
    """Call the eight installed calculators on exact selected saved operands."""
    common = validate_shared_fields(sheet, provider=provider); _parameters(parameters)
    # Source anchors and every assignment were checked above, before filtering.
    index = v._validate_common(common, provider)
    populations = {kind: {p['population_id']: p for p in common['populations'][kind]} for kind in v.POPULATION_KEYS}
    alignments, trees = index['alignments'], index['trees']
    result = {key: [] for key in v.COMMON_COMPONENT_KEYS}
    result['diagnostics'] = deepcopy(common['qualifications'])
    requirements = deepcopy(common['missing_requirements']); coordinate_rows = {}

    def population(kind, pid):
        v._require(pid in populations[kind], 'requested_population_unknown')
        return populations[kind][pid]

    def retain(field, component):
        nonlocal requirements
        result[field].append(component)
        # Do not feed provider diagnostics/requirements into a shared-family
        # helper whose reason vocabulary is intentionally narrower.
        requirements = _merge_requirements(requirements, calc.calculation_requirements(component))
        result['diagnostics'].extend(deepcopy(component.get('diagnostics', [])))

    def interpretation_missing(pid, reason, role, sources=(), *, conflict=False):
        nonlocal requirements
        requirement = {'requirement_id': c.scope(pid) + '/' + reason, 'kind': 'scientific_metadata', 'role': role,
                       'source_refs': list(dict.fromkeys(sources)), 'reason_code': reason}
        requirements = _merge_requirements(requirements, [requirement])
        result['diagnostics'].append({'code': 'bvbrc_phylogeny_' + reason, 'phase': 'association', 'path': '',
            'severity': 'error' if conflict else 'qualification', 'evidence_refs': list(dict.fromkeys(sources))})

    for request in parameters['alignment_requests']:
        pop = population('alignments', request['population_id']); alignment = alignments[pop['alignment_id']]
        alphabet, diagnostic = _alignment_alphabet(common, pop, request['alphabet'], index)
        if diagnostic is not None:
            result['diagnostics'].append({'code': 'bvbrc_phylogeny_' + diagnostic, 'phase': 'association',
                'path': '/populations/alignments/' + str(list(populations['alignments']).index(pop['population_id'])),
                'severity': 'qualification', 'evidence_refs': [alignment['artifact']['source_ref']]})
        retain('alignments', calc.alignment_components(alignment, population=pop, alphabet=alphabet, case_policy=request['case_policy'], pairs=tuple(tuple(p) for p in request['pairs'])))
        for row in calc.ungapped_coordinate_map(alignment, row_indices=tuple(pop['row_indices'])):
            coordinate_rows[(row['alignment_id'], row['row_index'], row['column_0based'])] = row
    for pid in parameters['original_coverage_population_ids']:
        pop = population('alignments', pid); alignment = alignments[pop['alignment_id']]
        retain('original_coverage', _coverage(common, alignment, pop, index['members']))
        for row in calc.ungapped_coordinate_map(alignment, row_indices=tuple(pop['row_indices'])):
            coordinate_rows[(row['alignment_id'], row['row_index'], row['column_0based'])] = row
    for request in parameters['tree_requests']:
        pop = population('leaves', request['population_id']); tree = trees[pop['tree_id']]
        native = [o for o in common['native_measurements'] if o['subject_id'] is not None and o['subject_id'].startswith(tree['tree_id'] + '/node/')]
        known = {o['unit'] for o in native if o['field'] == 'branch_length' and o['unit'] != 'native_unknown'}
        branch_unit = request['branch_unit']
        if request['branch_unit'] != 'native_unknown':
            if known != {request['branch_unit']} or any(o['unit'] == 'native_unknown' for o in native if o['field'] == 'branch_length'):
                conflict = bool(known - {request['branch_unit']})
                interpretation_missing(pop['population_id'], 'branch_unit_conflict' if conflict else 'branch_unit_unresolved', 'branch_model_units', [tree['source_location']['artifact']['source_ref']], conflict=conflict)
                branch_unit = 'native_unknown'
        support = [o for o in common['support_observations'] if o['tree_id'] == tree['tree_id'] and o['node_index'] != tree['root_node_index']]
        component = calc.tree_components(tree, leaf_population=pop, support_observations=tuple(support), native_measurements=tuple(native), branch_unit=branch_unit, pairs=tuple(tuple(p) for p in request['pairs']))
        retain('trees', component)
        raw_required = [r['requirement_id'] for r in common['missing_requirements'] if r['reason_code'] == 'raw_tree_required_for_branch_facts' and r['requirement_id'] == c.scope(tree['tree_id']) + '/raw_tree_required_for_branch_facts']
        if tree['source_format'] == 'phyloxml' and raw_required:
            # The original extraction explicitly required raw-tree branch
            # facts. XML-native observations remain saved, topology usable.
            quantities = [component['branch_length_sum'], component['known_branch_length_sum']]
            quantities += [quantity for row in component['branches'] for quantity in (row['length'], row['support_rescaled'])]
            quantities += [row['value'] for row in component['distances']]
            for quantity in quantities:
                quantity.update(value=None, state='missing', numerator=None, denominator=None)
                quantity['requirement_ids'] = list(dict.fromkeys(quantity['requirement_ids'] + raw_required))
    for request in parameters['bootstrap_requests']:
        v._require(request['reference_tree_id'] in trees, 'bootstrap_reference_unknown'); reference = trees[request['reference_tree_id']]
        pop = population('bootstraps', request['replicate_population_id']); _bootstrap_join(request, reference, pop, trees)
        missing_method = _bootstrap_method_evidenced(common, request, reference)
        if missing_method is not None:
            interpretation_missing(pop['population_id'], missing_method, 'bootstrap_method', [reference['source_location']['artifact']['source_ref']], conflict=missing_method.endswith('_conflict'))
            continue
        retain('bootstrap', calc.bootstrap_split_frequencies(reference, replicates=tuple(trees[tid] for tid in pop['tree_ids']), replicate_population=pop, tip_join=request['tip_join'], method=request['method']))
    for pid in parameters['composition_population_ids']:
        pop = population('composition', pid); subjects = {tuple(s[k] for k in ('kind', 'id', 'source_record_id')) for s in pop['member_subjects']}
        assignments = [r for r in common['joins']['functions'] if tuple(r['subject'][k] for k in ('kind', 'id', 'source_record_id')) in subjects]
        retain('composition', calc.function_composition(population=pop, assignments=tuple(assignments), equivalences=tuple(common['joins']['function_equivalences'])))
    for request in parameters['taxon_requests']:
        pop = population('taxonomy', request['population_id']); subjects = {tuple(s[k] for k in ('kind', 'id', 'source_record_id')) for s in pop['member_subjects']}
        assignments = [r for r in common['joins']['taxa'] if tuple(r['subject'][k] for k in ('kind', 'id', 'source_record_id')) in subjects]
        retain('taxonomy', calc.taxon_components(population=pop, rank=request['rank'], assignments=tuple(assignments)))
    for request in parameters['comparisons']:
        v._require(request['gene_tree_id'] in trees and request['organismal_tree_id'] in trees, 'comparison_tree_unknown')
        supplied = [row for row in common['joins']['organismal_tips'] if row['gene_tree_id'] == request['gene_tree_id'] and row['organismal_tree_id'] == request['organismal_tree_id']]
        v._require(len(request['tip_pairs']) == len(supplied) and all(row in supplied for row in request['tip_pairs']), 'comparison_join_not_supplied')
        retain('comparisons', calc.compare_unrooted_relationships(trees[request['gene_tree_id']], comparison_id=request['comparison_id'], organismal_tree=trees[request['organismal_tree_id']], injective_tip_join=tuple(request['tip_pairs'])))
    result['coordinate_maps'] = list(coordinate_rows.values()); result['missing_requirements'] = _merge_requirements(requirements)
    return deepcopy(result)


__all__ = ['calculate_common_components']
