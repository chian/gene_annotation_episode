"""Credit: one finding unit per distinct retained scientific finding among the assessments this episode holds (the old
``BiochemicalFeasibilityEvidenceCredit``: ``credit_projector`` returned the A110 ``finding_progress()``, a
``ScientificFindingProgress`` over ``FindingProgressPolicy``; ``credit_view`` delegated to
``services.scientific_credit``). Unbounded; reads, attempts and waiting earn nothing by themselves; a child's returned
credit is never added.

``credit`` has no services: it reads the held assessments through ``records`` (``records.list('assessment', scope)``
replaces the old known-assessment set, which the old runner kept from receipts: what the episode holds is what it
received or produced) and hands them to the library's projector with the original assignment's scope and proposed
annotation, as the old ``read_details`` filtered them.

BLOCKED-ON-STORE-ACCESS (library not carried): ``ScientificFindingProgress.read_details`` and
``project_finding_progress`` (``findings/biochemical_feasibility_evidence/investigation_progress.py``) are still in
the old form: ``store._require``, ``store.db`` (``current_revisions``), a spool SQLite connection, and the helpers of
``finding_validity.py`` and ``scientific_findings.py`` (``_assessment_write_extent``, ``_record_roots``,
``_assert_library_write_scope``). The call below stays as written; it fails until that family is carried."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)


def projector(parent):
    """The A110 credit projector of the commission (``finding_progress()`` of the old ``task_projector``)."""
    return ScientificFindingProgress(FindingProgressPolicy(parent['finding_unit']))


def finding_progress(records, parent):
    """The projection of the findings this episode holds: ``credit``, ``retained_finding_count``,
    ``inactive_dependencies`` and ``detail_pages``. ``parent`` is the parent input (or the summary that holds it)."""
    scope = parent['scope']
    known = [row['id'] for row in records.list('assessment', scope)]
    return projector(parent)(records, scope, known_assessment_refs=known,
                             assignment={'scope': scope, 'proposed_annotation_ref': parent['proposed_annotation_ref']})


def credit(summary, records):
    return float(finding_progress(records, summary)['credit'])
