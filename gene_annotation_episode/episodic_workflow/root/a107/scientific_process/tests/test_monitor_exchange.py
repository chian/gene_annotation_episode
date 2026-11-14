"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a107'
    parent_type = 'ScientificProcessEpisode'
    parent_role = 'scientific_process'
