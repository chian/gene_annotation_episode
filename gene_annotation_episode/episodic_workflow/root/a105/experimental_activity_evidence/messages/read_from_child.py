"""What this episode takes from a child's admitted return (both children declare the page-level return form, see
``literature_finding_forms.sheet_return_fields``): its credit, the per-annotation scores and the controlled features of the
subscoring rows of its finding, the references of the persisted subscoring-sheet states (always selected by
``msg_to_child``); from the literature child the selected answers as counts and references; from the head child the
selected ``committed_record_refs``. This episode computes nothing from the scores or the features (OWNER_DECISION 10: the
levels above the page only receive the controlled results). The state records are held through the ``returned`` receipts
and are handed to the next run in custody."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SHEET_STATE_REFS)

COMMITTED = 'committed_record_refs'


def read_from_child(slot, result, summary, records):
    if slot not in ('experimental_activity_evidence', 'literature'):
        raise LookupError('no_such_child_slot:' + slot)
    finding = result['finding']
    report = {'slot': slot, 'credit': result['credit'], 'scores': finding['scores'], 'features': finding['features'],
              'sheet_state_refs': list(result[SHEET_STATE_REFS]),
              'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else []}
    report['committed_record_refs'] = result[COMMITTED] if COMMITTED in result else []
    return report
