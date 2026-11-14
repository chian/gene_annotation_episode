from copy import deepcopy
import hashlib
from pathlib import Path
from jsonschema import Draft202012Validator
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.vcf_result_measurements as vcf
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_contracts import selected_field_schema as _literal_schema
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_native import _canonical, _content, _finite_json
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract
ADAPTER_ID = 'bvbrc_variation'
ADAPTER_VERSION = '1'
PARAMETERS_VERSION = 'bvbrc_variation_parameters_v1'
SELECTION_VERSION = 'bvbrc_variation_selection_v1'
VALUE_VERSION = 'bvbrc_variation_selected_field_v1'
DOCUMENT_VERSION = 'bvbrc_variation_native_document_v1'
SHEET_VERSION = 'bvbrc_variation_observations_v1'
COMPONENTS_VERSION = 'bvbrc_variation_retained_components_v1'
_DEPENDENCIES = ('__init__.py', 'acquisition.py', 'domain.py', 'public_configuration.py', 'bvbrc_variation_bundle_adapter.py', 'bvbrc_annotation_bundle_adapter.py', 'bvbrc_annotation_contracts.py', 'bvbrc_annotation_native.py', 'vcf_result_measurements.py', 'alignment_correspondence.py', 'sequence_composition_grader.py', 'sequence_composition_counts.py', 'ucsc_acquisition.py', 'data_acquisition_receipts.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json')

def _require(condition, code='bvbrc_variation_bundle_invalid'):
    if not condition:
        raise ValueError(code)

def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _text():
    return dict(type='string', minLength=1)

def _validate(value, schema, code):
    _finite_json(value)
    try:
        Draft202012Validator(schema).validate(value)
    except Exception as error:
        raise ValueError(code) from error
    return deepcopy(value)

def implementation_sha256():
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_variation_bundle_adapter')

def parameters_schema():
    return _object(dict(version=dict(const=PARAMETERS_VERSION), analysis_id=_text(), application_id=dict(const='Variation'), documents=dict(type='array', minItems=1, items=_object(dict(document_id=_text(), requirement_id=_text(), representation=dict(const='vcf'))))))

def validate_parameters(value):
    value = _validate(value, parameters_schema(), 'bvbrc_variation_parameters_invalid')
    _require(len({row['document_id'] for row in value['documents']}) == len(value['documents']), 'bvbrc_variation_document_identity_ambiguous')
    return value

def selection_schema():
    result = vcf.vcf_result_schema('Selection')
    definitions = result.pop('$defs')
    return {**_object(dict(version=dict(const=SELECTION_VERSION), document_id=_text(), vcf=result)), '$defs': definitions}

def validate_selection(value):
    value = _validate(value, selection_schema(), 'bvbrc_variation_selection_invalid')
    vcf.validate_vcf_selection(value['vcf'], sheet=None)
    return value

def selected_field_schema():
    definitions = _literal_schema()['$defs']
    native = vcf.vcf_result_schema('Value')
    native_definitions = native.pop('$defs')
    native_definitions.pop('Return')
    _require(not set(definitions).intersection(native_definitions))
    definitions.update(native_definitions)
    selection = selection_schema()
    selection.pop('$defs')
    result = _object(dict(version=dict(const=VALUE_VERSION), selection=selection, state=dict(enum=['available', 'source_unavailable']), value=dict(anyOf=[native, dict(type='null')]), context={'$ref': '#/$defs/AnnotationJSON32'}, issues={'$ref': '#/$defs/AnnotationJSON32'}))
    result['allOf'] = [{'if': {'properties': {'state': {'const': 'source_unavailable'}}}, 'then': {'properties': {'value': {'type': 'null'}}}}, {'if': {'properties': {'state': {'const': 'available'}}}, 'then': {'properties': {'value': native}}}]
    return {**result, '$defs': definitions}

def requested_form_schema(fields):
    _finite_json(fields)
    _require(type(fields) is list)
    names, properties = ([], {})
    definitions = selected_field_schema()['$defs']
    for field in fields:
        _require(type(field) is dict and set(field) == {'field', 'selection'} and (type(field['field']) is str) and bool(field['field']) and (field['field'] not in names))
        name, selection = (field['field'], validate_selection(field['selection']))
        schema = selected_field_schema()
        schema.pop('$defs')
        schema['properties']['selection'] = dict(const=selection)
        schema['x-bvbrc-variation-selection'] = selection
        properties[name] = schema
        names.append(name)
    return dict(type='object', properties=properties, required=names, additionalProperties=False, **{'$defs': definitions})

def validate_requested_form(value):
    _finite_json(value)
    _require(type(value) is dict and set(value) == {'type', 'properties', 'required', 'additionalProperties', '$defs'} and (type(value['properties']) is dict) and (type(value['required']) is list))
    fields = []
    for name in value['required']:
        _require(type(name) is str and name in value['properties'] and (type(value['properties'][name]) is dict))
        fields.append(dict(field=name, selection=value['properties'][name].get('x-bvbrc-variation-selection')))
    _require(_canonical(value) == _canonical(requested_form_schema(fields)), 'bvbrc_variation_requested_form_invalid')
    return deepcopy(value)

