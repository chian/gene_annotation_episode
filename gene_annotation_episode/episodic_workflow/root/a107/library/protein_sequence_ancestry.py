"""A107 protein sequence ancestry."""
from __future__ import annotations
import math
from typing import get_args
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a107.alignment_site_native import immutable_record
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError, RECORD_SCHEMAS
from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.a107 import protein_structure_contracts as a
_SUBJECTS = frozenset({'input', 'read_subject', 'feature', 'product', 'reference'})
_FAMILY = 'native_protein_structure_bundle_v1'
_CODES = frozenset(get_args(a.IssueCode))
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, v: type(v) is int).redefine('number', lambda _, v: type(v) in (int, float) and math.isfinite(v)))
_RECORD_VALIDATORS = {kind: _STRICT(RECORD_SCHEMAS[kind]) for kind in ('feature', 'product', 'reference', 'source', 'observation')}

def _fail(code, *, stage='authority', field='descriptor', role=None, artifact_role=None):
    raise ProteinStructureOperandError(a.issue(code, stage=stage, field=field, role=role, artifact_role=artifact_role))

def _require(condition, code='conflicting_identity', **where):
    if not condition:
        _fail(code, **where)

def _checked(function, *args, stage='authority', field='descriptor', code=None, artifact_role=None, **kwargs):
    """Translate only declared data failures; do not hide programming failures."""
    try:
        return function(*args, **kwargs)
    except ProteinStructureOperandError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
        name = code or (str(error) if str(error) in _CODES else 'invalid_schema')
        _fail(name, stage=stage, field=field, artifact_role=artifact_role)

def _payload(record):
    return {key: value for key, value in record.items() if key not in {'id', 'record_type', 'origin'}}

def _record(store, reference, kinds, *, field='descriptor'):
    try:
        record = store.get(reference)
    except (ContractError, KeyError, TypeError, ValueError):
        _fail('conflicting_identity', field=field)
    _require(type(record) is dict and record.get('id') == reference and (record.get('record_type') in kinds), field=field)
    kind = record['record_type']
    if kind in _RECORD_VALIDATORS:
        _checked(lambda value: _require(_RECORD_VALIDATORS[kind].is_valid(value), 'invalid_schema', field=field), _payload(record), field=field)
        _checked(immutable_record, record, code='conflicting_identity', field=field)
    return record

def is_protein_structure_sequence_operand(store, reference_ref: str) -> bool:
    """Classify only immutable typed sequence ancestry, without granting use.

    Iterative DFS validates every parent (even after finding protected material).
    Completed DAG nodes are reusable; an active node is a contradictory cycle.
    Input/read_subject leaves retain their ordinary validation at the tool.
    """
    _require(type(reference_ref) is str, 'invalid_schema')
    active, completed = (set(), {})
    stack = [(reference_ref, False, None)]
    while stack:
        reference, leaving, edges = stack.pop()
        if leaving:
            completed[reference] = any((completed[parent] for parent in edges))
            active.remove(reference)
            continue
        if reference in completed:
            continue
        _require(reference not in active)
        record = _record(store, reference, _SUBJECTS)
        kind = record['record_type']
        if kind in {'input', 'read_subject'}:
            completed[reference] = False
        elif kind == 'reference':
            source = _record(store, record['source_ref'], {'source'})
            completed[reference] = source['provider'] == 'episode.execution_result' and source['version'] == _FAMILY
        else:
            edges = [record['subject_ref']] if kind == 'feature' else record['parent_refs']
            active.add(reference)
            stack.append((reference, True, edges))
            stack.extend(((parent, False, None) for parent in reversed(edges)))
    return completed[reference_ref]
