"""Explicit four-field information and separate local commissioning contracts."""
from __future__ import annotations

from copy import deepcopy

from .native_blast_contracts import (
    PROGRAMS, NATIVE_BLAST_JOB_SCHEMA, NATIVE_BLAST_REQUESTED_JOB_SCHEMA,
    finite_json_copy, _schema, _absolute,
)

_DESCRIPTIONS = {
    'blastn': 'Measure nucleotide correspondence between one supplied query and one supplied subject.',
    'blastp': 'Measure protein correspondence between one supplied query and one supplied subject.',
    'blastx': 'Measure translated nucleotide-query correspondence to one supplied protein subject.',
    'tblastn': 'Measure protein-query correspondence to one supplied translated nucleotide subject.',
    'tblastx': 'Measure translated correspondence between one supplied nucleotide query and one supplied nucleotide subject.',
}
_MEANINGS = {
    'blastn': 'Both original coordinate axes and alignment columns are nucleotides. Preserve selected task, strand, ranges, scoring and filtering.',
    'blastp': 'Both original coordinate axes and alignment columns are amino acids. Preserve substitutions and gaps separately from paired residues.',
    'blastx': 'Query coordinates are original nucleotides, reference coordinates amino acids, and alignment columns amino acids. Preserve query genetic code and frame; each paired translated residue occupies three query nucleotides.',
    'tblastn': 'Query coordinates are amino acids, reference coordinates original nucleotides, and alignment columns amino acids. Preserve subject genetic code and frame; each paired translated residue occupies three reference nucleotides.',
    'tblastx': 'Both coordinate axes are original nucleotides and alignment columns amino acids. Preserve both genetic codes, frames and directions; paired translated residues occupy three positions on each original nucleotide axis.',
}


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


def native_blast_tool_contracts(rows, *, resource_kind, resource_id):
    """Describe the real selected launch route; grant no scientific execution."""
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id or '\0' in resource_id:
        raise ValueError('native_blast_local_paired_resource_required')
    result = []
    for binding in validate_native_blast_bindings(rows):
        program = binding['program']
        schema = deepcopy(NATIVE_BLAST_REQUESTED_JOB_SCHEMA)
        schema['properties']['native_blast']['allOf'] = [{'properties': {
            'program': {'const': program}, 'mode': {'const': 'pairwise'},
            'software': {'const': binding['software']}}}]
        instructions = (
            'Supply one actual FASTA query_sequence and one actual FASTA subject_sequence with their exact byte identities, '
            'operand bindings and explicitly selected native options. ' + _MEANINGS[program] + ' '
            'Select one original report: single-file JSON15 or tabular6/tabular7 with exact columns and delimiter. '
            'Correspondence requires both lengths, qseq/sseq traceback, endpoints, frames where translated, native scores and identity/gap counts; '
            'unreported measurements remain unavailable. Retain complete stdout, stderr and the selected original report. '
            'Commission the requested_job through the existing launch episode and its configured launch_local child; '
            'that resource child selects practical.job.start under its caller allocation. The native producer executes one selected -subject command. '
            'No database, index, download, remote search, automatic retry or alternate resource is part of this operation. '
            'Monitoring uses existing native status and selected stdout/stderr observations; a live process alone does not establish productive search progress. '
            'Results acquisition reads the original sealed native_blast_bundle_v1 and all complete original artifacts, uses '
            'parse_blast_report_collection with their actual declared format, then populate_blast_pairwise_sheet and '
            'calculate_blast_pairwise_components. These are separate readers, numerical storage and deterministic calculations. '
            'Request the numerical components and query/reference relationships needed by the receiving episode. '
            'Coverage counts paired original positions over actual operand lengths; union coverage is not a chosen global alignment. '
            'Repeated or conflicting HSP mappings are explicit. E-values remain native quantities and never multiply paired-sequence relevance. '
            'Missing, failed, partial and successful zero-hit outputs are distinct. '
            'This information does not grant direct execution to a scientific or root episode.')
        result.append({'name': 'native.' + program, 'description': _DESCRIPTIONS[program],
            'resources': 'local', 'instructions': instructions, 'input_schema': schema,
            'invocation_route': {'kind': 'commission', 'routes': [{'entry_role': 'launch',
                'resource_id': resource_id, 'resource_role': 'launch_local'}]}})
    return result


def native_blast_tool_information(rows, *, resource_kind, resource_id):
    return [{key: row[key] for key in ('name', 'description', 'resources', 'instructions')}
        for row in native_blast_tool_contracts(rows, resource_kind=resource_kind, resource_id=resource_id)]
