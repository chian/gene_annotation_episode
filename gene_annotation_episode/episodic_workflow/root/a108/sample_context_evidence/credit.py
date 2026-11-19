"""Credit of the A108 sample-context head: the number of distinct retained A108 findings it holds as known, in finding
units, never bounded, clamped or rescaled here.

Carried from the old ``credit.py`` (``SampleContextEvidenceCredit.credit_kind`` 'scientific', ``credit_projector`` ->
``original_task_projector``, ``credit_view`` -> ``services.scientific_credit``) at 97308b94c. The projector is
``ScientificFindingProgress(FindingProgressPolicy(credit_unit))`` of ``findings/sample_context_evidence/
investigation_progress.py``, built from the commissioned evidence task (``whole_axis_findings``, A108): the old
``original_task_projector`` is the check of the evidence task in ``messages/read_from_parent.py``. The old credit view
ran that projector with the local commission and the receipt arguments (the assessments this episode knows); here the
known assessments are the summary's: the assessments the episode's own tool outcomes returned and the children's
returned findings named (``messages/internal_summary.py``). With a proposed annotation the projector keeps only the
assessments of that hypothesis, as the old local credit did.

The old ``credit_projector`` refused a yield-bound task without ``proposed_annotation_ref``; the assignment form requires
it now. The old ``None`` for an axis entry that is neither an instruction nor an evidence-axis entry is the check of the
entry in ``task.py``'s ``process_selection``.

The projector reads the held records through custody (``records``); its finding-validity spool is a private SQLite
database of its own, not the Store."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)


def projector(summary):
    """The finding-progress projector of the commissioned evidence task (the old ``original_task_projector``)."""
    return ScientificFindingProgress(FindingProgressPolicy(summary['evidence_task']['credit_unit']))


def credit_binding(summary):
    """The credit definition the model is shown: the projector's ``as_record()``."""
    return projector(summary).as_record()


def credit_view(summary, records):
    """The old credit view: ``credit`` with ``retained_finding_count``, ``source_contributions``,
    ``inactive_dependencies`` and ``detail_pages`` over the assessments the episode knows."""
    return projector(summary)(records, summary['scope'], known_assessment_refs=list(summary['known_assessment_refs']),
                              assignment={'scope': summary['scope'],
                                          'proposed_annotation_ref': summary['proposed_annotation_ref']})


def credit(summary, records):
    """One finding unit for each distinct retained, current finding of the proposed annotation that the episode
    knows."""
    return credit_view(summary, records)['credit']
