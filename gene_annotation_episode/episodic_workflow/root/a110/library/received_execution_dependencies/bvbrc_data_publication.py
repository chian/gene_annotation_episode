from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_fields import FIELD_REGISTRY
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_readers import validate_data_sheet
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_schema import json_digest, validate
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_views import validate_data_result_selector
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
_NON_FAILURES = {'bvbrc_schema_observed_variant', 'bvbrc_input_unavailable'}
_INVALID_REASONS = {'native_value_invalid', 'unrepresentable_numeric_value', 'conflicting_metadata', 'ambiguous_join', 'sequence_type_mismatch', 'incompatible_input'}

def _same(left, right):
    return json_digest(left) == json_digest(right)

def _require(condition, code):
    if not condition:
        raise ContractError(code)

def _unique(values):
    result, seen = ([], set())
    for value in values:
        key = json_digest(value)
        if key not in seen:
            result.append(deepcopy(value))
            seen.add(key)
    return result

def _issue(code, *, row=None, field=None, path=None, phase='projection'):
    return {'code': code, 'phase': phase, 'row_index': row, 'field': field, 'native_path': path, 'http_status': None}

def _publication_inputs(request, selector, value):
    _require(value is not None, 'bvbrc_publication_inputs_required')
    inputs = validate('PublicationInputs', value)
    prepared = inputs['prepared']
    _require(_same(prepared['original_request'], request), 'bvbrc_publication_request_mismatch')
    _require(_same(prepared['page_selector'], selector['page']), 'bvbrc_publication_page_mismatch')
    selected = [{'collection': item['binding']['collection'], 'source_ref': item['binding']['source_ref']} for item in inputs['input_results']]
    _require(_same(selected, selector['inputs']), 'bvbrc_publication_input_selection_mismatch')
    _require(_same(inputs['supplied_metadata'], selector['supplied_metadata']), 'bvbrc_publication_metadata_selection_mismatch')
    for item in inputs['input_results']:
        binding, sheet = (item['binding'], validate_data_sheet(item['sheet']))
        _require(binding['collection'] == sheet['collection'] and binding['native_sha256'] == sheet['custody']['native_sha256'], 'bvbrc_publication_input_binding_mismatch')
        _require(sheet['mode'] == 'page' and sheet['qualification']['service_matches'] and sheet['qualification']['request_matches'] and (sheet['custody']['native_profile'] == 'solr_json_envelope_v1'), 'bvbrc_publication_input_incompatible')
    expected = _unique([{'source_ref': item['provenance']['source_ref'], 'record_path': item['provenance']['record_path'], 'metadata_sha256': json_digest({key: child for key, child in item.items() if key != 'provenance'})} for item in inputs['supplied_metadata']])
    actual = [{key: item[key] for key in ('source_ref', 'record_path', 'metadata_sha256')} for item in inputs['metadata_bindings']]
    _require(_same(expected, actual), 'bvbrc_publication_metadata_binding_mismatch')
    return inputs

def _row_failures(row, fields):
    """Invalid selected values are failures; native absence remains an answer."""
    result = [issue for issue in row['issues'] if issue['code'] not in _NON_FAILURES and (issue['field'] is None or issue['field'] in fields)]
    for cell in row['cells'] + row['numerical_cells']:
        if cell['field'] in fields and (cell['status'] in {'invalid', 'unrepresentable'} or cell.get('reason') in _INVALID_REASONS):
            codes = [code for code in cell['issue_codes'] if code not in _NON_FAILURES]
            result.extend((_issue(code, row=row['row_index'], field=cell['field'], path=cell['native_path']) for code in codes or ['bvbrc_invalid_native_field']))
    return result

