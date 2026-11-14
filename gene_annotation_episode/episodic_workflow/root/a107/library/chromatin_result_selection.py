"""A107 original chromatin result selection; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_interaction_contracts import chromatin_record_schema, validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_received_fact_contracts import SAVED_SOURCE, validate_chromatin_fact_values

def chromatin_result_selector_schema():
    return chromatin_record_schema('ResultSelector')

def validate_chromatin_result_selector(selector, *, request):
    request = validate_chromatin_record('ChromatinRequest', request)
    selector = validate_chromatin_record('ResultSelector', selector)
    if not set(selector['population_keys']) <= {row['population_key'] for row in request['populations']}:
        raise ValueError('chromatin_result_population_conflict')
    parameters = selector['parameters']
    for field, mode in (('contact', 'cis_anchor_contact_enrichment'), ('insulation', 'cross_window_insulation_heuristic')):
        if (parameters[field] is not None) != (mode in request['analysis_modes']):
            raise ValueError('chromatin_result_analysis_mode_conflict')
    kind = selector['projection']['kind']
    if kind in {'contact_pairs', 'distance_expectations'} and parameters['contact'] is None or (kind in {'insulation_windows', 'domains'} and parameters['insulation'] is None):
        raise ValueError('chromatin_result_projection_mode_conflict')
    if selector['mode'] == 'saved_sheet_recalculation':
        validate_chromatin_fact_values(SAVED_SOURCE, [selector['saved_sheet_bundle']])
    return selector
