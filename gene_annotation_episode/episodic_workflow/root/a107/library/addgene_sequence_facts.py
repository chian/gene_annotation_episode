"""A107 addgene sequence facts."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.library import addgene_sequence_native as native
FACT_SOURCE = 'execution_addgene_sequence_facts'
FACT_VERSION = 'addgene_sequence_fact_v1'

def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
_PAGE = native.ADDGENE_SEQUENCE_PAGE_SCHEMA['properties']
_NATIVE_ROW = _PAGE['records']['items']
_NULLABLE_ROW = {**deepcopy(_NATIVE_ROW), 'type': ['object', 'null']}
_SELECTED_ROW = _object(dict(selection_ordinal={'type': 'integer', 'minimum': 0}, record_ordinal={'type': 'integer', 'minimum': 0}, status=deepcopy(_NATIVE_ROW['properties']['sequence_status']), issue_codes={'type': 'array', 'uniqueItems': True, 'items': {'enum': [*_NATIVE_ROW['properties']['issue_codes']['items']['enum'], 'selected_record_unavailable']}}, symbol_count={'type': 'null'}, sequence_file_ref={'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': 'artifact', 'pattern': '^artifact_[0-9a-f]{64}$'}, native_record=_NULLABLE_ROW))
ADDGENE_SEQUENCE_FACT_SCHEMA = _object(dict(version={'const': FACT_VERSION}, source_ref={'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source', 'pattern': '^source_[0-9a-f]{24}$'}, requested_id=deepcopy(_PAGE['requested_id']), response_complete=deepcopy(_PAGE['response_complete']), parse_status=deepcopy(_PAGE['parse_status']), authentication_required=deepcopy(_PAGE['authentication_required']), issues=deepcopy(_PAGE['issues']), selected_rows={'type': 'array', 'items': _SELECTED_ROW}))
ADDGENE_SEQUENCE_FACTS_SCHEMA = {'type': 'array', 'items': deepcopy(ADDGENE_SEQUENCE_FACT_SCHEMA), 'x-source': FACT_SOURCE}
