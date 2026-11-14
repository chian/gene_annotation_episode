"""Atomic ordinary derivation over an explicitly received VCF result.

The shared input owner supplies File authority; the pure VCF owner supplies
all parsing and calculation. Delivering the result Source grants no inputs,
private sheets or native-caller capability.
"""
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import vcf_result_measurements as core
from gene_annotation_episode.episodic_workflow.root.a108.execution_contracts import digest
FACT_SOURCE = 'vcf_result_outcomes'

def vcf_result_fact_sources():
    schema = core.vcf_result_schema('Return')
    report = {'$schema': schema['$schema'], '$defs': schema['$defs'], 'type': 'array', 'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    report['$id'] = 'urn:gene-annotation:vcf-result-return:' + digest(report)
    return {FACT_SOURCE: dict(type='array', meaning='Selected retained VCF fields, original associations, record/allele/sample populations and capture qualifications. Supplied-result analysis does not establish execution or success of a variant caller or annotation pipeline.', report_schema=report)}
