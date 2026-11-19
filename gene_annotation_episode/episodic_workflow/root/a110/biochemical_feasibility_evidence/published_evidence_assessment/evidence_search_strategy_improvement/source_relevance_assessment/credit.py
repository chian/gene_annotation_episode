"""Credit: scientific information progress, one ``finding_unit`` for each distinct current retained typed finding
the episode holds (its children's returned findings among them: each child returns its retained assessments and the
records they name). Carried from the old ``credit.py`` (``credit_kind`` 'scientific'; ``credit_view`` ->
``services.scientific_credit(context, receiver_selection)``; ``credit_projector`` None). The old shared
``scientific_credit`` is not read; the library's retained-finding projection is
``findings/biochemical_feasibility_evidence/investigation_progress.py``, called here with the records the episode
holds. Search, reading, navigation, repeated reading and a saved reaction sheet by itself earn nothing (the goal
text: "A search or read earns no scientific credit by itself"). A parent's credit is its own measurement over what
it holds, never a sum of its children's credits. Credit is never bounded, clamped or rescaled here."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    finding_progress_credit)


def credit(summary, records):
    return finding_progress_credit(records, summary['scope'], summary['finding_unit'],
                                   summary['known_assessment_refs'])
