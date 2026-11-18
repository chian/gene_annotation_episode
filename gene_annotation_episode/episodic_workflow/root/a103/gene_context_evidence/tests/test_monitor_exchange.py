"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a103'
    parent_type = 'GeneContextEvidenceEpisode'
    parent_role = 'gene_context_evidence'
