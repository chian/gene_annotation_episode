"""Caller-valued practical progress from validated, currently satisfied facts.

The projection counts original requirement keys, never commands or files. It
returns cumulative credit, so losing a previously established fact produces the
ordinary signed loss at the controller rather than a hidden upward clamp.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .practical_execution_records import validate_assignment


def project_practical_credit(assignment, initial_validations, receipts):
    """Project already-qualified immutable receipts; execute and validate no work."""
    assignment = validate_assignment(assignment)
    requirements = {item['key']: item for item in assignment['progress_requirements']}
    initial = {key: False for key in requirements}
    latest = {}

    def apply(validations, states):
        seen = set()
        for validation in validations:
            key = validation['key']
            if (key not in requirements or key in seen or type(validation['satisfied']) is not bool
                    or validation['predicate'] != requirements[key]['predicate']):
                raise ValueError('invalid_practical_credit_validation')
            seen.add(key)
            states[key] = validation['satisfied']
            latest[key] = deepcopy(validation)

    apply(initial_validations, initial)
    states = dict(initial)
    for receipt in receipts:
        apply(receipt['validations'], states)
    initial_credit = math.fsum(requirements[key]['credit'] for key, satisfied in initial.items() if satisfied)
    credit = math.fsum(requirements[key]['credit'] for key, satisfied in states.items() if satisfied)
    return {'credit': credit, 'operational_credit': credit, 'initial_credit': initial_credit,
        'satisfied_keys': sorted(key for key, satisfied in states.items() if satisfied),
        'requirements': [{'key': key, 'credit': requirements[key]['credit'],
            'satisfied': states[key], 'validation': deepcopy(latest.get(key))}
            for key in requirements],
        'operational_credit_binding': {'version': 'practical_requirement_credit_v1',
            'qualification': 'original_requirement_predicates_from_actual_selected_action_facts',
            'aggregation': 'sum_currently_satisfied_original_requirement_keys',
            'baseline': 'immutable_initial_validations',
            'requirements': deepcopy(assignment['progress_requirements']),
            'scientific_credit': False, 'monitoring_credit': False}}


__all__ = ['project_practical_credit']
