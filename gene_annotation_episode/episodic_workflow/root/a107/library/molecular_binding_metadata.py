"""A107 molecular binding metadata."""
import json
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a107.molecular_sequence_execution_contracts import _software
from gene_annotation_episode.episodic_workflow.root.a107 import molecular_sequence_ordinary as ordinary
from gene_annotation_episode.episodic_workflow.root.a107 import molecular_sequence_result_contracts as contracts
BINDING_VERSION = 'native_molecular_sequence_binding_v1'

def _require(condition, code):
    if not condition:
        raise ContractError('ordinary_orf_' + code)

def _copy(value):
    return json.loads(canonical(value))

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)

def validate_native_molecular_sequence_bindings(bindings):
    """Pure deployment/adapter metadata checks; no installed-software claim."""
    bindings = _copy(bindings)
    _require(type(bindings) is list and bool(bindings), 'bindings_required')
    for row in bindings:
        _closed(row, ('version', 'operation', 'deployment', 'software'), 'binding_fields_invalid')
        _require(row['version'] == BINDING_VERSION and row['operation'] in contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS, 'binding_operation_invalid')
        ordinary._deployment(row['operation'], row['deployment'])
        _software(row['software'])
        _require(row['deployment']['runtime']['executable'] == row['software']['python'] and row['deployment']['runtime']['home'] == row['software']['python_home'], 'binding_runtime_conflict')
    return bindings
