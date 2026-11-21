"""The investigation_finding features of one A105 subscoring row, read by code from the row (never typed by a model,
never prose). Pure: a validated row in, a validated feature record out; no Store, no custody, no I/O.

Which row field feeds which feature is fixed by the contract (FEATURE_SOURCES); the feature record is checked against
the contract's FEATURE_FIELDS. The contract defines feature sources for the subscoring row only; the main-sheet row and
the axis output have none, so this module has no main_row_features and no axis_features.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    FEATURE_FIELDS,
    FEATURE_SOURCES,
    validate_features,
    validate_row,
)

# feature name -> row field, taken from FEATURE_SOURCES: a string source is one feature fed by that row field, a tuple
# source is several row fields each carried under its own name.
_ROW_FIELD_OF_FEATURE = {
    'sheet_ref': FEATURE_SOURCES['sheet_ref'],
    'evidence_type': FEATURE_SOURCES['evidence_type'],
    'assertion_ref': FEATURE_SOURCES['assertion_ref'],
    'target_id': FEATURE_SOURCES['target_id'],
    **{name: name for name in FEATURE_SOURCES['number_of_assays']},
    'relative_deviation': FEATURE_SOURCES['deviation'],
    **{name: name for name in FEATURE_SOURCES['signal']},
    'status': FEATURE_SOURCES['status'],
}


def row_features(row):
    """The investigation_finding features of one subscoring row (FEATURE_FIELDS): the sheet reference (row_ref), the
    evidence type (sheet), the candidate (assertion_ref), the target the evidence is about (target_id, OWNER_DECISION 18), the number of assays (experiments, independent_groups), the
    statistical deviation (relative_deviation, null when the sheet has none), the signal (net, support, opposition; null
    when the status is unknown) and the status (row_status). An unknown stays null and is never turned into a number.
    The row is a COMPLETE subscoring row (validate_row first: a prose or unknown field refuses it); the record is
    checked with the contract's validate_features."""
    validate_row(row)
    if set(_ROW_FIELD_OF_FEATURE) != set(FEATURE_FIELDS):
        raise ValueError('the contract FEATURE_SOURCES and FEATURE_FIELDS name different features')
    features = {feature: row[field] for feature, field in _ROW_FIELD_OF_FEATURE.items()}
    return validate_features(features)
