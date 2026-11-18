"""Substantive A101 policy definitions; original live runtime globals retained."""

def enrich_completion_snapshot(self, source, context, snapshot, facts):
    snapshot.update(initial_credit=self.journal.row('runtime_episodes', source.episode_id)['initial_credit'], credit=facts['credit'], controller_credit=self.source_controller_credit(source), episode_yield=facts['episode_yield'], parent_invocation_ref=self.services.scientific_parent_invocation(context))

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('enrich_completion_snapshot',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'enrich_completion_snapshot': 'enrich_completion_snapshot'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.completion_report')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
