"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a104'
    parent_type = 'EvolutionaryHistoryEvidenceEpisode'
    parent_role = 'evolutionary_history_evidence'
