"""Labelled synthetic material allocations; no model or external measurements."""
from copy import deepcopy

import pytest

from gene_annotation_episode.credit import AXES, CreditPolicy, project_credit, softened_hypervolume
from gene_annotation_episode.state import Store
from gene_annotation_episode import library_targets


def library_fixture(tmp_path):
    path = tmp_path / 'three-original-reads.fastq'
    path.write_text('@A synthetic\nACGT\n+\nIIII\n@B synthetic\nACGTAC\n+\nIIIIII\n@C synthetic\nACGTACGTAC\n+\nIIIIIIIIII\n')
    store = Store(tmp_path / 'state')
    store.create_problem(path, molecule='dna')
    target, = store.targets()
    native, parameters = store.context_mask_target_query({'subject_refs': [target['id']]}, target['id'])
    members = sorted([dict(row) for row in store.db.execute(native, parameters)], key=lambda row: row['length'])
    source = source_fixture(store, 'sample-observations')
    sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic actual sample',
        'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')
    return store, target, members, source, sample


def source_fixture(store, label):
    artifact = store.artifact('Labelled synthetic fixture: '+label)
    return store.put('source', {'provider': 'synthetic_fixture', 'accession': label,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')


def select_mask(store, target, members):
    selected = library_targets.select(store, target['id'], member_refs=[row['member_ref'] for row in members])
    return {'subject_refs': [target['id']], 'read_selection_refs': [selected['id']]}


def context_account(store, target, source, sample, label, rows, *, allocation=None, account=None):
    """Rows explicitly declare kind, applicability, mask, and optional disposition."""
    full = {'subject_refs': [target['id']]}
    account = full if account is None else account
    allocation = full if allocation is None else allocation
    interpretations, saved = [], []
    for index, values in enumerate(rows):
        kind, applicability, mask = values[:3]
        relation, disposition = values[3:] if len(values) > 3 else ('strengthens', 'supported')
        observation = store.put('observation', {'subject_refs': [sample['id']],
            'source_subject_refs': [sample['id']], 'kind': kind, 'source_ref': source['id'],
            'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')
        hypothesis = store.put('hypothesis', {'subject_refs': [sample['id']],
            'predicate': 'biological_role', 'value': {'type': 'enum', 'value': ('growth', 'present', 'intact')[index]},
            'context_refs': []}, origin='reasoning')
        assessment = store.put('assessment', {'hypothesis_ref': hypothesis['id'],
            'observation_ref': observation['id'], 'relation': relation, 'applicability': applicability,
            'extent_basis': 'context_allocation', 'context_account_scope': account,
            'context_scope': mask, 'condition_refs': [], 'assumption_refs': [],
            'expected_revision': 0}, origin='reasoning')
        interpretations.append({'hypothesis_ref': hypothesis['id'], 'disposition': disposition,
                                'assessment_refs': [assessment['id']]})
        saved.append((observation, hypothesis, assessment))
    annotation = store.put('annotation', {'subject_ref': sample['id'],
        'footprint_kind': 'whole_input_context', 'context_account_scope': account,
        'context_scope': allocation, 'coherent_sets': [{'interpretations': interpretations,
            'context_refs': []}], 'alternative_refs': [], 'resolution': 'selected',
        'expected_revision': 0}, origin='reasoning')
    return annotation, saved


def revision_payload(row):
    from gene_annotation_episode.domain import RECORD_SCHEMAS
    payload = {key: deepcopy(value) for key, value in row.items()
               if key in RECORD_SCHEMAS[row['record_type']]['properties']}
    if row['record_type'] == 'annotation':
        for group in payload['coherent_sets']:
            group.pop('id', None)
    payload['expected_revision'] = row['revision']
    return payload


