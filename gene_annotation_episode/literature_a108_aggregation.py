"""Main A108 evidence scoring sheet over admitted contextual observations.

The evidence amount is a set cardinality, not a sum of child totals. Original
observations shared by papers, database records or biological domains contribute
once to the overall amount; support, conflict and unresolved relations survive.
"""
from copy import deepcopy

from .domain import ContractError, canonical, obj, validate_schema
from .literature_a108_grading import (
    COMPONENTS as COUNT_COMPONENTS, DOMAIN_BY_TYPE, DOMAINS, RELATIONS, UNIT,
    count_sets, missing_inputs_schema, observation_sets_schema,
    reference_schema, references_schema, relation_metadata, relation_schema,
    sets_from_relations, strings_schema,
)

VERSION = 'a108_across_observation_aggregation_v1'
SCOPE = 'a108_across_observation_aggregation'
COMPONENTS = (*DOMAINS, 'overall')


def component_selection_schema():
    return obj({'sheet_ref': reference_schema('source'),
                'component': {'const': 'evidence_amount'}})


def aggregation_population_schema():
    return obj({'assertion_ref': reference_schema('hypothesis'),
        'target_context_ref': reference_schema('context', True),
        'contributions': {'type': 'array', 'items': component_selection_schema()}})


def aggregation_cell_schema():
    return obj({'component': {'enum': list(COMPONENTS)},
        'evaluation_scope': {'const': SCOPE},
        'assertion_ref': reference_schema('hypothesis'),
        'target_context_ref': reference_schema('context', True),
        'value': {'type': ['integer', 'null']},
        'available_value': {'type': ['integer', 'null']},
        'status': {'enum': ['complete', 'partial', 'unavailable']},
        'unit': {'const': UNIT},
        **{name: {'type': ['integer', 'null']} for name in COUNT_COMPONENTS},
        'observation_sets': observation_sets_schema(),
        'observation_refs': references_schema(),
        'relation_refs': references_schema('hypothesis'),
        'source_subject_refs': references_schema(),
        'source_context_refs': references_schema('context'),
        'source_refs': references_schema('source'),
        'measurement_keys': strings_schema(),
        'relations': {'type': 'array', 'items': relation_schema()},
        'selected_components': {'type': 'array', 'items': component_selection_schema()},
        'unavailable_sheet_refs': references_schema('source'),
        'missing_inputs': missing_inputs_schema(),
        'qualifications': strings_schema(),
        'formula': {'type': 'string'}, 'meaning': {'type': 'string'},
        'annotation_credit': {'type': 'null'}})


def aggregation_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A108'},
        'evaluation_scope': {'const': SCOPE},
        'assertion_ref': reference_schema('hypothesis'),
        'target_context_ref': reference_schema('context', True),
        'cells': obj({name: aggregation_cell_schema() for name in COMPONENTS}),
        'annotation_credit': {'type': 'null'}})


def _fail(reason):
    raise ContractError('a108_aggregation_' + reason)


def _unique_rows(rows):
    return list({canonical(row): deepcopy(row) for row in rows}.values())


def _validate_selected_cell(row, arguments):
    if row['component'] != 'evidence_amount':
        _fail('evidence_amount_component_required')
    if row['assertion_ref'] != arguments['assertion_ref']:
        _fail('assertion_binding_mismatch')
    if row['target_context_ref'] != arguments['target_context_ref']:
        _fail('target_context_binding_mismatch')
    if row['domain'] != DOMAIN_BY_TYPE[row['grader_type']]:
        _fail('grader_domain_mismatch')
    actual_sets = sets_from_relations(row['relations'])
    if actual_sets != row['observation_sets']:
        _fail('observation_set_relation_mismatch')
    if not row['relations']:
        if row['value'] is not None or row['available_value'] is not None or row['status'] != 'unavailable':
            _fail('empty_selection_value_mismatch')
    else:
        expected = count_sets(actual_sets)['evidence_amount']
        if row['value'] != expected or row['available_value'] != expected or row['status'] == 'unavailable':
            _fail('source_count_mismatch')


