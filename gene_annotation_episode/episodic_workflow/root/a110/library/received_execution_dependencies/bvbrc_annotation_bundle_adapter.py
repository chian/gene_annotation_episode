from __future__ import annotations
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_contracts import APPLICATIONS, validate_parameters, validate_requested_form, validate_facts, VALUE_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_native import COMPONENTS_VERSION as NATIVE_COMPONENTS_VERSION, _canonical, _finite_json, _field, _issue, validate_annotation_document
ADAPTER_ID = 'bvbrc_annotation'
ADAPTER_VERSION = '1'
SHEET_VERSION = 'bvbrc_annotation_observations_v1'
COMPONENTS_VERSION = 'bvbrc_annotation_retained_components_v1'

def _require(condition, code='bvbrc_annotation_bundle_invalid'):
    if not condition:
        raise ValueError(code)

def _saved(sheet, components, parameters):
    """Authenticate structure/association only; the host authenticates content."""
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {'version', 'analysis_id', 'original_task', 'documents'} and (sheet['version'] == SHEET_VERSION) and (sheet['analysis_id'] == parameters['analysis_id']))
    task = validate_contract('OriginalTask', sheet['original_task'])
    _require(task['required_application_id'] == task['native_application_id'] == parameters['application_id'] and parameters['application_id'] in APPLICATIONS)
    _require(type(sheet['documents']) is list and len(sheet['documents']) == len(parameters['documents']))
    for row, specification in zip(sheet['documents'], parameters['documents'], strict=True):
        _require(type(row) is dict and set(row) == {'document_id', 'specification', 'state', 'candidate_contents', 'document'} and (row['document_id'] == specification['document_id']) and (_canonical(row['specification']) == _canonical(specification)) and (type(row['state']) is str) and (row['state'] in {'available', 'missing', 'ambiguous', 'incompatible'}) and (type(row['candidate_contents']) is list))
        if row['state'] == 'available':
            document = validate_annotation_document(row['document'])
            _require(document['expected_task_id'] == task['task_id'] and document['representation'] == specification['representation'] and (_canonical(row['candidate_contents']) == _canonical([document['content']])))
        else:
            _require(row['document'] is None)
        for content in row['candidate_contents']:
            validate_contract('ContentBinding', content)
        _require(row['state'] != 'ambiguous' or len(row['candidate_contents']) > 1)
        _require(row['state'] != 'incompatible' or len(row['candidate_contents']) == 1)
    _require(type(components) is dict and set(components) == {'version', 'analysis_id', 'documents'} and (components['version'] == COMPONENTS_VERSION) and (components['analysis_id'] == parameters['analysis_id']) and (type(components['documents']) is list) and (len(components['documents']) == len(sheet['documents'])))
    for result, row in zip(components['documents'], sheet['documents'], strict=True):
        _require(type(result) is dict and set(result) == {'document_id', 'components'} and (result['document_id'] == row['document_id']))
        value, document = (result['components'], row['document'])
        if document is None:
            _require(value is None)
            continue
        _require(type(value) is dict and set(value) == {'version', 'status', 'document_sha256', 'population', 'capture_complete', 'reported_contig_count', 'reported_feature_count', 'contigs', 'features', 'definitions', 'issues'} and (value['version'] == NATIVE_COMPONENTS_VERSION) and (type(value['status']) is str) and (value['status'] in {'complete', 'partial'}) and (type(value['definitions']) is dict) and (type(value['issues']) is list) and (value['capture_complete'] is document['capture_complete']) and (value['document_sha256'] == hashlib.sha256(_canonical(document)).hexdigest()), 'bvbrc_annotation_saved_document_conflict')
        for name, count in (('contigs', 'reported_contig_count'), ('features', 'reported_feature_count')):
            records = document['records'][name]['rows']
            if records is None:
                _require(value[count] is None and value[name] is None)
            else:
                _require(type(value[count]) is int and value[count] == len(records) and (type(value[name]) is list) and (len(value[name]) == len(records)))
                for calculated, record in zip(value[name], records, strict=True):
                    _require(type(calculated) is dict and type(calculated.get('ordinal')) is int and (calculated['ordinal'] == record['ordinal']) and (calculated.get('id') == record['id']))
    return (sheet, components)

def _member_selection(node, names):
    if names is None:
        return deepcopy(node)
    if node['kind'] != 'object':
        return None
    selected = set(names)
    return {'kind': 'object', 'members': [deepcopy(row) for row in node['members'] if row['name'] in selected]}

def _missing_members(node, names, path):
    if names is None or node['kind'] != 'object':
        return []
    present = {row['name'] for row in node['members']}
    return [_issue('native_selected_member_missing', path + '/' + name.replace('~', '~0').replace('/', '~1')) for name in names if name not in present]

def _record(value, ordinal, pointer, *, state=None):
    if state is None:
        state = 'stored_null' if value is None or (type(value) is dict and value.get('kind') == 'null') else 'available'
    return {'requested_ordinal': ordinal, 'source_pointer': pointer, 'state': state, 'value': deepcopy(value)}

