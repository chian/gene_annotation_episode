"""A107 original genomic overlap selected result; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_genomic_overlap_contracts import validate_genomic_overlap_record

def _require(condition, code='genomic_overlap_worker_invalid_record'):
    if not condition:
        raise ValueError(code)

def _selector(value, *, mode, request=None):
    value = validate_genomic_overlap_record('Selector', value)
    _require(value['mode'] == mode and len(set(value['comparison_keys'])) == len(value['comparison_keys']))
    for name in ('minimum_a_fraction', 'minimum_b_fraction'):
        fraction = value['parameters'][name]
        _require(fraction['numerator'] <= fraction['denominator'])
    projection = value['projection']
    occurrences = [(r['set_key'], r['occurrence_key']) for r in projection['occurrence_keys']]
    _require(len(set(occurrences)) == len(occurrences))
    _require(projection['kind'] == 'occurrence_rows' or not occurrences)
    if request is not None:
        keys = [row['comparison_key'] for row in request['comparisons']]
        _require([key for key in keys if key in value['comparison_keys']] == value['comparison_keys'], 'genomic_overlap_worker_selector_binding')
        selected_sets = {pair[side] for pair in request['comparisons'] if pair['comparison_key'] in value['comparison_keys'] for side in ('a_set_key', 'b_set_key')}
        _require(all((key in selected_sets for key, _ in occurrences)))
    return value
