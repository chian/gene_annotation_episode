"""The return (A105 scoring paradigm, OWNER_DECISION 10: the levels above the page only receive and pass up controlled
results). Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
investigation_finding): the per-annotation scores (target_id, status, support, opposition, net, scalar) and the controlled
row features (sheet_ref, evidence_type, assertion_ref, target_id, experiments, independent_groups, relative_deviation, net,
support, opposition, status) of the latest child return that changed the sheet (the whole sheet as it stands), as numbers,
counts and vocabulary values; nothing is combined or recomputed here. The row resolution is the credit channel and is not part of the
finding (the contract keeps the score and credit channels apart; the credit goes up as ``credit``). Selectable:
``sheet_state_refs`` (the persisted sheet states of the latest child return, or the states this episode was given when it
commissioned none, handed to the next run) and ``committed_record_refs`` (the assessments the head committed, the
children's committed records and the sheet states)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    SHEET_FINDING_FORM, SHEET_STATE_REFS)

COMMITTED = 'committed_record_refs'
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The per-annotation scores and the controlled features of the subscoring rows of the A105 '
                     'experimental-activity investigation', form=SHEET_FINDING_FORM),
    SHEET_STATE_REFS: Field('record_refs', 'The persisted subscoring-sheet states (the whole sheet as it stands after '
                            'the latest child return)', required=False),
    COMMITTED: Field('record_refs', 'The assessments this episode committed, the records its children committed and '
                     'the sheet states', required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'scores': list(summary['scores']), 'features': list(summary['features'])}}
    if SHEET_STATE_REFS in selection:
        result[SHEET_STATE_REFS] = list(summary['sheet_state_refs'])
    if COMMITTED in selection:
        result[COMMITTED] = summary['committed_record_refs']
    return result
