"""Closed commissioning and finite saved-fact contracts for MSA and MetaCATS.

These schemas describe ordinary supplied records, not an expression language.
No parser, calculator, acquisition or resource selection runs during validation.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
from urllib.parse import quote, unquote

from .bvbrc_appservice_contracts import _Validator, _finite_json, _same, contract_schema

VERSION = 'bvbrc_alignment_bundle_parameters_v1'
PROVIDERS = ('msa', 'metacats')
RESERVED = ('@families', '@requirements')
REFERENCE_KINDS = ('field', 'alignment', 'member', 'population', 'category', 'group',
    'tree', 'split', 'function', 'taxon', 'comparison', 'test', 'family', 'method',
    'transformation', 'role', 'requirement', 'reason', 'xmfa_document', 'xmfa_file', 'xmfa_record')
MSA_MODES = ('ordinary_new_alignment', 'ordinary_prealigned', 'segment_alignment',
    'segment_concatenation', 'mauve_first_block_projection', 'mauve_blocks')
METACATS_MODES = ('files', 'groups', 'auto')
STATES = ('available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible')
COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')
BRANCH_UNITS = ('expected_substitutions_per_model_site', 'joint_mixed_partition_model_site', 'native_unknown')
SUPPORT_SCALES = ('fraction', 'percent', 'statistic', 'native_unknown')
DIFFERENCE_CATEGORIES = ('identical_canonical', 'substitution', 'insertion_relative_to_reference',
    'deletion_relative_to_reference', 'both_gap', 'ambiguous_or_other')
SUPPLIED_ROLES = ('observed_run', 'common_associations', 'function_assignments',
    'taxonomy_assignments', 'msa_context', 'metacats_context', 'xmfa_sources')
ROLE_READERS = {
    'original_sequences': ('aligned_fasta', 'metacats_input_fasta'),
    'staged_sequences': ('aligned_fasta', 'metacats_input_fasta'),
    'alignment': ('aligned_fasta', 'metacats_input_fasta'),
    'msa_frequency': ('msa_frequency',), 'consensus': ('aligned_fasta',),
    'tree': ('newick',), 'organismal_tree': ('newick',),
    'full_xmfa': ('mauve_xmfa_v1', None), 'xmfa_staged_source': (None,),
    'metadata': ('metacats_metadata',), 'adjusted_matrix': ('metacats_adjusted_matrix',),
    'chisq_export': ('metacats_chisq',), 'pair_export': ('metacats_pair',),
    'raw_r_omnibus': ('metacats_raw_r',), 'raw_r_pairwise': ('metacats_raw_r',),
    'native_run_evidence': (None,),
}


def require(condition, code='shape_invalid'):
    if not condition:
        raise ValueError('bvbrc_alignment_bundle_' + code)


def _object(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def _enum(*values):
    return {'enum': list(values)}


def _array(item, *, unique=False, minimum=0):
    result = {'type': 'array', 'items': item, 'minItems': minimum}
    if unique:
        result['uniqueItems'] = True
    return result


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _union(*schemas):
    return {'oneOf': list(schemas)}


def _pair(item):
    return {'type': 'array', 'items': item, 'minItems': 2, 'maxItems': 2}


ID = {'type': 'string', 'minLength': 1}
TEXT = {'type': 'string'}
INDEX = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
NUMBER = {'type': 'number'}
BOOL = {'type': 'boolean'}
N = _nullable(NUMBER)
I = _nullable(INDEX)
IDS = _array(ID, unique=True)
INDICES = _array(INDEX, unique=True)
SLOT = _object(analysis_id=ID, slot_id=ID)
TREE = _object(analysis_id=ID, slot_id=ID, tree_index=INDEX)
MEMBER = _object(input_binding_id=ID, member_id=ID)
SUBJECT = _object(kind=_enum('input_member', 'feature', 'genome'), id=ID, source_record_id=ID)
CONTENT = _object(source_ref=ID, artifact_field=_enum('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref'),
    artifact_ref=ID, sha256={'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, byte_count=INDEX)
EVIDENCE = _object(content=CONTENT, pointer={'type': 'string', 'pattern': r'^(?:/(?:[^~]|~[01])*)?$'})
EVIDENCES = _array(EVIDENCE)
CELL_REF = _object(block_index=INDEX, record_index=INDEX, column_0based=INDEX)
QUERY = _object(member_number=POSITIVE, position_0based=INDEX)
TEST = _object(category_id=ID, column_0based=INDEX, kind=_enum('omnibus', 'pairwise'), group_ids=_array(ID, unique=True, minimum=2))
SCOPED_TEST = _object(analysis_id=ID, test=TEST)
REQUEST_REF = _object(analysis_id=ID, request_id=ID)
REFERENCE = _object(alignment_id=SLOT, row_index=INDEX, original_member=_nullable(MEMBER),
    native_ref_type=ID, native_ref_string=_nullable(TEXT), identity_state=_enum('resolved', 'unresolved'), evidence=EVIDENCES)
TIP_JOIN = _object(gene_tree_id=TREE, gene_node_index=INDEX, organismal_tree_id=TREE,
    organismal_node_index=INDEX, subject=SUBJECT, evidence=EVIDENCES)
XMFA_SELECTION = _object(population_id=ID, document_id=SLOT,
    block_columns=_array(_object(block_index=INDEX, columns_0based=INDICES)),
    member_numbers=_array(POSITIVE, unique=True), completeness=_enum(*COMPLETENESS), evidence=EVIDENCES)


def _check(schema, value, code='shape_invalid'):
    _finite_json(value)
    require(_Validator(schema).is_valid(value), code)
    return deepcopy(value)


def _provider(provider):
    require(provider in PROVIDERS, 'provider_invalid')


def encode_reference(kind: str, analysis_id: str, identifier: str) -> str:
    require(kind in REFERENCE_KINDS and type(analysis_id) is str and bool(analysis_id)
        and type(identifier) is str and bool(identifier), 'reference_invalid')
    require(kind not in ('requirement', 'reason') or analysis_id == '@requirements', 'reference_scope_invalid')
    try:
        return 'bvbrc_alignment_' + kind + ':' + quote(analysis_id, safe='') + '/' + quote(identifier, safe='')
    except UnicodeError as exc:
        raise ValueError('bvbrc_alignment_bundle_reference_invalid') from exc


def decode_reference(reference: str) -> tuple[str, str, str]:
    require(type(reference) is str and reference.startswith('bvbrc_alignment_'), 'reference_invalid')
    prefix, separator, rest = reference.partition(':')
    parts = rest.split('/')
    require(separator and len(parts) == 2, 'reference_invalid')
    try:
        kind = prefix.removeprefix('bvbrc_alignment_')
        aid, identity = (unquote(part, encoding='utf-8', errors='strict') for part in parts)
    except UnicodeError as exc:
        raise ValueError('bvbrc_alignment_bundle_reference_invalid') from exc
    require(encode_reference(kind, aid, identity) == reference, 'reference_noncanonical')
    return kind, aid, identity


def _reader_schemas(provider):
    encoding = _enum('ascii', 'utf-8')
    result = {'aligned_fasta': _object(reader=_enum('aligned_fasta'), id_rule=_enum('first_whitespace_token'), encoding=encoding)}
    if provider == 'msa':
        result.update(msa_frequency=_object(reader=_enum('msa_frequency'), alphabet=_enum('dna', 'protein'),
            layout=_enum('current_without_reference', 'current_with_reference'), encoding=encoding),
            newick=_object(reader=_enum('newick'), dialect=_enum('newick', 'raxml_branch_labels', 'bvbrc_double_quoted_names'), allow_multiple=BOOL),
            mauve_xmfa_v1=_object(reader=_enum('mauve_xmfa_v1'), dialect=_enum('mauve1'), alphabet=_enum('dna'), encoding=encoding))
    else:
        result.update(metacats_input_fasta=_object(reader=_enum('metacats_input_fasta'), id_rule=_enum('first_whitespace_token'), encoding=encoding),
            metacats_chisq=_object(reader=_enum('metacats_chisq'), layout=_enum('current_filtered_tsv', 'legacy_example_tsv'), category_id=ID, encoding=encoding),
            metacats_pair=_object(reader=_enum('metacats_pair'), layout=_enum('current_filtered_tsv'), category_id=ID, encoding=encoding),
            metacats_raw_r=_object(reader=_enum('metacats_raw_r'), kind=_enum('omnibus', 'pairwise'), layout=_enum('r_write_table_single_result_string'), category_id=ID, encoding=encoding),
            metacats_metadata=_object(reader=_enum('metacats_metadata'), delimiter=_enum('tab'), header=_enum('present', 'absent'), encoding=encoding),
            metacats_adjusted_matrix=_object(reader=_enum('metacats_adjusted_matrix'), category_id=ID, encoding=encoding))
    return result


def _composition(unit):
    return _object(population_id=ID, unit=_enum(*unit), member_subjects=_array(SUBJECT, unique=True),
        assignment_completeness=_enum(*COMPLETENESS), membership_completeness=_enum(*COMPLETENESS), evidence=EVIDENCES)


def _family(scoped=False):
    return _object(family_id=ID, analysis_ids=_array(ID, unique=True, minimum=1), category_ids=_array(ID, unique=True, minimum=1),
        test_kind=_enum('omnibus', 'pairwise'), eligibility=_enum('variable_site_positive_df'),
        population_state=_enum('complete', 'known_count_only', 'declared_upper_bound', 'unknown'), total_test_count=I,
        assumption=_nullable(_object(kind=_enum('independently_known_count', 'parent_declared_upper_bound'), count=INDEX, evidence=EVIDENCES)),
        p_value_basis=_enum('native_unadjusted', 'source_mathematical_recalculation', 'biological_mathematical_recalculation'),
        evidence=EVIDENCES, selection=_enum('all_eligible', 'explicit_tests'), tests=_array(SCOPED_TEST if scoped else TEST, unique=True))


MULTIPLICITY_FIELDS = {'method': _enum('none', 'bonferroni', 'holm', 'bh', 'by'),
    'alpha': {'type': 'number', 'minimum': 0, 'maximum': 1},
    'dependence_assumption': _enum('none_required_between_tests', 'independent_or_positive_regression_dependence_assumed')}


def _request_schemas(provider):
    fields = {
        'alignment': dict(population_id=ID, alphabet=_enum('dna', 'rna', 'protein', 'unknown'), case_policy=_enum('uppercase', 'literal'), pairs=_array(_pair(INDEX), unique=True)),
        'ungapped_map': dict(alignment_id=SLOT, row_indices=INDICES),
        'original_coverage': dict(population_id=ID), 'function_composition': dict(population_id=ID),
        'taxonomy': dict(population_id=ID, rank=ID),
    }
    if provider == 'msa':
        fields.update(tree=dict(population_id=ID, branch_unit=_enum(*BRANCH_UNITS), pairs=_array(_pair(INDEX), unique=True)),
            relationship_comparison=dict(comparison_id=ID, gene_tree_id=TREE, organismal_tree_id=TREE, injective_tip_join=_array(TIP_JOIN)),
            msa_entropy=dict(population_id=ID, alphabet=_enum('dna', 'protein'), case_policy=_enum('uppercase'), terminal_gap=_enum('-'), observed_table_id=_nullable(SLOT), native_rounding=_enum('binary64_fixed_2_ties_to_even', None)),
            msa_reference_differences=dict(population_id=ID, reference=REFERENCE, member_row_indices=INDICES, alphabet=_enum('dna', 'protein'), case_policy=_enum('preserve', 'uppercase')),
            xmfa_column_coordinates=dict(document_id=SLOT, cells=_array(CELL_REF, unique=True), use_source_bindings=BOOL),
            xmfa_source_positions=dict(document_id=SLOT, queries=_array(QUERY, unique=True), use_source_bindings=BOOL),
            xmfa_alignment_components=dict(document_id=SLOT, selection=XMFA_SELECTION, selected_pairs=_array(_pair(POSITIVE), unique=True), case_policy=_enum('preserve', 'uppercase')),
            xmfa_interval_coverage=dict(document_id=SLOT, selection=XMFA_SELECTION, use_source_bindings=BOOL, basis=_enum('represented', 'multi_member_block', 'cooccupied_column')))
    else:
        statistics = dict(counts_request_id=ID, alphabet=_enum('na', 'aa'), epsilon={'type': 'number', 'minimum': 0},
            nucleotide_padding=_enum('ACGT_at_variable_sites'), omnibus_continuity=_enum('r_default_2x2_min_delta'),
            selected_pairs=_array(_pair(ID), unique=True), distribution_backend=_object(name=_enum('scipy_chi2_integer_df_logtail_v1'), version=ID))
        fields.update(native_group_counts=dict(population_id=ID, category_id=ID, case_policy=_enum('preserve', 'uppercase'), terminal_mask=_enum('native_terminal_dash_to_hash'), native_input_hash_policy=_enum('exclude_hash')),
            biological_group_counts=dict(population_id=ID, category_id=ID, group_population_id=ID, case_policy=_enum('preserve', 'uppercase'), terminal_gap_policy=_enum('exclude_terminal_dash'), original_hash_policy=_enum('exclude_hash')),
            native_statistics={**statistics, 'pair_df_policy': _enum('native_source', 'standard_pair'), 'pair_zero_policy': _enum('retain_math_and_native_zero_to_one')},
            biological_statistics={**statistics, 'pair_df_policy': _enum('standard_pair')},
            native_effects=dict(counts_request_id=ID, selected_pairs=_array(_pair(ID), unique=True), zero_margin_policy=_enum('drop_for_raw_effect_only')),
            biological_effects=dict(counts_request_id=ID, selected_pairs=_array(_pair(ID), unique=True), zero_margin_policy=_enum('drop_for_raw_effect_only')),
            expected_adequacy=dict(statistics_request_id=ID, statistics_kind=_enum('native_reproduction', 'biological')),
            multiplicity=dict(family=_family(), p_values=_union(
                _object(kind=_enum('statistical_results'), statistics_request_ids=_array(ID, unique=True, minimum=1), field=_enum('mathematical_p')),
                _object(kind=_enum('native_tables'), table_ids=_array(SLOT, unique=True, minimum=1), eligibility_statistics_request_ids=IDS)), **MULTIPLICITY_FIELDS))
    return {kind: _object(kind=_enum(kind), request_id=ID, **body) for kind, body in fields.items()}


def parameters_schema(*, provider: str) -> dict:
    _provider(provider)
    readers = _reader_schemas(provider)
    roles = [role for role, names in ROLE_READERS.items() if any(n in readers for n in names) or role == 'native_run_evidence'
        or provider == 'msa' and role in ('full_xmfa', 'xmfa_staged_source')]
    sources = _union(_object(kind=_enum('acquired_role'), bundle_role=ID),
        _object(kind=_enum('supplied_content'), content=CONTENT),
        _object(kind=_enum('original_input'), input_binding_id=ID, content=CONTENT))
    slots = []
    for role in roles:
        variants = [readers[r] for r in ROLE_READERS[role] if r in readers]
        if None in ROLE_READERS[role]:
            variants.append({'type': 'null'})
        slots.append(_object(analysis_id=ID, slot_id=ID, semantic_role=_enum(role), source=sources, reader=_union(*variants)))
    if provider == 'msa':
        analysis = _object(analysis_id=ID, mode=_enum(*MSA_MODES), alignment_id=_nullable(SLOT), frequency_table_id=_nullable(SLOT),
            consensus_alignment_id=_nullable(SLOT), tree_id=_nullable(TREE), full_xmfa_slot_id=_nullable(ID), xmfa_document_id=_nullable(SLOT),
            segment_ids=IDS, reference=_nullable(REFERENCE), output_role_evidence=EVIDENCES)
    else:
        analysis = _object(analysis_id=ID, mode=_enum(*METACATS_MODES), alignment_id=_nullable(SLOT), metadata_document_id=_nullable(SLOT),
            category_ids=IDS, adjusted_matrix_ids=_array(SLOT, unique=True), chisq_table_ids=_array(SLOT, unique=True),
            pair_table_ids=_array(SLOT, unique=True), raw_r_table_ids=_array(SLOT, unique=True), output_role_evidence=EVIDENCES)
    populations = [_object(kind=_enum('whole_alignment'), population_id=ID, alignment=SLOT),
        _object(kind=_enum('alignment_subset'), population_id=ID, alignment=SLOT, row_indices=INDICES, columns_0based=INDICES,
            completeness=_enum(*COMPLETENESS), evidence=EVIDENCES),
        _object(kind=_enum('composition'), population=_composition(('sequence_member', 'feature'))),
        _object(kind=_enum('taxonomy'), population=_composition(('sequence_member', 'feature', 'genome')))]
    if provider == 'msa':
        populations.append(_object(kind=_enum('whole_tree'), population_id=ID, tree=TREE))
    supplied = [r for r in SUPPLIED_ROLES if r != ('metacats_context' if provider == 'msa' else 'msa_context') and (provider == 'msa' or r != 'xmfa_sources')]
    plan = _object(analysis=analysis, population_plans=_array(_union(*populations)),
        scientific_inputs=_array(_object(role=_enum(*supplied), evidence=EVIDENCE)),
        read_parameters=_object(source_dialect=_enum('retained_bvbrc_' + provider)),
        calculation_parameters=_object(version=_enum('bvbrc_' + provider + '_components_v1'), requests=_array(_union(*_request_schemas(provider).values()))))
    cross = _object(family_request_id=ID, family=_family(scoped=True), p_values=_union(
        _object(kind=_enum('statistical_results'), requests=_array(REQUEST_REF, unique=True, minimum=1), field=_enum('mathematical_p')),
        _object(kind=_enum('native_tables'), tables=_array(SLOT, unique=True, minimum=1), eligibility_statistics_requests=_array(REQUEST_REF, unique=True))), **MULTIPLICITY_FIELDS)
    return deepcopy(_object(version=_enum(VERSION), artifact_selection=_array(_union(*slots)), analyses=_array(plan, minimum=1),
        multiplicity_families=_array(cross) if provider == 'metacats' else {'type': 'array', 'items': cross, 'maxItems': 0}))


def _refs_in_request(request):
    """Only declared request paths; never search arbitrary dictionaries."""
    kind = request['kind']; result = []
    for key in ('alignment_id', 'observed_table_id', 'document_id'):
        if key in request and request[key] is not None:
            result.append((request[key], False))
    if kind == 'msa_reference_differences':
        result.append((request['reference']['alignment_id'], False))
    if kind == 'relationship_comparison':
        result += [(request[k], True) for k in ('gene_tree_id', 'organismal_tree_id')]
        result += [(join[k], True) for join in request['injective_tip_join'] for k in ('gene_tree_id', 'organismal_tree_id')]
    if kind.startswith('xmfa_') and 'selection' in request:
        result.append((request['selection']['document_id'], False))
    if kind == 'multiplicity' and request['p_values']['kind'] == 'native_tables':
        result += [(ref, False) for ref in request['p_values']['table_ids']]
    return result


def _request_dependencies(request):
    if 'counts_request_id' in request:
        return [request['counts_request_id']]
    if 'statistics_request_id' in request:
        return [request['statistics_request_id']]
    if request['kind'] == 'multiplicity':
        plan = request['p_values']
        return plan['statistics_request_ids' if plan['kind'] == 'statistical_results' else 'eligibility_statistics_request_ids']
    return []


def _family_relations(family, *, scoped=False):
    require(family['selection'] != 'all_eligible' or not family['tests'], 'all_eligible_with_tests')
    for item in family['tests']:
        row = item['test'] if scoped else item
        require(row['kind'] == family['test_kind'] and row['category_id'] in family['category_ids'], 'family_selector_scope_conflict')
        require(row['kind'] != 'pairwise' or len(row['group_ids']) == 2, 'test_pair_invalid')
        require(not scoped or item['analysis_id'] in family['analysis_ids'], 'family_analysis_scope_conflict')
    assumption = family['assumption']
    state = family['population_state']
    if state == 'complete':
        require(assumption is None, 'complete_family_assumption')
    elif state in ('known_count_only', 'declared_upper_bound'):
        expected = 'independently_known_count' if state == 'known_count_only' else 'parent_declared_upper_bound'
        require(assumption is not None and assumption['kind'] == expected and assumption['evidence'], 'family_assumption_required')
    if assumption is not None:
        require(assumption['count'] == family['total_test_count'], 'family_count_conflict')


def validate_parameters(parameters: dict, *, provider: str) -> dict:
    parameters = _check(parameters_schema(provider=provider), parameters)
    plans = {p['analysis']['analysis_id']: p for p in parameters['analyses']}
    require(len(plans) == len(parameters['analyses']) and not set(plans).intersection(RESERVED), 'analysis_identity_conflict')
    slots = {(s['analysis_id'], s['slot_id']): s for s in parameters['artifact_selection']}
    require(len(slots) == len(parameters['artifact_selection']), 'slot_identity_conflict')
    require(all(aid in plans for aid, _ in slots), 'slot_analysis_unknown')
    def ref(value, aid, tree=False, reader=None):
        require(value['analysis_id'] == aid and (aid, value['slot_id']) in slots, 'slot_reference_unknown')
        selected = slots[(aid, value['slot_id'])]['reader']
        require(not tree or selected is not None and selected['reader'] == 'newick', 'tree_reader_conflict')
        require(reader is None or selected is not None and selected['reader'] in reader, 'slot_reader_conflict')
    for (aid, _), slot in slots.items():
        reader = slot['reader']
        if reader is not None and slot['semantic_role'] in ('raw_r_omnibus', 'raw_r_pairwise'):
            require(reader['kind'] == ('omnibus' if slot['semantic_role'] == 'raw_r_omnibus' else 'pairwise'), 'raw_r_role_conflict')
        if reader is not None and 'category_id' in reader:
            require(reader['category_id'] in plans[aid]['analysis']['category_ids'], 'reader_category_unknown')
    for aid, plan in plans.items():
        analysis = plan['analysis']
        doc_fields = ('alignment_id', 'frequency_table_id', 'consensus_alignment_id', 'xmfa_document_id') if provider == 'msa' else ('alignment_id', 'metadata_document_id')
        for key in doc_fields:
            if analysis[key] is not None:
                ref(analysis[key], aid)
        if provider == 'msa':
            if analysis['tree_id'] is not None:
                ref(analysis['tree_id'], aid, True)
            if analysis['reference'] is not None:
                ref(analysis['reference']['alignment_id'], aid)
                require(analysis['reference']['alignment_id'] == analysis['alignment_id'], 'reference_alignment_conflict')
            if analysis['full_xmfa_slot_id'] is not None:
                require((aid, analysis['full_xmfa_slot_id']) in slots and slots[(aid, analysis['full_xmfa_slot_id'])]['semantic_role'] == 'full_xmfa', 'xmfa_slot_conflict')
            if analysis['xmfa_document_id'] is not None:
                require(analysis['xmfa_document_id']['slot_id'] == analysis['full_xmfa_slot_id'], 'xmfa_document_slot_conflict')
        else:
            for key in ('adjusted_matrix_ids', 'chisq_table_ids', 'pair_table_ids', 'raw_r_table_ids'):
                for value in analysis[key]:
                    ref(value, aid)
        populations = {}
        for population in plan['population_plans']:
            pid = population.get('population_id', population.get('population', {}).get('population_id'))
            require(pid not in populations, 'population_identity_conflict'); populations[pid] = population
            for key in ('alignment', 'tree'):
                if key in population:
                    ref(population[key], aid, key == 'tree')
        roles = [v['role'] for v in plan['scientific_inputs']]
        require(len(roles) == len(set(roles)), 'supplied_role_duplicate')
        requests = {r['request_id']: r for r in plan['calculation_parameters']['requests']}
        require(len(requests) == len(plan['calculation_parameters']['requests']), 'request_identity_conflict')
        for request in requests.values():
            kind = request['kind']
            for operand, tree in _refs_in_request(request):
                ref(operand, aid, tree)
            if 'population_id' in request:
                require(request['population_id'] in populations, 'population_not_declared')
                expected = 'composition' if kind == 'function_composition' else 'taxonomy' if kind == 'taxonomy' else 'whole_tree' if kind == 'tree' else None
                population = populations[request['population_id']]
                require(population['kind'] == expected if expected else population['kind'] in ('whole_alignment', 'alignment_subset'), 'request_population_kind_conflict')
            if kind.startswith('xmfa_'):
                require(analysis['mode'] == 'mauve_blocks', 'xmfa_mode_conflict')
                if 'selection' in request:
                    require(request['selection']['document_id'] == request['document_id'], 'xmfa_selection_conflict')
                    require(len({b['block_index'] for b in request['selection']['block_columns']}) == len(request['selection']['block_columns']), 'xmfa_block_duplicate')
                if 'selected_pairs' in request:
                    pairs = request['selected_pairs']
                    require(all(a != b and a in request['selection']['member_numbers'] and b in request['selection']['member_numbers'] for a,b in pairs) and len({tuple(sorted(p)) for p in pairs}) == len(pairs), 'xmfa_pair_conflict')
            if kind == 'relationship_comparison':
                require(all(j['gene_tree_id'] == request['gene_tree_id'] and j['organismal_tree_id'] == request['organismal_tree_id'] for j in request['injective_tip_join']), 'comparison_tree_conflict')
            if 'category_id' in request:
                require(request['category_id'] in analysis['category_ids'], 'request_category_unknown')
            for dependency in _request_dependencies(request):
                require(dependency in requests, 'dependency_unknown')
                expected = 'native_group_counts' if kind in ('native_statistics', 'native_effects') else 'biological_group_counts' if kind in ('biological_statistics', 'biological_effects') else ('native_statistics' if request.get('statistics_kind') == 'native_reproduction' else 'biological_statistics') if kind == 'expected_adequacy' else ('biological_statistics' if request['family']['p_value_basis'] == 'biological_mathematical_recalculation' else 'native_statistics')
                require(requests[dependency]['kind'] == expected, 'dependency_kind_conflict')
            if kind == 'multiplicity':
                _family_relations(request['family'])
                require(request['family']['analysis_ids'] == [aid] and set(request['family']['category_ids']) <= set(analysis['category_ids']), 'family_scope_conflict')
                require((request['p_values']['kind'] == 'native_tables') == (request['family']['p_value_basis'] == 'native_unadjusted'), 'family_basis_conflict')
        pending, done = set(requests), set()
        while pending:
            ready = {r for r in pending if set(_request_dependencies(requests[r])) <= done}
            require(ready, 'dependency_cycle'); pending -= ready; done |= ready
    families = parameters['multiplicity_families']
    require(len({r['family_request_id'] for r in families}) == len(families), 'family_request_duplicate')
    for row in families:
        family = row['family']; _family_relations(family, scoped=True)
        require(set(family['analysis_ids']) <= set(plans), 'family_analysis_unknown')
        require(set(family['category_ids']) <= {cat for aid in family['analysis_ids'] for cat in plans[aid]['analysis']['category_ids']}, 'family_category_unknown')
        source = row['p_values']; require((source['kind'] == 'native_tables') == (family['p_value_basis'] == 'native_unadjusted'), 'family_basis_conflict')
        if source['kind'] == 'native_tables':
            for operand in source['tables']:
                require(operand['analysis_id'] in family['analysis_ids'], 'family_source_scope_conflict')
                ref(operand, operand['analysis_id'], reader=('metacats_chisq', 'metacats_pair', 'metacats_raw_r'))
        for target in source['requests' if source['kind'] == 'statistical_results' else 'eligibility_statistics_requests']:
            require(target['analysis_id'] in family['analysis_ids'], 'family_source_scope_conflict')
            targets = {r['request_id']: r for r in plans[target['analysis_id']]['calculation_parameters']['requests']}
            expected = 'biological_statistics' if family['p_value_basis'] == 'biological_mathematical_recalculation' else 'native_statistics'
            require(target['request_id'] in targets and targets[target['request_id']]['kind'] == expected, 'family_request_kind_conflict')
    return deepcopy(parameters)


# The finite projection catalog maps each token to its original request kind
# and exact selector. It never interprets an expression or arbitrary path.
MEASUREMENT_CATALOG = {}


def _metrics(kinds, names, selector):
    for name in names.split():
        MEASUREMENT_CATALOG[name] = {'request_kinds': tuple(kinds), 'selector': selector}


_metrics(('alignment',), 'member_count site_count cell_count gap_cells gap_fraction canonical_cells canonical_fraction ambiguity_cells ambiguity_fraction stop_cells stop_fraction other_nongap_cells other_nongap_fraction', _object())
_metrics(('alignment',), 'site_gap_count site_canonical_count site_ambiguity_count site_stop_count site_other_nongap_count site_gap_fraction site_canonical_fraction site_canonical_majority_fraction site_canonical_entropy_bits', _object(column_0based=INDEX))
_metrics(('alignment',), 'row_nongap_count row_matrix_occupancy', _object(row_index=INDEX))
_metrics(('alignment',), 'pair_identical_positions pair_substitutions pair_both_gap_positions pair_a_gap_only_positions pair_b_gap_only_positions pair_unpaired_nongap_ambiguous_positions pair_identity_fraction', _object(row_a=INDEX, row_b=INDEX))
_metrics(('original_coverage',), 'original_length original_covered_positions original_member_coverage', _object(row_index=INDEX, input_binding_id=ID, member_id=ID))
_metrics(('msa_entropy',), 'eligible_count internal_gap_count terminal_gap_excluded_count literal_entropy_bits native_score_recalculated score_residual', _object(column_0based=INDEX))
_metrics(('msa_reference_differences',), 'difference_category_count', _object(row_index=INDEX, category=_enum(*DIFFERENCE_CATEGORIES)))
_metrics(('native_statistics', 'biological_statistics'), 'epsilon augmented_total continuity_delta chi_square df mathematical_p log_p', _object(test=TEST))
_metrics(('native_statistics',), 'native_zero_rule_p', _object(test=TEST))
_metrics(('native_effects', 'biological_effects'), 'raw_chi_square cramers_v raw_minimum_expected raw_cells_below_5 raw_cells_below_1 raw_cell_denominator', _object(column_0based=INDEX))
_metrics(('native_effects', 'biological_effects'), 'total_variation', _object(column_0based=INDEX, group_ids=_pair(ID)))
_metrics(('native_effects', 'biological_effects'), 'frequency_delta', _object(column_0based=INDEX, group_ids=_pair(ID), symbol=TEXT))
_metrics(('expected_adequacy',), 'minimum_expected cells_below_5 cells_below_1 cell_denominator', _object(test=TEST))
_metrics(('function_composition',), 'total_members members_with_recorded_assignment members_without_recorded_assignment', _object())
_metrics(('function_composition',), 'assigned_members fraction_all fraction_recorded', _object(function_key=ID))
_metrics(('taxonomy',), 'known_members unknown_members distinct_known_taxa same_taxon_pairs known_taxon_pairs same_taxon_pair_fraction', _object())
_metrics(('taxonomy',), 'taxon_member_count', _object(taxon_id=ID))
_metrics(('tree',), 'tip_count internal_node_count rooted_representation_polytomies unrooted_degree_polytomies branch_length_sum known_branch_length_sum missing_branch_length_count', _object())
_metrics(('tree',), 'branch_length support_rescaled', _object(node_index=INDEX))
_metrics(('tree',), 'patristic_distance', _object(node_a=INDEX, node_b=INDEX))
_metrics(('relationship_comparison',), 'matched_tips gene_splits organismal_splits shared_splits rf rf_fraction', _object())

XMFA_METRIC_SCHEMA = _union(
    _object(metric=_enum('selected_column_count', 'present_member_count', 'zero_member_count', 'omitted_member_count'), block_index=INDEX),
    _object(metric=_enum('site_present_member_count', 'absent_member_count', 'gap_count', 'nongap_count', 'canonical_count', 'ambiguity_count', 'other_count', 'literal_entropy_bits', 'canonical_entropy_bits', 'canonical_majority_fraction'), block_index=INDEX, column_0based=INDEX),
    _object(metric=_enum('symbol_count'), block_index=INDEX, column_0based=INDEX, symbol=TEXT),
    _object(metric=_enum('identical_canonical', 'substitutions', 'a_only_gap', 'b_only_gap', 'both_gap', 'ambiguous_or_other', 'comparable_canonical', 'identity_fraction'), block_index=INDEX, member_a=POSITIVE, member_b=POSITIVE))
NATIVE_FIELDS = _union(*[_object(kind=_enum(k)) for k in ('score', 'n_sequences', 'chi_square', 'p_value', 'df')],
    _object(kind=_enum('dna_count'), symbol=_enum('A', 'T', 'G', 'C', 'Deletion')),
    _object(kind=_enum('protein_count'), detail_index=INDEX),
    _object(kind=_enum('export_group_count'), heading_index=INDEX, count_index=INDEX),
    _object(kind=_enum('raw_r_group_count'), position_1based=POSITIVE, count_index=INDEX))


def _selection_schemas(provider):
    allowed = set(_request_schemas(provider))
    measurements = [_object(kind=_enum('measurement'), analysis_id=ID, request_id=ID, metric=_enum(metric), selector=info['selector'])
        for metric, info in MEASUREMENT_CATALOG.items() if allowed.intersection(info['request_kinds'])]
    native = _union(*[_object(kind=_enum(k)) for k in (('score', 'n_sequences') if provider == 'msa' else ('chi_square', 'p_value', 'df'))],
        *([_object(kind=_enum('dna_count'), symbol=_enum('A', 'T', 'G', 'C', 'Deletion')), _object(kind=_enum('protein_count'), detail_index=INDEX)] if provider == 'msa' else [
            _object(kind=_enum('export_group_count'), heading_index=INDEX, count_index=INDEX),
            _object(kind=_enum('raw_r_group_count'), position_1based=POSITIVE, count_index=INDEX)]))
    rows = {
        'measurement': _union(*measurements),
        'native_measurement': _object(kind=_enum('native_measurement'), analysis_id=ID, table=SLOT, row_index=INDEX, field=native),
        'function_composition': _object(kind=_enum('function_composition'), analysis_id=ID, request_id=ID, function_keys=IDS),
        'qualifications': _object(kind=_enum('qualifications'), analysis_id=ID, slot_id=_nullable(ID), request_id=_nullable(ID)),
        'missing_requirements': _object(kind=_enum('missing_requirements')),
    }
    if provider == 'msa':
        rows.update(msa_sites=_object(kind=_enum('msa_sites'), analysis_id=ID, request_id=ID, columns_0based=INDICES),
            reference_differences=_object(kind=_enum('reference_differences'), analysis_id=ID, request_id=ID, row_indices=INDICES, columns_0based=INDICES),
            tree_branches=_object(kind=_enum('tree_branches'), analysis_id=ID, request_id=ID, node_indices=INDICES),
            xmfa_coordinates=_object(kind=_enum('xmfa_coordinates'), analysis_id=ID, request_id=ID, cells=_array(CELL_REF, unique=True)),
            xmfa_source_positions=_object(kind=_enum('xmfa_source_positions'), analysis_id=ID, request_id=ID, queries=_array(QUERY, unique=True)),
            xmfa_alignment_measurements=_object(kind=_enum('xmfa_alignment_measurements'), analysis_id=ID, request_id=ID, measurements=_array(XMFA_METRIC_SCHEMA, unique=True)),
            xmfa_coverage=_object(kind=_enum('xmfa_coverage'), analysis_id=ID, request_id=ID, member_numbers=_array(POSITIVE, unique=True), include_intervals=BOOL, include_original_coverage=BOOL))
    else:
        rows.update(group_counts=_object(kind=_enum('group_counts'), analysis_id=ID, request_id=ID, columns_0based=INDICES, group_ids=IDS, symbols=_array(TEXT, unique=True)),
            statistical_tests=_object(kind=_enum('statistical_tests'), analysis_id=ID, request_id=ID, tests=_array(TEST, unique=True)),
            multiplicity=_object(kind=_enum('multiplicity'), analysis_id=_nullable(ID), request_id=_nullable(ID), family_request_id=_nullable(ID), selection=_enum('all_family', 'explicit_tests'), tests=_array(SCOPED_TEST, unique=True)))
    return rows


def validate_selection(selection: dict, *, provider: str) -> dict:
    _provider(provider)
    schemas = _selection_schemas(provider)
    require(type(selection) is dict and selection.get('kind') in schemas, 'selection_kind_invalid')
    _check(schemas[selection['kind']], selection, 'selection_invalid')
    if selection.get('analysis_id') is not None:
        require(selection['analysis_id'] not in RESERVED, 'reserved_analysis_id')
    if selection['kind'] == 'native_measurement':
        require(selection['analysis_id'] == selection['table']['analysis_id'], 'native_selection_scope_conflict')
    elif selection['kind'] == 'multiplicity':
        local = selection['analysis_id'] is not None and selection['request_id'] is not None and selection['family_request_id'] is None
        global_ = selection['analysis_id'] is None and selection['request_id'] is None and selection['family_request_id'] is not None
        require(local or global_, 'multiplicity_selector_scope_invalid')
        require(selection['selection'] != 'all_family' or not selection['tests'], 'multiplicity_all_with_tests')
        require(not local or all(t['analysis_id'] == selection['analysis_id'] for t in selection['tests']), 'multiplicity_selector_scope_invalid')
    tests = selection.get('tests', [])
    if selection['kind'] == 'measurement' and 'test' in selection['selector']:
        tests = [selection['selector']['test']]
    for item in tests:
        test = item.get('test', item)
        require(test['kind'] != 'pairwise' or len(test['group_ids']) == 2, 'test_pair_invalid')
    return deepcopy(selection)


def _reference_schema(kind):
    token = r'(?:[A-Za-z0-9._~-]|%[0-9A-F]{2})+'
    return {'type': 'string', 'pattern': '^bvbrc_alignment_' + kind + ':' + token + '/' + token + '$'}


UNITS = ('rows', 'columns', 'characters', 'positions', 'sequences', 'observations', 'members',
    'taxa', 'pairs', 'tips', 'nodes', 'edges', 'splits', 'fraction', 'signed_fraction', 'bits',
    'hundredths_of_bit', 'pseudocount_per_cell', 'augmented_observations', 'expected_observations',
    'cells', 'chi_square', 'degrees_of_freedom', 'probability', 'natural_log_probability',
    *BRANCH_UNITS, 'percent', 'native_statistic', 'nucleotides', 'nucleotide_placements')
ORIGINS = ('native_observation', 'calculated', 'fitted', 'derived', 'native_observed', 'native_fitted')
REQUIREMENT_REFS = _array(_reference_schema('requirement'), unique=True)
MEASUREMENT_FACT = _object(value=N, state=_enum(*STATES), unit=_enum(*UNITS), origin=_enum(*ORIGINS),
    method_ref=_nullable(_reference_schema('method')), population_ref=_nullable(_reference_schema('population')),
    numerator=N, denominator=N, requirement_refs=REQUIREMENT_REFS)
ORIGINAL_COORDINATE_FACT = _object(member_ref=_reference_schema('member'), interval_0based_half_open=_pair(INDEX),
    strand=_enum('+', '-', 'unknown'), translation_table=_nullable(POSITIVE), transformation_ref=_nullable(_reference_schema('transformation')))
MSA_SITE_FACT = _object(alignment_ref=_reference_schema('alignment'), population_ref=_reference_schema('population'),
    column_0based=INDEX, eligible_count=N, internal_gap_count=N, terminal_gap_excluded_count=N,
    literal_entropy_bits=N, native_score_recalculated=N, score_residual=N,
    strict_majority_consensus=_nullable(TEXT), requirement_refs=REQUIREMENT_REFS)
DIFFERENCE_FACT = _object(alignment_ref=_reference_schema('alignment'), row_index=INDEX, column_0based=INDEX,
    member_character=TEXT, reference_character=TEXT, category=_enum(*DIFFERENCE_CATEGORIES),
    member_ungapped_position_0based=I, reference_ungapped_position_0based=I,
    member_original=_nullable(ORIGINAL_COORDINATE_FACT), reference_original=_nullable(ORIGINAL_COORDINATE_FACT))
GROUP_COUNT_FACT = _object(alignment_ref=_reference_schema('alignment'), population_ref=_reference_schema('population'),
    category_ref=_reference_schema('category'), group_ref=_reference_schema('group'), column_0based=INDEX, symbol=TEXT,
    count=I, basis=_enum('biological', 'native_reproduction'), state=_enum(*STATES), requirement_refs=REQUIREMENT_REFS)
STATISTICAL_TEST_FACT = _object(test_ref=_reference_schema('test'), category_ref=_reference_schema('category'),
    column_0based=INDEX, kind=_enum('omnibus', 'pairwise'), group_refs=_array(_reference_schema('group'), unique=True),
    basis=_enum('biological', 'native_reproduction'), chi_square=N, df=N, p_value=N, log_p=N, native_zero_rule_p=N,
    numerical_state=_enum('finite', 'underflow', 'unavailable'), requirement_refs=REQUIREMENT_REFS)
FUNCTION_FACT = _object(population_ref=_reference_schema('population'), function_ref=_reference_schema('function'),
    assigned_members=N, total_members=N, members_with_recorded_assignment=N, fraction_all=N,
    fraction_recorded=N, requirement_refs=REQUIREMENT_REFS)
BRANCH_FACT = _object(tree_ref=_reference_schema('tree'), node_index=INDEX, split_ref=_nullable(_reference_schema('split')),
    length=N, length_unit=_enum(*BRANCH_UNITS), support_rescaled=N, support_method=_enum('fasttree_sh_like', 'native_unknown'),
    support_scale=_enum(*SUPPORT_SCALES), requirement_refs=REQUIREMENT_REFS)
MULTIPLICITY_FACT = _object(family_ref=_reference_schema('family'), test_ref=_reference_schema('test'), input_p=N,
    adjusted_p=N, method=MULTIPLICITY_FIELDS['method'], alpha=MULTIPLICITY_FIELDS['alpha'], total_test_count=I,
    rejected_at_alpha=_nullable(BOOL), p_value_basis=_enum('native_unadjusted', 'source_mathematical_recalculation', 'biological_mathematical_recalculation'), requirement_refs=REQUIREMENT_REFS)

# Original diagnostics remain saved unchanged. Unregistered upstream codes have
# one explicit outward qualification; free text is never admitted as a code.
DIAGNOSTIC_CODES = frozenset('''alignment_original_task_conflict alignment_slot_missing alignment_slot_ambiguous
alignment_slot_incomplete alignment_slot_sha256_conflict alignment_declared_format_conflict alignment_supplied_content_unbound
alignment_supplied_evidence_unbound alignment_supplied_value_invalid alignment_document_unavailable alignment_member_join_missing
alignment_member_join_conflicting original_member_occurrence_ambiguous alignment_transformation_unproven alignment_original_coordinates_required
msa_reference_unresolved msa_consensus_correspondence_unresolved msa_segment_membership_unresolved msa_prealigned_definition_mismatch
msa_full_xmfa_binding_required alignment_deployed_version_unproven metacats_metadata_join_missing metacats_metadata_duplicate_conflict
metacats_category_conflict metacats_biological_group_membership_required metacats_native_ordinal_required metacats_r_column_evidence_required
metacats_exported_label_conflict metacats_original_hash_provenance_required metacats_test_family_incomplete
alignment_calculation_dependency_unavailable alignment_calculation_invalid alignment_projection_dependency_unavailable
alignment_unregistered_qualification output_association_unproven output_version_unproven duplicate_artifact_representation
xmfa_source_extractor_unbound xmfa_source_record_bytes_conflict xmfa_source_bytes_required xmfa_source_reader_required'''.split())
# Finite literals from the consumed native readers, association/sheet
# validators, scientific calculators and retained host acquisition records.
# Source/line evidence: verification/tool_graders_bvbrc_alignment_bundle_2026-10-25/DIAGNOSTIC_REGISTRY_013.json.
DIAGNOSTIC_CODES |= frozenset('''
acquisition_dependency_invalid
acquisition_receipt_ref_missing
acquisition_source_conflict
acquisition_status_conflict
acquisition_transport_conflict
alignment_deployed_version_unproven
alignment_document_unavailable
alignment_label_missing
alignment_lengths_unequal
alignment_symbol_invalid
alignment_transformation_unproven
alignment_whitespace_ignored
appservice_event_operation_conflict
appservice_event_projection_conflict
artifact_invalid
artifact_sha256_mismatch
biological_group_calculated_p_underflow
biological_group_original_member_identity_unknown
bvbrc_alignment_provider_alignment_unknown
bvbrc_alignment_provider_alphabet_invalid
bvbrc_alignment_provider_array_invalid
bvbrc_alignment_provider_automatic_alignment_unknown
bvbrc_alignment_provider_automatic_input_unknown
bvbrc_alignment_provider_automatic_policy_invalid
bvbrc_alignment_provider_automatic_transform_unsupported
bvbrc_alignment_provider_automatic_transformation_unknown
bvbrc_alignment_provider_block_index_invalid
bvbrc_alignment_provider_column_unknown
bvbrc_alignment_provider_command_missing
bvbrc_alignment_provider_command_role_invalid
bvbrc_alignment_provider_completeness_invalid
bvbrc_alignment_provider_component_invalid
bvbrc_alignment_provider_correspondence_member_conflict
bvbrc_alignment_provider_correspondence_transformation_conflict
bvbrc_alignment_provider_declaration_version_invalid
bvbrc_alignment_provider_declarations_invalid
bvbrc_alignment_provider_dependence_kind_invalid
bvbrc_alignment_provider_dependence_reference_unknown
bvbrc_alignment_provider_dependency_invalid
bvbrc_alignment_provider_diagnostic_invalid
bvbrc_alignment_provider_document_kind_invalid
bvbrc_alignment_provider_documents_invalid
bvbrc_alignment_provider_duplicate_document
bvbrc_alignment_provider_duplicate_identifier
bvbrc_alignment_provider_duplicate_index
bvbrc_alignment_provider_duplicate_inline_host_identity
bvbrc_alignment_provider_duplicate_member_key
bvbrc_alignment_provider_duplicate_original_member
bvbrc_alignment_provider_duplicate_record
bvbrc_alignment_provider_duplicate_row_reference
bvbrc_alignment_provider_duplicate_tree
bvbrc_alignment_provider_empty_equivalence
bvbrc_alignment_provider_encoding_invalid
bvbrc_alignment_provider_entity_evidence_missing
bvbrc_alignment_provider_entity_member_unknown
bvbrc_alignment_provider_entity_source_kind_invalid
bvbrc_alignment_provider_entity_subject_kind_invalid
bvbrc_alignment_provider_feature_source_kind_invalid
bvbrc_alignment_provider_feature_source_unknown
bvbrc_alignment_provider_function_equivalence_conflict
bvbrc_alignment_provider_function_source_unknown
bvbrc_alignment_provider_gap_symbol_invalid
bvbrc_alignment_provider_genome_source_kind_invalid
bvbrc_alignment_provider_host_member_fact_conflict
bvbrc_alignment_provider_host_member_join_invalid
bvbrc_alignment_provider_host_member_molecule_conflict
bvbrc_alignment_provider_host_member_unknown
bvbrc_alignment_provider_id_rule_invalid
bvbrc_alignment_provider_inline_binding_conflict
bvbrc_alignment_provider_inline_binding_unknown
bvbrc_alignment_provider_inline_encoding_invalid
bvbrc_alignment_provider_inline_header_conflict
bvbrc_alignment_provider_inline_header_empty
bvbrc_alignment_provider_inline_header_missing
bvbrc_alignment_provider_inline_input_invalid
bvbrc_alignment_provider_inline_label_conflict
bvbrc_alignment_provider_inline_line_conflict
bvbrc_alignment_provider_inline_member_conflict
bvbrc_alignment_provider_inline_member_digest_or_occurrence_conflict
bvbrc_alignment_provider_inline_member_document_missing
bvbrc_alignment_provider_inline_member_row_unknown
bvbrc_alignment_provider_inline_member_sequence_conflict
bvbrc_alignment_provider_inline_no_rows
bvbrc_alignment_provider_inline_occurrence_missing
bvbrc_alignment_provider_inline_original_missing
bvbrc_alignment_provider_inline_parameters_invalid
bvbrc_alignment_provider_inline_range_invalid
bvbrc_alignment_provider_inline_row_order_invalid
bvbrc_alignment_provider_inline_sequence_conflict
bvbrc_alignment_provider_inline_sequence_empty
bvbrc_alignment_provider_inline_sequence_layout_whitespace_removed
bvbrc_alignment_provider_inline_sequence_symbol_invalid
bvbrc_alignment_provider_input_binding_unknown
bvbrc_alignment_provider_input_document_invalid
bvbrc_alignment_provider_input_selection_invalid
bvbrc_alignment_provider_input_selection_kind_invalid
bvbrc_alignment_provider_inputs_invalid
bvbrc_alignment_provider_integer_invalid
bvbrc_alignment_provider_interval_invalid
bvbrc_alignment_provider_join_basis_invalid
bvbrc_alignment_provider_leaf_population_invalid
bvbrc_alignment_provider_leaf_population_tip_unknown
bvbrc_alignment_provider_member_entity_array_conflict
bvbrc_alignment_provider_member_reference_unknown
bvbrc_alignment_provider_member_source_array_conflict
bvbrc_alignment_provider_member_source_unknown
bvbrc_alignment_provider_merge_evidence_missing
bvbrc_alignment_provider_merge_rule_invalid
bvbrc_alignment_provider_metadata_member_invalid
bvbrc_alignment_provider_missing_member_conflict
bvbrc_alignment_provider_molecule_invalid
bvbrc_alignment_provider_multiple_originals_without_concatenation
bvbrc_alignment_provider_occurrence_index_conflict
bvbrc_alignment_provider_origin_invalid
bvbrc_alignment_provider_original_artifact_conflict
bvbrc_alignment_provider_original_document_incomplete
bvbrc_alignment_provider_original_document_unknown
bvbrc_alignment_provider_original_header_conflict
bvbrc_alignment_provider_original_interval_missing_member
bvbrc_alignment_provider_original_interval_outside_member
bvbrc_alignment_provider_original_member_ambiguous
bvbrc_alignment_provider_original_member_label_missing
bvbrc_alignment_provider_original_member_missing
bvbrc_alignment_provider_original_member_occurrence_ambiguous
bvbrc_alignment_provider_original_pointer_conflict
bvbrc_alignment_provider_original_row_join_missing
bvbrc_alignment_provider_original_row_unknown
bvbrc_alignment_provider_original_sequence_conflict
bvbrc_alignment_provider_pointer_invalid
bvbrc_alignment_provider_population_alignment_unknown
bvbrc_alignment_provider_population_completeness_overstated
bvbrc_alignment_provider_population_identity_conflict
bvbrc_alignment_provider_provider_invalid
bvbrc_alignment_provider_reader_document_conflict
bvbrc_alignment_provider_reader_document_count_invalid
bvbrc_alignment_provider_reader_document_unknown
bvbrc_alignment_provider_reader_invalid
bvbrc_alignment_provider_reader_multiple_trees_conflict
bvbrc_alignment_provider_reader_ok_document_missing
bvbrc_alignment_provider_reader_parameter_conflict
bvbrc_alignment_provider_reader_parameter_invalid
bvbrc_alignment_provider_reader_provider_conflict
bvbrc_alignment_provider_reader_status_invalid
bvbrc_alignment_provider_rename_after_conflict
bvbrc_alignment_provider_rename_before_conflict
bvbrc_alignment_provider_rename_member_conflict
bvbrc_alignment_provider_requirement_invalid
bvbrc_alignment_provider_resolved_member_missing
bvbrc_alignment_provider_row_reference_unknown
bvbrc_alignment_provider_row_state_invalid
bvbrc_alignment_provider_segment_interval_conflict
bvbrc_alignment_provider_segment_order_conflict
bvbrc_alignment_provider_segment_unknown
bvbrc_alignment_provider_semantic_declaration_scope_invalid
bvbrc_alignment_provider_setting_conflict_code_invalid
bvbrc_alignment_provider_setting_conflict_reference_invalid
bvbrc_alignment_provider_setting_name_invalid
bvbrc_alignment_provider_setting_value_invalid
bvbrc_alignment_provider_shape_invalid
bvbrc_alignment_provider_source_kind_invalid
bvbrc_alignment_provider_staged_coordinate_conflict
bvbrc_alignment_provider_strand_invalid
bvbrc_alignment_provider_subject_member_unknown
bvbrc_alignment_provider_subject_source_unknown
bvbrc_alignment_provider_symbol_invalid
bvbrc_alignment_provider_taxonomy_source_unknown
bvbrc_alignment_provider_text_invalid
bvbrc_alignment_provider_transformation_kind_invalid
bvbrc_alignment_provider_transformation_member_conflict
bvbrc_alignment_provider_transformation_row_conflict
bvbrc_alignment_provider_transformation_unknown
bvbrc_alignment_provider_translation_invalid
bvbrc_alignment_provider_translation_table_conflict
bvbrc_alignment_provider_tree_document_conflict
bvbrc_alignment_provider_tree_format_invalid
bvbrc_alignment_provider_tree_identity_conflict
bvbrc_alignment_provider_tree_order_invalid
bvbrc_metacats_artifact_digest_conflict
bvbrc_metacats_association_alignment_rows_required
bvbrc_metacats_association_analysis_document_unknown
bvbrc_metacats_association_analysis_native_document_conflict
bvbrc_metacats_association_assignment_group_unknown
bvbrc_metacats_association_assignment_member_unknown
bvbrc_metacats_association_assignment_row_member_conflict
bvbrc_metacats_association_assignment_scope_invalid
bvbrc_metacats_association_assignment_state_invalid
bvbrc_metacats_association_auto_entry_order_invalid
bvbrc_metacats_association_auto_fetched_sequence_association_required
bvbrc_metacats_association_auto_input_mode_conflict
bvbrc_metacats_association_biological_group_population_required
bvbrc_metacats_association_biological_row_membership_conflicting
bvbrc_metacats_association_biological_row_membership_missing
bvbrc_metacats_association_biological_row_membership_unresolved
bvbrc_metacats_association_category_column_missing
bvbrc_metacats_association_category_definition_required
bvbrc_metacats_association_category_groups_conflict
bvbrc_metacats_association_category_heading_conflict
bvbrc_metacats_association_category_heading_without_header
bvbrc_metacats_association_category_metadata_missing
bvbrc_metacats_association_category_metadata_unknown
bvbrc_metacats_association_category_original_metadata_conflict
bvbrc_metacats_association_category_population_conflict
bvbrc_metacats_association_category_scope_invalid
bvbrc_metacats_association_category_state_invalid
bvbrc_metacats_association_column_category_unknown
bvbrc_metacats_association_column_export_identity_incomplete
bvbrc_metacats_association_column_export_reference_missing
bvbrc_metacats_association_column_group_unknown
bvbrc_metacats_association_column_identity_missing
bvbrc_metacats_association_column_state_invalid
bvbrc_metacats_association_column_wrong_label_conflict
bvbrc_metacats_association_declaration_scope_invalid
bvbrc_metacats_association_dependency_invalid
bvbrc_metacats_association_exported_column_group_conflict
bvbrc_metacats_association_exported_column_unknown
bvbrc_metacats_association_exported_group_unknown
bvbrc_metacats_association_exported_heading_conflict
bvbrc_metacats_association_exported_identity_missing
bvbrc_metacats_association_exported_label_conflict
bvbrc_metacats_association_exported_state_invalid
bvbrc_metacats_association_exported_table_unknown
bvbrc_metacats_association_group_category_conflict
bvbrc_metacats_association_group_completeness_invalid
bvbrc_metacats_association_group_identity_conflict
bvbrc_metacats_association_group_identity_noncanonical
bvbrc_metacats_association_group_metadata_unknown
bvbrc_metacats_association_group_metadata_value_conflict
bvbrc_metacats_association_group_source_category_unknown
bvbrc_metacats_association_group_source_mode_conflict
bvbrc_metacats_association_group_source_record_unknown
bvbrc_metacats_association_input_mode_invalid
bvbrc_metacats_association_metadata_alignment_scope_conflict
bvbrc_metacats_association_metadata_alignment_token_conflict
bvbrc_metacats_association_metadata_category_cell_absent
bvbrc_metacats_association_metadata_document_unknown
bvbrc_metacats_association_metadata_join_original_input_conflict
bvbrc_metacats_association_metadata_join_policy_invalid
bvbrc_metacats_association_metadata_join_scope_invalid
bvbrc_metacats_association_metadata_member_row_conflict
bvbrc_metacats_association_metadata_member_state_invalid
bvbrc_metacats_association_metadata_member_token_conflict
bvbrc_metacats_association_metadata_resolved_identity_invalid
bvbrc_metacats_association_missing_group_conflict
bvbrc_metacats_association_native_assignment_biological_unknown
bvbrc_metacats_association_native_assignment_group_conflict
bvbrc_metacats_association_native_assignment_identity_missing
bvbrc_metacats_association_native_assignment_member_conflict
bvbrc_metacats_association_native_assignment_metadata_conflict
bvbrc_metacats_association_native_assignment_metadata_value_conflict
bvbrc_metacats_association_native_assignment_state_invalid
bvbrc_metacats_association_native_map_group_conflict
bvbrc_metacats_association_native_map_scope_invalid
bvbrc_metacats_association_native_output_group_identity_unresolved
bvbrc_metacats_association_native_r_column_identity_required
bvbrc_metacats_association_native_r_group_association_unresolved
bvbrc_metacats_association_native_row_unknown
bvbrc_metacats_association_native_test_identity_duplicate
bvbrc_metacats_association_omnibus_column_population_conflict
bvbrc_metacats_association_pair_export_identity_ambiguous
bvbrc_metacats_association_pair_identity_invalid
bvbrc_metacats_association_population_category_unknown
bvbrc_metacats_association_population_duplicate
bvbrc_metacats_association_population_group_conflict
bvbrc_metacats_association_population_group_identity_conflict
bvbrc_metacats_association_population_plan_invalid
bvbrc_metacats_association_population_plan_kind_invalid
bvbrc_metacats_association_r_column_order_invalid
bvbrc_metacats_association_r_evidence_matrix_conflict
bvbrc_metacats_association_r_evidence_missing
bvbrc_metacats_association_r_token_ordinal_conflict
bvbrc_metacats_association_raw_pair_column_conflict
bvbrc_metacats_association_resolved_group_missing
bvbrc_metacats_association_shape_invalid
bvbrc_metacats_association_test_alignment_conflict
bvbrc_metacats_association_test_category_conflict
bvbrc_metacats_association_test_category_unknown
bvbrc_metacats_association_test_column_group_conflict
bvbrc_metacats_association_test_column_outside_alignment
bvbrc_metacats_association_test_column_unknown
bvbrc_metacats_association_test_group_unknown
bvbrc_metacats_association_test_groups_token_conflict
bvbrc_metacats_association_test_identity_missing
bvbrc_metacats_association_test_kind_conflict
bvbrc_metacats_association_test_position_conflict
bvbrc_metacats_association_test_state_invalid
bvbrc_metacats_association_test_table_unknown
bvbrc_metacats_association_unresolved_test_identity
bvbrc_metacats_association_wrong_label_without_difference
bvbrc_metacats_association_wrong_native_label
bvbrc_metacats_duplicate_native_symbol
bvbrc_metacats_empty_input
bvbrc_metacats_encoding_invalid
bvbrc_metacats_legacy_method_unresolved
bvbrc_metacats_legacy_star_unresolved
bvbrc_metacats_malformed_native_number
bvbrc_metacats_matrix_row_invalid
bvbrc_metacats_matrix_token_unresolved
bvbrc_metacats_native_fewer_5_unresolved
bvbrc_metacats_native_group_cell_unparsed
bvbrc_metacats_native_group_heading_unresolved
bvbrc_metacats_native_header_conflict
bvbrc_metacats_native_number_incompatible
bvbrc_metacats_native_number_missing
bvbrc_metacats_native_numeric_overflow
bvbrc_metacats_native_numeric_underflow
bvbrc_metacats_native_position_invalid
bvbrc_metacats_provider_dependency_contract_invalid
bvbrc_metacats_provider_document_provider_conflict
bvbrc_metacats_provider_metacats_tree_population_invalid
bvbrc_metacats_provider_native_observation_association_invalid
bvbrc_metacats_provider_native_observation_document_conflict
bvbrc_metacats_provider_native_observation_unit_conflict
bvbrc_metacats_provider_reserved_analysis_id
bvbrc_metacats_provider_shape_invalid
bvbrc_metacats_provider_sheet_identity_invalid
bvbrc_metacats_provider_sheet_requirement_omitted
bvbrc_metacats_ragged_matrix
bvbrc_metacats_ragged_metadata
bvbrc_metacats_ragged_native_row
bvbrc_metacats_raw_group_positions_conflict
bvbrc_metacats_raw_pair_order_conflict
bvbrc_metacats_raw_site_token_invalid
bvbrc_metacats_raw_wrapper_invalid
bvbrc_metacats_raw_wrapper_trailing_data
bvbrc_metacats_raw_wrapper_truncated
bvbrc_msa_artifact_digest_conflict
bvbrc_msa_duplicate_native_coordinate
bvbrc_msa_duplicate_native_residue
bvbrc_msa_empty_site_population
bvbrc_msa_encoding_conflict
bvbrc_msa_incomplete_alignment
bvbrc_msa_malformed_detail
bvbrc_msa_malformed_native_number
bvbrc_msa_native_comparison_selected_row_subset
bvbrc_msa_native_consensus_unresolved
bvbrc_msa_native_coordinate_outside_alignment
bvbrc_msa_native_coordinate_unavailable
bvbrc_msa_native_count_total_conflict
bvbrc_msa_native_header_conflict
bvbrc_msa_native_number_unavailable
bvbrc_msa_native_residue_unresolved
bvbrc_msa_native_table_partial
bvbrc_msa_native_vs_recalculated_conflict
bvbrc_msa_original_residue_map_required
bvbrc_msa_provider_analysis_document_conflict
bvbrc_msa_provider_analysis_tree_unknown
bvbrc_msa_provider_consensus_alignment_conflict
bvbrc_msa_provider_consensus_column_population_conflict
bvbrc_msa_provider_consensus_coordinate_conflict
bvbrc_msa_provider_consensus_duplicate
bvbrc_msa_provider_consensus_full_population_required
bvbrc_msa_provider_consensus_population_unknown
bvbrc_msa_provider_consensus_position_conflict
bvbrc_msa_provider_consensus_sequence_conflict
bvbrc_msa_provider_consensus_state_invalid
bvbrc_msa_provider_consensus_symbol_conflict
bvbrc_msa_provider_consensus_table_conflict
bvbrc_msa_provider_consensus_unresolved_columns
bvbrc_msa_provider_dependency_contract_invalid
bvbrc_msa_provider_document_provider_conflict
bvbrc_msa_provider_gap_fill_segment_interval_conflict
bvbrc_msa_provider_gap_fill_sequence_conflict
bvbrc_msa_provider_mode_invalid
bvbrc_msa_provider_native_branch_length_conflict
bvbrc_msa_provider_native_length_population_conflict
bvbrc_msa_provider_native_observation_missing
bvbrc_msa_provider_native_observation_population_conflict
bvbrc_msa_provider_native_observation_source_conflict
bvbrc_msa_provider_native_support_node_conflict
bvbrc_msa_provider_native_support_population_conflict
bvbrc_msa_provider_native_support_source_conflict
bvbrc_msa_provider_native_support_value_conflict
bvbrc_msa_provider_native_tree_node_unknown
bvbrc_msa_provider_native_tree_source_conflict
bvbrc_msa_provider_reference_analysis_conflict
bvbrc_msa_provider_reference_original_conflict
bvbrc_msa_provider_reference_original_occurrence_ambiguous
bvbrc_msa_provider_reference_original_proof_missing
bvbrc_msa_provider_reference_row_unknown
bvbrc_msa_provider_segment_alignment_unknown
bvbrc_msa_provider_segment_concatenated_interval_conflict
bvbrc_msa_provider_segment_final_alignment_missing
bvbrc_msa_provider_segment_genome_conflict
bvbrc_msa_provider_segment_member_unknown
bvbrc_msa_provider_segment_order_duplicate
bvbrc_msa_provider_segment_original_interval_conflict
bvbrc_msa_provider_segment_population_conflict
bvbrc_msa_provider_segment_source_unknown
bvbrc_msa_provider_segment_state_invalid
bvbrc_msa_provider_shape_invalid
bvbrc_msa_provider_sheet_version_invalid
bvbrc_msa_provider_source_reports_missing
bvbrc_msa_provider_source_tree_unknown
bvbrc_msa_provider_support_association_conflict
bvbrc_msa_provider_support_association_missing
bvbrc_msa_provider_support_reference_unknown
bvbrc_msa_provider_transformation_segment_interval_conflict
bvbrc_msa_provider_transformation_segment_order_conflict
bvbrc_msa_provider_transformation_segment_unknown
bvbrc_msa_provider_tree_alignment_unknown
bvbrc_msa_provider_tree_binding_invalid
bvbrc_msa_provider_tree_command_unknown
bvbrc_msa_provider_tree_semantics_invalid
bvbrc_msa_provider_tree_tip_conflict
bvbrc_msa_provider_xmfa_binding_document_unknown
bvbrc_msa_provider_xmfa_slot_document_conflict
bvbrc_msa_provider_xmfa_slot_missing
bvbrc_msa_ragged_native_row
bvbrc_msa_reference_coordinate_conflict
bvbrc_msa_requested_reference_unresolved
bytes_required
capability_expired_at_retrieval
capability_expiry_time_uninterpretable
capability_http_error
capability_not_possessed
capability_unavailable
capability_url_conflict
catalog_definition_invalid
checksum_algorithm_unverified
conflicting_http_framing
conflicting_http_header
content_encoding_uninterpreted
content_length_invalid
download_body_count_conflict
download_incomplete
download_snapshot_missing
download_transport_identity_conflict
download_transport_request_conflict
duplicate_acquisition_receipt
duplicate_artifact_representation
duplicate_json_member
empty_input
encoding_invalid
fasta_header_missing
http_header_projection_conflict
issued_effect_unknown
metacats_calculated_p_underflow
msa_consensus_correspondence_unresolved
msa_full_xmfa_binding_required
msa_prealigned_definition_mismatch
msa_reference_unresolved
msa_segment_membership_unresolved
native_manifest_member_invalid
native_manifest_outputs_invalid
native_manifest_parameters_invalid
native_manifest_success_invalid
native_request_conflict
native_response_incomplete
native_response_invalid
native_snapshot_missing
native_task_failed
native_upload_checksum_invalid
native_upload_error
native_upload_file_invalid
native_upload_node_invalid
native_upload_node_missing
native_upload_size_invalid
native_upload_status
object_completeness_unproven
object_size_conflict
original_task_mismatch
output_association_missing
output_association_unproven
output_version_unproven
phylogeny_alignment_label_missing
phylogeny_alignment_lengths_unequal
phylogeny_alignment_symbol_invalid
phylogeny_alignment_whitespace_ignored
phylogeny_artifact_invalid
phylogeny_artifact_sha256_mismatch
phylogeny_bytes_required
phylogeny_empty_input
phylogeny_encoding_invalid
phylogeny_fasta_header_missing
phylogeny_native_number_invalid
phylogeny_negative_branch_length
phylogeny_newick_double_quote_dialect_required
phylogeny_newick_multiple_disallowed
phylogeny_newick_rooted_marker_conflict
phylogeny_newick_syntax_invalid
phylogeny_newick_truncated
phylogeny_original_map_incomplete
phylogeny_reader_parameter_invalid
publication_dependency_conflict
publication_evidence_missing
publication_input_bindings_conflict
publication_operation_conflict
publication_producer_source_missing
publication_requirement_conflict
range_conflict
range_ignored
reader_parameter_invalid
receipt_origin_conflict
snapshot_binding_conflict
snapshot_selection_conflict
submission_handoff_unconfirmed
task_info_object_invalid
task_info_text_encoding_invalid
task_manifest_mismatch
task_manifest_object_invalid
unselected_artifact_retained
upload_checksum_mismatch
upload_checksum_unobserved
upload_file_acceptance_unproven
upload_file_metadata_missing
upload_filename_mismatch
upload_node_mismatch
upload_sha256_unobserved
upload_size_mismatch
upload_size_unobserved
workspace_target_conflict
workspace_target_unconfirmed
xmfa_all_zero_block
xmfa_coordinate_invalid
xmfa_digest_mismatch
xmfa_document_unrecognized
xmfa_duplicate_member_record
xmfa_empty_comparison_population
xmfa_empty_input
xmfa_encoding_invalid
xmfa_header_malformed
xmfa_input_population_partial
xmfa_invocation_mode_missing
xmfa_member_invalid
xmfa_metadata_conflict
xmfa_metadata_duplicate
xmfa_metadata_integer_invalid
xmfa_missing_block_terminator
xmfa_original_map_conflict
xmfa_original_map_missing
xmfa_overlapping_placement
xmfa_pair_not_coobserved
xmfa_row_width_conflict
xmfa_selected_population_partial
xmfa_sequence_before_header
xmfa_sequence_symbol_invalid
xmfa_source_binding_conflict
xmfa_source_binding_missing
xmfa_source_bytes_required
xmfa_source_extractor_unbound
xmfa_source_reader_required
xmfa_source_record_bytes_conflict
xmfa_source_sequence_mismatch
xmfa_source_span_outside_input
xmfa_span_mismatch
xmfa_strand_invalid
xmfa_unparsed_line
xmfa_version_missing
xmfa_version_unsupported
xmfa_zero_record_has_residues
'''.split())
QUALIFICATION_FACT = _object(code=_enum(*sorted(DIAGNOSTIC_CODES)),
    phase=_enum('custody', 'prepare', 'transport', 'native_decode', 'association', 'publication', 'recovery', 'return'),
    severity=_enum('error', 'qualification'), role_ref=_nullable(_reference_schema('role')), requirement_refs=REQUIREMENT_REFS)
REQUIREMENT_FACT = _object(requirement_ref=_reference_schema('requirement'),
    kind=_enum('definition', 'input_metadata', 'input_bytes', 'original_task', 'task_manifest', 'output_metadata',
        'output_bytes', 'byte_version_evidence', 'scientific_metadata', 'parser_binding'),
    role_ref=_nullable(_reference_schema('role')), source_refs=IDS, reason_ref=_reference_schema('reason'))
XMFA_FORWARD_SOURCE_FACT = _object(file_ref=_reference_schema('xmfa_file'), record_ref=_reference_schema('xmfa_record'),
    entry_1based=POSITIVE, position_0based=INDEX, strand=_enum('+', '-'))
XMFA_ORIGINAL_BASE_FACT = _object(member_ref=_reference_schema('member'), position_0based=INDEX,
    original_length=INDEX, strand=_enum('+', '-'), transformation_ref=_reference_schema('transformation'))
XMFA_COORDINATE_FACT = _object(document_ref=_reference_schema('xmfa_document'), cell=CELL_REF,
    member_number=_nullable(POSITIVE), aligned_symbol=TEXT, state=_enum('residue', 'gap', 'absent_zero', 'incompatible'),
    native_position_1based=_nullable(POSITIVE), native_position_0based=I, native_strand=_enum('+', '-', None),
    forward_symbol=_nullable(TEXT), source_state=_enum('resolved', 'missing', 'conflicting', 'not_applicable'),
    source_coordinate=_nullable(XMFA_FORWARD_SOURCE_FACT), original_coordinates=_array(XMFA_ORIGINAL_BASE_FACT), requirement_refs=REQUIREMENT_REFS)
XMFA_INVERSE_FACT = _object(document_ref=_reference_schema('xmfa_document'), member_number=POSITIVE,
    position_0based=INDEX, state=_enum('unique', 'multiple', 'none_in_document', 'unknown'), matches=_array(CELL_REF),
    search_completeness=_enum(*COMPLETENESS), requirement_refs=REQUIREMENT_REFS)
XMFA_MEASUREMENT_FACT = _object(document_ref=_reference_schema('xmfa_document'), population_ref=_reference_schema('population'),
    selection=_object(metric=_enum(*(token for shape in XMFA_METRIC_SCHEMA['oneOf'] for token in shape['properties']['metric']['enum'])),
        block_index=INDEX, column_0based=I, symbol=_nullable(TEXT), member_a=_nullable(POSITIVE), member_b=_nullable(POSITIVE)),
    measurement=MEASUREMENT_FACT)
XMFA_ORIGINAL_COVERAGE_FACT = _object(member_ref=_reference_schema('member'), original_length=N,
    known_union_bases=N, coverage_fraction=N, mapping_completeness=_enum(*COMPLETENESS))
XMFA_COVERAGE_FACT = _object(document_ref=_reference_schema('xmfa_document'), population_ref=_reference_schema('population'),
    member_number=POSITIVE, basis=_enum('represented', 'multi_member_block', 'cooccupied_column'),
    source_length=N, known_union_bases=N, placement_bases=N, multiply_represented_bases=N, excess_placement_bases=N,
    selected_coverage_fraction=N, complement_bases=N, known_union_intervals=_nullable(_array(_pair(INDEX))),
    complement_intervals=_nullable(_array(_pair(INDEX))), membership_completeness=_enum(*COMPLETENESS),
    original_coverage=_nullable(_array(XMFA_ORIGINAL_COVERAGE_FACT)), requirement_refs=REQUIREMENT_REFS)

FACT_SCHEMAS = {
    'measurement': MEASUREMENT_FACT, 'native_measurement': MEASUREMENT_FACT,
    **{kind: _nullable(_array(schema)) for kind, schema in (
        ('msa_sites', MSA_SITE_FACT), ('reference_differences', DIFFERENCE_FACT), ('group_counts', GROUP_COUNT_FACT),
        ('statistical_tests', STATISTICAL_TEST_FACT), ('function_composition', FUNCTION_FACT), ('tree_branches', BRANCH_FACT),
        ('multiplicity', MULTIPLICITY_FACT), ('xmfa_coordinates', XMFA_COORDINATE_FACT), ('xmfa_source_positions', XMFA_INVERSE_FACT),
        ('xmfa_alignment_measurements', XMFA_MEASUREMENT_FACT), ('xmfa_coverage', XMFA_COVERAGE_FACT))},
    'qualifications': _array(QUALIFICATION_FACT), 'missing_requirements': _array(REQUIREMENT_FACT),
}


def requested_form_schema(fields: dict, *, provider: str) -> dict:
    _provider(provider)
    require(type(fields) is dict and all(type(k) is str and k for k in fields), 'requested_fields_invalid')
    properties = {}
    for name, selection in fields.items():
        selection = validate_selection(selection, provider=provider)
        properties[name] = {**deepcopy(FACT_SCHEMAS[selection['kind']]), 'x-alignment-fact': selection}
    return _object(**properties)


def validate_requested_form(requested_form: dict, *, provider: str) -> dict:
    _provider(provider); _finite_json(requested_form)
    require(type(requested_form) is dict and set(requested_form) == {'type', 'properties', 'required', 'additionalProperties'}, 'requested_form_invalid')
    require(type(requested_form['properties']) is dict and type(requested_form['required']) is list, 'requested_form_invalid')
    require(all(type(v) is dict and 'x-alignment-fact' in v for v in requested_form['properties'].values()), 'requested_form_invalid')
    expected = requested_form_schema({k: v['x-alignment-fact'] for k, v in requested_form['properties'].items()}, provider=provider)
    normalized = deepcopy(requested_form)
    require(len(normalized['required']) == len(set(normalized['required'])) and set(normalized['required']) == set(expected['required']), 'requested_required_conflict')
    normalized['required'] = expected['required']
    require(_same(normalized, expected), 'requested_form_noncanonical')
    return deepcopy(requested_form)


__all__ = ['validate_parameters', 'parameters_schema', 'requested_form_schema', 'validate_requested_form',
    'validate_selection', 'encode_reference', 'decode_reference', 'FACT_SCHEMAS']
