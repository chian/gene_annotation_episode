"""Target match: who was measured. Is one experiment's target the claim's protein? (A105 contract, SIGNATURES['target_match']).

Computed by code from controlled fields only, never by the model. Pure: arguments in, a controlled record out. What the
experiment asked is a separate question, answered by literature_relevance (owner, 2026-11-21: "Use target and relevance. It
does make sense you need both"); this module looks at the target alone.

record  a mapping that carries the experiment's identity features (contract IDENTITY_FIELDS): 'experiment_type',
        'target_id' (the molecule the assay is about; null when no member record states it) and 'partner_id' (the
        optional other molecule the target is tested against; null when not stated). Each is a record reference or null.
claim   the candidate claim (contract CLAIM_FIELDS): predicate, subject_id and partner_id (or null).

OWNER_DECISION 18 (the target molecule). The target is the one identity field the match requires. Values are compared
after the contract's comparable_identity_name (casefold, whitespace collapse, fused tags such as eYFP or His6 removed from the start and end).

Result: {'target_match': one of TARGET_MATCH, 'reasons': [one code of TARGET_MATCH_REASONS]}. Checked in this order:

  not_stated  target_not_stated: the record states no target_id. The grader matches no candidate and earns no score; it
              still counts in the credit as the contract's resolution says (no 'target known' question is added; a target
              left unknown leaves the direction unknown).
  different   target_differs_from_subject: a target is stated, differs from the claim's subject_id, and the assayed protein
              was not identified.
  same        target_names_agree: the target equals the subject (the assayed protein not identified, or identified as the
              exact sequence).
  same        partner_route: see below.
  same        target_sequence_identical: the names differ, the assayed protein was identified and is the exact sequence.
  related     target_sequence_related: the assayed protein was identified (a closeness is given) and is below the exact
              sequence (EXACT_SEQUENCE_CLOSENESS): a related protein. (2026-11-21: the third argument, subject_closeness, is
              the closeness of the assayed protein's sequence to the claim subject's, or None when it was not identified.
              Identified: the sequence decides and a name that differs no longer excludes; not identified: the names decide.)

'catalyzes' (activity_rate class) is NOT symmetric: the subject is the enzyme (the record's target_id), so a record whose target
is the claim's substrate or reaction is a different target. The partner (the substrate) is not looked at here: whether the
experiment tested the claim's question is relevance's.

SYMMETRIC predicates (SYMMETRIC_PREDICATES): when the target is the claim's partner and the record's partner is the
claim's subject (both stated), the target is the same, reason partner_route. A pair named only by the target stays different.

Only a result whose target match is 'same' or 'related' (and whose relevance is not 'irrelevant') gives support or opposition
(the contract's on_row), so every other case stays out of the scores.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLAIM_FIELDS,
    CLAIM_PREDICATES,
    SYMMETRIC_PREDICATES,
    EXPERIMENT_TYPES,
    TARGET_MATCH,
    is_name,
    comparable_identity_name,
    normalize_identity_ref,
)

# The fixed vocabulary of reason codes (codes, never prose). Exactly one is returned per call.
TARGET_MATCH_REASONS = (
    'target_names_agree',                              # same: the target equals the subject
    'partner_route',                                   # same: symmetric predicate, target is the claim partner and partner the claim subject
    'target_sequence_identical',                       # same: the names differ, the assayed protein's sequence is the target's
    'target_sequence_related',                         # related: the assayed protein is a related protein (closeness below the exact sequence)
    'target_differs_from_subject',                     # different
    'target_not_stated',                               # not_stated: the record states no target
)

# EXPERT_REVIEW (owner to confirm): the bottom of the identified_closeness scale, the standing of a result whose assayed protein
# could not be identified (or has no sequence). 0.05, not 0: owner rule "no gate, every score gradual", and the result still
# comes from a real measurement of a protein the paper names; but "only credit for identifiable sequences", so it is near
# the bottom. Also the standing of a resolved subject of closeness 0, so the scale has no step between the two.
SUBJECT_UNIDENTIFIED_STANDING = 0.05
# EXPERT_REVIEW (owner to confirm): the closeness from which the assayed protein is the exact sequence (target match 'same');
# below it the protein is related (target match 'related'). The label only: the contribution scales smoothly with the closeness
# itself (identified_closeness), so no threshold changes any number. 0.99 leaves room for the rounding of an identity x
# coverage closeness over identical sequences (identical sequences give 1.0).
EXACT_SEQUENCE_CLOSENESS = 0.99


def _check_record(record):
    if not isinstance(record, dict):
        raise ValueError('target_match record must be a mapping')
    experiment_type = record['experiment_type']
    if experiment_type not in EXPERIMENT_TYPES:
        raise ValueError(f'target_match record.experiment_type is outside EXPERIMENT_TYPES: {experiment_type!r}')
    for name in ('target_id', 'partner_id'):
        value = record[name]
        if value is not None and (not isinstance(value, str) or not is_name(normalize_identity_ref(value))):
            raise ValueError(f'target_match record.{name} must be a molecule name or null: {value!r}')
    return experiment_type


def _check_claim(claim):
    if not isinstance(claim, dict):
        raise ValueError('target_match claim must be a mapping')
    extra = sorted(set(claim) - set(CLAIM_FIELDS))
    if extra:
        raise ValueError(f'target_match claim has fields outside CLAIM_FIELDS: {extra}')
    predicate = claim['predicate']
    if predicate not in CLAIM_PREDICATES:
        raise ValueError(f'target_match claim.predicate is outside CLAIM_PREDICATES: {predicate!r}')
    for name, nullable in (('subject_id', False), ('partner_id', True)):
        value = claim[name]
        if value is None and nullable:
            continue
        if not isinstance(value, str) or not is_name(normalize_identity_ref(value)):
            raise ValueError(f'target_match claim.{name} must be a molecule name{" or null" if nullable else ""}: {value!r}')
    return predicate


def _result(target_match, reason):
    if target_match not in TARGET_MATCH or reason not in TARGET_MATCH_REASONS:
        raise ValueError(f'target_match result outside its vocabulary: {target_match!r}, {reason!r}')
    return {'target_match': target_match, 'reasons': [reason]}


def is_partner_route(record, claim):
    return (claim['predicate'] in SYMMETRIC_PREDICATES and record['partner_id'] is not None and claim['partner_id'] is not None
            and comparable_identity_name(record['target_id']) == comparable_identity_name(claim['partner_id'])
            and comparable_identity_name(record['partner_id']) == comparable_identity_name(claim['subject_id']))


def assayed_molecule(record, claim):
    """'partner' when the molecule whose sequence must be identified is the record's partner (the symmetric partner route:
    the record's partner is the claim's subject), else 'target'. Names only; the record's target must be stated."""
    return 'partner' if (comparable_identity_name(record['target_id']) != comparable_identity_name(claim['subject_id'])
                         and is_partner_route(record, claim)) else 'target'


