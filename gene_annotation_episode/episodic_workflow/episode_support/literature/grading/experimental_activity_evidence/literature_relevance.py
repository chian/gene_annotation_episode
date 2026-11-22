"""Relevance: what was asked. Did the experiment test the claim's question? (A105 contract, SIGNATURES['relevance']).

Computed by code from controlled fields only, never by the model. Pure: arguments in, a controlled record out. Who was
measured is a separate question, answered by literature_target (owner, 2026-11-21: "Use target and relevance. It does make
sense you need both"). The real case that needed this: an ultracentrifugation experiment on PopZ alone (no partner, no
interaction stated, no measured effect) passed the target check for the claim "PopZ binds ParB", yet it never tested binding.

record  a mapping with 'experiment_type', 'target_id', 'partner_id' (as literature_target), 'statement' (a value of
        QUALITATIVE_STATEMENT or None) and 'effect_measured' (a bool: the converted grader has a point effect).
claim   the candidate claim (contract CLAIM_FIELDS): predicate, subject_id and partner_id (or null).

Result: {'relevance': one of RELEVANCE, 'reasons': [one code of RELEVANCE_REASONS]}. Checked in this order:

  irrelevant  experiment_type_cannot_test_predicate: the type's class does not list the claim's predicate.
  relevant    claim_names_no_partner: the claim names no partner (a reaction term, or a claim about the subject alone); the
              record's partner is not compared.
  relevant    partner_agrees: both name a partner and they are equal.
  relevant    partner_route: a symmetric predicate, the record's target is the claim's partner and its partner the claim's subject.
  irrelevant  other_partner: both name a partner and they differ.
  unresolved  partner_not_stated: the claim names a partner, the record names none, but the experiment measured an interaction
              (an interaction statement, or a measured effect). The owner's standing rule: a missing identity link gets an
              unresolved grade, it is not thrown out. On the row it is treated exactly as such a result was treated before
              this check existed (no new weight, no new threshold).
  irrelevant  no_partner_in_experiment: the claim names a partner, the record names none and measured no interaction.

'irrelevant' results stay off the row and are never scored; 'relevant' and 'unresolved' may enter a row (RELEVANCE_ON_ROW).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLAIM_FIELDS,
    CLAIM_PREDICATES,
    CLAIM_PREDICATES_BY_CLASS,
    CLASS_OF_EXPERIMENT_TYPE,
    EXPERIMENT_TYPES,
    QUALITATIVE_STATEMENT,
    RELEVANCE,
    is_name,
    comparable_identity_name,
    normalize_identity_ref,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_target import is_partner_route

# The fixed vocabulary of reason codes (codes, never prose). Exactly one is returned per call.
RELEVANCE_REASONS = (
    'claim_names_no_partner',                          # relevant
    'partner_agrees',                                  # relevant
    'partner_route',                                   # relevant
    'other_partner',                                   # irrelevant
    'no_partner_in_experiment',                        # irrelevant
    'experiment_type_cannot_test_predicate',           # irrelevant
    'partner_not_stated',                              # unresolved
)


def _check_record(record):
    if not isinstance(record, dict):
        raise ValueError('relevance record must be a mapping')
    experiment_type = record['experiment_type']
    if experiment_type not in EXPERIMENT_TYPES:
        raise ValueError(f'relevance record.experiment_type is outside EXPERIMENT_TYPES: {experiment_type!r}')
    for name in ('target_id', 'partner_id'):
        value = record[name]
        if value is not None and (not isinstance(value, str) or not is_name(normalize_identity_ref(value))):
            raise ValueError(f'relevance record.{name} must be a molecule name or null: {value!r}')
    statement = record['statement']
    if statement is not None and statement not in QUALITATIVE_STATEMENT:
        raise ValueError(f'relevance record.statement is outside QUALITATIVE_STATEMENT: {statement!r}')
    if not isinstance(record['effect_measured'], bool):
        raise ValueError(f"relevance record.effect_measured must be a bool: {record['effect_measured']!r}")
    return experiment_type


def _check_claim(claim):
    if not isinstance(claim, dict):
        raise ValueError('relevance claim must be a mapping')
    extra = sorted(set(claim) - set(CLAIM_FIELDS))
    if extra:
        raise ValueError(f'relevance claim has fields outside CLAIM_FIELDS: {extra}')
    predicate = claim['predicate']
    if predicate not in CLAIM_PREDICATES:
        raise ValueError(f'relevance claim.predicate is outside CLAIM_PREDICATES: {predicate!r}')
    for name, nullable in (('subject_id', False), ('partner_id', True)):
        value = claim[name]
        if value is None and nullable:
            continue
        if not isinstance(value, str) or not is_name(normalize_identity_ref(value)):
            raise ValueError(f'relevance claim.{name} must be a molecule name{" or null" if nullable else ""}: {value!r}')
    return predicate


def _result(relevance_value, reason):
    if relevance_value not in RELEVANCE or reason not in RELEVANCE_REASONS:
        raise ValueError(f'relevance result outside its vocabulary: {relevance_value!r}, {reason!r}')
    return {'relevance': relevance_value, 'reasons': [reason]}


def relevance(record, claim):
    experiment_type = _check_record(record)
    predicate = _check_claim(claim)
    if predicate not in CLAIM_PREDICATES_BY_CLASS.get(CLASS_OF_EXPERIMENT_TYPE[experiment_type], ()):
        return _result('irrelevant', 'experiment_type_cannot_test_predicate')
    if claim['partner_id'] is None:
        return _result('relevant', 'claim_names_no_partner')
    if record['partner_id'] is not None:
        if comparable_identity_name(record['partner_id']) == comparable_identity_name(claim['partner_id']):
            return _result('relevant', 'partner_agrees')
        if record['target_id'] is not None and is_partner_route(record, claim):
            return _result('relevant', 'partner_route')
        return _result('irrelevant', 'other_partner')
    if record['statement'] in ('interaction_detected', 'interaction_not_detected') or record['effect_measured']:
        return _result('unresolved', 'partner_not_stated')
    return _result('irrelevant', 'no_partner_in_experiment')
