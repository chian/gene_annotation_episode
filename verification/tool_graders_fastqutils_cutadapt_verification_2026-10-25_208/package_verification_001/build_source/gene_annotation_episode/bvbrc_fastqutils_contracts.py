"""Pure FastqUtils shape, content and relationship contracts.

The schema describes stored measurements. It is not a numerical rule engine;
scientific calculations remain separate ordinary functions. These helpers do
not acquire data, authenticate possession or grant episode capabilities.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

_SCHEMA = json.loads(files(__package__).joinpath('bvbrc_fastqutils_schemas.json').read_text())
_DEFS = _SCHEMA['$defs']
_LEGACY_DEFS = json.loads(files(__package__).joinpath(
    'bvbrc_fastqutils_legacy_v2_schemas.json').read_text())['$defs']
_FAILURES = frozenset(_DEFS['ContractFailure']['properties']['code']['enum'])
_POINTER = re.compile(r'(?:/(?:[^~/]|~[01])*)*\Z')
_INTEGER = re.compile(r'(?:0|[1-9][0-9]*)\Z')


class FastqUtilsContractError(ValueError):
    def __init__(self, code: str, path: str = ''):
        if code not in _FAILURES or type(path) is not str or not _POINTER.fullmatch(path):
            raise ValueError('invalid_fastqutils_contract_error')
        self.code, self.path = code, path
        self.diagnostics = [{'code': code, 'path': path, 'source_refs': [], 'affected_refs': []}]
        super().__init__(code)


def _require(condition, code='saved_relationship_conflict', path=''):
    if not condition:
        raise FastqUtilsContractError(code, path)


def _token(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def _pointer(parts):
    return ''.join('/' + _token(part) for part in parts)


def validate_finite_json(value: object) -> None:
    active = set()

    def visit(item, path):
        kind = type(item)
        if item is None or kind in (bool, int):
            return
        if kind is float:
            _require(math.isfinite(item), 'nonfinite_json', path)
            return
        if kind is str:
            try:
                item.encode('utf-8', errors='strict')
            except UnicodeError as error:
                raise FastqUtilsContractError('nonfinite_json', path) from error
            return
        _require(kind in (dict, list), 'nonfinite_json', path)
        _require(id(item) not in active, 'nonfinite_json', path)
        active.add(id(item))
        try:
            if kind is dict:
                for key, child in item.items():
                    _require(type(key) is str, 'nonfinite_json', path)
                    visit(key, path)
                    visit(child, path + '/' + _token(key))
            else:
                for index, child in enumerate(item):
                    visit(child, path + '/' + str(index))
        finally:
            active.remove(id(item))

    try:
        visit(value, '')
    except RecursionError as error:
        raise FastqUtilsContractError('nonfinite_json') from error


def canonical_json(value: object) -> str:
    validate_finite_json(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def bytes_sha256(raw: bytes) -> str:
    _require(type(raw) is bytes, 'shape_invalid')
    return hashlib.sha256(raw).hexdigest()


_StrictValidator = validators.extend(Draft202012Validator, type_checker=(
    Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, v: type(v) is int)
    .redefine('number', lambda _, v: type(v) in (int, float) and (type(v) is int or math.isfinite(v)))
    .redefine('object', lambda _, v: type(v) is dict)
    .redefine('array', lambda _, v: type(v) is list)))


@lru_cache(maxsize=256)
def _validator(name):
    _require(type(name) is str and name in _DEFS, 'shape_invalid')
    return _StrictValidator({'$ref': '#/$defs/' + name, '$defs': _DEFS})


def validate_contract(name: str, value: object):
    validate_finite_json(value)
    error = next(_validator(name).iter_errors(value), None)
    if error is not None:
        raise FastqUtilsContractError('shape_invalid', _pointer(error.absolute_path))
    return deepcopy(value)


def checked_bytes(raw: bytes, *, content: dict) -> bytes:
    binding = validate_contract('Host_ContentBinding', content)
    _require(type(raw) is bytes, 'shape_invalid')
    _require(len(raw) == binding['byte_count'] and bytes_sha256(raw) == binding['sha256'], 'binding_conflict')
    return raw


def pointer_value(value: object, pointer: str):
    _require(type(pointer) is str and _POINTER.fullmatch(pointer), 'reference_invalid')
    current = value
    for token in pointer.split('/')[1:]:
        key = token.replace('~1', '/').replace('~0', '~')
        if type(current) is dict:
            _require(key in current, 'reference_invalid', pointer)
            current = current[key]
        elif type(current) is list:
            _require(_INTEGER.fullmatch(key), 'reference_invalid', pointer)
            try:
                index = int(key)
            except ValueError as error:
                raise FastqUtilsContractError('reference_invalid', pointer) from error
            _require(index < len(current), 'reference_invalid', pointer)
            current = current[index]
        else:
            raise FastqUtilsContractError('reference_invalid', pointer)
    validate_finite_json(current)
    return deepcopy(current)


def _unique(rows, field='id', path=''):
    result = {}
    for index, row in enumerate(rows):
        key = row[field]
        _require(key not in result, 'duplicate_identity', path + '/' + str(index) + '/' + field)
        result[key] = row
    return result


def validate_parameters(value: dict) -> dict:
    result = validate_contract('ProviderParameters', value)
    _unique(result['documents'], 'document_id', '/documents')
    _unique(result['metadata_bindings'], 'metadata_id', '/metadata_bindings')
    _unique(result['calculation_requests'], 'calculation_id', '/calculation_requests')
    return result


def _definition_closure(name, definitions=None):
    definitions = _DEFS if definitions is None else definitions
    retained = {}

    def walk(value):
        if type(value) is dict:
            if '$ref' in value:
                reference = value['$ref']
                _require(reference.startswith('#/$defs/'), 'requested_form_invalid')
                key = reference[len('#/$defs/'):]
                _require(key in definitions, 'requested_form_invalid')
                if key not in retained:
                    retained[key] = deepcopy(definitions[key])
                    walk(definitions[key])
            for child in value.values():
                walk(child)
        elif type(value) is list:
            for child in value:
                walk(child)
    walk({'$ref': '#/$defs/' + name})
    return retained


def make_requested_schema(form: dict) -> dict:
    form = validate_contract('RequestedForm', form)
    _unique(form['fields'], 'field', '/fields')
    properties = {}
    for field in form['fields']:
        selection = field['selection']
        _require(selection['cardinality'] != 'one_target' or selection['expected_cardinality'] == 1,
                 'requested_form_invalid')
        properties[field['field']] = {'$ref': '#/$defs/ProjectedField',
                                     'x-bvbrc-fastqutils': deepcopy(selection)}
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False, '$defs': _definition_closure('ProjectedField')}


def validate_requested_form(schema: dict) -> dict:
    validate_finite_json(schema)
    _require(type(schema) is dict and type(schema.get('properties')) is dict, 'requested_form_invalid')
    # Canonical durable JSON sorts object keys. The declared array preserves
    # the parent's field order through storage and must name each exact field.
    names = schema.get('required')
    _require(type(names) is list and all(type(name) is str for name in names)
        and len(names) == len(set(names)) and set(names) == set(schema['properties']), 'requested_form_invalid')
    fields = []
    for field in names:
        node = schema['properties'][field]
        _require(type(node) is dict and 'x-bvbrc-fastqutils' in node, 'requested_form_invalid')
        fields.append({'field': field, 'selection': deepcopy(node['x-bvbrc-fastqutils'])})
    form = {'version': 'fastqutils_projection_v2', 'fields': fields}
    expected = make_requested_schema(form)
    if canonical_json(schema) != canonical_json(expected):
        # Exact historical grammar only, not arbitrary subsets or weakened
        # definitions. Keep the original field order and selectors unchanged.
        legacy_validator = _StrictValidator({'$ref': '#/$defs/RequestedForm', '$defs': _LEGACY_DEFS})
        _require(legacy_validator.is_valid(form), 'requested_form_invalid')
        expected['$defs'] = _definition_closure('ProjectedField', _LEGACY_DEFS)
        _require(canonical_json(schema) == canonical_json(expected), 'requested_form_invalid')
    return form


def _encoding(basis, *, metadata=None):
    validate_contract('EncodingBasis', basis)
    kind = basis['basis']
    declared = ('metadata_id', 'evidence', 'declaration')
    if kind == 'unknown':
        _require(basis['encoding'] == 'unknown' and basis['native_locator'] is None
                 and all(basis[key] is None for key in declared))
    elif kind in ('native_bam_phred', 'native_sam_phred'):
        expected = 'bam_phred' if kind == 'native_bam_phred' else 'phred33'
        _require(basis['encoding'] == expected and basis['native_locator'] is not None
                 and all(basis[key] is None for key in declared))
    else:
        _require(all(basis[key] is not None for key in declared) and basis['native_locator'] is None)
        _require(basis['declaration']['encoding'] == basis['encoding'])
        if metadata is not None:
            item = metadata.get(basis['metadata_id'])
            _require(item is not None and item['kind'] == 'encoding_declaration'
                     and canonical_json(item['value']) == canonical_json(basis['declaration'])
                     and canonical_json(item['evidence']) == canonical_json(basis['evidence']))


def _lineage_basis(basis, *, metadata=None, lineage=None):
    if basis is None:
        return
    validate_contract('LineageBasis', basis)
    if basis['basis'] == 'unknown':
        _require(all(basis[key] is None for key in ('metadata_id', 'evidence', 'declaration', 'native_lineage_ref')))
    elif basis['basis'] == 'explicit_source_bound_declaration':
        _require(all(basis[key] is not None for key in ('metadata_id', 'evidence', 'declaration'))
                 and basis['native_lineage_ref'] is None)
        if metadata is not None:
            item = metadata.get(basis['metadata_id'])
            _require(item is not None and item['kind'] == 'lineage_declaration'
                     and canonical_json(item['evidence']) == canonical_json(basis['evidence'])
                     and canonical_json(item['value']) == canonical_json(basis['declaration']))
    else:
        _require(all(basis[key] is None for key in ('metadata_id', 'evidence', 'declaration'))
                 and basis['native_lineage_ref'] is not None)
        if lineage is not None:
            edge = lineage.get(basis['native_lineage_ref'])
            expected = 'native_report_before_after' if basis['basis'] == 'native_report' else 'observed_record_correspondence'
            _require(edge is not None and edge['kind'] == expected)


def _cell(cell):
    from .bvbrc_fastqutils_metric_specs import metric_spec
    spec = metric_spec(cell['metric'])
    _require(cell['unit'] in spec['units'] and cell['axis']['kind'] in spec['axis_kinds'])
    _require(cell['meaning'] == spec['meaning'] and cell['precision'] == spec['precision'])
    value = cell['value']
    domain = spec['value_domain']
    if value is not None:
        if domain == 'nonnegative_integer':
            _require(type(value) is int and value >= 0)
        elif domain == 'nonnegative_number':
            _require(value >= 0)
        elif domain == 'number_0_1':
            _require(0 <= value <= 1)
        elif domain == 'integer_0_100':
            _require(type(value) is int and 0 <= value <= 100)
    lower, upper = cell['axis']['lower'], cell['axis']['upper']
    _require(lower is None or upper is None or lower <= upper)


def _locator(locator):
    start, end = locator['byte_start'], locator['byte_end']
    _require(start is None or end is None or start <= end)


def _population(pop, *, artifacts, records, populations, metadata=None, native=False):
    _require(set(pop['member_artifact_refs']) <= set(artifacts))
    _require(set(pop['member_record_refs']) <= set(records))
    _require(set(pop['parent_population_refs']) <= set(populations)
             and set(pop['disjoint_from_refs']) <= set(populations))
    _require(pop['id'] not in pop['parent_population_refs'] and pop['id'] not in pop['disjoint_from_refs'])
    _require(len(pop['member_record_refs']) == len(set(pop['member_record_refs'])))
    _encoding(pop['encoding_basis'], metadata=metadata)
    _require(pop['quality_encoding'] == pop['encoding_basis']['encoding'])
    for reference in pop['member_record_refs']:
        _require(records[reference]['artifact_ref'] in pop['member_artifact_refs'])
    for reference in pop['member_artifact_refs']:
        _require(artifacts[reference]['document_id'] in pop['document_ids'])
    if native:
        _require(pop['association_ref'] is None)
        _require(pop['encoding_basis']['basis'] != 'explicit_source_bound_declaration')


def validate_native_document(value: dict) -> None:
    from . import bvbrc_fastqutils_identity as identity
    doc = validate_contract('NativeDocument', value)
    artifact = doc['artifact']
    content = artifact['content_binding']
    _require(doc['document_id'] == artifact['document_id'])
    _require(artifact['source_ref'] == content['source_ref'] and artifact['content_ref'] == content['artifact_ref']
             and artifact['sha256'] == content['sha256'] and artifact['byte_count'] == content['byte_count'],
             'binding_conflict', '/artifact')
    context = {'analysis_id': doc['analysis_id'], 'document_id': doc['document_id'],
               'task_ref': artifact['task_ref'], 'content': content, 'native_name': artifact['native_name'],
               'declared_format': artifact['declared_format'], 'producer_version': artifact['producer_version'],
               'transfer_scope': artifact['transfer_scope'], 'identity': artifact['identity']}
    _require(artifact['id'] == identity.artifact_ref(context), 'reference_invalid', '/artifact/id')
    collections = {'cells': 'cell', 'categories': 'category', 'labels': 'label',
                   'sequence_records': 'sequence', 'alignment_records': 'alignment', 'alignment_headers': 'header'}
    all_rows = {}
    for collection, kind in collections.items():
        for index, row in enumerate(doc[collection]):
            _require(row['id'] not in all_rows, 'duplicate_identity', '/' + collection + '/' + str(index))
            all_rows[row['id']] = row
            _require(row['id'] == identity.native_ref(kind, context, row.get('ordinal', index)), 'reference_invalid')
            _require(row['artifact_ref'] == artifact['id'], 'binding_conflict')
            _locator(row['locator'])
            if 'association_ref' in row:
                _require(row['association_ref'] is None)
    populations = _unique(doc['populations'])
    records = {row['id']: row for name in ('sequence_records', 'alignment_records') for row in doc[name]}
    artifacts = {artifact['id']: artifact}
    for pop in populations.values():
        _require(pop['id'] == identity.population_ref(context, pop['population_key'], pop['population_ordinal']),
                 'reference_invalid')
        _require(pop['document_ids'] == [doc['document_id']])
        _population(pop, artifacts=artifacts, records=records, populations=populations, native=True)
    for cell in doc['cells']:
        _cell(cell)
        _require(cell['population_ref'] is None or cell['population_ref'] in populations)
    for row in doc['sequence_records']:
        _require(row['quality_symbols'] is None or len(row['sequence']) == len(row['quality_symbols']))
        _require(row['phred_values'] is None or len(row['sequence']) == len(row['phred_values']))
    for row in doc['alignment_records']:
        _require(row['sequence'] is None or row['phred_values'] is None
                 or len(row['sequence']) == len(row['phred_values']))
        if artifact['actual_format'] == 'bam_1':
            _require(row['native_quality_symbols'] is None)
        elif artifact['actual_format'] == 'sam_1_6':
            _require(row['native_quality_symbols'] is not None)
    sections = set()
    for section in doc['sections']:
        key = section['key'], section['ordinal']
        _require(key not in sections, 'duplicate_identity')
        sections.add(key)
        _locator(section['locator'])
        for field, collection in (('cell_refs', 'cells'), ('category_refs', 'categories'), ('label_refs', 'labels')):
            allowed = {row['id']: row for row in doc[collection]}
            _require(len(section[field]) == len(set(section[field])))
            for reference in section[field]:
                row = allowed.get(reference)
                _require(row is not None and (row['section_key'], row['section_ordinal']) == key)
        _require(all(index < len(doc['raw_blocks']) for index in section['raw_block_ordinals']))
    for collection in ('cells', 'categories', 'labels'):
        for row in doc[collection]:
            _require((row['section_key'], row['section_ordinal']) in sections)
    headers = {row['id'] for row in doc['alignment_headers']}
    for entry in doc['reference_dictionary']:
        _require(entry['header_ref'] is None or entry['header_ref'] in headers)
    _unique(doc['native_lineage'])
    for edge in doc['native_lineage']:
        _require(edge['before_population_ref'] in populations and edge['after_population_ref'] in populations)
        _require(edge['document_ids'] == [doc['document_id']] and edge['source_refs'] == [artifact['source_ref']])
    _unique(doc['requirements'])


def _original_metadata(value):
    from . import bvbrc_fastqutils_identity as identity
    original = value['original_task']
    task = original['submission_receipt_ref']
    analysis = value['analysis_id']
    _require(value['task_ref'] == task, 'binding_conflict', '/task_ref')
    _require(original['native_application_id'] == original['required_application_id'] == 'FastqUtils', 'binding_conflict')
    libraries = _unique(value['libraries'])
    stages = _unique(value['stages'])
    metadata = _unique(value['supplied_metadata'], 'metadata_id')
    for library in libraries.values():
        _require(library['task_ref'] == task and library['id'] == identity.library_ref(
            analysis, task, library['input_pointer']), 'reference_invalid')
        original_value = pointer_value(original['submitted_parameters'], library['input_pointer'])
        _require(canonical_json(original_value) == canonical_json(library['submitted_value']))
        _require(set(library['metadata_ids']) <= set(metadata))
    recipe = original['submitted_parameters'].get('recipe', [])
    _require(type(recipe) is list)
    for stage in stages.values():
        index = stage['recipe_ordinal']
        _require(type(index) is int and 0 <= index < len(recipe))
        _require(stage['task_ref'] == task and stage['id'] == identity.stage_ref(analysis, task, index))
        _require(stage['requested_token'] == recipe[index]
                 and stage['request_pointer'] == '/submitted_parameters/recipe/' + str(index))
        # A requested recipe or a scientific association assumption is not an
        # execution trace. No such trace format is bound by this contract.
        _require(stage['observed_state'] == 'unknown')
        token = recipe[index].upper()
        _require(stage['mode'] == (token if token in {'TRIM', 'PAIRED_FILTER', 'FASTQC', 'ALIGN', 'SCRUB_HUMAN'} else 'UNKNOWN'))
    for association in _unique(value['associations']).values():
        _require(association['task_ref'] == task and association['library_ref'] in libraries)
        _require(association['stage_ref'] is None or association['stage_ref'] in stages)
        _require(set(association['metadata_ids']) <= set(metadata))
        if association['basis'] == 'explicit_assertion':
            _require(association['state'] != 'established')
    _unique(value['requirements'])
    return metadata


def validate_metadata(value: dict) -> None:
    value = validate_contract('Metadata', value)
    _original_metadata(value)
    _unique(value['populations'])
    _unique(value['measurements'])
    for cell in value['measurements']:
        _require(cell['metric'] == 'verified_pair_count')
        _cell(cell)


def validate_sheet(value: dict) -> None:
    sheet = validate_contract('Sheet', value)
    metadata = _original_metadata(sheet)
    docs = _unique(sheet['documents'], 'document_id')
    artifacts, records = {}, {}
    native_cells, native_categories, native_populations = {}, {}, {}
    for doc in docs.values():
        validate_native_document(doc)
        _require(doc['analysis_id'] == sheet['analysis_id'] and doc['artifact']['task_ref'] == sheet['task_ref'])
        artifact = doc['artifact']
        _require(artifact['id'] not in artifacts, 'duplicate_identity')
        artifacts[artifact['id']] = artifact
        for name, target in (('cells', native_cells), ('categories', native_categories), ('populations', native_populations)):
            for row in doc[name]:
                _require(row['id'] not in target, 'duplicate_identity')
                target[row['id']] = row
        for name in ('sequence_records', 'alignment_records'):
            records.update({row['id']: row for row in doc[name]})
    populations = _unique(sheet['populations'])
    cells = _unique(sheet['measurements'])
    categories = _unique(sheet['categories'])
    associations = _unique(sheet['associations'])
    _require(set(native_cells) <= set(cells) and set(native_categories) <= set(categories)
             and set(native_populations) <= set(populations))
    for reference, row in native_cells.items():
        _require(canonical_json({k: v for k, v in cells[reference].items() if k != 'association_ref'}) ==
                 canonical_json({k: v for k, v in row.items() if k != 'association_ref'}))
    for reference, row in native_categories.items():
        _require(canonical_json({k: v for k, v in categories[reference].items() if k != 'association_ref'}) ==
                 canonical_json({k: v for k, v in row.items() if k != 'association_ref'}))
    for reference, row in native_populations.items():
        changed = {'association_ref', 'quality_encoding', 'encoding_evidence_refs', 'encoding_basis'}
        _require(canonical_json({k: v for k, v in populations[reference].items() if k not in changed}) ==
                 canonical_json({k: v for k, v in row.items() if k not in changed}))
    for pop in populations.values():
        _population(pop, artifacts=artifacts, records=records, populations=populations, metadata=metadata)
        _require(set(pop['document_ids']) <= set(docs))
        _require(pop['association_ref'] is None or pop['association_ref'] in associations)
    for cell in cells.values():
        _cell(cell)
        _require(cell['artifact_ref'] in artifacts and (cell['population_ref'] is None or cell['population_ref'] in populations))
        _require(cell['association_ref'] is None or cell['association_ref'] in associations)
        if cell['id'] not in native_cells:
            _require(cell['metric'] == 'verified_pair_count')
    lineage = _unique(sheet['native_lineage'])
    for edge in lineage.values():
        _require(edge['before_population_ref'] in populations and edge['after_population_ref'] in populations)
    for item in metadata.values():
        _require(item['evidence']['pointer'] == '' or _POINTER.fullmatch(item['evidence']['pointer']))


def validate_components(value: dict, *, sheet: dict) -> None:
    from .bvbrc_fastqutils_identity import component_ref
    from .bvbrc_fastqutils_metric_specs import component_spec
    components = validate_contract('Components', value)
    validate_sheet(sheet)
    _require(components['sheet_sha256'] == json_sha256(sheet), 'saved_hash_conflict')
    _require(components['analysis_id'] == sheet['analysis_id'] == components['parameters']['analysis_id'])
    parameters = components['parameters']
    parameter_hash = json_sha256(parameters)
    jobs = _unique(parameters['calculations'], 'calculation_id')
    _unique(components['components'])
    populations = {row['id']: row for row in sheet['populations']}
    measurements = {row['id']: row for row in sheet['measurements']}
    metadata = {row['metadata_id']: row for row in sheet['supplied_metadata']}
    lineage = {row['id']: row for row in sheet['native_lineage']}
    for job in jobs.values():
        _require(set(job['population_refs']) <= set(populations) and set(job['operand_measurement_refs']) <= set(measurements))
        _lineage_basis(job['lineage_basis'], metadata=metadata, lineage=lineage)
    for row in components['components']:
        job = jobs.get(row['calculation_id'])
        _require(job is not None and row['method'] == job['method'])
        spec = component_spec(row['metric'])
        _require(row['method'] == spec['method'] and row['unit'] in spec['units'])
        _require(row['parameter_sha256'] == parameter_hash, 'saved_hash_conflict')
        _require(row['id'] == component_ref(sheet['analysis_id'], components['sheet_sha256'], parameter_hash,
                 row['calculation_id'], row['metric'], row['threshold']), 'reference_invalid')
        _require(set(row['population_refs']) <= set(job['population_refs'])
                 and set(row['operand_measurement_refs']) <= set(job['operand_measurement_refs']))
        if row['encoding_basis'] is not None:
            _encoding(row['encoding_basis'], metadata=metadata)
        _lineage_basis(row['lineage_basis'], metadata=metadata, lineage=lineage)
        _require(canonical_json(row['lineage_basis']) == canonical_json(job['lineage_basis']))
        if row['metric'] == 'q_ge_threshold_fraction':
            _require(row['threshold'] in job['quality_thresholds'] and type(row['threshold']) is int)
        else:
            _require(row['threshold'] is None)
        expected_meaning = spec.get('meaning_by_comparison_kind', {}).get(job['comparison_kind'], spec['meaning'])
        expected_uncertainty = spec.get('uncertainty_by_comparison_kind', {}).get(job['comparison_kind'], spec['uncertainty'])
        _require(row['meaning'] == expected_meaning and row['uncertainty'] == expected_uncertainty)

