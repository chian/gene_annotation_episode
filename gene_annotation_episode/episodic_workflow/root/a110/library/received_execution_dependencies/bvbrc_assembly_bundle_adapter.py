from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_bundle_adapter import _record, _missing_members, _member_selection
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_native import _canonical, _finite_json, _issue
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_assembly_contracts import APPLICATIONS, VALUE_VERSION, validate_parameters, validate_requested_form, validate_facts
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_assembly_native import COMPONENTS_VERSION as NATIVE_COMPONENTS_VERSION, validate_assembly_document
ADAPTER_ID = 'bvbrc_assembly'
ADAPTER_VERSION = '1'
SHEET_VERSION = 'bvbrc_assembly_observations_v1'
COMPONENTS_VERSION = 'bvbrc_assembly_retained_components_v1'
_COMPONENT_FIELDS = {'version', 'document_sha256', 'representation', 'status', 'population', 'records', 'retained_symbol_total', 'total_length_nt', 'n50_nt', 'l50', 'n50_crossing_record_ordinal', 'n_count', 'n_block_count', 'native_reported_fields', 'definitions', 'issues'}

def _require(condition, code='bvbrc_assembly_bundle_invalid'):
    if not condition:
        raise ValueError(code)

def _saved(sheet, components, parameters):
    """Check saved associations without native parsing or numerical work."""
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {'version', 'analysis_id', 'original_task', 'documents'} and (sheet['version'] == SHEET_VERSION) and (sheet['analysis_id'] == parameters['analysis_id']))
    task = validate_contract('OriginalTask', sheet['original_task'])
    _require(task['required_application_id'] == task['native_application_id'] == parameters['application_id'] and parameters['application_id'] in APPLICATIONS)
    _require(type(sheet['documents']) is list and len(sheet['documents']) == len(parameters['documents']))
    for row, specification in zip(sheet['documents'], parameters['documents'], strict=True):
        _require(type(row) is dict and set(row) == {'document_id', 'specification', 'state', 'candidate_contents', 'document'} and (row['document_id'] == specification['document_id']) and (_canonical(row['specification']) == _canonical(specification)) and (type(row['state']) is str) and (row['state'] in {'available', 'missing', 'ambiguous', 'incompatible'}) and (type(row['candidate_contents']) is list))
        if row['state'] == 'available':
            document = validate_assembly_document(row['document'])
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
        _require(type(value) is dict and set(value) == _COMPONENT_FIELDS and (value['version'] == NATIVE_COMPONENTS_VERSION) and (value['representation'] == document['representation']) and (type(value['status']) is str) and (value['status'] in {'complete', 'partial'}) and (value['document_sha256'] == hashlib.sha256(_canonical(document)).hexdigest()) and (type(value['definitions']) is dict) and (type(value['issues']) is list) and (type(value['native_reported_fields']) is list) and (_canonical(value['issues']) == _canonical(document['issues'])), 'bvbrc_assembly_saved_document_conflict')
        for name in ('retained_symbol_total', 'total_length_nt', 'n50_nt', 'l50', 'n50_crossing_record_ordinal', 'n_count', 'n_block_count'):
            _require(value[name] is None or (type(value[name]) is int and value[name] >= 0))
        records = document['native_document']['rows'] if document['representation'] == 'assembly_fasta' and document['native_document'] is not None else None
        _require((value['records'] is None) == (records is None))
        _require(type(value['population']) is dict and set(value['population']) == {'scope', 'complete_artifact_population', 'observed_record_count', 'intended_genome_completeness'} and (value['population']['scope'] == 'one_selected_retained_artifact') and (value['population']['intended_genome_completeness'] is None) and (type(value['population']['complete_artifact_population']) in ({bool} if records is not None else {type(None)})) and (type(value['population']['observed_record_count']) is (type(None) if records is None else int)) and (value['population']['observed_record_count'] == (None if records is None else len(records))))
        if records is not None:
            _require(type(value['records']) is list and len(value['records']) == len(records))
            for measured, native in zip(value['records'], records, strict=True):
                _require(type(measured) is dict and set(measured) == {'record_ordinal', 'member_label', 'composition', 'n_run_intervals_0based', 'n_run_count'} and (type(measured['record_ordinal']) is int) and (measured['record_ordinal'] == native['row_index']) and (measured['member_label'] == native['member_label']) and (type(measured['composition']) is dict) and (set(measured['composition']) == {'sheet', 'components'}) and (type(measured['composition']['sheet']) is dict) and (measured['composition']['sheet'].get('sequence') == native['sequence']))
    return (sheet, components)

