"""Tool information for explicitly configured native database utilities.

Pure descriptors do not establish installed programs or connected episode paths.
The shared execution binding must admit a descriptor before offering it to work.
"""
from __future__ import annotations
from copy import deepcopy

from .native_blast_contracts import finite_json_copy
from .native_blast_utility_contracts import (
    MODES, SOFTWARE_SCHEMA, NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA,
    _error, _path, _schema, native_blast_utility_job_schema,
)

_DESCRIPTIONS = {
    'create_sequence_database': 'Build a retained nucleotide or protein BLAST database from supplied FASTA sequences.',
    'extract_sequences': 'Retrieve explicitly selected sequences or ranges from a supplied prepared BLAST database.',
    'info': 'Read the selected prepared BLAST database’s native counts, molecule and volume information.',
    'metadata': 'Retrieve the selected prepared BLAST database’s native JSON metadata and file inventory.',
    'integrity': 'Run the explicitly selected BLAST database integrity checks and preserve their actual coverage and diagnostics.',
}
_INSTRUCTIONS = {
    'create_sequence_database': (
        'Supply one plain FASTA and choose nucleotide or protein, database format4 or5, title, identifier parsing '
        'and hash-index options explicitly. Optional taxonomy maps and masking artifacts must be supplied with their '
        'own identities; selecting this job does not generate either. Keep every produced database component, including '
        'native metadata and sidecars. A zero exit does not establish that every file was captured or that a later '
        'search used the database. A failed build can leave partial files; retain them without presenting a usable '
        'prepared database. Taxonomy assignments describe the selected inputs and do not establish gene function. '),
    'extract_sequences': (
        'Select an already prepared database and an explicit list of sequence identifiers. This binding does not select '
        'a default database or retrieve all entries. Duplicate requests remain distinct. Native identifier, accession, '
        'OID and full sequence length accompany the returned sequence. A requested range uses one-based inclusive '
        'endpoints; retained normalized coordinates use zero-based half-open endpoints. The returned fragment length '
        'is distinct from the full sequence length. Preserve strand, missing identifiers and unassociated rows. '
        'Do not join records by output position or choose the first duplicate accession. get_dups and target_only '
        'are mutually exclusive native options. '),
    'info': (
        'Select the exact prepared database. Retain the native title, database format, molecule, sequence/residue '
        'counts and volume identities when reported. Select exact_length explicitly if that measurement is needed. '
        'Absent counts remain unavailable. Counts describe this database population, not the frequency of a function. '),
    'metadata': (
        'Select the exact prepared database and retain its native metadata JSON. Preserve native reported file names, '
        'byte totals, sequence counts, residue counts and original field locations. Native metadata is not itself '
        'the workflow prepared-database manifest. Writer metadata and later inspection metadata can include different '
        'file populations; do not silently substitute one byte total for another. '),
    'integrity': (
        'Select the exact prepared database and the full or sampled checking methods. Preserve the native diagnostic '
        'output and return code. Requested sampling counts do not establish actual checked counts or sampled OIDs. '
        'A sampled pass is not a full database pass. Retain useful passing sequence checks even when another check '
        'fails. Missing taxonomy data, missing files and an execution failure are distinct from evidence that '
        'sequences are corrupt. Required reference data must be explicitly configured; no lookup or download is '
        'added automatically. '),
}


def validate_native_blast_utility_bindings(rows: list[dict]) -> list[dict]:
    rows = finite_json_copy(rows)
    if type(rows) is not list: _error('binding_rows_required')
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {'program','mode','software','molecules'}:
            _error('binding_shape')
        pair = row['program'],row['mode']
        if pair not in MODES or pair in seen: _error('binding_program_mode')
        seen.add(pair)
        _schema(row['software'],SOFTWARE_SCHEMA)
        _path(row['software']['executable'],absolute=True)
        if (type(row['molecules']) is not list or not row['molecules'] or
            any(type(v) is not str or v not in {'dna','protein'} for v in row['molecules']) or
            len(row['molecules']) != len(set(row['molecules']))):
            _error('binding_molecules')
    return rows


def native_blast_utility_tool_contracts(bindings: list[dict], *, resource_kind: str,
                                      resource_id: str) -> list[dict]:
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id or '\0' in resource_id:
        _error('configured_local_resource_required')
    contracts = []
    for row in validate_native_blast_utility_bindings(bindings):
        program,mode = row['program'],row['mode']
        schema = deepcopy(NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA)
        job_schema = native_blast_utility_job_schema(program=program,mode=mode)
        job_schema['properties']['software'] = {'const':row['software']}
        job_schema['properties']['operation']['allOf'].append({'properties':{'molecule':{'enum':row['molecules']}}})
        schema['properties']['native_blast_utility'] = job_schema
        instructions = _INSTRUCTIONS[mode] + (
            'Commission the selected job through launch and its configured local-compute child under the caller’s '
            'allocation. It is one native utility invocation; preparation, extraction and integrity checking are '
            'separately selected operations. The infrastructure does not choose follow-up work. Retain original '
            'inputs, output files and diagnostic streams. Results acquisition uses the deterministic typed utility '
            'records and returns only the parent’s requested fields. These are supporting operations without an '
            'independent annotation-confidence score. Keep database-scale work off this local resource; remote '
            'execution requires its own actually configured resource binding.')
        contracts.append({'name':'native.'+program+'.'+mode,'description':_DESCRIPTIONS[mode],
            'resources':'local','instructions':instructions,'input_schema':schema,
            'invocation_route':{'kind':'commission','routes':[{'entry_role':'launch',
                'resource_id':resource_id,'resource_role':'launch_local'}]}})
    return contracts
