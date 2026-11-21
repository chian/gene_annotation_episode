"""Bearing: how one experiment's target relates to one candidate claim (A105 contract, SIGNATURES['bearing']).

Computed by code from controlled fields only, never by the model. Pure: arguments in, a controlled record out.

record  a mapping that carries the experiment's identity features (contract IDENTITY_FIELDS): 'experiment_type',
        'target_id' (the molecule the assay is about; null when no member record states it) and 'partner_id' (the
        optional other molecule the target is tested against; null when not stated). Each is a record reference or null.
claim   the candidate claim (contract CLAIM_FIELDS): predicate, subject_id, partner_id (or null), and the prediction
        fields, which bearing does not read.

OWNER_DECISION 18 (the target molecule). The target is the one identity field bearing requires. Values are compared
after the contract's normalize_identity_ref (casefold, whitespace collapse).

Result: {'bearing': one of BEARING, 'reasons': [one code of BEARING_REASONS]}. Checked in this order:

  none               target_not_stated: the record states no target_id. The grader bears on no candidate and earns no
                     score; it still counts in the credit as the contract's resolution says (no 'target known' question
                     is added; a target left unknown leaves the direction unknown).
  none               experiment_type_cannot_bear_on_predicate: the type's class does not list the claim's predicate in
                     CLAIM_PREDICATES_BY_CLASS.
  different_subject  target_differs_from_subject: a target is stated and differs from the claim's subject_id.
  different_subject  partner_contradicts_claim: the target equals the subject, BOTH sides state a partner, and they differ.
  direct             predicate_and_target_agree: the class bears the predicate, the target equals the subject, and when
                     both sides state a partner the partners are equal (a partner stated by one side only is not a
                     conflict).
  transfer           NEVER returned: the contract has no relation vocabulary (homolog / related subject) yet.

SYMMETRIC predicates (SYMMETRIC_PREDICATES): when the target is the claim's partner and the record's partner is the
claim's subject (both stated), the result is direct, reason partner_route. A pair named only by the target stays
different_subject.

Only 'direct' gives support or opposition (the contract), so every other case stays out of the scores.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    BEARING,
    CLAIM_FIELDS,
    CLAIM_PREDICATES,
    CLAIM_PREDICATES_BY_CLASS,
    SYMMETRIC_PREDICATES,
    CLASS_OF_EXPERIMENT_TYPE,
    EXPERIMENT_TYPES,
    is_name,
    normalize_identity_ref,
)

# The fixed vocabulary of reason codes (codes, never prose). Exactly one is returned per call.
BEARING_REASONS = (
    'predicate_and_target_agree',                      # direct
    'partner_route',                                   # direct: symmetric predicate, target is the claim partner and partner the claim subject
    'target_differs_from_subject',                    # different_subject
    'partner_contradicts_claim',                      # different_subject: target agrees, both partners stated, they differ
    'target_not_stated',                              # none: the record states no target
    'experiment_type_cannot_bear_on_predicate',       # none: the type's class does not list the predicate
)


def _check_record(record):
    if not isinstance(record, dict):
        raise ValueError('bearing record must be a mapping')
    experiment_type = record['experiment_type']
    if experiment_type not in EXPERIMENT_TYPES:
        raise ValueError(f'bearing record.experiment_type is outside EXPERIMENT_TYPES: {experiment_type!r}')
    for name in ('target_id', 'partner_id'):
        value = record[name]
        if value is not None and (not isinstance(value, str) or not is_name(normalize_identity_ref(value))):
            raise ValueError(f'bearing record.{name} must be a molecule name or null: {value!r}')
    return experiment_type


def _check_claim(claim):
    if not isinstance(claim, dict):
        raise ValueError('bearing claim must be a mapping')
    extra = sorted(set(claim) - set(CLAIM_FIELDS))
    if extra:
        raise ValueError(f'bearing claim has fields outside CLAIM_FIELDS: {extra}')
    predicate = claim['predicate']
    if predicate not in CLAIM_PREDICATES:
        raise ValueError(f'bearing claim.predicate is outside CLAIM_PREDICATES: {predicate!r}')
    for name, nullable in (('subject_id', False), ('partner_id', True)):
        value = claim[name]
        if value is None and nullable:
            continue
        if not isinstance(value, str) or not is_name(normalize_identity_ref(value)):
            raise ValueError(f'bearing claim.{name} must be a molecule name{" or null" if nullable else ""}: {value!r}')
    return predicate


def _result(bearing, reason):
    if bearing not in BEARING or reason not in BEARING_REASONS:
        raise ValueError(f'bearing result outside its vocabulary: {bearing!r}, {reason!r}')
    return {'bearing': bearing, 'reasons': [reason]}


def bearing(record, claim):
    experiment_type = _check_record(record)
    predicate = _check_claim(claim)
    if record['target_id'] is None:
        return _result('none', 'target_not_stated')
    if predicate not in CLAIM_PREDICATES_BY_CLASS.get(CLASS_OF_EXPERIMENT_TYPE[experiment_type], ()):
        return _result('none', 'experiment_type_cannot_bear_on_predicate')
    if normalize_identity_ref(record['target_id']) != normalize_identity_ref(claim['subject_id']):
        if predicate in SYMMETRIC_PREDICATES and record['partner_id'] is not None and claim['partner_id'] is not None \
                and normalize_identity_ref(record['target_id']) == normalize_identity_ref(claim['partner_id']) \
                and normalize_identity_ref(record['partner_id']) == normalize_identity_ref(claim['subject_id']):
            return _result('direct', 'partner_route')
        return _result('different_subject', 'target_differs_from_subject')
    if record['partner_id'] is not None and claim['partner_id'] is not None \
            and normalize_identity_ref(record['partner_id']) != normalize_identity_ref(claim['partner_id']):
        return _result('different_subject', 'partner_contradicts_claim')
    return _result('direct', 'predicate_and_target_agree')
