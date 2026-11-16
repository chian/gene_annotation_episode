from __future__ import annotations
from copy import deepcopy
import re
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.infernal_search_contracts import SHEET_SCHEMA, validate_infernal_search_sheet, validate_infernal_search_scores
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_contracts import RFAM_ALIGNMENT_COUNT_FIELDS, RFAM_METRIC_UNITS, RFAM_MISSING_REASONS, closed_object, finite_json_copy, is_int, is_number, is_text, query_strand_record_key, rfam_digest, validate_rfam_projection, validate_rfam_table_projection, validate_rfam_input_identity, validate_rfam_capture, validate_rfam_alignment_result
PARSE_VERSION = 'rfam_batch_parse_result_v2'
PROFILES = {'json': 'rfam_single_json', 'tblout': 'rfam_batch_tblout', 'out': 'rfam_batch_report'}
HIT_ALIASES = {'native_score_bits': 'bitscore', 'native_evalue': 'evalue', 'native_gc_fraction': 'gc_fraction', 'native_start_1i': 'sequence_from', 'native_end_1i': 'sequence_to', 'query_length_nt': 'sequence_length', 'query_span_nt': 'sequence_span_length', 'query_span_fraction': 'sequence_span_fraction', 'model_length_positions': 'consensus_length', 'model_coverage_fraction': 'represented_model_fraction', 'native_bias_bits': 'bias_bits', 'native_model_from_1i': 'model_from', 'native_model_to_1i': 'model_to', 'native_model_span_positions': 'model_span_length', 'native_model_span_fraction': 'model_span_fraction', **{name: name for name in ('display_model_from', 'display_model_to', 'represented_model_positions', 'represented_query_positions', 'model_consensus_equal_fraction', 'native_rank', 'native_alignment_accuracy', *RFAM_ALIGNMENT_COUNT_FIELDS)}}
POPULATION_ALIASES = {'query_length_nt': 'union_denominator', 'selected_row_count': 'hit_count', 'valid_interval_row_count': 'valid_geometry_count', 'query_strand_sum_span_nt': 'span_sum', 'query_strand_union_span_nt': 'union_numerator', 'query_strand_union_fraction': 'union_span_fraction', 'query_strand_overlap_excess_nt': 'overlap_excess'}
_REPORT_FIELDS = {'rank': 'native_rank', 'inclusion': 'inclusion', 'evalue': 'evalue', 'score': 'bitscore', 'bias': 'bias_bits', 'model_type': 'algorithm', 'model_from': 'model_from', 'model_to': 'model_to', 'query_from': 'sequence_from', 'query_to': 'sequence_to', 'accuracy': 'native_alignment_accuracy', 'model_boundary': 'native_model_boundary', 'query_boundary': 'native_sequence_boundary', 'truncation': 'truncation', 'gc': 'gc_fraction'}

def _matched_report_member(query, membership, row_identities):
    members = [r for r in membership['queries'] if r['native_query_name'] == query['native_query_name']]
    if len(members) != 1 or members[0]['length_nt'] != query['submitted_length_nt'] or any((name == query['native_query_name'] and key != query['query_occurrence_key'] for name, key in row_identities)):
        return None
    return members[0]