def target_match(record, claim, subject_closeness):
    """subject_closeness: the closeness (0..1) of the assayed protein's sequence to the claim subject's, or None when the
    assayed protein was not identified. Identified: the sequence decides (same at the exact sequence, related for a related
    protein; the name is no longer the test). Not identified: the names decide (equal names same, differing names different)."""
    _check_record(record)
    _check_claim(claim)
    if subject_closeness is not None and not 0.0 <= subject_closeness <= 1.0:
        raise ValueError(f'target_match subject_closeness must be in 0..1 or None: {subject_closeness!r}')
    if record['target_id'] is None:
        return _result('not_stated', 'target_not_stated')
    names_equal = comparable_identity_name(record['target_id']) == comparable_identity_name(claim['subject_id'])
    partner_route = not names_equal and is_partner_route(record, claim)
    if not names_equal and not partner_route and subject_closeness is None:
        return _result('different', 'target_differs_from_subject')
    if subject_closeness is None:
        return _result('same', 'partner_route' if partner_route else 'target_names_agree')
    if subject_closeness < EXACT_SEQUENCE_CLOSENESS:
        return _result('related', 'target_sequence_related')
    return _result('same', 'partner_route' if partner_route else 'target_names_agree' if names_equal else 'target_sequence_identical')


def identified_closeness(result):
    """The result's standing factor in 0..1 (2026-11-21): how far the assayed protein is the claim's target, smooth in the
    result's subject_closeness.

        standing = SUBJECT_UNIDENTIFIED_STANDING + (1 - SUBJECT_UNIDENTIFIED_STANDING) * subject_closeness

    When a name matched several records, subject_closeness is that of the CLOSEST one (page_update measures each and keeps
    it): the closest carries the result. The number of matches (subject_match_count) is a recorded fact and lowers nothing
    (owner, 2026-11-21: "halving makes no sense"; two database entries of one protein are not two doubts).

    A subject that could not be identified (resolution 'unresolved', or a record with no sequence to compare, closeness null)
    stands at SUBJECT_UNIDENTIFIED_STANDING, the bottom of the scale: never a gate, so the scale stays continuous with a
    resolved subject of closeness 0. It reads the result's fields directly."""
    if result['subject_resolution'] == 'unresolved' or result['subject_closeness'] is None:
        return SUBJECT_UNIDENTIFIED_STANDING
    return SUBJECT_UNIDENTIFIED_STANDING + (1.0 - SUBJECT_UNIDENTIFIED_STANDING) * result['subject_closeness']