def aggregate_a108(arguments, source_cells):
    """Union exactly selected, possessed, authenticated subscoring components.

    The storage adapter verifies saved-cell identity and actual receipt. This
    function verifies the scientific bindings and calculates cardinalities; it
    cannot acquire private cells or assign new scientific interpretations.
    """
    from .literature_a108_grading_storage import grading_cells_schema

    validate_schema(arguments, aggregation_population_schema())
    validate_schema(source_cells, grading_cells_schema())
    args, received = deepcopy(arguments), deepcopy(source_cells)
    requested = [(item['sheet_ref'], item['component']) for item in args['contributions']]
    if len(requested) != len(set(requested)):
        _fail('duplicate_component_selection')
    rows = {}
    for row in received:
        key = row['sheet_ref'], row['component']
        if key in rows:
            _fail('duplicate_source_component')
        rows[key] = row
        _validate_selected_cell(row, args)
    if set(rows) != set(requested):
        _fail('selected_components_not_received')

    # A changed interpretation of one original observation/claim is a revision,
    # not independent support and conflict. Different contextual claims may
    # legitimately give the same original observation both directional roles.
    relation_directions = {}
    for row in received:
        for relation in row['relations']:
            key = relation['original_observation_key'], relation['context_claim_ref']
            prior = relation_directions.setdefault(key, relation['relation'])
            if prior != relation['relation']:
                _fail('incompatible_selected_revisions')

    cells = {}
    for component in COMPONENTS:
        selected = [rows[key] for key in requested
                    if component == 'overall' or rows[key]['domain'] == component]
        relations = _unique_rows(relation for row in selected for relation in row['relations'])
        sets = sets_from_relations(relations)
        values = count_sets(sets) if relations else {name: None for name in COUNT_COMPONENTS}
        metadata = relation_metadata(relations)
        source_refs = list(dict.fromkeys([
            *metadata['source_refs'], *(row['sheet_ref'] for row in selected)]))
        metadata['source_refs'] = source_refs
        missing = _unique_rows(item for row in selected for item in row['missing_inputs'])
        unavailable = list(dict.fromkeys(row['sheet_ref'] for row in selected
                                        if row['status'] == 'unavailable'))
        partial = bool(missing or unavailable or any(row['status'] == 'partial' for row in selected))
        qualifiers = [*metadata['qualifications'],
            'counts_of_assessed_original_contextual_observations',
            'shared_observations_unioned_not_child_scores_summed',
            'no_annotation_probability_or_investigation_progress_inferred']
        if any(row['status'] == 'conditional' for row in selected):
            qualifiers.append('contains_source_qualified_transfer_or_condition_specific_evidence')
        if not selected:
            qualifiers.append('no_subscoring_component_selected_for_this_domain')
        if partial:
            qualifiers.append('known_eligible_counts_preserved_with_unresolved_selected_relations')
        metadata['qualifications'] = list(dict.fromkeys(qualifiers))
        cells[component] = {'component': component, 'evaluation_scope': SCOPE,
            'assertion_ref': args['assertion_ref'], 'target_context_ref': args['target_context_ref'],
            'value': values['evidence_amount'], 'available_value': values['evidence_amount'],
            'status': 'unavailable' if not relations else 'partial' if partial else 'complete',
            'unit': UNIT, **values, 'observation_sets': sets,
            **metadata, 'relations': relations,
            'selected_components': [{'sheet_ref': row['sheet_ref'], 'component': row['component']}
                                    for row in selected],
            'unavailable_sheet_refs': unavailable, 'missing_inputs': missing,
            'formula': '|union(selected support observation sets) union union(selected conflict observation sets)|',
            'meaning': ('Distinct original observations supporting or conflicting with the selected '
                + ('organism-context claims across all domains' if component == 'overall'
                   else component + ' claims')
                + '. Support, conflict, overlap, unresolved and net counts retain their separate meanings.'),
            'annotation_credit': None}
    result = {'version': VERSION, 'axis': 'A108', 'evaluation_scope': SCOPE,
        'assertion_ref': args['assertion_ref'], 'target_context_ref': args['target_context_ref'],
        'cells': cells, 'annotation_credit': None}
    validate_schema(result, aggregation_sheet_schema())
    return result


__all__ = ['VERSION', 'SCOPE', 'COMPONENTS', 'component_selection_schema',
    'aggregation_population_schema', 'aggregation_cell_schema',
    'aggregation_sheet_schema', 'aggregate_a108']


def annotation_scalar(cell):
    """Bound the signed balance of A108's original-observation unions.

    The extra unit in the denominator is an explicit root softening convention,
    not an observed pseudocount, prior probability, or change to A108 counts.
    """
    from collections.abc import Mapping
    from .root_axis_scalars import _result
    if cell.get('component') != 'overall':
        raise ValueError('root_scalar_final_context_component_required')
    sets = cell.get('observation_sets')
    if not isinstance(sets, Mapping) or set(sets) != {'support', 'conflict', 'unresolved'}:
        raise ValueError('root_scalar_original_observation_sets_required')
    # Use original sets rather than adding domain/child counts. A single
    # observation can legitimately belong to both directional sets.
    support = set(sets['support'])
    conflict = set(sets['conflict'])
    amount, net = len(support | conflict), len(support) - len(conflict)
    if not amount and cell.get('status') == 'unavailable':
        return _result('A108', None,
            formula='(original_support_count-original_conflict_count)/(1+original_evidence_amount)',
            inputs=cell, reasons=('no_assessed_contextual_observation',))
    if (cell.get('evidence_amount') != amount or cell.get('net_support') != net
            or cell.get('support_count') != len(support)
            or cell.get('conflict_count') != len(conflict)):
        raise ValueError('root_scalar_context_count_set_mismatch')
    value = net / (1 + amount) if amount else None
    return _result('A108', value,
        formula='(original_support_count-original_conflict_count)/(1+original_evidence_amount)',
        inputs=cell, reasons=() if amount else ('no_assessed_contextual_observation',),
        status=('partial' if cell.get('status') == 'partial' and value is not None else None))

