"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a106'
    parent_type = 'PerturbationEvidenceEpisode'
    parent_role = 'perturbation_evidence'
