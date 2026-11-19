"""Credit: the A103 context credit of the records this Episode holds, over the fixed scope. The projector is the
library's; it reads the held attachments and measurements through the records it is handed and never bounds,
clamps or rescales the value. ``credit_view`` is the whole view (the current A103 sheet, the per-target sheets, the
measurement-specific attachments), which ``internal_summary`` shows to the model."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)


def credit_view(records, scope):
    return A103ContextCredit()(records, scope, known_record_refs=records.refs())


def credit(summary, records):
    return credit_view(records, summary['assignment']['scope'])['credit']
