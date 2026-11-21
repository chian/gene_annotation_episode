"""Bearing: how one experiment's target relates to one candidate claim (A105 contract, SIGNATURES['bearing']).

Computed by code from controlled fields only, never by the model. Pure: arguments in, a controlled record out.

record  a mapping that carries the experiment's identity features (contract IDENTITY_FIELDS): 'experiment_type',
        'target_id' (the molecule the assay is about; null when no member record states it) and 'partner_id' (the
        optional other molecule the target is tested against; null when not stated). Each is a record reference or null.
claim   the candidate claim (contract CLAIM_FIELDS): predicate, subject_id and partner_id (or null).

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
  transfer           target_sequence_related: the assayed protein was identified (a closeness is given) and is below the
                     exact sequence (EXACT_SEQUENCE_CLOSENESS): a related protein. (2026-11-21: the third argument of
                     bearing, subject_closeness, is the closeness of the assayed protein's sequence to the claim
                     subject's, or None when it was not identified. Identified: the sequence decides and a name that
                     differs no longer excludes; not identified: the names decide, as above.)

'catalyzes' (activity_rate class) is NOT symmetric: the subject is the enzyme (the record's target_id), so a record whose target
is the claim's substrate or reaction is different_subject. Its claim partner is null when the hypothesis value is a reaction
term (literature_claim.TERM_PARTNER_IS_NOT_A_MOLECULE), and then the record's stated substrate is not compared (a partner stated
by one side only is not a conflict): bearing is by the target alone. When the claim names a substrate molecule and the record
states another substrate, the result is different_subject (partner_contradicts_claim). No code differs from binding: the rule
above already does this.

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
    'target_sequence_identical',                      # direct: the names differ, the assayed protein's sequence is the target's
    'target_sequence_related',                        # transfer: the assayed protein is a related protein (closeness below the exact sequence)
)

# EXPERT_REVIEW (owner to confirm): the bottom of the identified_closeness scale, the standing of a result whose assayed protein
# could not be identified (or has no sequence). 0.05, not 0: owner rule "no gate, every score gradual", and the result still
# comes from a real measurement of a protein the paper names; but "only credit for identifiable sequences", so it is near
# the bottom. Also the standing of a resolved subject of closeness 0, so the scale has no step between the two.
SUBJECT_UNIDENTIFIED_STANDING = 0.05
# EXPERT_REVIEW (owner to confirm): the closeness from which the assayed protein is the exact sequence (bearing 'direct');
# below it the protein is related (bearing 'transfer'). The label only: the contribution scales smoothly with the closeness
# itself (identified_closeness), so no threshold changes any number. 0.99 leaves room for the rounding of an identity x
# coverage closeness over identical sequences (identical sequences give 1.0).
EXACT_SEQUENCE_CLOSENESS = 0.99


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


def _is_partner_route(record, claim):
    return (claim['predicate'] in SYMMETRIC_PREDICATES and record['partner_id'] is not None and claim['partner_id'] is not None
            and normalize_identity_ref(record['target_id']) == normalize_identity_ref(claim['partner_id'])
            and normalize_identity_ref(record['partner_id']) == normalize_identity_ref(claim['subject_id']))


def assayed_molecule(record, claim):
    """'partner' when the molecule whose sequence must be identified is the record's partner (the symmetric partner route:
    the record's partner is the claim's subject), else 'target'. Names only; the record's target must be stated."""
    return 'partner' if (normalize_identity_ref(record['target_id']) != normalize_identity_ref(claim['subject_id'])
                         and _is_partner_route(record, claim)) else 'target'


def bearing(record, claim, subject_closeness):
    """subject_closeness: the closeness (0..1) of the assayed protein's sequence to the claim subject's, or None when the
    assayed protein was not identified. Identified: the sequence decides (direct at the exact sequence, transfer for a related
    protein; the name is no longer the test). Not identified: the names decide as before (equal names direct, differing names
    different_subject)."""
    experiment_type = _check_record(record)
    predicate = _check_claim(claim)
    if subject_closeness is not None and not 0.0 <= subject_closeness <= 1.0:
        raise ValueError(f'bearing subject_closeness must be in 0..1 or None: {subject_closeness!r}')
    if record['target_id'] is None:
        return _result('none', 'target_not_stated')
    if predicate not in CLAIM_PREDICATES_BY_CLASS.get(CLASS_OF_EXPERIMENT_TYPE[experiment_type], ()):
        return _result('none', 'experiment_type_cannot_bear_on_predicate')
    names_equal = normalize_identity_ref(record['target_id']) == normalize_identity_ref(claim['subject_id'])
    partner_route = not names_equal and _is_partner_route(record, claim)
    if not names_equal and not partner_route and subject_closeness is None:
        return _result('different_subject', 'target_differs_from_subject')
    if not partner_route and record['partner_id'] is not None and claim['partner_id'] is not None \
            and normalize_identity_ref(record['partner_id']) != normalize_identity_ref(claim['partner_id']):
        return _result('different_subject', 'partner_contradicts_claim')
    if subject_closeness is None:
        return _result('direct', 'partner_route' if partner_route else 'predicate_and_target_agree')
    if subject_closeness < EXACT_SEQUENCE_CLOSENESS:
        return _result('transfer', 'target_sequence_related')
    return _result('direct', 'partner_route' if partner_route else 'predicate_and_target_agree' if names_equal else 'target_sequence_identical')


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
