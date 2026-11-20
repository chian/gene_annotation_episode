"""The native job of one chunk of an all-vs-all search, built from controlled values.

A launching episode holds the set (a FASTA artifact in custody), the chunk it is asked for and the search parameters.
``chunk_of`` cuts the chunk's text from the set (the whole set when there is one chunk) and ``native_chunk_job`` makes
the job the all-vs-all contract validates (``blast_all_vs_all_job``): both operands are staged files inside the job's
own directory, so their paths are the directory plus the staged name. Pure: no file, no store, no service. The
contract, the set functions and the kind derivation are called, never rewritten."""
from __future__ import annotations

import hashlib

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_all_vs_all_job import (
    VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_all_vs_all_sets import (
    chunk_ranges, chunk_text, set_summary)

SET_NAME = 'set.fasta'
QUERY_NAME = 'query.fasta'


def chunk_of(set_text, chunk_index, chunk_count):
    """The chunk ``chunk_index`` of ``chunk_count`` of the set: its text (the whole set when there is one chunk), its
    first and last ordinal and its record count."""
    whole = set_summary(set_text)
    ranges = chunk_ranges(whole['record_count'], chunk_count)
    if type(chunk_index) is not int or not 0 <= chunk_index < chunk_count:
        raise ValueError('blast_all_vs_all_chunk_index_invalid')
    first, last = ranges[chunk_index]
    text = set_text if chunk_count == 1 else chunk_text(set_text, first, last)
    return {'text': text, 'first_ordinal': first, 'last_ordinal': last, 'record_count': last - first + 1}


def _operand(role, name, directory, text, record_count, artifact_ref):
    data = text.encode()
    return {'role': role, 'path': str(directory / name), 'format': 'fasta', 'sha256': hashlib.sha256(data).hexdigest(),
            'size_bytes': len(data), 'record_count': record_count, 'artifact_ref': artifact_ref}


def native_chunk_job(set_text, chunk, *, program, parameters, chunk_index, chunk_count, executable, executable_sha256,
                     directory, set_ref, chunk_ref):
    """The native all-vs-all job of the chunk. ``directory`` is the job's own directory (a ``pathlib.Path``), where the
    set and the chunk are staged as ``set.fasta`` and ``query.fasta``; ``set_ref`` and ``chunk_ref`` are the artifacts
    they come from (the chunk is the set itself when there is one chunk)."""
    whole = set_summary(set_text)
    return {'version': VERSION, 'program': program, 'mode': 'all_vs_all',
            'software': {'executable': str(executable), 'sha256': executable_sha256, 'engine_version': None},
            'environment': {},
            'operands': [_operand('query_set', QUERY_NAME, directory, chunk['text'], chunk['record_count'], chunk_ref),
                         _operand('subject_set', SET_NAME, directory, set_text, whole['record_count'], set_ref)],
            'set': {'sha256': whole['sha256'], 'record_count': whole['record_count'],
                    'total_letters': whole['total_letters']},
            'chunk': {'index': chunk_index, 'count': chunk_count, 'first_ordinal': chunk['first_ordinal'],
                      'last_ordinal': chunk['last_ordinal']},
            'parameters': dict(parameters), 'metadata': {}}


__all__ = ['QUERY_NAME', 'SET_NAME', 'chunk_of', 'native_chunk_job']
