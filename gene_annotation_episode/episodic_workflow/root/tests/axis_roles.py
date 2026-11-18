"""Each arm's evidence-axis head role and class-name prefix, for test helpers shared across arms.

Arms are renamed from the generic head one at a time; this table is the single place the shared helpers read
an arm's head from (docs/axis_restructure_20261117/README.md).
"""

HEAD = {
    'a101': 'sequence_homology_evidence', 'a102': 'structural_homology_evidence', 'a103': 'gene_context_evidence',
    'a104': 'evolutionary_history_evidence', 'a105': 'experimental_activity_evidence', 'a106': 'perturbation_evidence',
    'a107': 'partner_presence_evidence', 'a108': 'sample_context_evidence', 'a110': 'biochemical_feasibility_evidence',
}
CLASS = {
    'a101': 'SequenceHomologyEvidence', 'a102': 'StructuralHomologyEvidence', 'a103': 'GeneContextEvidence',
    'a104': 'EvolutionaryHistoryEvidence', 'a105': 'ExperimentalActivityEvidence', 'a106': 'PerturbationEvidence',
    'a107': 'PartnerPresenceEvidence', 'a108': 'SampleContextEvidence', 'a110': 'BiochemicalFeasibilityEvidence',
}


def axis_of(module):
    """The arm package (e.g. 'a102') of a module under gene_annotation_episode.episodic_workflow.root."""
    return module.__name__.split('.')[3]
