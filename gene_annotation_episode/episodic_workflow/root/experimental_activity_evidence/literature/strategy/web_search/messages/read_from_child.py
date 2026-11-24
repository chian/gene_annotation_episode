"""What this episode takes from its page child's admitted return (``page/messages/final_to_parent.py``): its credit, the
per-annotation scores and the controlled features of the subscoring rows of its finding, the references of the persisted
subscoring-sheet states (always selected by ``msg_to_child``), and the source-lead dispositions as counts and references.
Nothing else of the child's work reaches this episode; the state records are held through the ``returned`` receipts and
are handed to the next page in custody. This episode computes nothing from them (OWNER_DECISION 10: the levels above the
page only receive the controlled results)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SHEET_STATE_REFS)


def read_from_child(slot, result, summary, records):
    finding = result['finding']
    return {'slot': slot, 'credit': result['credit'], 'scores': finding['scores'], 'features': finding['features'],
            'sheet_state_refs': list(result[SHEET_STATE_REFS]),
            'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else []}
