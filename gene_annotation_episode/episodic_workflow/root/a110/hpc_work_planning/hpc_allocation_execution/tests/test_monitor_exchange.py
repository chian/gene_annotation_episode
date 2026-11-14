"""Private parent monitor request and original receipt connection."""
from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a110.hpc_work_planning.hpc_allocation_execution.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a110'
    parent_type = 'HPCEpisode'
    parent_role = 'hpc_execution'
