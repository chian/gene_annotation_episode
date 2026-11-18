"""Each arm's evidence-axis head role and class-name prefix, for test helpers shared across arms.

Arms are renamed from the generic head one at a time; this table is the single place the shared helpers read
an arm's head from (docs/axis_restructure_20261117/README.md).
"""

HEAD = {
    'a101': 'sequence_homology_evidence', 'a102': 'scientific_process', 'a103': 'scientific_process',
    'a104': 'scientific_process', 'a105': 'experimental_activity_evidence', 'a106': 'perturbation_evidence',
    'a107': 'scientific_process', 'a108': 'sample_context_evidence', 'a110': 'scientific_process',
}
CLASS = {
    'a101': 'SequenceHomologyEvidence', 'a102': 'ScientificProcess', 'a103': 'ScientificProcess',
    'a104': 'ScientificProcess', 'a105': 'ExperimentalActivityEvidence', 'a106': 'PerturbationEvidence',
    'a107': 'ScientificProcess', 'a108': 'SampleContextEvidence', 'a110': 'ScientificProcess',
}


def axis_of(module):
    """The arm package (e.g. 'a102') of a module under gene_annotation_episode.episodic_workflow.root."""
    return module.__name__.split('.')[3]
