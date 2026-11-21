"""The candidate claim of a hypothesis record (A105 contract OWNER_DECISION 1, CLAIM_FIELDS): predicate, subject_id and
partner_id; a claim names molecules only, never a physical prediction or threshold. Pure: a hypothesis record and the
names of the records it points at in, a claim out; no Store, no custody, no I/O.

A hypothesis record (domain RECORD_SCHEMAS['hypothesis']) holds subject_refs (record IDs), predicate, value (a typed
atom) and context_refs. It holds record IDs, not molecule names, so the caller supplies ``names``: {record ref: the
name the record carries (a term label)}, read from the records by the caller. The claim is read as 'subject predicate
partner':

  predicate   the hypothesis predicate, which must be one of CLAIM_PREDICATES (a predicate no class bears is refused).
  subject_id  the name of the single subject_refs entry (several subjects are refused: the claim has one subject).
  partner_id  the name of the record the value points at (value type 'term_ref' or 'reference'); any other value type
              (a number, an enum such as absent) is not a partner and is refused, never read as null.

Names are returned normalized (normalize_identity_ref), as every other level carries them, and must be molecule names
(is_name)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLAIM_FIELDS,
    CLAIM_PREDICATES,
    is_name,
    normalize_identity_ref,
)

PARTNER_VALUE_TYPES = ('term_ref', 'reference')

# 'catalyzes' (activity_rate class; decided 2026-11-21, owner to confirm). The A105 hypotheses of this predicate carry a
# reaction term (a 'term_ref' whose term record has term_type 'reaction'), which is not a molecule. The claim is built from
# the hypothesis record and the LABELS of the records it points at; the term_type is on the term record and is not given to
# this module, so a 'term_ref' that is a reaction cannot be told from a 'term_ref' that is a chemical here. For 'catalyzes'
# a 'term_ref' value therefore gives partner_id null (bearing by the target, the enzyme, alone). A 'reference' value points
# at a molecule record (the substrate) and stays the partner, so the record's stated substrate must then agree with it
# (bearing, partner_contradicts_claim). MISSING, needs a change outside G: the caller (the page's hypothesis_claim in task.py)
# would have to pass the term types for a chemical term_ref to be kept as a substrate partner.
TERM_PARTNER_IS_NOT_A_MOLECULE = ('catalyzes',)


def validate_claim(claim):
    """Refuse a claim that has fields outside CLAIM_FIELDS or misses one, a predicate outside CLAIM_PREDICATES, or a subject
    or partner that is not a molecule name."""
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
    if hypothesis['predicate'] in TERM_PARTNER_IS_NOT_A_MOLECULE and value['type'] == 'term_ref':
        partner_id = None
    else:
        partner_id = _name_of(value['ref'], names, 'partner')
    claim = {
        'predicate': hypothesis['predicate'],
        'subject_id': _name_of(subject_refs[0], names, 'subject'),
        'partner_id': partner_id,
    }
    return validate_claim(claim)
