"""Credit: scientific information progress, one ``finding_unit`` for each distinct current retained typed finding the
episode knows (its own committed assessments). Carried from the old ``credit.py`` (``credit_kind`` 'scientific';
``credit_view`` -> ``services.scientific_credit(context, receiver_selection)``; ``credit_projector`` None). The old
shared ``scientific_credit`` is not read; the library's received-scientific-finding projection is
``findings/biochemical_feasibility_evidence/investigation_progress.py``, called here with the records the episode
holds. Search, reading, navigation, repeated reading and a saved reaction sheet by itself earn nothing (the goal
text: "A search or read earns no scientific credit by itself"). Credit is never bounded, clamped or rescaled here."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    finding_progress_credit)


def credit(summary, records):
    return finding_progress_credit(records, summary['scope'], summary['finding_unit'],
                                   summary['known_assessment_refs'])
