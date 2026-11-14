from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import obj
LUMPY_OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')
MACS2_SELECTOR_VERSION = 'macs2_peak_file_source_selector_v1'
LUMPY_SELECTOR_VERSION = 'lumpy_file_source_selector_v1'
MACS2_OUTPUT_ROLES = ('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal')
MACS2_SELECTOR_SCHEMA = obj({'version': {'const': MACS2_SELECTOR_VERSION}, 'output_roles': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(MACS2_OUTPUT_ROLES)}}})
LUMPY_SELECTOR_SCHEMA = obj({'version': {'const': LUMPY_SELECTOR_VERSION}, 'output_roles': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(LUMPY_OUTPUT_ROLES)}}})

def is_macs2_file_source_selector(value):
    return isinstance(value, dict) and value.get('version') == MACS2_SELECTOR_VERSION

def is_lumpy_file_source_selector(value):
    return isinstance(value, dict) and value.get('version') == LUMPY_SELECTOR_VERSION
