from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.atac_differential_result_contracts import atac_result_schema, validate_atac_result_record, require, digest

def atac_result_selector_schema():
    schema = atac_result_schema('ResultSelector')
    schema['$id'] = 'urn:gene-annotation:atac:selector:' + digest(schema)
    return schema

def validate_atac_result_selector(selector, *, request):
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts import validate_atac_record
    request = validate_atac_record('Request', request)
    selector = validate_atac_result_record('ResultSelector', selector)
    require(selector['comparison_key'] == request['comparison_key'], 'atac_result_comparison_conflict')
    require(set(selector['projection']['run_keys']) <= {'callpeak1', 'callpeak2'}, 'atac_result_unknown_run')
    return selector
