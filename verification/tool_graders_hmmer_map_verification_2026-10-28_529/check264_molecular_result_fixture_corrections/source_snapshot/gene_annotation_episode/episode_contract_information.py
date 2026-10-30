"""Pure information and form-reference helpers over supplied frozen contracts.

There is no source, workflow factory, runtime, episode or model dependency here.
An explicitly parameterized registered fact uses its pure schema builder.
Structural consistency and content fingerprints do not authenticate custody or
the original C1/C4 boundary; the integration owner must establish those facts.
"""
from collections.abc import Mapping
import re

from .boundary_validation import parse_json_object
from .communication import ReportBoundaryError, validate_closed_schema
from .schema_information_text import (SchemaInformationError, _copy_json,
                                      render_schema_information, schema_fingerprint)
from .schema_support import _schema_nodes


OPERATION_INFORMATION_VERSION = 'operation_contract_information_v1'
RETURN_INFORMATION_VERSION = 'return_contract_information_v1'
DECLARATION_VERSION = 'episode_report_contract_declaration_v1'
FACT_REFERENCE_PREFIX = 'episode-fact:'
_UNIPROT_SOURCE = 'uniprot_selected_returns'
_UNIPROT_SELECTION = 'x-uniprot-selection'
_RESTRICTION_SOURCE = 'restriction_mapping_results'
_RESTRICTION_SELECTION = 'x-restriction-selection'
_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.:+/\-]*\Z')
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')


class ContractInformationError(ValueError):
    def __init__(self, code, field=None):
        self.code, self.field = code, field
        super().__init__(code + (':' + field if field else ''))


def _copy(value, field):
    try:
        return _copy_json(value, field=field)
    except (SchemaInformationError, RecursionError) as error:
        raise ContractInformationError('invalid_contract_json', field) from error


def _name(value, field):
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ContractInformationError('invalid_contract_name', field)
    return value


def _roles(permitted_child_roles):
    if not isinstance(permitted_child_roles, (list, tuple)):
        raise ContractInformationError('explicit_child_roles_required', 'permitted_child_roles')
    roles = [_name(role, 'permitted_child_roles') for role in permitted_child_roles]
    if len(set(roles)) != len(roles):
        raise ContractInformationError('duplicate_child_role', 'permitted_child_roles')
    return roles


def _outcome(result=None, *, failure=None):
    return {'status': 'completed' if failure is None else 'invalid',
        'record_refs': [], 'changed_record_refs': [], 'result': result,
        'feedback': None if failure is None else {'category': 'decision_exchange', 'code': failure}}


def _schema(value, field, *, object_only=False):
    if not isinstance(value, Mapping) and (object_only or type(value) is not bool):
        raise ContractInformationError('schema_object_required', field)
    return _copy(value, field)


def _catalog(catalog):
    if not isinstance(catalog, (list, tuple)):
        raise ContractInformationError('frozen_catalog_required', 'catalog')
    selected = {}
    for index, row in enumerate(catalog):
        field = f'catalog[{index}]'
        if (not isinstance(row, Mapping) or not {'name', 'description', 'input_schema'} <= row.keys()
                or type(row['description']) is not str):
            raise ContractInformationError('invalid_catalog_entry', field)
        name = _name(row['name'], field + '.name')
        if name in selected:
            raise ContractInformationError('duplicate_catalog_operation', field + '.name')
        selected[name] = {'name': name, 'description': row['description'],
                          'input_schema': _schema(row['input_schema'], field + '.input_schema')}
    return selected


def _role_facts(facts_by_role, role):
    if not isinstance(facts_by_role, Mapping):
        raise ContractInformationError('frozen_fact_map_required', 'facts_by_role')
    facts = facts_by_role.get(role, {})
    if not isinstance(facts, Mapping):
        raise ContractInformationError('invalid_role_fact_map', 'facts_by_role.' + role)
    return facts


def _fact(facts, source):
    row = facts[source]
    field = 'fact.' + source
    if (not isinstance(row, Mapping) or not {'type', 'meaning', 'report_schema'} <= row.keys()
            or type(row['meaning']) is not str):
        raise ContractInformationError('invalid_fact_contract', field)
    schema = _schema(row['report_schema'], field + '.report_schema', object_only=True)
    declared_type = _copy(row['type'], field + '.type')
    if 'type' not in schema or schema_fingerprint(declared_type) != schema_fingerprint(schema['type']):
        raise ContractInformationError('fact_type_mismatch', field + '.type')
    if 'x-source' in schema and schema['x-source'] != source:
        raise ContractInformationError('fact_source_selector_conflict', field + '.report_schema.x-source')
    return {'type': declared_type, 'meaning': row['meaning'], 'report_schema': schema}


