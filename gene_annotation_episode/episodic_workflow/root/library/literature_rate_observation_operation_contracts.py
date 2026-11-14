"""Original reported-observation operation schemas and identifiers; no reading or grading."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.domain import REF, obj
from .literature_rate_observation_input_contracts import CELL, TEXT, SOURCE_KINDS, label_schema

PROVIDER='literature.a105.reported_rate_observations'


GRID_POPULATION='a105_reported_curve_population_v1'


GRID_REQUESTED='requested_rate_grid_components'


def rate_observation_population_schema():
    observation = obj({'label': label_schema(), 'value_cell': deepcopy(CELL)})
    group = obj({'label': label_schema(), 'observations': {'type': 'array',
        'minItems': 1, 'items': observation}})
    return obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
        'worksheet': deepcopy(TEXT), **{name: label_schema() for name in ('panel','subject','native_unit')},
        'groups': {'type': 'array', 'minItems': 1, 'items': group},
        'reference_group': deepcopy(TEXT), 'test_group': deepcopy(TEXT)})


def rate_observation_operation_schema():
    from .literature_rate_observation_input_contracts import reported_rate_grid_population_schema
    from .literature_reported_curve_precision_contracts import reported_curve_precision_request_schema
    return {'type':'object','anyOf':[rate_observation_population_schema(),obj({
        'version':{'const':GRID_POPULATION},'grid':reported_rate_grid_population_schema(),
        'calculation':reported_curve_precision_request_schema()})]}


