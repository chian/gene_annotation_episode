"""A101 credit selection for a commissioned scientific process."""
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import A101SequenceCredit

def original_task_projector(assignment):
    return A101SequenceCredit()

def scientific_guidance():
    return 'A101 owns sequence similarity evidence. For an NCBI BLAST search that may run remotely, use the configured Launch API job when available: submit once, return its execution_handoff_refs to this episode, and let a separately selected monitor or Results episode check that same RID. The handoff is operational progress, not homology evidence. If that RID is waiting and no useful A101 work remains, return the handoff reference and current credit to your parent so it can choose another evidence axis. Consider ClusteredNR (nr_clustered_seq) for an initial blastx search; choose the database for the scientific question and preserve the selected database in the original request.\n\n'
