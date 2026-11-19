"""Exact protein identity and publication leads, with retained source custody.

These operations find source records and citations. They never interpret a
database annotation as an experiment or assign experimental evidence credit.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import parse_qs, urlsplit

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError, REF, obj
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_homology_evidence.source_locations import received_source


IDENTITY_TOOL = 'public.literature.sequence_identity'
REFERENCES_TOOL = 'source.sequence.references'


from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_discovery_values import identity_schema, references_schema, _records, _sequence, _summary, identity_result, reference_results





def protein_operand(registry, subject_ref, scope):
    registry._check_sequence_operand(subject_ref, scope)
    if registry.store.subject_molecule(subject_ref) != 'protein':
        raise ContractError('literature_sequence_requires_protein')
    sequence = registry._sequence(subject_ref).upper()
    if not sequence or not re.fullmatch('[A-Z]+', sequence):
        raise ContractError('literature_sequence_requires_residue_string')
    return sequence


def identity_request(registry, arguments, scope):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    query = 'checksum:' + hashlib.md5(sequence.encode('ascii')).hexdigest().upper()
    if 'reviewed' in arguments:
        query += ' AND reviewed:' + str(arguments['reviewed']).lower()
    return registry.clients.uniprot_search, {'query': query,
        'size': arguments.get('size', 10),
        **({'cursor': arguments['cursor']} if 'cursor' in arguments else {})}











def publish_identity(registry, arguments, scope, snapshot):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    source = registry._source('uniprot', None, snapshot=snapshot,
        operand_refs=[arguments['subject_ref']])
    records = _records(snapshot.content)
    return identity_result(sequence, records, arguments, source, snapshot)


def references(registry, arguments, scope, permitted_inputs):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    artifact = received_source(registry.store, arguments['source_ref'], 'original',
        permitted_inputs=permitted_inputs, scope=scope)
    records = _records(registry.store.get_artifact(artifact['id']))
    index = arguments['record_index']
    if index >= len(records):
        raise ContractError('sequence_identity_record_index_out_of_bounds')
    record = records[index]
    if _sequence(record) != sequence:
        raise ContractError('sequence_identity_full_sequence_not_equal')
    return reference_results(record, index, arguments, artifact)