def operation_contract_information(*, catalog, operation):
    """Describe one unique supplied actual operation; grant no capability."""
    operation = _name(operation, 'operation')
    entries = _catalog(catalog)
    if operation not in entries:
        return _outcome(failure='operation_contract_not_available')
    selected = entries[operation]
    schema = selected['input_schema']
    return _outcome({'information_kind': OPERATION_INFORMATION_VERSION, 'operation': operation,
        'meaning': selected['description'], 'input_schema': schema, 'schema_sha256': schema_fingerprint(schema),
        'text': render_schema_information(schema, title='Arguments for ' + operation)})


def return_contract_information(*, facts_by_role, permitted_child_roles, role, source):
    """Describe a permitted child's declared fact type, without reading facts."""
    role, source = _name(role, 'role'), _name(source, 'source')
    if role not in _roles(permitted_child_roles):
        return _outcome(failure='return_child_role_not_available')
    facts = _role_facts(facts_by_role, role)
    if source not in facts:
        return _outcome(failure='return_contract_not_available')
    selected = _fact(facts, source)
    schema = selected['report_schema']
    return _outcome({'information_kind': RETURN_INFORMATION_VERSION, 'role': role, 'source': source,
        'meaning': selected['meaning'], 'report_schema': schema, 'schema_sha256': schema_fingerprint(schema),
        'text': render_schema_information(schema, title='Return source ' + source + ' for ' + role)})


def _submitted(text):
    if type(text) is not str:
        raise ContractInformationError('submitted_schema_text_required', 'submitted_schema_json')
    try:
        schema = parse_json_object(text)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ContractInformationError('invalid_submitted_schema_json', 'submitted_schema_json') from error
    if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
        raise ContractInformationError('closed_top_level_form_required', 'submitted_schema_json')
    return schema


def _references(schema):
    found = []
    # Existing exact native A105 literals own their local definition resources.
    # Only internal refs inside these complete top-level fact documents are
    # opaque here. _closed still requires their exact registered schema; all
    # aliases, external/dynamic refs and altered documents remain constrained.
    native = {field for field, node in schema.get('properties', {}).items()
        if isinstance(node, dict) and node.get('x-source') in {
            'literature_gel_component_cells', 'literature_controlled_response_component_cells',
            'literature_kinetic_summary_precision_cells', 'literature_measurement_comparison_cells', 'literature_concentration_window_cells'}}
    for path, node in _schema_nodes(schema):
        if not isinstance(node, dict):
            continue
        references = {'$ref', '$dynamicRef', '$recursiveRef'} & node.keys()
        if not references:
            continue
        if (len(path) > 2 and path[0] == 'properties' and path[1] in native
                and set(node) == {'$ref'} and type(node['$ref']) is str
                and node['$ref'].startswith('#/$defs/')):
            continue
        selected_uniprot = (set(node) == {'$ref', _UNIPROT_SELECTION}
            and node.get('$ref') == FACT_REFERENCE_PREFIX + _UNIPROT_SOURCE)
        selected_restriction = (set(node) == {'$ref', _RESTRICTION_SELECTION}
            and node.get('$ref') == FACT_REFERENCE_PREFIX + _RESTRICTION_SOURCE)
        if (len(path) != 2 or path[0] != 'properties'
                or (set(node) != {'$ref'} and not selected_uniprot and not selected_restriction)
                or type(node['$ref']) is not str or not node['$ref'].startswith(FACT_REFERENCE_PREFIX)):
            raise ContractInformationError('unsupported_form_reference', 'submitted_schema_json')
        source = _name(node['$ref'][len(FACT_REFERENCE_PREFIX):], 'source')
        found.append((path[1], source))
    return found


def _closed(schema):
    try:
        return validate_closed_schema(schema)
    except (ReportBoundaryError, TypeError, ValueError, RecursionError) as error:
        raise ContractInformationError('invalid_expanded_closed_form', 'expanded_schema') from error


def _restriction_schema(submitted_field, field):
    from .restriction_mapping_selection import restriction_selected_return_schema
    if _RESTRICTION_SELECTION not in submitted_field:
        raise ContractInformationError('explicit_fact_selection_required', field)
    try:
        return restriction_selected_return_schema(submitted_field[_RESTRICTION_SELECTION])
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ContractInformationError('invalid_fact_selection', field) from error