def validate_selected_field(value):
    value = _validate(value, selected_field_schema(), 'bvbrc_variation_selected_field_invalid')
    validate_selection(value['selection'])
    context = value['context']
    _require(type(context) is dict and set(context) == {'analysis_id', 'original_task', 'document_id', 'resolution', 'representation', 'content', 'vcf_sheet_sha256'} and (type(context['analysis_id']) is str) and bool(context['analysis_id']) and (context['document_id'] == value['selection']['document_id']) and (context['representation'] == 'vcf') and (type(context['resolution']) is str) and (context['resolution'] in {'available', 'missing', 'ambiguous', 'incompatible'}))
    validate_contract('OriginalTask', context['original_task'])
    if value['state'] == 'available':
        content = _content(context['content'])
        _require(context['resolution'] == 'available')
        vcf.validate_vcf_components(dict(version=vcf.COMPONENTS_VERSION, sheet_sha256=context['vcf_sheet_sha256'], value=value['value']))
        _require(_canonical(value['value']['selection']) == _canonical(value['selection']['vcf']) and value['value']['input']['source_ref'] == value['value']['input']['input_id'] == content['source_ref'] and (value['value']['input']['retained_file'] == dict(artifact_ref=content['artifact_ref'], sha256=content['sha256'], size_bytes=content['byte_count'], format='vcf')))
    else:
        _require(context['resolution'] != 'available' and context['content'] is None and (context['vcf_sheet_sha256'] is None))
    return value

def _saved(sheet, components, parameters, form):
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {'version', 'analysis_id', 'original_task', 'documents'} and (sheet['version'] == SHEET_VERSION) and (sheet['analysis_id'] == parameters['analysis_id']))
    task = validate_contract('OriginalTask', sheet['original_task'])
    _require(task['required_application_id'] == task['native_application_id'] == parameters['application_id'])
    _require(type(sheet['documents']) is list and len(sheet['documents']) == len(parameters['documents']))
    for row, spec in zip(sheet['documents'], parameters['documents'], strict=True):
        _require(type(row) is dict and set(row) == {'document_id', 'specification', 'state', 'candidate_contents', 'document'} and (row['document_id'] == spec['document_id']) and (_canonical(row['specification']) == _canonical(spec)) and (type(row['state']) is str) and (row['state'] in {'available', 'missing', 'ambiguous', 'incompatible'}) and (type(row['candidate_contents']) is list))
        for content in row['candidate_contents']:
            validate_contract('ContentBinding', content)
        _require(row['state'] != 'ambiguous' or len(row['candidate_contents']) > 1)
        _require(row['state'] != 'incompatible' or len(row['candidate_contents']) == 1)
        document = row['document']
        if row['state'] != 'available':
            _require(document is None)
            continue
        _require(type(document) is dict and set(document) == {'version', 'representation', 'content', 'expected_task_id', 'capture_complete', 'vcf_sheet', 'issues'} and (document['version'] == DOCUMENT_VERSION) and (document['representation'] == spec['representation']) and (document['expected_task_id'] == task['task_id']) and (type(document['capture_complete']) is bool) and (_canonical(row['candidate_contents']) == _canonical([document['content']])))
        content = _content(document['content'])
        native = vcf.validate_vcf_sheet(document['vcf_sheet'])
        _require(native['input']['source_ref'] == native['input']['input_id'] == content['source_ref'] and native['input']['retained_file'] == dict(artifact_ref=content['artifact_ref'], sha256=content['sha256'], size_bytes=content['byte_count'], format='vcf') and ((native['input']['capture']['state'] == 'complete') is document['capture_complete']) and (_canonical(document['issues']) == _canonical(vcf._gather_issues(native))))
    _require(type(components) is dict and set(components) == {'version', 'analysis_id', 'fields'} and (components['version'] == COMPONENTS_VERSION) and (components['analysis_id'] == parameters['analysis_id']) and (type(components['fields']) is list) and (len(components['fields']) == len(form['required'])))
    documents = {row['document_id']: row for row in sheet['documents']}
    for saved, name in zip(components['fields'], form['required'], strict=True):
        selection = form['properties'][name]['x-bvbrc-variation-selection']
        _require(type(saved) is dict and set(saved) == {'field', 'selection', 'components'} and (saved['field'] == name) and (_canonical(saved['selection']) == _canonical(selection)) and (selection['document_id'] in documents))
        document, value = (documents[selection['document_id']]['document'], saved['components'])
        _require((document is None) == (value is None))
        if value is not None:
            value = vcf.validate_vcf_components(value)
            _require(value['sheet_sha256'] == vcf._hash(document['vcf_sheet']) and _canonical(value['value']['selection']) == _canonical(selection['vcf']) and (_canonical(value['value']['input']) == _canonical(document['vcf_sheet']['input'])))
    return (sheet, components)

def project_variation_facts(sheet, components, *, parameters, requested_form):
    parameters, form = (validate_parameters(parameters), validate_requested_form(requested_form))
    sheet, components = _saved(sheet, components, parameters, form)
    documents = {row['document_id']: row for row in sheet['documents']}
    facts = {}
    for result in components['fields']:
        selection, measured = (result['selection'], result['components'])
        resolution = documents[selection['document_id']]
        document = resolution['document']
        value = dict(version=VALUE_VERSION, selection=deepcopy(selection), state='source_unavailable' if document is None else 'available', value=None if measured is None else deepcopy(measured['value']), context=dict(analysis_id=parameters['analysis_id'], original_task=deepcopy(sheet['original_task']), document_id=selection['document_id'], resolution=resolution['state'], representation='vcf', content=None if document is None else deepcopy(document['content']), vcf_sheet_sha256=None if measured is None else measured['sheet_sha256']), issues=[] if document is None else deepcopy(document['issues']))
        facts[result['field']] = validate_selected_field(value)
    return _validate(facts, form, 'bvbrc_variation_facts_invalid')

def validate_saved_variation_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_variation_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), 'bvbrc_variation_saved_facts_conflict')
    return deepcopy(expected)

def variation_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    qualified = bool(missing_requirements) or bundle_status != 'ok'
    qualified |= any((row['severity'] == 'error' for row in diagnostics))
    qualified |= any((fact['state'] != 'available' or not fact['value']['population']['record_population_complete'] for fact in facts.values()))
    return 'partial' if qualified else 'ok'
