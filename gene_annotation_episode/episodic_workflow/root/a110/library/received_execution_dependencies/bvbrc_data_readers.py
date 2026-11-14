from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_fields import FIELD_REGISTRY
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_schema import validate
NUMERIC_TEXT_GRAMMARS = {'nonnegative_decimal_integer': {'pattern': '^[0-9]+$', 'numeric_type': 'integer', 'minimum': 0}, 'finite_nonnegative_decimal_scientific': {'pattern': '^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$', 'numeric_type': 'number', 'minimum': 0}}
_GRAMMARS = deepcopy(NUMERIC_TEXT_GRAMMARS)
_NUMBER = re.compile('-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
_WARNING = 'bvbrc_schema_observed_variant'

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def _escape(value):
    return value.replace('~', '~0').replace('/', '~1')

@dataclass(frozen=True)
class _Number:
    """An original JSON token, distinct from both strings and Python numbers."""
    text: str

    @property
    def integer(self):
        return not any((char in self.text for char in '.eE'))

    def project(self):
        try:
            if self.integer:
                return int(self.text)
            number = float(self.text)
            if not math.isfinite(number) or (number == 0 and Decimal(self.text) != 0):
                return None
            return number
        except (ValueError, OverflowError, InvalidOperation):
            return None

def _atom(value):
    result = dict(kind='null', string_value=None, number_value=None, boolean_value=None, number_lexeme=None)
    if isinstance(value, _Number):
        result.update(kind='number', number_value=value.project(), number_lexeme=value.text)
    elif type(value) is str:
        result.update(kind='string', string_value=value)
    elif type(value) is bool:
        result.update(kind='boolean', boolean_value=value)
    elif value is not None:
        raise ValueError('unsupported_native_atom')
    return result

def _matches_atom(atom, spec):
    kind = atom['kind']
    native_type = spec['solr_type']
    if native_type in ('int', 'long'):
        return kind == 'number' and _Number(atom['number_lexeme']).integer
    if native_type == 'float':
        return kind == 'number'
    if native_type == 'boolean':
        return kind == 'boolean'
    return kind == 'string'

def _native_cell(raw, *, field, spec, row_key, path, selected=True):
    cell = {'cell_key': row_key + '/field/' + _escape(field), 'field': field, 'native_path': path, 'presence': 'absent', 'native_shape': 'absent', 'atoms': [], 'status': 'missing', 'field_schema_status': 'not_evaluated', 'issue_codes': []}
    if not selected:
        cell.update(presence='unselected', status='unselected')
        return cell
    if type(raw) is not dict or field not in raw:
        return cell
    value = raw[field]
    if value is None:
        cell.update(presence='null', native_shape='null')
        return cell
    cell.update(presence='present', status='valid', field_schema_status='match')
    cell['native_shape'] = 'array' if type(value) is list else 'object' if type(value) is dict else 'scalar'
    values = value if type(value) is list else [value]
    if any((type(item) in (dict, list) for item in values)):
        cell.update(status='invalid', field_schema_status='mismatch', issue_codes=['bvbrc_invalid_native_field'])
        return cell
    cell['atoms'] = [_atom(item) for item in values]
    exception = 'finite_json_number' in spec['observed_variants'] and isinstance(value, _Number)
    compatible = exception or (spec['multi_valued'] == (type(value) is list) and all((_matches_atom(atom, spec) for atom in cell['atoms'])))
    if not compatible:
        cell.update(status='invalid', field_schema_status='mismatch')
        cell['issue_codes'].append('bvbrc_invalid_native_field')
    if exception:
        cell['field_schema_status'] = 'observed_exception'
        cell['issue_codes'].append(_WARNING)
    if any((atom['kind'] == 'number' and atom['number_value'] is None for atom in cell['atoms'])):
        if compatible:
            cell['status'] = 'unrepresentable'
        cell['issue_codes'].append('bvbrc_unrepresentable_numeric_value')
    return cell

def _numeric_cell(cell, spec):
    result = {key: cell[key] for key in ('cell_key', 'field', 'native_path')}
    result.update(value=None, status='missing', reason='native_field_absent', quantity_kind=spec['quantity_kind'], unit_code=spec['unit_code'], unit_basis=spec['unit_basis'], unit_cell_keys=[], denominator_value=None, denominator_basis='unknown', origin='unavailable', uncertainty_cell_keys=[], issue_codes=list(cell['issue_codes']))
    if cell['presence'] != 'present':
        result['reason'] = {'absent': 'native_field_absent', 'null': 'native_null', 'unselected': 'not_selected'}[cell['presence']]
        if cell['presence'] == 'unselected':
            result['status'] = 'unselected'
        return result
    if cell['status'] in ('invalid', 'unrepresentable'):
        result.update(status='invalid', reason='unrepresentable_numeric_value' if cell['status'] == 'unrepresentable' else 'native_value_invalid')
        return result
    if cell['native_shape'] == 'scalar' and len(cell['atoms']) == 1 and (cell['atoms'][0]['kind'] == 'number'):
        result.update(value=cell['atoms'][0]['number_value'], status='reported', reason=None, origin='native_reported')
        return result
    grammar_name = spec['numeric_text_grammar']
    if grammar_name is None:
        result.update(status='incompatible', reason='native_format_unverified')
        return result
    text = cell['atoms'][0]['string_value'] if cell['native_shape'] == 'scalar' else None
    grammar = _GRAMMARS[grammar_name]
    if text is None or re.fullmatch(grammar['pattern'], text) is None:
        result.update(status='invalid', reason='native_value_invalid')
    else:
        try:
            value = int(text) if grammar['numeric_type'] == 'integer' else float(text)
            decimal = Decimal(text)
            if decimal < 0:
                result.update(status='invalid', reason='native_value_invalid')
            elif type(value) is float and (not math.isfinite(value) or (value == 0 and decimal != 0)):
                result.update(status='invalid', reason='unrepresentable_numeric_value')
            else:
                result.update(value=value, status='parsed_numeric_text', reason=None, origin='derived_from_native_text')
        except (ValueError, OverflowError, InvalidOperation):
            result.update(status='invalid', reason='unrepresentable_numeric_value')
    if result['status'] == 'invalid':
        result['issue_codes'].append('bvbrc_unrepresentable_numeric_value' if result['reason'] == 'unrepresentable_numeric_value' else 'bvbrc_invalid_native_field')
    return result

def _validated_sheet(value):
    """Validate D2 row/cell semantics without imposing host custody or joins."""
    sheet = validate('DataSheet', value)
    collection, digest = (sheet['collection'], sheet['custody']['native_sha256'])
    registry = FIELD_REGISTRY[collection]
    selected = sheet['selected_fields']
    if any((field not in registry['fields'] for field in selected)):
        raise ValueError('bvbrc_unknown_field')
    if sheet['page']['mode'] != sheet['mode']:
        raise ValueError('bvbrc_inconsistent_sheet_mode')
    if sheet['mode'] != 'page' and (selected or sheet['page']['requested_offset'] is not None or sheet['page']['requested_limit'] is not None or (sheet['page']['next_offset'] is not None) or (sheet['page']['population_coverage'] != 'unknown')):
        raise ValueError('bvbrc_inconsistent_sheet_mode')
    for index, row in enumerate(sheet['rows']):
        key = digest + '/row/' + str(index)
        if row['row_index'] != index or row['row_key'] != key:
            raise ValueError('bvbrc_invalid_row_identity')
        expected_path = ('/response/docs/' if sheet['custody']['native_profile'] == 'solr_json_envelope_v1' else '/') + str(index)
        if row['native_path'] != expected_path:
            raise ValueError('bvbrc_invalid_row_identity')
        if [cell['field'] for cell in row['cells']] != selected:
            raise ValueError('bvbrc_invalid_selected_cells')
        for cell in row['cells']:
            field = cell['field']
            if cell['cell_key'] != key + '/field/' + _escape(field) or cell['native_path'] != row['native_path'] + '/' + _escape(field):
                raise ValueError('bvbrc_invalid_cell_identity')
            if cell['presence'] != 'present' and cell['atoms']:
                raise ValueError('bvbrc_invalid_native_atoms')
            if cell['native_shape'] == 'scalar' and len(cell['atoms']) != 1:
                raise ValueError('bvbrc_invalid_native_atoms')
            for atom in cell['atoms']:
                kind = atom['kind']
                expected_key = {'string': 'string_value', 'number': 'number_value', 'boolean': 'boolean_value'}.get(kind)
                if any((atom[key] is not None for key in ('string_value', 'number_value', 'boolean_value') if key != expected_key)):
                    raise ValueError('bvbrc_invalid_native_atoms')
                if kind == 'number':
                    lexeme = atom['number_lexeme']
                    projected = _Number(lexeme).project() if type(lexeme) is str else None
                    if lexeme is None or _NUMBER.fullmatch(lexeme) is None or projected != atom['number_value'] or (type(projected) is not type(atom['number_value'])):
                        raise ValueError('bvbrc_invalid_numeric_lexeme')
                    if atom['number_value'] is None and 'bvbrc_unrepresentable_numeric_value' not in cell['issue_codes']:
                        raise ValueError('bvbrc_unqualified_numeric_loss')
                elif atom['number_lexeme'] is not None or (expected_key and atom[expected_key] is None):
                    raise ValueError('bvbrc_invalid_native_atoms')
            if cell['presence'] == 'unselected':
                raise ValueError('bvbrc_unselected_acquired_cell')
            spec = registry['fields'][field]
            if cell['presence'] in ('absent', 'null'):
                raw = {} if cell['presence'] == 'absent' else {field: None}
            elif cell['native_shape'] == 'object' or (cell['native_shape'] == 'array' and cell['status'] == 'invalid' and (not cell['atoms'])):
                if cell['presence'] != 'present' or cell['atoms'] or cell['status'] != 'invalid' or (cell['field_schema_status'] != 'mismatch') or (cell['issue_codes'] != ['bvbrc_invalid_native_field']):
                    raise ValueError('bvbrc_invalid_native_atoms')
                continue
            elif cell['native_shape'] in ('scalar', 'array'):
                values = [_Number(atom['number_lexeme']) if atom['kind'] == 'number' else atom['string_value'] if atom['kind'] == 'string' else atom['boolean_value'] if atom['kind'] == 'boolean' else None for atom in cell['atoms']]
                raw = {field: values if cell['native_shape'] == 'array' else values[0]}
            else:
                raise ValueError('bvbrc_invalid_native_atoms')
            expected_cell = _native_cell(raw, field=field, spec=spec, row_key=key, path=cell['native_path'])
            if _canonical(cell) != _canonical(expected_cell):
                raise ValueError('bvbrc_inconsistent_native_cell')
        expected = [_numeric_cell(cell, registry['fields'][cell['field']]) for cell in row['cells'] if registry['fields'][cell['field']]['numeric_projection']]
        if _canonical(row['numerical_cells']) != _canonical(expected):
            raise ValueError('bvbrc_inconsistent_numeric_cells')
        identity_cells = [cell for cell in row['cells'] if cell['field'] == registry['unique_key']]
        if identity_cells:
            identity = identity_cells[0]
            native_id = identity['atoms'][0]['string_value'] if identity['status'] == 'valid' and identity['native_shape'] == 'scalar' and identity['atoms'] and (identity['atoms'][0]['kind'] == 'string') else None
            if row['native_id'] != (native_id or None):
                raise ValueError('bvbrc_inconsistent_native_identity')
        has_invalid = row['native_id'] is None or any((cell['status'] in ('invalid', 'unrepresentable') for cell in row['cells'])) or any((cell['status'] == 'invalid' for cell in expected))
        if (row['status'] == 'valid') == has_invalid:
            raise ValueError('bvbrc_inconsistent_row_status')
    page = sheet['page']
    valid = sum((row['status'] == 'valid' for row in sheet['rows']))
    if page['returned_row_count'] != len(sheet['rows']) or page['valid_row_count'] != valid or page['invalid_row_count'] != len(sheet['rows']) - valid:
        raise ValueError('bvbrc_inconsistent_page_counts')
    if sheet['qualification']['requested_fields_valid'] != (valid == len(sheet['rows'])):
        raise ValueError('bvbrc_inconsistent_row_qualification')
    if len(sheet['facets']) != (1 if sheet['mode'] == 'facet' else 0):
        raise ValueError('bvbrc_inconsistent_facet_selection')
    for facet in sheet['facets']:
        field = facet['request']['field']
        if field not in registry['fields'] or not registry['fields'][field]['facet_supported']:
            raise ValueError('bvbrc_facet_field_not_supported')
        for index, bucket in enumerate(facet['buckets']):
            key = digest + '/facet/' + _escape(field) + '/bucket/' + str(index)
            if bucket['bucket_key'] != key or bucket['term_cell_key'] != key + '/term' or bucket['native_path'] != facet['native_location'] + '/' + str(index * 2):
                raise ValueError('bvbrc_invalid_bucket_identity')
            term = bucket['term']
            if term is None:
                if bucket['status'] != 'invalid' or bucket['is_missing_bucket'] is not None:
                    raise ValueError('bvbrc_invalid_facet_term')
            else:
                if term['kind'] not in ('string', 'null'):
                    raise ValueError('bvbrc_invalid_facet_term')
                expected_term = _atom(term['string_value'] if term['kind'] == 'string' else None)
                if term != expected_term or bucket['is_missing_bucket'] != (term['kind'] == 'null'):
                    raise ValueError('bvbrc_invalid_facet_term')
            if bucket['status'] == 'valid' and (bucket['count'] is None or bucket['issues']):
                raise ValueError('bvbrc_invalid_facet_count')
        nonmissing = sum((bucket['is_missing_bucket'] is False for bucket in facet['buckets']))
        if facet['returned_nonmissing_bucket_count'] != nonmissing:
            raise ValueError('bvbrc_inconsistent_facet_counts')
        window = 'invalid' if facet['issues'] or any((bucket['status'] == 'invalid' for bucket in facet['buckets'])) else 'more_unknown' if nonmissing >= facet['request']['limit'] else 'exhausted_window'
        if facet['bucket_window_status'] != window:
            raise ValueError('bvbrc_inconsistent_facet_window')
        expected_complete = bool(page['response_complete'] and window == 'exhausted_window' and (facet['request']['offset'] == 0) and (facet['request']['min_count'] <= 1) and facet['request']['include_missing'])
        if facet['all_categories_complete'] != expected_complete:
            raise ValueError('bvbrc_inconsistent_facet_completeness')
    return sheet

def validate_data_sheet(value: dict) -> dict:
    """Return a detached saved sheet after finite/closed D2 semantic checks.

    Checks registered field membership, native row/cell identities and paths,
    scalar atom kinds/lexemes, numerical projections of those atoms, row/page
    counts and facet references/windows. Invalid input raises ValueError. Valid
    partial sheets and recorded population conflicts remain usable; calculators
    retain the corresponding unavailable reasons. This function reads no raw
    source, performs no acquisition, mutates no caller data and confers no host
    custody, source possession, biological join or episode admission.
    """
    return _validated_sheet(value)
