"""Private parent monitor request and original receipt connection."""
import pytest

from gene_annotation_episode.episodic_workflow.root.tests.monitor_parent_exchange import MonitorParentExchangeChecks
from ...episode_bindings import EpisodeBindingRegistry

class TestMonitorExchange(MonitorParentExchangeChecks):
    parent_module = 'gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.episode'
    axis_module = 'gene_annotation_episode.episodic_workflow.root.a102'
    parent_type = 'StructuralHomologyEvidenceEpisode'
    parent_role = 'structural_homology_evidence'

    @pytest.fixture(autouse=True)
    def private_receiver_registry(self, exchange):
        # This receipt fixture commissions no private published-evidence child.
        # Supply the real empty registry used by the receiver's ownership check.
        exchange.workflow.episode_bindings = EpisodeBindingRegistry()
        return exchange
