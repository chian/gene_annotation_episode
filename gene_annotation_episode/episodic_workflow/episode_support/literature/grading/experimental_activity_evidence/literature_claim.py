"""The candidate claim of a hypothesis record (A105 contract OWNER_DECISION 1, CLAIM_FIELDS): predicate, subject_id,
partner_id and the optional prediction pair. Pure: a hypothesis record and the names of the records it points at in,
a claim out; no Store, no custody, no I/O.

A hypothesis record (domain RECORD_SCHEMAS['hypothesis']) holds subject_refs (record IDs), predicate, value (a typed
atom) and context_refs. It holds record IDs, not molecule names, so the caller supplies ``names``: {record ref: the
name the record carries (a term label)}, read from the records by the caller. The claim is read as 'subject predicate
partner':

  predicate   the hypothesis predicate, which must be one of CLAIM_PREDICATES (a predicate no class bears is refused).
  subject_id  the name of the single subject_refs entry (several subjects are refused: the claim has one subject).
  partner_id  the name of the record the value points at (value type 'term_ref' or 'reference'); any other value type
              (a number, an enum such as absent) is not a partner and is refused, never read as null.
  prediction_under_claim, prediction_under_alternative, prediction_unit
              null: a hypothesis record has no field that states a prediction pair, so none is ever invented.

Names are returned normalized (normalize_identity_ref), as every other level carries them, and must be molecule names
(is_name)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLAIM_FIELDS,
    CLAIM_PREDICATES,
    is_name,
    normalize_identity_ref,
)

PARTNER_VALUE_TYPES = ('term_ref', 'reference')


def validate_claim(claim):
    """Refuse a claim that has fields outside CLAIM_FIELDS or misses one, a predicate outside CLAIM_PREDICATES, a subject or
    partner that is not a molecule name, or a prediction that breaks the pair rule (both numbers and a unit, or none)."""
    if not isinstance(claim, dict) or set(claim) != set(CLAIM_FIELDS):
        raise ValueError(f'claim must hold exactly the CLAIM_FIELDS {sorted(CLAIM_FIELDS)}')
    if claim['predicate'] not in CLAIM_PREDICATES:
        raise ValueError(f"claim.predicate is outside CLAIM_PREDICATES: {claim['predicate']!r}")
    for name, nullable in (('subject_id', False), ('partner_id', True)):
        value = claim[name]
        if value is None and nullable:
            continue
        if not isinstance(value, str) or not is_name(value) or value != normalize_identity_ref(value):
            raise ValueError(f'claim.{name} must be a normalized molecule name{" or null" if nullable else ""}: {value!r}')
    pair = (claim['prediction_under_claim'], claim['prediction_under_alternative'], claim['prediction_unit'])
    if any(item is not None for item in pair) and any(item is None for item in pair):
        raise ValueError('claim prediction_under_claim, prediction_under_alternative and prediction_unit are given together or all null')
    return claim


def _name_of(ref, names, role):
    if ref not in names:
        raise ValueError(f'the {role} record {ref!r} has no name in ``names``')
    name = names[ref]
    if not isinstance(name, str):
        raise ValueError(f'the name of the {role} record {ref!r} must be a string: {name!r}')
    return normalize_identity_ref(name)


def claim_of_hypothesis(hypothesis, names):
    if not isinstance(hypothesis, dict):
        raise ValueError('hypothesis must be a mapping')
    subject_refs = hypothesis['subject_refs']
    if len(subject_refs) != 1:
        raise ValueError(f'a claim has one subject; the hypothesis has {len(subject_refs)} subject_refs')
    value = hypothesis['value']
    if value['type'] not in PARTNER_VALUE_TYPES:
        raise ValueError(f"the hypothesis value of type {value['type']!r} is not a partner record; no claim is read from it")
    claim = {
        'predicate': hypothesis['predicate'],
        'subject_id': _name_of(subject_refs[0], names, 'subject'),
        'partner_id': _name_of(value['ref'], names, 'partner'),
        'prediction_under_claim': None,
        'prediction_under_alternative': None,
        'prediction_unit': None,
    }
    return validate_claim(claim)
