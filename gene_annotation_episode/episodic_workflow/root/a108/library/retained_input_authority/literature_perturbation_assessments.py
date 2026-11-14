"""A106 experiment identity and assessment revisions; no new scoring policy.

The existing point/summary readers and calculators own the numbers. This layer
links their saved results to one actual experiment and one revisable question.
It never treats a source format, report, or revised judgment as another assay.
"""
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj
EXPERIMENT_TYPES = {'intervention_response': {'question': "What does the intervention establish about the molecule's contribution to the observed outcome?", 'designs': ('native_deletion_restoration', 'selective_perturbation_restoration', 'cas_free_reconstitution', 'variant_replacement', 'other_explicit', 'unknown', 'conflicting'), 'considerations': ('actual molecule, recipient, donor, coexisting copies and required partners', 'intended intervention, measured extent and unintended amount changes', 'same endpoint, eligibility denominator, normalization, conditions and timing', 'measurement calibration, detection limits and source uncertainty', 'reference/intervention contrast and genuinely separate restoration arm if present', 'nuisance amount comparability versus endpoint-scale alternative-effect bounds', 'biological/preparation/technical units, pairing and shared controls'), 'reader': 'read_perturbation_inputs', 'calculators': ('populate_source_restoration', 'populate_source_summary_restoration'), 'combination': 'Existing within-experiment source restoration product; no new cross-experiment rule.'}}

def assessment_schema():
    reference = {**REF, 'x-reference-namespace': 'reference'}
    source = {**REF, 'x-reference-namespace': 'source'}
    text = {'type': 'string', 'minLength': 1}
    return obj({'experiment_ref': reference, 'experiment_type': {'enum': list(EXPERIMENT_TYPES)}, 'assessment_key': text, 'scientific_question': text, 'conclusion': text, 'limitations': {'type': 'array', 'items': text}, 'revision_reason': {'type': ['string', 'null'], 'minLength': 1}, 'revises_sheet_ref': {**source, 'type': ['string', 'null']}})