def _select_members(value, names, pointer, *, native=False):
    if names is None:
        return (deepcopy(value), [])
    if native:
        return (_member_selection(value, names), _missing_members(value, names, pointer))
    if type(value) is not dict:
        return (None, [])
    return ({name: deepcopy(value[name]) for name in names if name in value}, [_issue('selected_component_member_missing', pointer + '/' + name.replace('~', '~0').replace('/', '~1')) for name in names if name not in value])

def project_assembly_facts(sheet, components, *, parameters, requested_form):
    parameters, form = (validate_parameters(parameters), validate_requested_form(requested_form))
    sheet, components = _saved(sheet, components, parameters)
    documents = {row['document_id']: row for row in sheet['documents']}
    measured = {row['document_id']: row['components'] for row in components['documents']}
    facts = {}
    for name in form['required']:
        selection = form['properties'][name]['x-bvbrc-assembly-selection']
        _require(selection['document_id'] in documents, 'bvbrc_assembly_selected_document_missing')
        resolution = documents[selection['document_id']]
        document, result = (resolution['document'], measured[selection['document_id']])
        kind, records, total, requested, matched = (selection['kind'], [], None, None, None)
        issues = deepcopy(document['issues'] if document is not None else [_issue('assembly_document_' + resolution['state'], '/documents/' + resolution['document_id'])])
        source = None if document is None else document['native_document']
        if kind == 'records' and source is not None and (document['representation'] == 'assembly_fasta'):
            total = len(source['rows'])
            ordinals = selection['ordinals'] if selection['ordinals'] is not None else list(range(total))
            requested, matched = (len(ordinals), 0)
            for ordinal in ordinals:
                pointer = '/native_document/rows/' + str(ordinal)
                if ordinal >= total:
                    records.append(_record(None, ordinal, pointer, state='path_missing'))
                else:
                    value, notes = _select_members(source['rows'][ordinal], selection['member_names'], pointer)
                    issues.extend(notes)
                    matched += 1
                    records.append(_record(value, ordinal, pointer))
        elif kind != 'records' and document is not None and (source is not None or kind == 'components'):
            total = requested = matched = 1
            value = result if kind == 'components' else source
            pointer = '/components' if kind == 'components' else '/native_document'
            value, notes = _select_members(value, selection['member_names'], pointer, native=kind == 'native_document' and document['representation'] != 'assembly_fasta')
            issues.extend(notes)
            records = [_record(value, None, pointer, state='incompatible' if value is None else None)]
        else:
            ordinals = selection['ordinals'] if selection['ordinals'] is not None else [None]
            state = 'incompatible' if kind == 'records' and source is not None else 'source_unavailable'
            records = [_record(None, ordinal, None, state=state) for ordinal in ordinals]
            requested = len(selection['ordinals']) if selection['ordinals'] is not None else None
        records = records[selection['offset']:selection['offset'] + selection['limit']]
        context = dict(analysis_id=parameters['analysis_id'], original_task=deepcopy(sheet['original_task']), document_id=resolution['document_id'], resolution=resolution['state'], representation=resolution['specification']['representation'], content=None if document is None else deepcopy(document['content']), capture_complete=None if document is None else document['capture_complete'], definitions=None if result is None else deepcopy(result['definitions']))
        facts[name] = dict(version=VALUE_VERSION, selection=deepcopy(selection), records=records, record_accounting=dict(retained_total=total, requested_occurrences=requested, matched_occurrences=matched, returned_occurrences=len(records), population_scope='retained_native_records_only', intended_population_complete=None), context=context, issues=issues)
    return validate_facts(facts, requested_form=form)

def validate_saved_assembly_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_assembly_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), 'bvbrc_assembly_saved_facts_conflict')
    return deepcopy(expected)

def assembly_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    qualified = bool(missing_requirements) or any((row['severity'] == 'error' or row['code'] == 'native_capture_incomplete' for row in diagnostics))
    qualified |= any((record['state'] not in {'available', 'stored_null'} for fact in facts.values() for record in fact['records']))
    qualified |= any((issue['code'] in {'native_selected_member_missing', 'selected_component_member_missing'} for fact in facts.values() for issue in fact['issues']))
    return 'partial' if qualified or bundle_status != 'ok' else 'ok'