def select_rfam_common_sheet(value, *, representation):
    """Select a populated common sheet."""
    if type(value) is dict and value.get('version') == PARSE_VERSION:
        closed_object(value, ('version', 'representation', 'status', 'format', 'sheet', 'issues'), code='rfam_sheet_invalid')
        if value['representation'] != representation or value['status'] not in {'complete', 'partial'}:
            raise ContractError('rfam_sheet_invalid')
        value = value['sheet']
    try:
        if type(value) is dict and value.get('schema') == SHEET_SCHEMA and (type(value.get('hits')) is list):
            for hit in value['hits']:
                if type(hit) is not dict:
                    continue
                lengths, details = (hit.get('lengths'), hit.get('source_details'))
                model = lengths.get('model') if type(lengths) is dict else None
                if type(model) is dict and model.get('value') is not None or (type(details) is dict and details.get('model_metadata_ref') is not None):
                    raise ContractError('rfam_model_binding_unverified')
        sheet = validate_infernal_search_sheet(value)
        if not isinstance(sheet.get('source_context'), dict) or sheet['source_context'].get('profile') != PROFILES.get(representation):
            raise ContractError('rfam_sheet_invalid')
        _validate_rfam_source_cells(sheet, representation)
    except (ValueError, KeyError, TypeError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError('rfam_sheet_invalid') from error
    return sheet

def _validate_batch_population_links(sheet, representation):
    """Authenticate native membership declarations, without scoring a population."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_table import _report_membership
    context = sheet['source_context']
    identity, capture = (context['input_identity'], context['capture'])
    queries, declarations = (identity['queries'], sheet['sequence_populations'])
    if len(queries) != len(declarations):
        raise ContractError('rfam_sheet_invalid')
    native_rows = {}
    for hit in sheet['hits']:
        native_rows.setdefault(hit['sequence']['name'], []).append(hit)
    if representation == 'out':
        membership = _report_membership(context['membership'])
        if any((membership[k] != capture[k] for k in ('artifact_ref', 'source_sha256', 'request_job_id'))) or type(context['population_complete']) is not bool:
            raise ContractError('rfam_sheet_invalid')
        by_name, header_lines = ({}, set())
        for row in membership['queries']:
            if row['query_header_line'] in header_lines:
                raise ContractError('rfam_sheet_invalid')
            header_lines.add(row['query_header_line'])
            by_name.setdefault(row['native_query_name'], []).append(row)
        complete = context['population_complete']
        if complete and (not membership['complete'] or not capture['body_complete'] or set(by_name) != {q['native_query_name'] for q in queries}):
            raise ContractError('rfam_sheet_invalid')
        for query, declaration in zip(queries, declarations):
            member = _matched_report_member(query, membership, [(h['sequence']['name'], h['query_occurrence_key']) for h in sheet['hits']])
            if declaration['reported_set_complete'] != complete or declaration['reported_row_count'] != (None if member is None else member['reported_hit_count']) or declaration['membership_basis'] != ('frozen_complete_input' if member is None else 'both') or (complete and (member is None or member['length_nt'] != query['submitted_length_nt'] or member['reported_hit_count'] != len(native_rows.get(query['native_query_name'], [])))):
                raise ContractError('rfam_sheet_invalid')
    else:
        bindings, populations = (context['occurrence_bindings'], context['query_population'])
        if type(bindings) is not list or type(populations) is not list or len(bindings) != len(queries) or (len(populations) != len(queries)):
            raise ContractError('rfam_sheet_invalid')
        for index, (query, binding, population, declaration) in enumerate(zip(queries, bindings, populations, declarations)):
            closed_object(population, ('query_occurrence_key', 'submitted_length_nt', 'membership_basis', 'reported_row_count', 'reported_set_complete'), code='rfam_sheet_invalid')
            observed = native_rows.get(query['native_query_name'], [])
            if binding != dict(sequence_metadata_index=index, native_query_name=query['native_query_name'], query_occurrence_key=query['query_occurrence_key'], selected_occurrence_ordinal=index) or population['query_occurrence_key'] != query['query_occurrence_key'] or population['submitted_length_nt'] != query['submitted_length_nt'] or (population['membership_basis'] not in {'frozen_complete_input', 'native_report', 'both'}) or (type(population['reported_set_complete']) is not bool) or (population['reported_row_count'] != (len(observed) if observed or population['reported_set_complete'] else None)) or any((declaration[k] != population[k] for k in ('reported_row_count', 'reported_set_complete', 'membership_basis'))):
                raise ContractError('rfam_sheet_invalid')
        complete = all((p['reported_set_complete'] for p in populations))
        if any((p['reported_set_complete'] for p in populations)) != complete:
            raise ContractError('rfam_sheet_invalid')
        if complete:
            if not capture['body_complete'] or any((not a['retained_population_complete'] for a in sheet['artifacts'])) or (not set(native_rows) <= {q['native_query_name'] for q in queries}):
                raise ContractError('rfam_sheet_invalid')
            if context.get('report_membership') is not None:
                membership = _report_membership(context['report_membership'])
                members = {q['native_query_name']: q for q in membership['queries']}
                if not membership['complete'] or membership['request_job_id'] != identity['expected_job_id'] or len(members) != len(membership['queries']) or (set(members) != {q['native_query_name'] for q in queries}) or any((members[q['native_query_name']]['length_nt'] != q['submitted_length_nt'] or members[q['native_query_name']]['reported_hit_count'] != p['reported_row_count'] for q, p in zip(queries, populations))):
                    raise ContractError('rfam_sheet_invalid')
    if any((hit['population_complete'] != complete for hit in sheet['hits'])):
        raise ContractError('rfam_sheet_invalid')

def _validate_rfam_source_cells(sheet, representation):
    """Check format identity and source-bound display facts, without reparsing.

    Closed historical validators remain useful here as validators of the same
    retained source facts. No historical scoring sheet or calculation is made.
    """
    context = sheet['source_context']
    capture, identity = (context['capture'], context['input_identity'])
    if representation == 'json':
        validate_rfam_input_identity(identity)
        validate_rfam_capture(capture)
        if capture['representation'] != 'json' or capture['request_job_id'] != identity['expected_job_id'] or capture['request_sequence_sha256'] != identity['submitted_sequence_sha256'] or (context['job']['job_id'] != identity['expected_job_id']):
            raise ContractError('rfam_sheet_invalid')
        population = context['population']
        closed_object(population, ('native_reported_count', 'observed_row_count', 'family_bucket_count', 'count_agrees', 'body_complete', 'result_identity_matches', 'reported_set_complete', 'provider_filtering_known', 'all_model_hits_complete'), code='rfam_sheet_invalid')
        if population['body_complete'] != capture['body_complete'] or population['result_identity_matches'] is not True or (not is_int(population['observed_row_count'])) or (population['observed_row_count'] != len(sheet['hits'])) or (not is_int(population['family_bucket_count'])) or (population['native_reported_count'] is not None and (not is_int(population['native_reported_count']))) or any((type(population[k]) is not bool for k in ('body_complete', 'count_agrees', 'reported_set_complete'))) or (population['count_agrees'] and population['native_reported_count'] != population['observed_row_count']) or (population['reported_set_complete'] and (not (population['body_complete'] and population['count_agrees']))):
            raise ContractError('rfam_sheet_invalid')
        declarations = sheet['sequence_populations']
        expected_count = population['observed_row_count'] if population['observed_row_count'] or population['reported_set_complete'] else None
        if len(declarations) != 1 or declarations[0]['reported_set_complete'] != population['reported_set_complete'] or declarations[0]['reported_row_count'] != expected_count:
            raise ContractError('rfam_sheet_invalid')
    else:
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_report_contracts import validate_rfam_saved_batch_identity
        validate_rfam_saved_batch_identity(identity, capture, representation=representation)
        _validate_batch_population_links(sheet, representation)
    for ordinal, hit in enumerate(sheet['hits']):
        details = hit['source_details']
        if details['profile'] != context['profile'] or hit['locator']['artifact_id'] != capture['artifact_ref']:
            raise ContractError('rfam_sheet_invalid')
        if hit['lengths']['model']['value'] is not None or details.get('model_metadata_ref') is not None:
            raise ContractError('rfam_model_binding_unverified')
        if representation == 'json':
            pointer = '/hits/' + details['family_name'].replace('~', '~0').replace('/', '~1') + '/' + str(details['family_list_ordinal'])
            if details['document_ordinal'] != ordinal or details['native_json_pointer'] != pointer or hit['locator']['json_pointer'] != pointer or (hit['hit_id'] != capture['artifact_ref'] + pointer) or (hit['model']['name'] != details['family_name']) or (hit['query_occurrence_key'] != identity['query_occurrence_key']) or (details['identity_valid'] != (hit['attribution']['model'] == 'valid')):
                raise ContractError('rfam_sheet_invalid')
            raw = details.get('raw_row')
            if details.get('raw_row_digest') is not None:
                if rfam_digest(raw) != details['raw_row_digest']:
                    raise ContractError('rfam_sheet_invalid')
                if isinstance(raw, dict):
                    valid_accession = type(raw.get('acc')) is str and re.fullmatch('RF[0-9]{5}', raw['acc']) is not None
                    valid_identity = raw.get('id') == details['family_name'] and bool(details['family_name']) and valid_accession
                    if details['identity_valid'] != valid_identity or hit['model']['accession'] != (raw['acc'] if valid_accession else None):
                        raise ContractError('rfam_sheet_invalid')
            correspondence, envelope = (hit['correspondence'], details['alignment_identity'])
            if (correspondence is None) != (envelope is None):
                raise ContractError('rfam_alignment_binding_conflict')
            if correspondence is not None:
                expected = dict(artifact_ref=capture['artifact_ref'], hit_key=hit['hit_id'], query_occurrence_key=hit['query_occurrence_key'], family_accession=hit['model']['accession'])
                if envelope['hit_identity'] != expected or envelope['query_strand'] != hit['strand']:
                    raise ContractError('rfam_alignment_binding_conflict')
                validate_rfam_alignment_result({**envelope, **{k: v for k, v in correspondence.items() if k != 'blocks'}})
                if correspondence['status'] in {'complete', 'partial'}:
                    interval = hit['sequence_interval']
                    if not details['identity_valid'] or not details['query_coordinates_valid'] or interval is None or (correspondence['display_query_from'] != hit['sequence_from']) or (correspondence['display_query_to'] != hit['sequence_to']) or any((a < interval[0] or b > interval[1] for a, b in correspondence['aligned_query_intervals'])):
                        raise ContractError('rfam_alignment_coordinate_conflict')
                    complement = str.maketrans('ACGTURYSWKMBDHVN', 'UGCAAYRSWMKVHDBN')
                    for pair in correspondence['paired_positions']:
                        if not interval[0] <= pair['query_position'] < interval[1]:
                            raise ContractError('rfam_alignment_coordinate_conflict')
                        observed = identity['submitted_sequence'][pair['query_position']].upper()
                        if hit['strand'] == '-':
                            observed = observed.translate(complement)
                        if observed.replace('T', 'U') != pair['query_symbol'].upper().replace('T', 'U'):
                            raise ContractError('rfam_alignment_query_conflict')
        elif representation == 'out':
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_report_contracts import _validate_lines, _validate_correspondence, REPORT_CORRESPONDENCE_VERSION
            source = _validate_lines(details['source_lines'], 'rfam_sheet_invalid')
            origin = details['score_line'] or details['alignment_summary_line']
            if hit['hit_id'] != capture['artifact_ref'] + '/lines/' + str(origin) or hit['locator']['line'] != origin or hit['model']['accession'] is not None:
                raise ContractError('rfam_sheet_invalid')
            members = [r for r in context['membership']['queries'] if r['query_header_line'] == details['query_header_line']]
            if len(members) != 1 or members[0]['native_query_name'] != hit['sequence']['name']:
                raise ContractError('rfam_sheet_invalid')
            queries = [q for q in identity['queries'] if q['query_occurrence_key'] == hit['query_occurrence_key']]
            query = queries[0] if len(queries) == 1 else None
            if query is not None and (query['native_query_name'] != hit['sequence']['name'] or query['submitted_length_nt'] != members[0]['length_nt']):
                raise ContractError('rfam_sheet_invalid')
            if hit['correspondence'] is not None:
                native = {name: hit.get(common) for name, common in _REPORT_FIELDS.items()}
                _validate_correspondence(dict(version=REPORT_CORRESPONDENCE_VERSION, **hit['correspondence']), dict(native=native, strand=hit['strand']), query, source, 'rfam_sheet_invalid')

def _missing_reason(hit, metric, cell):
    details = hit['source_details']
    missing = details.get('missing', {})
    if hit['attribution']['sequence'] != 'valid' or hit['attribution']['model'] != 'valid':
        return 'identity_rejected'
    if metric in missing:
        return missing[metric]
    native = next((key for key, value in _REPORT_FIELDS.items() if value == cell), None)
    if native in missing:
        return missing[native]
    if metric in {'model_length_positions', 'model_coverage_fraction', 'native_model_span_fraction'}:
        return 'model_length_unavailable'
    if metric in {'query_span_nt', 'query_span_fraction', 'native_model_span_positions'}:
        return 'coordinates_invalid'
    if cell in ('display_model_from', 'display_model_to', 'represented_model_positions', 'represented_query_positions', 'model_consensus_equal_fraction', *RFAM_ALIGNMENT_COUNT_FIELDS):
        if details['profile'] == 'rfam_batch_tblout':
            return 'not_reported'
        correspondence = hit.get('correspondence')
        if metric == 'model_consensus_equal_fraction' and correspondence and (correspondence.get('model_consensus_compared_count') == 0):
            return 'no_determinate_pairs'
        return missing.get('correspondence', 'alignment_not_parsed' if correspondence is None else 'alignment_unsupported' if correspondence['status'] in {'partial', 'unsupported'} else 'alignment_conflict')
    return 'not_reported'

def project_rfam_infernal_result(sheet: dict, calculation: dict, *, projection: dict, artifact_bindings: dict, representation: str) -> dict:
    """Select aliases of authenticated saved common cells; never calculate scores."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_report_contracts import RFAM_REPORT_METRIC_UNITS, RFAM_REPORT_MISSING_REASONS, validate_rfam_report_projection
    code = 'rfam_projection_reference_conflict'
    try:
        sheet = select_rfam_common_sheet(sheet, representation=representation)
        calculation = validate_infernal_search_scores(calculation, sheet=sheet)
    except (ValueError, TypeError, KeyError) as error:
        raise ContractError(code) from error
    if calculation['parameters'] != {'hit_scope': 'reported'}:
        raise ContractError(code)
    projection = {'json': validate_rfam_projection, 'tblout': validate_rfam_table_projection, 'out': validate_rfam_report_projection}[representation](projection)
    bindings = finite_json_copy(artifact_bindings, code=code)
    closed_object(bindings, ('source_ref', 'sheet_ref', 'calculation_ref', 'sheet_digest', 'calculation_digest'), code=code)
    if any((not is_text(bindings[k]) for k in ('source_ref', 'sheet_ref', 'calculation_ref'))) or bindings['source_ref'] != sheet['source_context']['capture']['source_ref'] or bindings['sheet_digest'] != rfam_digest(sheet) or (bindings['calculation_digest'] != rfam_digest(calculation)):
        raise ContractError(code)
    family = projection['family']
    rows = calculation['hits'] if family == 'hit' else calculation['sequence_strand_aggregates']
    keys = [r['hit_id'] if family == 'hit' else query_strand_record_key(r['query_occurrence_key'], r['strand']) for r in rows]
    if len(set(keys)) != len(keys):
        raise ContractError(code)
    choice = projection['rows']
    if 'record_keys' in choice:
        indices = {key: index for index, key in enumerate(keys)}
        if any((key not in indices for key in choice['record_keys'])):
            raise ContractError(code)
        selected = [indices[key] for key in choice['record_keys']]
    else:
        selected = range(choice['offset'], min(choice['offset'] + choice['limit'], len(rows)))
    original = {h['hit_id']: h for h in sheet['hits']}
    units = RFAM_REPORT_METRIC_UNITS if representation == 'out' else RFAM_METRIC_UNITS
    reasons = RFAM_REPORT_MISSING_REASONS if representation == 'out' else RFAM_MISSING_REASONS
    result = []
    for index in selected:
        row = rows[index]
        hit = original[row['hit_id']] if family == 'hit' else None
        values = row['attributed_components'] if family == 'hit' else row
        aliases = HIT_ALIASES if family == 'hit' else POPULATION_ALIASES
        measured, unavailable = ([], [])
        for metric in projection['metrics']:
            cell = aliases[metric]
            value = values[cell]
            if is_number(value):
                measured.append(dict(name=metric, value=value, unit=units[metric]))
            else:
                reason = _missing_reason(hit, metric, cell) if hit is not None else 'partial_body'
                if reason not in reasons:
                    raise ContractError(code)
                unavailable.append(dict(name=metric, reason=reason))
        projected = dict(record_key=keys[index], query_occurrence_key=row['query_occurrence_key'], family_accession=row['model'].get('accession') if hit is not None and hit['attribution']['model'] == 'valid' else None, strand=row['strand'], measured=measured, unavailable=unavailable)
        if representation == 'out':
            projected['model_name'] = row['model'].get('name') if hit is not None else None
        result.append(projected)
    return dict(version='rfam_selected_projection_v1', source_ref=bindings['source_ref'], sheet_ref=bindings['sheet_ref'], calculation_ref=bindings['calculation_ref'], family=family, selection=deepcopy(projection), available_row_count=len(rows), selected_row_count=len(result), more_rows=len(result) < len(rows), population_complete=all((p['reported_set_complete'] for p in sheet['sequence_populations'])) if family == 'hit' else all((r['complete_for_selected_population'] for r in rows)), rows=result)
