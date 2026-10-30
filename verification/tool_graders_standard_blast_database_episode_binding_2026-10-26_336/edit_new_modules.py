"""One-time mechanical adaptation of E custody to the accepted standard contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / 'gene_annotation_episode/native_blast_standard_database_result_publication.py'
s = path.read_text()
start = s.index('_ROLES_V2 =')
end = s.index('\n\ndef _failure', start)
s = s[:start] + "_MANIFEST_ROLES = {'native_blast_standard_database_result_worker_manifest_v1': _ROLES_V1}\n" + s[end:]
s = s.replace("            or value['version'] == 'native_blast_standard_database_result_worker_manifest_v2' and request['bundle']['program'] not in {'psiblast', 'deltablast'}\n", '')
start = s.index("        if value['version'] == 'native_blast_standard_database_result_worker_manifest_v2':")
end = s.index("    validate_schema(value['failures']", start)
s = s[:start] + '''        from .native_blast_standard_database_metadata import validate_standard_blast_database_sheet_set
        validate_standard_blast_database_sheet_set(sheets)
        if (sheets['collection'] != _json(store, artifact_refs['collection'])
                or sheets['prepared_inputs'] != _json(store, artifact_refs['inputs'])):
            raise ContractError('native_blast_standard_database_frozen_sheet_source_conflict')
        attempts = [r['value'] for r in sheets['prepared_inputs']['source_relations'] if r['kind'] == 'attempt']
        if attempts != [dict(bundle=request['bundle'], attempt_identity=request['authenticated_attempt'],
                bundle_source_ref=request['bundle_artifact_ref'], bundle_artifact_ref=request['bundle_artifact_ref'],
                bundle_sha256=request['bundle_capture']['sha256'])]:
            raise ContractError('native_blast_standard_database_frozen_sheet_attempt_conflict')
''' + s[end:]
start = s.index('def _frozen_convergence(')
end = s.index('def _preparation_failures(', start)
s = s[:start] + s[end:]
s = s.replace("            roles = _ROLES_V2 if request['bundle']['program'] in {'psiblast', 'deltablast'} else _ROLES_V1", "            roles = _ROLES_V1")
s = s.replace("    if frozen['manifest']['version'] == 'native_blast_standard_database_result_worker_manifest_v2':\n        _frozen_native_occurrences(store, prepared, frozen, rows)\n", '')
start = s.index('def _frozen_native_occurrences(')
end = s.index('def _projection(', start)
s = s[:start] + s[end:]
s = s.replace("    request['output_directory'] = str(generation / 'output')\n", "    request['output_directory'] = str(generation / 'output')\n    validate_schema(request, STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA)\n")
start = s.index('def _master_relation(')
end = s.index('def _hsp_payload(', start)
s = s[:start] + '''def _master_relation(store, inputs, calculations, query, axis):
    if axis != 'pssm_master':
        raise _QueryQualification('master_axis_unavailable')
    relation = _one([r for item in inputs['metadata'] if item['consumer'] == 'query_identity'
        and item['status'] == 'valid' and item['normalized'] is not None
        for r in item['normalized']['master_subjects'] if r['kind'] == 'pssm'
        and r['input_key'] == query['input_key'] and r['record_ordinal'] == query['record_ordinal']],
        'master_subject_relation_unresolved')
    if relation['subject_ref'] != query['subject_ref'] or relation['sequence_sha256'] != query['sequence_sha256']:
        raise _QueryQualification('master_subject_relation_conflict')
    source = store.get(relation['source']['source_ref'])
    if source['record_type'] != 'source':
        raise _QueryQualification('master_relation_source_record_unavailable')
    sheet = _one([s for s in inputs['pssm_sheets'] if s['artifact_key'] == query['artifact_key']],
        'master_positional_map_unavailable')
    original = _one([r for r in sheet['pssms'] if r['record_ordinal'] == query['record_ordinal']],
        'master_positional_map_unavailable')
    matrix = _one([r for item in calculations['pssm'] if item['artifact_key'] == query['artifact_key']
        for r in item['components']['matrices'] if r['pssm_key'] == original['pssm_key']
        and r['record_ordinal'] == query['record_ordinal']], 'master_positional_map_unavailable')
    master = matrix['master']
    if (master['status'] != 'complete' or master['sequence'] != query['sequence']
            or master['decoded_length'] != query['length'] or master['reported_length'] != query['length']
            or matrix['dimensions']['positions'] != query['length']
            or master['column_to_residue'] != [dict(column=i, master_position=i, symbol=s)
                for i, s in enumerate(query['sequence'])]):
        raise _QueryQualification('master_positional_map_conflict')
    return source['id']


def _at(value, pointer):
    """Resolve an exact frozen JSON pointer; no parser or calculator is called."""
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ContractError('native_blast_standard_database_frozen_component_pointer_invalid')
    try:
        for token in pointer.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not token.isdecimal() or str(int(token)) != token:
                    raise ValueError
                value = value[int(token)]
            else:
                value = value[token]
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise ContractError('native_blast_standard_database_frozen_component_pointer_invalid') from error
    return value


def _qualified_hsp(calculations, sheets, key, full_row, query):
    qualified = _one([r for r in calculations['qualified_hsp_components'] if r['row_key'] == key],
        'qualified_hsp_unresolved')
    if qualified['status'] != 'available' or qualified['component_pointer'] is None:
        raise _QueryQualification('qualified_hsp_unavailable')
    matches = [(i, r) for i, r in enumerate(calculations['sequence']) if r['search_key'] == key['search_key']]
    index, sequence = _one(matches, 'qualified_search_unresolved')
    if sequence['components'] is None:
        raise _QueryQualification('qualified_search_unavailable')
    base = '/sequence/' + str(index) + '/components'
    components = sequence['components']['components']
    hit_key = dict(key, hsp_ordinal=None, description_ordinal=None)
    hit = _one([r for r in components['row_keys']['hits'] if r['row_key'] == hit_key], 'qualified_hit_unresolved')
    hsp = _one([r for r in hit['hsps'] if r['row_key'] == key], 'qualified_hsp_unresolved')
    pointer = base + '/components/database_sheet/hits/' + str(hit['component_index']) + '/hsp_components/' + str(hsp['component_index'])
    references = [(i, r) for i, r in enumerate(components['coordinate_context']['references']) if r['row_key'] == hit_key]
    reference_index, _ = _one(references, 'qualified_reference_unresolved')
    if (qualified['sequence_component_pointer'] != base or qualified['component_pointer'] != pointer
            or qualified['query_binding_pointer'] != '/sequence/' + str(index) + '/sheet/query_binding'
            or qualified['reference_context_pointer'] != base + '/components/coordinate_context/references/' + str(reference_index)
            or sheets['sequence'][index]['search_key'] != key['search_key']):
        raise ContractError('native_blast_standard_database_frozen_qualified_pointer_conflict')
    binding = _at(sheets, qualified['query_binding_pointer'])
    if (binding is None or binding['full_length'] != query['length']
            or binding['sequence_sha256'] != query['sequence_sha256']
            or binding['operand']['subject_ref'] != query['subject_ref']):
        raise _QueryQualification('qualified_full_query_binding_unavailable')
    measured = _at(calculations, pointer)
    cells = {r['name']: r for r in full_row['measurements']}
    for axis in ('query', 'reference'):
        for name, group, field in (('qualified_paired_' + axis + '_units', 'counts', 'paired_' + axis + '_positions'),
                ('full_' + axis + '_paired_coverage', 'fractions', axis + '_paired_coverage')):
            cell = cells[name]
            if cell['value'] != measured[group].get(field) or cell['component_pointer'] != pointer + '/' + group + '/' + field:
                raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
            if group == 'fractions' and (cell['numerator'] != measured['counts'].get('paired_' + axis + '_positions')
                    or cell['denominator'] != measured['denominators'].get(axis + '_length')
                    or cell['complete'] != measured['geometry_available']):
                raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
    flag = _one([r for r in full_row['booleans'] if r['name'] == 'qualified_geometry_available'], 'qualified_geometry_flag_unavailable')
    if flag['value'] != measured['geometry_available'] or flag['component_pointer'] != pointer + '/geometry_available':
        raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
    return measured


''' + s[end:]
s = s.replace('    inputs, collection, calculations = documents', '    inputs, collection, calculations, sheets = documents')
s = s.replace("axis not in {'sequence', 'msa_master', 'pssm_master'}\n            or reference_axis not in {'sequence', 'profile_model', 'vdb_member'}", "axis not in {'sequence', 'pssm_master'}\n            or reference_axis != 'sequence'")
s = s.replace("    measured = component['component']", "    measured = _qualified_hsp(calculations, sheets, key, full_row, query)")
s = s.replace("reference_gap_columns='reference_gap_columns', paired_query_units='query_aligned_positions')\n    if reference_axis != 'profile_model':\n        names.update(identical_pairs='identical_positions', paired_identity='paired_identity',\n            alignment_identity='alignment_identity', paired_reference_units='reference_aligned_positions')", "reference_gap_columns='reference_gap_columns', qualified_paired_query_units='query_aligned_positions',\n        identical_pairs='identical_positions', paired_identity='paired_identity',\n        alignment_identity='alignment_identity', qualified_paired_reference_units='reference_aligned_positions')")
s = s.replace("kind='profile_match' if reference_axis == 'profile_model' else 'comparison'", "kind='comparison'")
s = s.replace("for role in ('inputs', 'collection', 'calculations')", "for role in ('inputs', 'collection', 'calculations', 'sheets')")
s = s.replace("projection = (preparation['full_rows_artifact_ref'] is not None and not projection_failures)", "projection = (preparation['full_rows_artifact_ref'] is not None and not _required_failures(projection_failures))")
s = s.replace("projection = prepared['full_rows_artifact_ref'] is not None and not projection_failures", "projection = prepared['full_rows_artifact_ref'] is not None and not _required_failures(projection_failures)")
pos = s.index('def publish_selected_standard_blast_database_rows(')
s = s[:pos] + '''def _required_failures(failures):
    # Missing biological query identity qualifies source-only publication. It
    # does not prevent faithful acquisition of requested numerical cells.
    return [row for row in failures if row['code'] != 'native_blast_standard_database_query_unbound']


''' + s[pos:]
s = s.replace("__all__ = ['prepare_standard_blast_database_grading'", "__all__ = ['validate_standard_blast_job_inputs', 'validate_standard_blast_selected_inputs', 'prepare_standard_blast_database_grading'")
path.write_text(s)
