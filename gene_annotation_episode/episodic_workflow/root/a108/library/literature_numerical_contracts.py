"""Exact A108 numerical declarations, separate from investigation instructions.

This bounded catalog names existing return schemas, not new readers or scores.
New legacy decisions can freeze their available declarations before selection.
Saved validation uses only that snapshot; it never substitutes today's factory.

Private declaration split, 2026-11-11: only A108 original-observation grading
and contextual aggregation schemas are declared. The private service exposes
this module through literature_numerical_contracts. Snapshot validation and
expansion use the original saved format without a foreign schema registry.

Root contract-information expansion and schema/JSON helper dependencies remain;
this split does not claim their independent parsing implementations are private.
"""
from collections.abc import Mapping
from importlib import import_module
import re
from gene_annotation_episode.episodic_workflow.root.a108.episode_contract_information import ContractInformationError, FACT_REFERENCE_PREFIX, expand_fact_form
from gene_annotation_episode.episodic_workflow.root.a108.schema_information_text import _copy_json, schema_fingerprint
from gene_annotation_episode.episodic_workflow.root.a108.schema_support import _schema_nodes
VERSION = 'literature_numerical_contracts_v1'
SAVED_MEMBER = 'literature_numerical_contracts'
_NAME = re.compile('[A-Za-z_][A-Za-z0-9_.:+/\\-]*\\Z')
_TYPES = frozenset(('null', 'object', 'array', 'number', 'integer', 'boolean', 'string'))
_SCHEMAS = {'literature_a108_grading_cells': ('library.literature_a108_grading_storage', 'grading_cells_schema'), 'literature_a108_aggregation_cells': ('library.literature_a108_aggregation_storage', 'aggregation_cells_schema')}
RETURN_MEANINGS = {'literature_a108_grading_cells': 'Requested purpose-specific A108 numerical counts of supporting, conflicting, overlapping and unresolved original organism-context observations. Preserve candidate and actual target organism/context, source-specific scientific criteria, original observation identity, qualified transfer and conditions. Evidence amount counts the supporting/conflicting union once; net support is separate. Repeated source representations add no observation, and these counts are not annotation probability or the Episode progress scalar.', 'literature_a108_aggregation_cells': 'Requested A108 main evidence scoring sheet components for physiology, environment, availability, localization and overall. Each retains evidence amount and separate support/conflict/overlap/net/unresolved counts, recomputed from possessed original observation unions. Shared observations across sources, children or domains count once. Unselected domains remain unavailable; source context, actual contributors and unresolved relationships remain explicit.'}

def registered_sources():
    return tuple(_SCHEMAS)

def registered_schema(source):
    """Return an existing detached exact type; acquire no scientific values."""
    if source not in _SCHEMAS:
        return None
    module, factory = _SCHEMAS[source]
    return _copy_json(getattr(import_module('.' + module, 'gene_annotation_episode.episodic_workflow.root.a108'), factory)())

def is_registered_schema(schema, *, source=None):
    if not isinstance(schema, Mapping):
        return False
    source = schema.get('x-source') if source is None else source
    if source not in _SCHEMAS or schema.get('x-source') != source:
        return False
    return schema_fingerprint(schema) == schema_fingerprint(registered_schema(source))

def uses_fact_references(schema):
    """Identify explicit chosen fact aliases, preserving literal native refs."""
    return any((isinstance(node, Mapping) and any((type(node.get(key)) is str and node[key].startswith(FACT_REFERENCE_PREFIX) for key in ('$ref', '$dynamicRef', '$recursiveRef'))) for _, node in _schema_nodes(schema)))

