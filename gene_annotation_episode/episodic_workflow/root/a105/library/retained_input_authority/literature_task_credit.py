"""Credit for an explicitly commissioned literature result, not tool activity."""
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, obj
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

def lead_schema():
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import _witness_schema
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'}, 'source_ref': {**REF, 'x-reference-namespace': 'source'}, 'subject_ref': {**REF, 'x-reference-namespace': 'reference'}, 'disposition': {'enum': ['relevant', 'not_relevant'], 'description': 'Whether the inspected source is a useful lead for this commissioned question. This is not evidence supporting or opposing the proposed annotation.'}, 'relevance_rationale': {'type': 'string', 'minLength': 1, 'description': 'Explain the specific connection between the witnessed source subject/result and the original question; a search hit or matching title alone is not verification.'}, 'witness': _witness_schema()})

def lead_return_schema():
    item = lead_schema()
    for name in ('proposed_annotation_ref', 'source_ref', 'subject_ref'):
        item['properties'][name]['format'] = 'reference'
    witness = item['properties']['witness']['properties']
    witness['source_ref'] = {**witness['source_ref'], 'format': 'reference'}
    return {'type': 'array', 'x-source': LEADS, 'items': item}

def screening_schema():
    return {'type': 'array', 'x-source': SCREENING, 'items': obj({'proposed_annotation_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'hypothesis'}, 'disposition': {'const': 'no_applicable_evidence'}, 'examined': {'type': 'array', 'items': obj({'source_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'source'}, 'artifact_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'artifact'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})}, 'annotation_support': {'const': 'not_assessed'}})}
