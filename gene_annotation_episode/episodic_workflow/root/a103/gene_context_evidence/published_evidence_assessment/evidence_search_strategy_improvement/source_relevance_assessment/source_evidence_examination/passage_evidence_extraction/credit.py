"""Credit: the A103 context credit of the records this Episode holds, over the fixed scope. The projector is the
library's; it reads the held attachments and measurements through the records it is handed and never bounds,
clamps or rescales the value."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)


def credit(summary, records):
    view = A103ContextCredit()(records, summary['assignment']['scope'], known_record_refs=records.refs())
    return view['credit']
