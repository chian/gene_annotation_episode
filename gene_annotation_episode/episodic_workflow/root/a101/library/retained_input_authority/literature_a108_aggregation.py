"""Main A108 evidence scoring sheet over admitted contextual observations.

The evidence amount is a set cardinality, not a sum of child totals. Original
observations shared by papers, database records or biological domains contribute
once to the overall amount; support, conflict and unresolved relations survive.
"""
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_a108_grading import COMPONENTS as COUNT_COMPONENTS, DOMAINS, UNIT, missing_inputs_schema, observation_sets_schema, reference_schema, references_schema, relation_schema, strings_schema
SCOPE = 'a108_across_observation_aggregation'
COMPONENTS = (*DOMAINS, 'overall')

def component_selection_schema():
    return obj({'sheet_ref': reference_schema('source'), 'component': {'const': 'evidence_amount'}})

def aggregation_cell_schema():
    return obj({'component': {'enum': list(COMPONENTS)}, 'evaluation_scope': {'const': SCOPE}, 'assertion_ref': reference_schema('hypothesis'), 'target_context_ref': reference_schema('context', True), 'value': {'type': ['integer', 'null']}, 'available_value': {'type': ['integer', 'null']}, 'status': {'enum': ['complete', 'partial', 'unavailable']}, 'unit': {'const': UNIT}, **{name: {'type': ['integer', 'null']} for name in COUNT_COMPONENTS}, 'observation_sets': observation_sets_schema(), 'observation_refs': references_schema(), 'relation_refs': references_schema('hypothesis'), 'source_subject_refs': references_schema(), 'source_context_refs': references_schema('context'), 'source_refs': references_schema('source'), 'measurement_keys': strings_schema(), 'relations': {'type': 'array', 'items': relation_schema()}, 'selected_components': {'type': 'array', 'items': component_selection_schema()}, 'unavailable_sheet_refs': references_schema('source'), 'missing_inputs': missing_inputs_schema(), 'qualifications': strings_schema(), 'formula': {'type': 'string'}, 'meaning': {'type': 'string'}, 'annotation_credit': {'type': 'null'}})