def project_annotation_facts(sheet, components, *, parameters, requested_form):
    """Copy selected retained values; never reparse or recalculate a saved run."""
    parameters, form = (validate_parameters(parameters), validate_requested_form(requested_form))
    sheet, components = _saved(sheet, components, parameters)
    documents = {row['document_id']: row for row in sheet['documents']}
    calculated = {row['document_id']: row['components'] for row in components['documents']}
    facts = {}
    for name in form['required']:
        selection = form['properties'][name]['x-bvbrc-annotation-selection']
        _require(selection['document_id'] in documents, 'bvbrc_annotation_selected_document_missing')
        resolution = documents[selection['document_id']]
        document, result = (resolution['document'], calculated[selection['document_id']])
        kind, records, total, requested, matched = (selection['kind'], [], None, None, None)
        issues = deepcopy(document['issues'] if document is not None else [_issue('annotation_document_' + resolution['state'], '/documents/' + resolution['document_id'])])
        if document is None or (document['native_document'] is None and kind != 'components'):
            ordinals = selection['ordinals'] if selection['ordinals'] is not None else [None]
            records = [_record(None, ordinal, None, state='source_unavailable') for ordinal in ordinals]
            requested = len(selection['ordinals']) if selection['ordinals'] is not None else None
        elif kind in {'contigs', 'features', 'analysis_events'}:
            source = document['records'][kind]
            rows = source['rows']
            total = None if rows is None else len(rows)
            ordinals = selection['ordinals'] if selection['ordinals'] is not None else list(range(total)) if total is not None else [None]
            requested, matched = (len(ordinals), None if rows is None else 0)
            for ordinal in ordinals:
                if rows is None:
                    records.append(_record(None, ordinal, source['path'], state='source_unavailable'))
                elif ordinal >= len(rows):
                    records.append(_record(None, ordinal, source['path'], state='path_missing'))
                else:
                    row = rows[ordinal]
                    value = _member_selection(row['native_record'], selection['member_names'])
                    issues.extend(_missing_members(row['native_record'], selection['member_names'], row['path']))
                    matched += 1
                    records.append(_record(value, ordinal, row['path'], state='incompatible' if value is None else None))
        else:
            total, requested, matched = (1, 1, 1)
            if kind == 'components':
                value = deepcopy(result)
                if selection['member_names'] is not None:
                    issues.extend((_issue('selected_component_member_missing', '/components/' + key) for key in selection['member_names'] if key not in value))
                    value = {key: value[key] for key in selection['member_names'] if key in value}
                records = [_record(value, None, '/components')]
            else:
                node, pointer = (document['native_document'], '/native_document')
                if kind == 'quality' and document['representation'] != 'quality_json':
                    quality = _field(node, 'quality', pointer)
                    node, pointer = (quality['value'], quality['path'])
                    if quality['state'] in {'missing', 'ambiguous'}:
                        records = [_record(None, None, pointer, state='path_missing' if quality['state'] == 'missing' else 'incompatible')]
                        matched = 0
                if not records:
                    value = _member_selection(node, selection['member_names'])
                    issues.extend(_missing_members(node, selection['member_names'], pointer))
                    records = [_record(value, None, pointer, state='incompatible' if value is None else None)]
        records = records[selection['offset']:selection['offset'] + selection['limit']]
        context = {'analysis_id': parameters['analysis_id'], 'original_task': deepcopy(sheet['original_task']), 'document_id': resolution['document_id'], 'resolution': resolution['state'], 'representation': resolution['specification']['representation'], 'content': None if document is None else deepcopy(document['content']), 'capture_complete': None if document is None else document['capture_complete'], 'native_task_identity': None if document is None else deepcopy(document['identity']), 'definitions': None if result is None else deepcopy(result['definitions'])}
        facts[name] = {'version': VALUE_VERSION, 'selection': deepcopy(selection), 'records': records, 'record_accounting': {'retained_total': total, 'requested_occurrences': requested, 'matched_occurrences': matched, 'returned_occurrences': len(records), 'population_scope': 'retained_native_records_only', 'intended_population_complete': None}, 'context': context, 'issues': issues}
    return validate_facts(facts, requested_form=form)

def validate_saved_annotation_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_annotation_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), 'bvbrc_annotation_saved_facts_conflict')
    return deepcopy(expected)

def annotation_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    """Status of this selected projection, without native success inference."""
    critical = {'native_analysis_reported_failure', 'native_capture_incomplete', 'native_task_identity_conflict', 'native_task_identity_ambiguous'}
    qualified = bool(missing_requirements) or any((row['severity'] == 'error' or row['code'] in critical for row in diagnostics))
    qualified |= any((record['state'] not in {'available', 'stored_null'} for fact in facts.values() for record in fact['records']))
    qualified |= any((issue['code'] in {'native_selected_member_missing', 'selected_component_member_missing'} for fact in facts.values() for issue in fact['issues']))
    return 'partial' if qualified or bundle_status != 'ok' else 'ok'
