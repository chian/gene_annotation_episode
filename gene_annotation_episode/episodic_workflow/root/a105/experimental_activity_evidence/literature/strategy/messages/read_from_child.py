"""What this episode takes from its web-search child's admitted return (``web_search/messages/final_to_parent.py``): its
credit, the per-annotation scores and the controlled features of the subscoring rows of its finding, the references of the
persisted subscoring-sheet states (always selected by ``msg_to_child``), and the selected answers as counts and references.
Nothing else of the child's work reaches this episode, and it computes nothing from the scores or the features (OWNER_DECISION
10: the levels above the page only receive the controlled results). The state records are held through the ``returned``
receipts and are handed to the next run in custody."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING, SHEET_STATE_REFS)


def read_from_child(slot, result, summary, records):
    finding = result['finding']
    return {'slot': slot, 'credit': result['credit'], 'scores': finding['scores'], 'features': finding['features'],
            'sheet_state_refs': list(result[SHEET_STATE_REFS]),
            'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else [],
            'screening_covered': result[SCREENING]['commissioned_spans_covered'] if SCREENING in result else False}