def requested_projection_failures(grading: dict, *, input_results: list[dict]) -> list[dict]:
    """Qualify the selected output from saved data, without host admission.

    An accurate missing/unselected/zero value is a valid typed result. Invalid
    unrelated fields do not reject a narrower projection. Incomplete transport,
    wrong selected response and malformed requested values remain partial.
    This is an operational endpoint assessment, never scientific acceptance.
    """
    grading = validate('PublishedGrading', grading)
    selector = validate_data_result_selector(grading['selector'], request=grading['prepared']['original_request'])
    inputs = _publication_inputs(grading['prepared']['original_request'], selector, {'version': 'bvbrc_data_publication_inputs_v1', 'prepared': grading['prepared'], 'input_results': input_results, 'supplied_metadata': selector['supplied_metadata'], 'metadata_bindings': grading['metadata_bindings']})
    _require(_same(grading['input_bindings'], [item['binding'] for item in inputs['input_results']]), 'bvbrc_publication_input_binding_mismatch')
    parsed = grading['parse_result']
    current = parsed['sheet']
    _require(current is not None or (parsed['status'] == 'failed' and bool(parsed['failures'])), 'bvbrc_publication_parse_failure_required')
    pages = ([] if current is None else [validate_data_sheet(current)]) + [item['sheet'] for item in inputs['input_results']]
    failures = list(parsed['failures']) if current is None else []
    for page in pages:
        failures.extend((issue for issue in page['issues'] if issue['row_index'] is None and issue['code'] not in _NON_FAILURES))
        if not page['transport']['body_complete'] and (not any((issue['code'] == 'bvbrc_response_body_incomplete' for issue in page['issues']))):
            failures.append(_issue('bvbrc_response_body_incomplete', phase='transport'))
    projection = selector['projection']
    family = projection['family']
    if family == 'collection_rows' and current is not None:
        fields = set(projection['numeric_fields'] + projection['metadata_fields'])
        fields.add(FIELD_REGISTRY[current['collection']]['unique_key'])
        for row in current['rows']:
            if row['row_index'] in projection['row_indices']:
                failures.extend(_row_failures(row, fields))
    elif family == 'feature_sequence':
        joined = grading['feature_sequence_sheet']
        _require(joined is not None, 'bvbrc_feature_sequence_sheet_required')
        for edge in joined['edges']:
            fields = set(projection['feature_metadata_fields'])
            fields.update({'feature_id', 'md5', 'sequence', 'sequence_type', edge['sequence_kind'].lower() + '_sequence_md5', edge['sequence_kind'].lower() + '_length'})
            failures.extend((issue for issue in edge['issues'] if issue['code'] not in _NON_FAILURES and (issue['field'] is None or issue['field'] in fields)))
            if edge['join_status'] in {'conflict', 'type_mismatch'}:
                failures.append(_issue('bvbrc_join_conflict', phase='join'))
            for page in pages:
                selected = {location['row_key'] for location in edge['feature_rows'] + edge['sequence_rows'] if location['collection'] == page['collection'] and location['native_sha256'] == page['custody']['native_sha256']}
                for row in page['rows']:
                    if row['row_key'] in selected:
                        failures.extend(_row_failures(row, fields))
    elif family == 'molecular_experiment':
        molecular = grading['molecular_sheet']
        _require(molecular is not None, 'bvbrc_molecular_sheet_required')
        selected_metadata = {(item['source_level'], item['field']) for item in projection['metadata_fields']}
        for row in molecular['rows']:
            identity_fields = {'id', 'exp_id', 'bioset_id', 'feature_id', 'entity_id'}
            fields = identity_fields | set(projection['measurement_fields']) | {field for level, field in selected_metadata if level == 'result'}
            failures.extend((issue for issue in row['issues'] if issue['code'] not in _NON_FAILURES and (issue['field'] is None or issue['field'] in fields)))
            if row['relationship_status'] == 'conflict':
                failures.append(_issue('bvbrc_join_conflict', phase='join'))
            for cell in row['measurements']:
                if cell['field'] in projection['measurement_fields'] and (cell['status'] == 'invalid' or cell['reason'] in _INVALID_REASONS or 'bvbrc_join_conflict' in cell['issue_codes']):
                    failures.append(_issue('bvbrc_join_conflict' if 'bvbrc_join_conflict' in cell['issue_codes'] else 'bvbrc_invalid_native_field', field=cell['field'], path=cell['native_path']))
            for metadata in row['metadata']:
                if (metadata['source_level'], metadata['field']) in selected_metadata and (metadata['status'] == 'conflict' or metadata['reason'] in _INVALID_REASONS):
                    native_field = metadata['field'] if metadata['source_level'] != 'supplied' else None
                    failures.append(_issue('bvbrc_join_conflict' if metadata['status'] == 'conflict' else 'bvbrc_invalid_native_field', field=native_field, phase='join'))
    return [validate('Issue', issue) for issue in _unique(failures)]
