"""Pure requested facts from frozen direct-MinHash publications.

The host must authenticate each original acquisition/publication receipt before
supplying ``{source_ref, grading}``. Passing JSON or a syntactically valid source
ID cannot establish custody. This module validates supplied relationships and
copies saved quantities; it does not read a store, acquire, parse again, regrade,
choose work, render a prompt, or assign credit.

The v1 publication contains C2 outputs calculated without pair metadata. The v2
envelope retains explicit calculation inputs with the same sheet/components.
Checks against native cells, supplied inputs and saved operands detect
inconsistent records; they never replace saved values or reconstruct a grade.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_minhash_grader import MINHASH_DIAGNOSTIC_CODES
_MATCHES = 'bvbrc_minhash_matches'
_COUNTS = 'bvbrc_minhash_counts'
_CALCULATIONS = 'bvbrc_minhash_calculations'
_CALCULATION_DIAGNOSTICS = 'bvbrc_minhash_calculation_diagnostics'
_METADATA = ('kmer_length', 'query_length', 'reference_length', 'alphabet_size')
_NATIVE_NUMBERS = ('reported_distance', 'reported_pvalue')
_HASH_COUNTS = ('shared_hashes', 'compared_union_hashes')
_DIAGNOSTIC_PATH = '^[a-z_]+(?:\\[[0-9]+\\])*(?:\\.[a-z_]+(?:\\[[0-9]+\\])*)*$'
_REF = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}
_STATUS = {'type': 'string', 'enum': ['ok', 'partial', 'invalid']}

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def minhash_fact_sources() -> dict:
    """Return detached recorded-source declarations for the closed form guard."""
    match = _object({'source_ref': _REF, 'row_index': {'type': 'integer', 'minimum': 0}, 'genome_id': {'type': ['string', 'null'], 'format': 'identifier', 'x-reference-namespace': 'bvbrc_minhash_genome'}, **{name: {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1} for name in (*_NATIVE_NUMBERS, 'shared_hash_fraction')}, **{name: {'type': ['integer', 'null'], 'minimum': 0} for name in _HASH_COUNTS}, 'parse_status': _STATUS})
    count = _object({'source_ref': _REF, 'returned_row_count': {'type': 'integer', 'minimum': 0}, 'parse_status': _STATUS, 'population_size': {'type': 'null'}, 'truncated': {'type': 'null'}})
    calculation = _object({'source_ref': _REF, 'row_index': {'type': 'integer', 'minimum': 0}, 'genome_id': {'type': ['string', 'null'], 'format': 'identifier', 'x-reference-namespace': 'bvbrc_minhash_genome'}, **{name: {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1} for name in ('shared_hash_fraction', 'recomputed_distance', 'recomputed_pvalue')}, 'unsaturated_distance': {'type': ['number', 'null'], 'minimum': 0}, **{name: {'type': ['integer', 'null'], 'minimum': 1} for name in _METADATA}, 'native_parameter_equivalence': {'type': 'string', 'enum': ['unestablished']}, 'parse_status': _STATUS, 'diagnostic_codes': {'type': 'array', 'items': {'type': 'string', 'enum': sorted(MINHASH_DIAGNOSTIC_CODES)}}})
    diagnostic = _object({'source_ref': _REF, 'code': {'type': 'string', 'enum': sorted(MINHASH_DIAGNOSTIC_CODES)}, 'path': {'type': 'string', 'pattern': _DIAGNOSTIC_PATH}, 'severity': {'type': 'string', 'enum': ['error', 'warning']}})
    return deepcopy({_MATCHES: {'type': 'array', 'meaning': 'Original ordered MinHash matches, native distance/p-value and sampled shared-hash quantities; nulls preserve unavailable cells.', 'report_schema': {'type': 'array', 'items': match, 'x-source': _MATCHES}}, _COUNTS: {'type': 'array', 'meaning': 'Actual returned array length and acquisition parse status; neither search population nor search completeness is known.', 'report_schema': {'type': 'array', 'items': count, 'x-source': _COUNTS}}, _CALCULATIONS: {'type': 'array', 'meaning': 'Saved sampled hash fractions, distance and p-value recalculations with their explicit pair inputs; native parameter equivalence remains unestablished and native parse status is separate from calculation availability.', 'report_schema': {'type': 'array', 'items': calculation, 'x-source': _CALCULATIONS}}, _CALCULATION_DIAGNOSTICS: {'type': 'array', 'meaning': 'Saved calculator diagnostics in original order, including unmatched pair metadata that cannot be assigned to a native result row.', 'report_schema': {'type': 'array', 'items': diagnostic, 'x-source': _CALCULATION_DIAGNOSTICS}}})
