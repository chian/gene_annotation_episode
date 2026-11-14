"""Closed v2 provider contracts; source custody remains with the API host.

These checks never acquire bytes, parse reports or recalculate correspondence.
Version 1 contracts and pins remain separate and unchanged.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from . import bvbrc_proteome_bundle_contracts as legacy
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_proteome_data_contracts import _plain, _Validator
from .bvbrc_proteome_directional_contracts import validate_directional_report
from .bvbrc_proteome_directional_numerical_contracts import validate_directional_numerical
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data

canonical, digest = legacy.canonical, legacy.digest
_FAILURES = (
    ('document_missing', 'output_bytes', 'proteome_directional_report', 'association'),
    ('document_ambiguous duplicate_document_selection', 'parser_binding', 'proteome_directional_report', 'association'),
    ('artifact_binding_conflict artifact_digest_mismatch', 'byte_version_evidence', 'proteome_directional_report', 'association'),
    ('format_incompatible nonzero_range_unsupported declared_version_conflict', 'parser_binding', 'proteome_directional_report', 'association'),
    ('reader_contract_invalid sheet_construction_failed calculation_failed', 'parser_binding', 'proteome_directional_report', 'native_decode'),
    ('requested_target_missing requested_value_unavailable', 'scientific_metadata', 'proteome_requested_projection', 'publication'),
    ('saved_identity_conflict saved_numerical_relationship_conflict', 'parser_binding', 'proteome_requested_projection', 'return'),
)
DIRECTIONAL_BINDING_DETAILS = {'proteome_directional_' + name: (kind, role, phase)
    for names, kind, role, phase in _FAILURES for name in names.split()}
DIRECTIONAL_BINDING_CODES = frozenset(DIRECTIONAL_BINDING_DETAILS)
DIRECTIONAL_BINDING_INPUT_KINDS = {name: value[0] for name, value in DIRECTIONAL_BINDING_DETAILS.items()}
BINDING_DETAILS = {**legacy.BINDING_DETAILS, **DIRECTIONAL_BINDING_DETAILS}
BINDING_CODES = frozenset(BINDING_DETAILS)


class ProteomeBundleV2Error(ValueError):
    def __init__(self, code, path=''):
        if code not in BINDING_CODES:
            raise ValueError('unknown_proteome_bundle_v2_failure_code')
        self.code, self.path = code, path
        super().__init__(code)


def _require(condition, code='proteome_directional_saved_identity_conflict', path=''):
    if not condition:
        raise ProteomeBundleV2Error(code, path)


_DOCUMENT = json.loads(Path(__file__).with_name('bvbrc_proteome_bundle_v2_schemas.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def _schema(name):
    definitions, reached = _DOCUMENT['$defs'], set()
    _require(name in definitions, 'proteome_parameters_invalid', '/name')
    def visit(node):
        if type(node) is dict:
            if '$ref' in node:
                key = node['$ref'].removeprefix('#/$defs/')
                if key not in definitions:
                    raise RuntimeError('invalid_packaged_proteome_v2_reference')
                if key not in reached:
                    reached.add(key)
                    visit(definitions[key])
            for child in node.values(): visit(child)
        elif type(node) is list:
            for child in node: visit(child)
    root = {'$schema': _DOCUMENT['$schema'], '$ref': '#/$defs/' + name}
    visit(root)
    root['$defs'] = {k: v for k, v in definitions.items() if k in reached}
    return root


def bundle_schema_v2(name):
    return deepcopy(_schema(name))


def parameters_schema_v2():
    return bundle_schema_v2('ProviderParametersV2')


@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))


def validate_shape_v2(name, value, *, code='proteome_directional_saved_identity_conflict', path=''):
    try:
        _plain(value)
        canonical(value).encode('utf-8')
        error = next(_validator(name).iter_errors(value), None)
        if error:
            for key in error.absolute_path: path = legacy._pointer(path, key)
            raise ProteomeBundleV2Error(code, path)
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, ProteomeBundleV2Error): raise
        raise ProteomeBundleV2Error(code, path + getattr(error, 'path', '')) from error
    return deepcopy(value)


def _checked(function, *args, path='', code='proteome_directional_saved_identity_conflict', **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        raise ProteomeBundleV2Error(code, path + getattr(error, 'path', getattr(error, 'pointer', ''))) from error


def validate_parameters_v2(value):
    result = validate_shape_v2('ProviderParametersV2', value, code='proteome_parameters_invalid')
    native, directional = result['native_documents'], result['directional_documents']
    ids = [x['document_id'] for x in native + directional]
    _require(bool(ids) and len(ids) == len(set(ids)), 'proteome_parameters_invalid', '/native_documents')
    for field in ('analysis_id', 'primary_document_id'):
        _require(result[field] is None or bool(result[field].strip()), 'proteome_parameters_invalid', '/' + field)
    for group, rows in (('native_documents', native), ('directional_documents', directional)):
        for i, row in enumerate(rows):
            for field in ('document_id', 'source_ref', 'raw_artifact_ref', 'requirement_id', 'report_key'):
                _require(field not in row or bool(row[field].strip()), 'proteome_parameters_invalid', f'/{group}/{i}/{field}')
            _checked(validate_contract, 'DeclaredFormat', row['declared_format'], code='proteome_parameters_invalid', path=f'/{group}/{i}/declared_format')
    _require(bool(native) == (result['primary_document_id'] is not None) == (result['calculation_parameters'] is not None),
             'proteome_parameters_invalid', '/primary_document_id')
    if native:
        _require(result['primary_document_id'] in [x['document_id'] for x in native], 'proteome_parameters_invalid', '/primary_document_id')
        _checked(validate_proteome_sheet_data, 'NativeCalculationParameters', result['calculation_parameters'],
                 code='proteome_parameters_invalid', path='/calculation_parameters')
    _require(bool(directional) == (result['directional_calculation_parameters'] is not None),
             'proteome_parameters_invalid', '/directional_calculation_parameters')
    if directional:
        keys = [x['report_key'] for x in directional]
        _require(len(keys) == len(set(keys)), 'proteome_parameters_invalid', '/directional_documents')
        _checked(validate_directional_numerical, 'DirectionalCalculationParameters', result['directional_calculation_parameters'],
                 code='proteome_parameters_invalid', path='/directional_calculation_parameters')
    if result['supplied_data_evidence'] is not None:
        _checked(validate_contract, 'SourceEvidence', result['supplied_data_evidence'], code='proteome_parameters_invalid', path='/supplied_data_evidence')
    return result


def validate_form_parameters(form, parameters):
    from .bvbrc_proteome_directional_fact_contracts import validate_requested_form_v2
    form = _checked(validate_requested_form_v2, form, code='proteome_requested_form_invalid', path='/requested_form')
    ids = {x['document_id'] for x in parameters['directional_documents']}
    for field, spec in form['properties'].items():
        selection = spec['x-bvbrc-proteome']
        if selection['kind'].startswith('directional_') and 'document_id' in selection:
            _require(selection['document_id'] in ids, 'proteome_requested_form_invalid', '/requested_form/properties/' + field)
    return form


def validate_result_selector_v2(value):
    result = _checked(validate_contract, 'ResultSelector', value, code='proteome_parameters_invalid')
    selected = result['adapter']
    _require(selected is not None and (selected['adapter_id'], selected['adapter_version']) == ('bvbrc_proteome', '2'),
             'proteome_parameters_invalid', '/adapter')
    params = validate_parameters_v2(selected['parameters'])
    validate_form_parameters(result['requested_schema'], params)
    requirements = result['requirements']
    ids = [x['requirement_id'] for x in requirements]
    _require(len(ids) == len(set(ids)), 'proteome_parameters_invalid', '/requirements')
    for group in ('native_documents', 'directional_documents'):
        for i, doc in enumerate(params[group]):
            if 'requirement_id' not in doc: continue
            matches = [x for x in requirements if x['requirement_id'] == doc['requirement_id']]
            _require(len(matches) == 1 and matches[0]['role'] == doc['role'] and matches[0]['declared_format'] == doc['declared_format'],
                     'proteome_parameters_invalid', f'/adapter/parameters/{group}/{i}')
    return result


def declaration_conflict(result, selection):
    version = selection['declared_format']['version']
    return version is not None and any(b['program']['value'] == 'BLASTP' and
        b['release']['state'] == 'present' and b['release']['value'] != version for b in result['banners'])


def validate_provider_sheet_v2(value):
    """Validate the envelope, unchanged legacy relationships and observed copies."""
    saved = validate_shape_v2('ProviderSheetV2', value)
    parameters = validate_parameters_v2(saved['parameters'])
    _require(saved['analysis_id'] == parameters['analysis_id'], path='/analysis_id')
    task = _checked(validate_contract, 'OriginalTask', saved['original_task'], path='/original_task')
    _require(task['required_application_id'] == task['native_application_id'] == 'GenomeComparison', path='/original_task')
    validate_form_parameters(saved['requested_form'], parameters)
    for i, row in enumerate(saved['supplied_values']):
        _checked(validate_contract, 'SourceEvidence', row['evidence'], path=f'/supplied_values/{i}/evidence')
    for kind, (name, contract) in legacy._RESULTS.items():
        results = ([saved[name]] if saved[name] is not None else []) if kind == 'original_input_index' else saved[name]
        for i, result in enumerate(results):
            _checked(legacy._validate_result, contract, result, f'/{name}/{i}')
    for name, contract in (('joins_result', 'NativeJoinsResult'), ('native_sheet_result', 'NativeSheetResult')):
        if saved[name] is not None:
            _checked(validate_proteome_sheet_data, contract, saved[name], path='/' + name)
    ids = [x['requirement_id'] for x in saved['requirements']]
    _require(len(ids) == len(set(ids)), path='/requirements')
    for name, contract in (('requirements', 'AcquisitionRequirement'), ('diagnostics', 'Diagnostic')):
        for i, row in enumerate(saved[name]):
            _checked(validate_contract, contract, row, path=f'/{name}/{i}')
            code = row['reason_code' if name == 'requirements' else 'code']
            _require(code in BINDING_CODES or code in legacy._PURE_CODES, path=f'/{name}/{i}')
            if code in BINDING_DETAILS:
                kind, role, phase = BINDING_DETAILS[code]
                _require((row['kind'] == kind and row['role'] == role) if name == 'requirements' else row['phase'] == phase, path=f'/{name}/{i}')
    supplied = legacy._selected_data(saved)
    view = {**saved, 'input_resolution': [r for r in saved['input_resolution'] if r['selector_kind'] != 'directional_document']}
    _checked(legacy._validate_resolution, view, supplied)
    _checked(legacy._index_task, saved)
    rows = [r for r in saved['input_resolution'] if r['selector_kind'] == 'directional_document']
    _require([r['selection_index'] for r in rows] == list(range(len(parameters['directional_documents']))), path='/input_resolution')
    accounted = []
    for row in rows:
        path = '/input_resolution/' + str(saved['input_resolution'].index(row))
        _require(len(row['requirement_ids']) == len(set(row['requirement_ids'])) and set(row['requirement_ids']) <= set(ids), path=path)
        _require(row['construction_evidence'] is None, path=path)
        index = row['result_index']
        if index is None:
            _require(row['state'] not in ('resolved', 'partial') and bool(row['requirement_ids']), path=path)
            continue
        _require(index < len(saved['directional_results']), path=path)
        accounted.append(index)
        result = _checked(validate_directional_report, saved['directional_results'][index], path=f'/directional_results/{index}')
        choice = parameters['directional_documents'][row['selection_index']]
        expected = 'incompatible' if declaration_conflict(result, choice) else {'ok':'resolved','partial':'partial','failure':'invalid'}[result['parse_state']]
        _require(row['state'] == expected and row['content'] == result['source']['content'] and
                 result['report_key'] == choice['report_key'] and result['declared_format'] == choice['declared_format']['format'], path=path)
        if 'source_ref' in choice:
            _require((choice['source_ref'], choice['raw_artifact_ref']) == (row['content']['source_ref'], row['content']['artifact_ref']), path=path)
    _require(accounted == list(range(len(saved['directional_results']))), path='/directional_results')
    observed = saved['directional_sheet_result']
    _require(bool(parameters['directional_documents']) == (observed is not None), path='/directional_sheet_result')
    if observed is not None:
        # This branch validates observations only; the component validator would
        # call geometry and must never be used for saved-return validation.
        _checked(validate_directional_numerical, 'DirectionalSheetResult', observed, path='/directional_sheet_result')
        if observed['sheet'] is not None:
            _require(observed['sheet']['reader_results'] == saved['directional_results'], path='/directional_sheet_result/sheet/reader_results')
    _legacy_copies(saved, supplied)
    legacy_sheet = None if saved['native_sheet_result'] is None else saved['native_sheet_result']['value']
    directional_sheet = None if observed is None else observed['sheet']
    numerical = saved['numerical_sheet']
    _require((numerical is None) == (legacy_sheet is None and directional_sheet is None), path='/numerical_sheet')
    if numerical is not None:
        _require(canonical(numerical['legacy_sheet']) == canonical(legacy_sheet) and numerical['directional_sheet'] == directional_sheet,
                 path='/numerical_sheet')
    return saved


def _legacy_copies(saved, supplied):
    native = saved['native_sheet_result']
    if native is not None and native['value'] is not None:
        value = native['value']
        selected = [r for r in saved['input_resolution'] if r['selector_kind'] == 'native_document' and
            saved['parameters']['native_documents'][r['selection_index']]['document_id'] == saved['parameters']['primary_document_id']]
        _require(len(selected) == 1 and selected[0]['content'] is not None and selected[0]['result_index'] is not None and
                 value['primary_source_ref'] == selected[0]['content']['source_ref'], path='/native_sheet_result/value/primary_source_ref')
        _require(canonical(value['native_results']) == canonical(saved['native_results']), path='/native_sheet_result/value/native_results')
        for envelope, field in (('input_index_result','input_index'),('joins_result','joins')):
            expected = saved[envelope]['value'] if saved[envelope] is not None else None
            _require(canonical(value[field]) == canonical(expected), path='/native_sheet_result/value/' + field)
        for envelope, field in (('inventory_results','inventories'),('feature_results','feature_snapshots'),
                                ('genome_results','genome_snapshots'),('sequence_results','sequence_snapshots')):
            _require(canonical(value[field]) == canonical([x['value'] for x in saved[envelope] if x['value'] is not None]), path='/native_sheet_result/value/' + field)
        _require(canonical([x['link'] for x in value['representation_comparisons']]) == canonical(supplied['representation_links'] if supplied else []) and
                 value['directional_attachment'] is None, path='/native_sheet_result/value/representation_comparisons')
    joins = saved['joins_result']
    if joins is not None and joins['value'] is not None:
        for source, target in (('execution_links','execution_links'),('native_links','requested_native_links'),('metadata_links','requested_metadata_links')):
            _require(canonical(joins['value'][target]) == canonical(supplied[source] if supplied else []), path='/joins_result/value/' + target)


def validate_saved_provider_v2(sheet, components, *, parameters, requested_form, original_task, bundle_sha256, bundle):
    from .bvbrc_proteome_directional_saved_validation import validate_saved_provider_v2 as validate
    return validate(sheet, components, parameters=parameters, requested_form=requested_form,
                    original_task=original_task, bundle_sha256=bundle_sha256, bundle=bundle)


__all__ = ['parameters_schema_v2', 'validate_parameters_v2', 'validate_result_selector_v2',
    'validate_provider_sheet_v2', 'validate_saved_provider_v2', 'bundle_schema_v2',
    'DIRECTIONAL_BINDING_CODES', 'DIRECTIONAL_BINDING_DETAILS', 'DIRECTIONAL_BINDING_INPUT_KINDS', 'ProteomeBundleV2Error']
