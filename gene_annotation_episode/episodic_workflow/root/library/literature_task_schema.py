"""Original commissioned literature task schema; no credit execution."""
from gene_annotation_episode.domain import REF, obj

VERSION = 'literature_local_task_v1'
def task_schema():
    from .literature_quantity_population_schema import quantity_population_schema
    from .literature_assay_grading_declarations import ASSAY_TYPES
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
        'cutoff': {'type': 'number', 'minimum': 0,
            'description': 'This commissioned episode stops when its available next-credit upper estimate is at or below this cutoff, measured in this task credit unit.'},
        'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0,
            'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'enum': ['A105', 'A106', 'A108']},
        'credit_unit': {'type': 'number', 'exclusiveMinimum': 0},
        'yield_settings': yield_settings}
    def task_object(properties):
        # Saved commissions predating private yield bindings did not carry
        # yield settings. A private controller requires the field explicitly.
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF,
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The original commissioned result and its explicit local credit unit. '
        'Select only a task whose typed result is requested by the original return contract. '
        'A106/A108 score computation is automatic work, not an episode-credit task.', 'anyOf': [
        task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
            'source_refs': refs}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
            'examined': {'type': 'array', 'minItems': 1, 'items': span}}),
        task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'source_answer'},
            'answer_kind': {'const': 'measurement'}, 'selection': quantity_population_schema(),
            'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                'items': {'enum': ['reported_value', 'reported_spread', 'relative_reported_spread']}}}),
        task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_experiments'},
            'experiments': {'type': 'array', 'minItems': 1, 'items': obj({
                'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}),
        task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_assembly'},
            'experiment_refs': refs, 'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                'items': {'enum': ['reliability', 'validity', 'relevance', 'attribution', 'overall']}}}),
    ]}


