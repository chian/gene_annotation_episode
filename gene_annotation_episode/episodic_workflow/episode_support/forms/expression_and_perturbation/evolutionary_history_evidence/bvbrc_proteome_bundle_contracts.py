"""Closed provider contracts; source custody remains with the API host.

These checks never acquire bytes, parse reports or recalculate correspondence.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence import bvbrc_proteome_native_bundle_contracts as native_layer
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.evolutionary_history_evidence.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_data_contracts import _plain, _Validator
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_contracts import validate_directional_report
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_numerical_contracts import validate_directional_numerical
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data
canonical, digest = (native_layer.canonical, native_layer.digest)
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.bvbrc_proteome_parameter_contracts import _FAILURES, DIRECTIONAL_BINDING_DETAILS, DIRECTIONAL_BINDING_CODES, DIRECTIONAL_BINDING_INPUT_KINDS, BINDING_DETAILS, BINDING_CODES, ProteomeBundleError, _require, _DOCUMENT, _schema, bundle_schema, parameters_schema

@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))

def validate_shape(name, value, *, code='proteome_directional_saved_identity_conflict', path=''):
    try:
        _plain(value)
        canonical(value).encode('utf-8')
        error = next(_validator(name).iter_errors(value), None)
        if error:
            for key in error.absolute_path:
                path = native_layer._pointer(path, key)
            raise ProteomeBundleError(code, path)
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, ProteomeBundleError):
            raise
        raise ProteomeBundleError(code, path + getattr(error, 'path', '')) from error
    return deepcopy(value)

def _checked(function, *args, path='', code='proteome_directional_saved_identity_conflict', **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        raise ProteomeBundleError(code, path + getattr(error, 'path', getattr(error, 'pointer', ''))) from error

def validate_parameters(value):
    result = validate_shape('ProviderParameters', value, code='proteome_parameters_invalid')
    native, directional = (result['native_documents'], result['directional_documents'])
    ids = [x['document_id'] for x in native + directional]
    _require(bool(ids) and len(ids) == len(set(ids)), 'proteome_parameters_invalid', '/native_documents')
    for field in ('analysis_id', 'primary_document_id'):
        _require(result[field] is None or bool(result[field].strip()), 'proteome_parameters_invalid', '/' + field)
    for group, rows in (('native_documents', native), ('directional_documents', directional)):
        for i, row in enumerate(rows):
            for field in ('document_id', 'source_ref', 'raw_artifact_ref', 'requirement_id', 'report_key'):
                _require(field not in row or bool(row[field].strip()), 'proteome_parameters_invalid', f'/{group}/{i}/{field}')
            _checked(validate_contract, 'DeclaredFormat', row['declared_format'], code='proteome_parameters_invalid', path=f'/{group}/{i}/declared_format')
    _require(bool(native) == (result['primary_document_id'] is not None) == (result['calculation_parameters'] is not None), 'proteome_parameters_invalid', '/primary_document_id')
    if native:
        _require(result['primary_document_id'] in [x['document_id'] for x in native], 'proteome_parameters_invalid', '/primary_document_id')
        _checked(validate_proteome_sheet_data, 'NativeCalculationParameters', result['calculation_parameters'], code='proteome_parameters_invalid', path='/calculation_parameters')
    _require(bool(directional) == (result['directional_calculation_parameters'] is not None), 'proteome_parameters_invalid', '/directional_calculation_parameters')
    if directional:
        keys = [x['report_key'] for x in directional]
        _require(len(keys) == len(set(keys)), 'proteome_parameters_invalid', '/directional_documents')
        _checked(validate_directional_numerical, 'DirectionalCalculationParameters', result['directional_calculation_parameters'], code='proteome_parameters_invalid', path='/directional_calculation_parameters')
    if result['supplied_data_evidence'] is not None:
        _checked(validate_contract, 'SourceEvidence', result['supplied_data_evidence'], code='proteome_parameters_invalid', path='/supplied_data_evidence')
    return result

def validate_form_parameters(form, parameters):
    from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_fact_contracts import validate_requested_form
    form = _checked(validate_requested_form, form, code='proteome_requested_form_invalid', path='/requested_form')
    ids = {x['document_id'] for x in parameters['directional_documents']}
    for field, spec in form['properties'].items():
        selection = spec['x-bvbrc-proteome']
        if selection['kind'].startswith('directional_') and 'document_id' in selection:
            _require(selection['document_id'] in ids, 'proteome_requested_form_invalid', '/requested_form/properties/' + field)
    return form

def validate_result_selector(value):
    result = _checked(validate_contract, 'ResultSelector', value, code='proteome_parameters_invalid')
    selected = result['adapter']
    _require(selected is not None and (selected['adapter_id'], selected['adapter_version']) == ('bvbrc_proteome', '1'), 'proteome_parameters_invalid', '/adapter')
    params = validate_parameters(selected['parameters'])
    validate_form_parameters(result['requested_schema'], params)
    requirements = result['requirements']
    ids = [x['requirement_id'] for x in requirements]
    _require(len(ids) == len(set(ids)), 'proteome_parameters_invalid', '/requirements')
    for group in ('native_documents', 'directional_documents'):
        for i, doc in enumerate(params[group]):
            if 'requirement_id' not in doc:
                continue
            matches = [x for x in requirements if x['requirement_id'] == doc['requirement_id']]
            _require(len(matches) == 1 and matches[0]['role'] == doc['role'] and (matches[0]['declared_format'] == doc['declared_format']), 'proteome_parameters_invalid', f'/adapter/parameters/{group}/{i}')
    return result

def declaration_conflict(result, selection):
    version = selection['declared_format']['version']
    return version is not None and any((b['program']['value'] == 'BLASTP' and b['release']['state'] == 'present' and (b['release']['value'] != version) for b in result['banners']))

def validate_provider_sheet(value):
    """Validate the envelope, native relationships and observed copies."""
    saved = validate_shape('ProviderSheet', value)
    parameters = validate_parameters(saved['parameters'])
    _require(saved['analysis_id'] == parameters['analysis_id'], path='/analysis_id')
    task = _checked(validate_contract, 'OriginalTask', saved['original_task'], path='/original_task')
    _require(task['required_application_id'] == task['native_application_id'] == 'GenomeComparison', path='/original_task')
    validate_form_parameters(saved['requested_form'], parameters)
    for i, row in enumerate(saved['supplied_values']):
        _checked(validate_contract, 'SourceEvidence', row['evidence'], path=f'/supplied_values/{i}/evidence')
    for kind, (name, contract) in native_layer._RESULTS.items():
        results = ([saved[name]] if saved[name] is not None else []) if kind == 'original_input_index' else saved[name]
        for i, result in enumerate(results):
            _checked(native_layer._validate_result, contract, result, f'/{name}/{i}')
    for name, contract in (('joins_result', 'NativeJoinsResult'), ('native_sheet_result', 'NativeSheetResult')):
        if saved[name] is not None:
            _checked(validate_proteome_sheet_data, contract, saved[name], path='/' + name)
    ids = [x['requirement_id'] for x in saved['requirements']]
    _require(len(ids) == len(set(ids)), path='/requirements')
    for name, contract in (('requirements', 'AcquisitionRequirement'), ('diagnostics', 'Diagnostic')):
        for i, row in enumerate(saved[name]):
            _checked(validate_contract, contract, row, path=f'/{name}/{i}')
            code = row['reason_code' if name == 'requirements' else 'code']
            _require(code in BINDING_CODES or code in native_layer._PURE_CODES, path=f'/{name}/{i}')
            if code in BINDING_DETAILS:
                kind, role, phase = BINDING_DETAILS[code]
                _require(row['kind'] == kind and row['role'] == role if name == 'requirements' else row['phase'] == phase, path=f'/{name}/{i}')
    supplied = native_layer._selected_data(saved)
    view = {**saved, 'input_resolution': [r for r in saved['input_resolution'] if r['selector_kind'] != 'directional_document']}
    _checked(native_layer._validate_resolution, view, supplied)
    _checked(native_layer._index_task, saved)
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
        expected = 'incompatible' if declaration_conflict(result, choice) else {'ok': 'resolved', 'partial': 'partial', 'failure': 'invalid'}[result['parse_state']]
        _require(row['state'] == expected and row['content'] == result['source']['content'] and (result['report_key'] == choice['report_key']) and (result['declared_format'] == choice['declared_format']['format']), path=path)
        if 'source_ref' in choice:
            _require((choice['source_ref'], choice['raw_artifact_ref']) == (row['content']['source_ref'], row['content']['artifact_ref']), path=path)
    _require(accounted == list(range(len(saved['directional_results']))), path='/directional_results')
    observed = saved['directional_sheet_result']
    _require(bool(parameters['directional_documents']) == (observed is not None), path='/directional_sheet_result')
    if observed is not None:
        _checked(validate_directional_numerical, 'DirectionalSheetResult', observed, path='/directional_sheet_result')
        if observed['sheet'] is not None:
            _require(observed['sheet']['reader_results'] == saved['directional_results'], path='/directional_sheet_result/sheet/reader_results')
    _native_copies(saved, supplied)
    native_sheet = None if saved['native_sheet_result'] is None else saved['native_sheet_result']['value']
    directional_sheet = None if observed is None else observed['sheet']
    numerical = saved['numerical_sheet']
    _require((numerical is None) == (native_sheet is None and directional_sheet is None), path='/numerical_sheet')
    if numerical is not None:
        _require(canonical(numerical['native_sheet']) == canonical(native_sheet) and numerical['directional_sheet'] == directional_sheet, path='/numerical_sheet')
    return saved

def _native_copies(saved, supplied):
    native = saved['native_sheet_result']
    if native is not None and native['value'] is not None:
        value = native['value']
        selected = [r for r in saved['input_resolution'] if r['selector_kind'] == 'native_document' and saved['parameters']['native_documents'][r['selection_index']]['document_id'] == saved['parameters']['primary_document_id']]
        _require(len(selected) == 1 and selected[0]['content'] is not None and (selected[0]['result_index'] is not None) and (value['primary_source_ref'] == selected[0]['content']['source_ref']), path='/native_sheet_result/value/primary_source_ref')
        _require(canonical(value['native_results']) == canonical(saved['native_results']), path='/native_sheet_result/value/native_results')
        for envelope, field in (('input_index_result', 'input_index'), ('joins_result', 'joins')):
            expected = saved[envelope]['value'] if saved[envelope] is not None else None
            _require(canonical(value[field]) == canonical(expected), path='/native_sheet_result/value/' + field)
        for envelope, field in (('inventory_results', 'inventories'), ('feature_results', 'feature_snapshots'), ('genome_results', 'genome_snapshots'), ('sequence_results', 'sequence_snapshots')):
            _require(canonical(value[field]) == canonical([x['value'] for x in saved[envelope] if x['value'] is not None]), path='/native_sheet_result/value/' + field)
        _require(canonical([x['link'] for x in value['representation_comparisons']]) == canonical(supplied['representation_links'] if supplied else []) and value['directional_attachment'] is None, path='/native_sheet_result/value/representation_comparisons')
    joins = saved['joins_result']
    if joins is not None and joins['value'] is not None:
        for source, target in (('execution_links', 'execution_links'), ('native_links', 'requested_native_links'), ('metadata_links', 'requested_metadata_links')):
            _require(canonical(joins['value'][target]) == canonical(supplied[source] if supplied else []), path='/joins_result/value/' + target)

def validate_saved_provider(sheet, components, *, parameters, requested_form, original_task, bundle_sha256, bundle):
    from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_saved_validation import validate_saved_provider as validate
    return validate(sheet, components, parameters=parameters, requested_form=requested_form, original_task=original_task, bundle_sha256=bundle_sha256, bundle=bundle)
__all__ = ['parameters_schema', 'validate_parameters', 'validate_result_selector', 'validate_provider_sheet', 'validate_saved_provider', 'bundle_schema', 'DIRECTIONAL_BINDING_CODES', 'DIRECTIONAL_BINDING_DETAILS', 'DIRECTIONAL_BINDING_INPUT_KINDS', 'ProteomeBundleError']
