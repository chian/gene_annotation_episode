"""Render shared evidence from saved receiver-authorized grading, without prose.

The publication advertises records. The ordinary read admits them. Only then
may existing scoring views supply these exact saved results. This module grants
no references, reads no private source bodies and computes no score or credit.
"""
from collections.abc import Mapping
from copy import deepcopy
import json


_SCORING_VIEWS = (
    ('a101_sheet', 'A101 sequence homology scoring sheet'),
    ('a102_sheet', 'A102 structural evidence scoring sheet'),
    ('a103_sheet', 'A103 genomic context scoring sheet'),
    ('a104_sheet', 'A104 evolutionary evidence scoring sheet'),
    ('target_sheets', 'Saved scoring for the received target'),
    ('tool_attachments', 'Saved grading for this measurement and use'),
    ('source_contributions', 'Saved source contribution to the scoring sheet'),
    ('literature_current_scoring_sheets', 'Saved literature subscoring and main evidence scoring sheets'),
    ('literature_assay_grading_cells', 'Saved A105 assay subscoring cells'),
    ('literature_a105_aggregation_cells', 'Saved A105 main evidence scoring cells'),
    ('literature_intervention_grading_cells', 'Saved A106 intervention subscoring cells'),
    ('literature_a106_subscore_cells', 'Saved A106 main evidence scoring cells'),
    ('literature_a108_grading_cells', 'Saved A108 contextual subscoring cells'),
    ('literature_a108_aggregation_cells', 'Saved A108 main evidence scoring cells'),
    ('component_axis_scoring_sheets', 'Saved component evidence scoring sheets'),
    ('received_structural_evidence', 'Received structural grading'),
    ('received_partner_and_chemical_evidence', 'Received experimental component grading'),
    ('received_partner_and_chemical_native_components', 'Received native component grading'),
    ('received_partner_and_chemical_qualifications', 'Saved grading for this particular component use'),
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
                    from .episode_work_report import _adapter_results
                    presented = _adapter_results(
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
