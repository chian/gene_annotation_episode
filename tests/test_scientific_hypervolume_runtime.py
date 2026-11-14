"""Synthetic scientific-record helpers and an explicit credit-binding check."""

import pytest

from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit
from gene_annotation_episode.state import Store


def evidence(store, target, kind):
    artifact = store.artifact('SYNTHETIC runtime integration evidence: '+kind)
    source = store.put('source', {
        'provider': 'synthetic_fixture', 'accession': kind, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')
    return store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [target], 'kind': kind,
        'source_ref': source['id'], 'measurements': [], 'dependencies': [],
        'anchor': None}, origin='external')


def assessment(hypothesis, observation, applicability, *, alias=None, revision=0):
    result = {'hypothesis_ref': hypothesis, 'observation_ref': observation,
        'relation': 'strengthens', 'applicability': applicability,
        'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': revision}
    if alias is not None:
        result['alias'] = alias
    return result


def annotation(target, hypothesis, assessments, revision, *, alias=None):
    result = {'subject_ref': target, 'footprint_kind': 'localized',
        'coherent_sets': [{'interpretations': [{'hypothesis_ref': hypothesis,
            'disposition': 'unresolved', 'assessment_refs': assessments}], 'context_refs': []}],
        'alternative_refs': [hypothesis], 'resolution': 'unresolved',
        'expected_revision': revision}
    if alias is not None:
        result['alias'] = alias
    return result


def commit(store, *, assessments, annotation_update, report):
    payload = {name: [] for name in store.reasoning_schema()['required']}
    payload['assessments'] = assessments
    payload['annotation_updates'] = [annotation_update]
    return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': report}


