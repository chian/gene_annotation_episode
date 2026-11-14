"""Explain the existing native rate selectors without changing their contract.

This module adds descriptions to a fresh copy of the frozen reader's schema.
It acquires no source, nominates no argument, interprets no experiment and
performs no parsing, numerical calculation, dispatch or observation accounting.
"""
from __future__ import annotations
from copy import deepcopy
from .literature_rate_native_inputs import rate_source_population_schema
from gene_annotation_episode.episodic_workflow.root.a107.library.literature_source_operand_information import _DEFINITION_GRAMMAR, _NUMBER, _WITNESS, _interpreted, _number, _unit, _witness

def rate_source_population_schema_with_information():
    """Return the existing closed schema with operand descriptions only."""
    schema = deepcopy(rate_source_population_schema())
    schema['description'] = 'Witness offsets use zero-based half-open source UTF-8 bytes; inner numeric selectors use Unicode characters within quote. Exact bytes verify custody, not experimental meaning. ' + _DEFINITION_GRAMMAR
    fields = schema['properties']
    _witness(fields['experiment']['anyOf'][0])
    for role in ('reference', 'test'):
        arm = fields['arms']['properties'][role]['anyOf'][0]['properties']
        for meaning in ('subject', 'construct', 'preparation', 'experiment', 'label', 'condition', 'endpoint', 'normalization', 'measurement_identity'):
            _witness(arm[meaning]['anyOf'][0])
        rate = arm['rate']['anyOf'][0]['properties']
        _number(rate['number'])
        endpoint_path = 'arguments.arms.' + role + '.endpoint'
        _unit(rate['unit'], endpoint_path)
        uncertainty = arm['uncertainty']['properties']
        _number(uncertainty['magnitude']['anyOf'][0])
        _number(uncertainty['count']['anyOf'][0])
        _unit(uncertainty['unit'], endpoint_path)
        _witness(uncertainty['kind_witnesses']['items'])
        _interpreted(uncertainty['sampling_basis'])
    comparison = fields['comparison']['properties']
    for relationship in ('subject_relation', 'endpoint_relation', 'normalization_relation'):
        _interpreted(comparison[relationship])
    _witness(comparison['intended_change']['anyOf'][0])
    _interpreted(fields['dependence'])
    _interpreted(fields['observation_model'])
    return schema
__all__ = ['rate_source_population_schema_with_information']
