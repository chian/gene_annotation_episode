"""Source-bound declarations and actual FASTQ mate joins, without acquisition.

Declarations retain their exact evidence and value. They do not certify a
recipe occurrence or turn a requested reference into an observed reference.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_bvbrc_fastqutils_contracts import FastqUtilsContractError, canonical_json, validate_contract
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_bvbrc_fastqutils_identity import requirement_ref

def _check(condition, code='binding_conflict', path=''):
    if not condition:
        raise FastqUtilsContractError(code, path)

def _escape(value):
    return str(value).replace('~', '~0').replace('/', '~1')

def _unique(values):
    """Stable exact deduplication; never select among conflicting records."""
    result, seen = ([], set())
    for value in values:
        key = canonical_json(value)
        if key not in seen:
            result.append(deepcopy(value))
            seen.add(key)
    return result

def _requirement(analysis, pointer, code, required, affected=(), sources=(), state='unavailable'):
    return validate_contract('Requirement', dict(id=requirement_ref(analysis, pointer, code), code=code, affected_refs=_unique(list(affected)), required_data=required, state=state, source_refs=_unique(list(sources))))

def _diagnostic(code, affected=(), sources=(), locator=None):
    return validate_contract('Diagnostic', dict(code=code, affected_refs=_unique(list(affected)), source_refs=_unique(list(sources)), locator=locator))

def _unknown_encoding():
    return dict(basis='unknown', encoding='unknown', metadata_id=None, evidence=None, declaration=None, native_locator=None)

def _pair_key(title, rule):
    if rule == 'exact_title':
        return title if title else None
    if rule == 'fastq_pair_0_3':
        token = title.split(' ', 1)[0]
        if len(token) >= 2 and token[-2] in '/_.' and (token[-1] in '12fr'):
            token = token[:-1]
        return token or None
    fields = title.split()
    token = fields[0] if fields else ''
    if rule == 'first_token_slash_mate' and len(token) >= 2 and (token[-2:] in ('/1', '/2')):
        token = token[:-2]
    return token or None