def expand_fact_form(submitted_schema_json, *, child_role, facts_by_role, permitted_child_roles):
    """Expand only explicitly chosen top-level fact refs, then check closedness."""
    child_role = _name(child_role, 'child_role')
    if child_role not in _roles(permitted_child_roles):
        raise ContractInformationError('return_child_role_not_available', 'child_role')
    submitted = _submitted(submitted_schema_json)
    references = _references(submitted)
    facts = _role_facts(facts_by_role, child_role)
    expanded, declarations = _copy(submitted, 'submitted_schema'), []
    for field, source in references:
        if source not in facts:
            raise ContractInformationError('return_contract_not_available', field)
        original = _fact(facts, source)['report_schema']
        submitted_field = submitted['properties'][field]
        if source == _RESTRICTION_SOURCE:
            from .restriction_mapping_returns import restriction_mapping_fact_sources
            base = restriction_mapping_fact_sources()[source]['report_schema']
            if schema_fingerprint(original) != schema_fingerprint(base):
                raise ContractInformationError('selected_fact_base_schema_mismatch', field)
            original = _restriction_schema(submitted_field, field)
        if _UNIPROT_SELECTION in submitted_field:
            # Availability remains the caller's frozen fact map. The pure
            # builder supplies the selected exact schema, not another source.
            from .uniprot_return_contracts import (uniprot_fact_sources,
                                                   uniprot_selected_return_schema)
            base = uniprot_fact_sources()[_UNIPROT_SOURCE]['report_schema']
            if schema_fingerprint(original) != schema_fingerprint(base):
                raise ContractInformationError('selected_fact_base_schema_mismatch', field)
            try:
                original = uniprot_selected_return_schema(submitted_field[_UNIPROT_SELECTION])
            except (ValueError, TypeError, OverflowError, RecursionError) as error:
                raise ContractInformationError('invalid_fact_selection', field) from error
        declarations.append({'field': field, 'source': source, 'schema_sha256': schema_fingerprint(original),
                             'source_had_x_source': 'x-source' in original})
        original['x-source'] = source
        expanded['properties'][field] = original
    expanded = _closed(expanded)
    declaration = {'version': DECLARATION_VERSION, 'child_role': child_role,
        'submitted_schema_json': submitted_schema_json, 'expanded_schema_sha256': schema_fingerprint(expanded),
        'fact_references': declarations}
    return {'expanded_schema': expanded, 'declaration': declaration}


def validate_saved_fact_form(*, child_role, submitted_schema_json, expanded_schema, declaration):
    """Validate SAVED relationships without a factory, state or custody claim."""
    child_role = _name(child_role, 'child_role')
    submitted = _submitted(submitted_schema_json)
    saved = _copy(declaration, 'declaration')
    expected_keys = {'version', 'child_role', 'submitted_schema_json', 'expanded_schema_sha256', 'fact_references'}
    if (not isinstance(saved, dict) or set(saved) != expected_keys or saved['version'] != DECLARATION_VERSION
            or saved['child_role'] != child_role or saved['submitted_schema_json'] != submitted_schema_json
            or type(saved['expanded_schema_sha256']) is not str
            or _DIGEST.fullmatch(saved['expanded_schema_sha256']) is None
            or not isinstance(saved['fact_references'], list)):
        raise ContractInformationError('saved_contract_declaration_mismatch', 'declaration')
    expanded = _closed(_schema(expanded_schema, 'expanded_schema', object_only=True))
    if schema_fingerprint(expanded) != saved['expanded_schema_sha256']:
        raise ContractInformationError('saved_expanded_schema_mismatch', 'expanded_schema')
    references = _references(submitted)
    if len(references) != len(saved['fact_references']):
        raise ContractInformationError('saved_fact_reference_roster_mismatch', 'declaration.fact_references')
    expected = _copy(submitted, 'submitted_schema')
    for (field, source), row in zip(references, saved['fact_references']):
        if (not isinstance(row, dict) or set(row) != {'field', 'source', 'schema_sha256', 'source_had_x_source'}
                or row['field'] != field or row['source'] != source or type(row['source_had_x_source']) is not bool
                or type(row['schema_sha256']) is not str or _DIGEST.fullmatch(row['schema_sha256']) is None):
            raise ContractInformationError('saved_fact_reference_roster_mismatch', 'declaration.fact_references')
        original = expanded['properties'].get(field)
        if not isinstance(original, dict) or original.get('x-source') != source:
            raise ContractInformationError('saved_fact_source_selector_mismatch', field)
        submitted_field = submitted['properties'][field]
        if (source == _RESTRICTION_SOURCE and schema_fingerprint(original) !=
                schema_fingerprint(_restriction_schema(submitted_field, field))):
            raise ContractInformationError('saved_fact_selection_mismatch', field)
        if (_UNIPROT_SELECTION in submitted_field and
                (_UNIPROT_SELECTION not in original or
                 schema_fingerprint(submitted_field[_UNIPROT_SELECTION]) !=
                 schema_fingerprint(original[_UNIPROT_SELECTION]))):
            raise ContractInformationError('saved_fact_selection_mismatch', field)
        original = _copy(original, field)
        if not row['source_had_x_source']:
            del original['x-source']
        if schema_fingerprint(original) != row['schema_sha256']:
            raise ContractInformationError('saved_fact_source_schema_mismatch', field)
        original['x-source'] = source
        expected['properties'][field] = original
    if schema_fingerprint(expected) != schema_fingerprint(expanded):
        raise ContractInformationError('saved_compact_expanded_form_mismatch', 'expanded_schema')
    return expanded


__all__ = ['OPERATION_INFORMATION_VERSION', 'RETURN_INFORMATION_VERSION', 'DECLARATION_VERSION',
           'FACT_REFERENCE_PREFIX', 'ContractInformationError', 'operation_contract_information',
           'return_contract_information', 'expand_fact_form', 'validate_saved_fact_form']