def freeze_contracts(*, facts_by_role, permitted_child_roles, action_schema):
    """Select exact available types; preserve caller roles and scientific meanings.

    A custom legacy form remains usable through its original literal route. It
    does not acquire a registered alias merely by sharing a source selector.
    """
    roles = list(permitted_child_roles)
    selected, source_types = ({}, {})
    for role in roles:
        facts = facts_by_role.get(role, {})
        source_types[role] = {source: {'type': _copy_json(row['type'])} for source, row in facts.items()}
        selected[role] = {source: _copy_json(row) for source, row in facts.items() if source in _SCHEMAS and isinstance(row, Mapping) and isinstance(row.get('meaning'), str) and is_registered_schema(row.get('report_schema'), source=source) and (schema_fingerprint(row.get('type')) == schema_fingerprint(row['report_schema']['type']))}
    if not any(selected.values()):
        return None
    record = {'version': VERSION, 'permitted_child_roles': roles, 'fact_sources_by_role': selected, 'fact_sources_sha256': schema_fingerprint(selected), 'source_types_by_role': source_types, 'source_types_sha256': schema_fingerprint(source_types), 'action_schema_sha256': schema_fingerprint(action_schema)}
    validate_frozen_contracts({SAVED_MEMBER: record, 'schema': action_schema})
    return record

def validate_frozen_contracts(saved):
    """Check original snapshot relationships without consulting any factory."""
    record = _copy_json(saved.get(SAVED_MEMBER))
    keys = {'version', 'permitted_child_roles', 'fact_sources_by_role', 'fact_sources_sha256', 'source_types_by_role', 'source_types_sha256', 'action_schema_sha256'}
    if not isinstance(record, dict) or set(record) != keys or record['version'] != VERSION or (record['fact_sources_sha256'] != schema_fingerprint(record['fact_sources_by_role'])) or (record['source_types_sha256'] != schema_fingerprint(record['source_types_by_role'])) or (record['action_schema_sha256'] != schema_fingerprint(saved['schema'])):
        raise ContractInformationError('original_literature_numerical_contracts_mismatch')
    roles, facts, types = (record['permitted_child_roles'], record['fact_sources_by_role'], record['source_types_by_role'])
    if not isinstance(roles, list) or any((type(role) is not str or _NAME.fullmatch(role) is None for role in roles)) or len(set(roles)) != len(roles) or (not isinstance(facts, dict)) or (set(facts) != set(roles)) or (not isinstance(types, dict)) or (set(types) != set(roles)):
        raise ContractInformationError('original_literature_numerical_roles_mismatch')
    for role, rows in facts.items():
        if not isinstance(rows, dict):
            raise ContractInformationError('original_literature_numerical_fact_map_mismatch')
        if not isinstance(types[role], dict):
            raise ContractInformationError('original_literature_numerical_source_types_mismatch')
        for source, row in types[role].items():
            if type(source) is not str or _NAME.fullmatch(source) is None or (not isinstance(row, dict)) or (set(row) != {'type'}):
                raise ContractInformationError('original_literature_numerical_source_types_mismatch')
            kinds = row['type'] if isinstance(row['type'], list) else [row['type']]
            if not kinds or any((type(kind) is not str or kind not in _TYPES for kind in kinds)) or len(set(kinds)) != len(kinds):
                raise ContractInformationError('original_literature_numerical_source_types_mismatch')
        for source, row in rows.items():
            if source not in _SCHEMAS or not isinstance(row, dict) or (not {'type', 'meaning', 'report_schema'} <= row.keys()) or (type(row['meaning']) is not str) or (not isinstance(row['report_schema'], dict)) or (row['report_schema'].get('x-source') != source) or (row['report_schema'].get('type') != 'array') or (row['type'] != 'array') or (types[role].get(source) != {'type': 'array'}):
                raise ContractInformationError('original_literature_numerical_fact_mismatch')
    return record

def expand_numerical_form(submitted_schema_json, *, child_role, saved):
    """Expand selected aliases only from the original bounded host snapshot."""
    record = validate_frozen_contracts(saved)
    return expand_fact_form(submitted_schema_json, child_role=child_role, facts_by_role=record['fact_sources_by_role'], permitted_child_roles=record['permitted_child_roles'])
__all__ = ['VERSION', 'SAVED_MEMBER', 'registered_sources', 'registered_schema', 'RETURN_MEANINGS', 'is_registered_schema', 'uses_fact_references', 'freeze_contracts', 'validate_frozen_contracts', 'expand_numerical_form']
