"""Render shared evidence from saved receiver-authorized grading, without prose.

The publication advertises records. The ordinary read admits them. Only then
may existing scoring views supply these exact saved results. This module grants
no references, reads no private source bodies and computes no score or credit.
"""
from collections.abc import Mapping
from copy import deepcopy
import json


_SCORING_VIEWS = (
    ('literature_current_scoring_sheets', 'Saved intervention subscoring and main evidence scoring sheets'),
    ('literature_intervention_grading_cells', 'Saved A106 intervention subscoring cells'),
    ('literature_a106_subscore_cells', 'Saved A106 main evidence scoring cells'),
)
_IDENTITY_FIELDS = ('sheet_ref', 'source_ref', 'comparison_source_ref',
    'feature_source_ref', 'contrast_source_ref', 'interface_source_ref',
    'observation_ref', 'measurement_ref', 'assessment_ref')


def publication_view(body):
    """Keep old publications immutable without repeating their authored summary."""
    value = deepcopy(body)
    if value.get('kind') == 'information':
        value.pop('qualification', None)
    if (value.get('kind') == 'disposition'
            and value.get('status') in {'fulfilled', 'partially_fulfilled'}):
        value.pop('reason', None)
    return value


def outcome_view(outcome):
    """Apply the same presentation rule to retained original action outcomes."""
    if not isinstance(outcome, Mapping) or not isinstance(outcome.get('result'), Mapping):
        return outcome
    body = outcome['result']
    version = body.get('version')
    if not isinstance(version, str) or not version.startswith('shared_investigation_information_'):
        return outcome
    return {**outcome, 'result': publication_view(body)}


def saved_grading_results(evidence_refs, *views):
    """Copy exact selected saved versions from existing authorized sheet views.

    Matching a paper or target mentioned somewhere in a sheet does not select
    that sheet. Only its own publication identity may match the selected record.
    Call this at the original read, after receipt, and retain that snapshot so a
    later delivery or revision cannot enter this action's historical result.
    """
    selected, results, seen = set(evidence_refs), [], set()

    def collect(value, name):
        if isinstance(value, Mapping):
            identities = {value[field] for field in _IDENTITY_FIELDS
                if isinstance(value.get(field), str)}
            if selected.intersection(identities):
                saved = {key: deepcopy(child) for key, child in value.items()
                    if key != 'subscoring_sheets'}
                key = json.dumps(saved, sort_keys=True, ensure_ascii=False, allow_nan=False)
                if key not in seen:
                    seen.add(key)
                    # Existing purpose-specific presentations retain native
                    # quantities and conditions without copying embedded job
                    # files or introducing a separate scientific verdict.
                    from .episode_work_report import _intervention_results
                    presented = _intervention_results(
                        {'kind': 'tool', 'tool': 'shared.read_information'}, {'result': saved}, {})
                    results.append({'saved_in': name,
                        'saved_result': presented if any(row.get('results') for row in presented) else saved})
                return
            for child in value.values():
                collect(child, name)
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect(child, name)

    for view in views:
        if not isinstance(view, Mapping):
            continue
        for key, name in _SCORING_VIEWS:
            if key in view:
                collect(view[key], name)
    return results
