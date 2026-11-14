from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_contracts import closed_object, finite_json_copy, is_int
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_table import RfamBatchTableParseResult
VERSION = 'rfam_batch_table_calculation_v1'
PARAMETERS = {'hit_scope': 'reported'}

def validate_rfam_table_inputs(parsed):
    code = 'rfam_projection_reference_conflict'
    parsed = finite_json_copy(parsed, code=code)
    closed_object(parsed, RfamBatchTableParseResult.__annotations__, code=code)
    if parsed['version'] != 'rfam_batch_tblout_parse_result_v1' or parsed['status'] not in {'complete', 'partial'} or parsed['format'] != 'infernal_tblout_1_cmscan_1_1_5' or (type(parsed['sheet']) is not dict) or (parsed['sheet'].get('schema') != 'infernal_search_sheet_v1') or (type(parsed['input_identity']) is not dict):
        raise ContractError(code)
    queries = parsed['input_identity'].get('queries')
    bindings, populations = (parsed['occurrence_bindings'], parsed['query_population'])
    if type(queries) is not list or not queries or type(bindings) is not list or (type(populations) is not list) or (len(bindings) != len(queries)) or (len(populations) != len(queries)) or (len(parsed['sheet'].get('sequence_metadata', [])) != len(queries)):
        raise ContractError(code)
    seen = set()
    for index, (query, binding, population, metadata) in enumerate(zip(queries, bindings, populations, parsed['sheet']['sequence_metadata'])):
        key = query.get('query_occurrence_key')
        if type(key) is not str or not key or key in seen or (binding != {'sequence_metadata_index': index, 'native_query_name': query.get('native_query_name'), 'query_occurrence_key': key, 'selected_occurrence_ordinal': index}) or (query.get('selected_occurrence_ordinal') != index) or (population.get('query_occurrence_key') != key) or (population.get('submitted_length_nt') != query.get('submitted_length_nt')) or (not is_int(query.get('submitted_length_nt'), minimum=1)) or (type(population.get('reported_set_complete')) is not bool) or (population.get('reported_row_count') is not None and (not is_int(population['reported_row_count']))) or (metadata.get('name') != query.get('native_query_name')) or (metadata.get('length') != query['submitted_length_nt']) or (metadata.get('sequence') != query.get('submitted_sequence')):
            raise ContractError(code)
        seen.add(key)
    return parsed

def _index(identity, queries):
    if type(identity) is not dict or identity.get('kind') != 'supplied_sequence_metadata':
        return None
    index = identity.get('metadata_index')
    if not is_int(index) or index >= len(queries):
        raise ContractError('rfam_projection_reference_conflict')
    return index
