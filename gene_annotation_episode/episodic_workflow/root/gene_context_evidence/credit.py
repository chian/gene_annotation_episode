"""Credit: the A103 context credit of the records this Episode holds, over the original scope and the proposed
annotation of the commission.

Carried from the old ``credit.py`` (credit kind ``scientific``; ``credit_projector`` returned the axis's
``A103ContextCredit`` of ``task_projector.py`` for a published-instruction axis entry; ``credit_view`` asked
``services.scientific_credit``). The projector is the library's, handed the read-only records: it reads the held
attachment sheets (work table ``a103_attachments``) and measurements (``a103_publications``) and never bounds, clamps
or rescales the value. The old ``credit_projector`` mandatory proposed annotation is ``read_from_parent``'s. A child's
returned credit is information in the summary; it is never added here: the sheets a child returns in its finding are
held here and counted by this Episode's own projector, under this Episode's own scope and assessments.

``credit_view`` is the whole old credit view (the number and the axis components); ``internal_summary.py`` shows it to
the model and ``credit`` returns its number."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)


def credit_view(records, parent):
    """The A103 context credit view over the held records, for the commissioned scope and proposed annotation."""
    assignment = {'scope': parent['scope'], 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    return A103ContextCredit()(records, parent['scope'], known_record_refs=records.refs(), assignment=assignment)


def credit(summary, records):
    return credit_view(records, summary['assignment'])['credit']
