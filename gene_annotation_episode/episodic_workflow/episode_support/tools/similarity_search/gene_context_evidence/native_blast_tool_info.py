"""Explicit four-field information and separate local commissioning contracts."""
from __future__ import annotations


from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import PROGRAMS, NATIVE_BLAST_JOB_SCHEMA, finite_json_copy, _schema, _absolute



def validate_native_blast_bindings(rows):
    rows = finite_json_copy(rows)
    if type(rows) is not list:
        raise ValueError('native_blast_explicit_binding_rows_required')
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {'program', 'mode', 'software'}
                or row['program'] not in PROGRAMS or row['mode'] != 'pairwise'):
            raise ValueError('native_blast_invalid_configured_binding')
        _schema(row['software'], NATIVE_BLAST_JOB_SCHEMA['properties']['software'])
        _absolute(row['software']['executable'])
        key = row['program'], row['mode']
        if key in seen:
            raise ValueError('native_blast_duplicate_program_mode_binding')
        seen.add(key)
    return rows


