"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a110'
    parent_type = 'BiochemicalFeasibilityEvidenceEpisode'
    parent_role = 'biochemical_feasibility_evidence'
