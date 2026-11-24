"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: the controlled features code read from the A103 attachment sheets
this Episode holds (``investigation_finding.FINDING_FORM``: the attribution state, the contribution, pending and
ambiguous counts, the covered fraction, one count per evidence type, one feature record per sheet) with the
references of the sheets and of every record a receiver's credit reads to count them. No model-written text is
returned. A parent may also select ``committed_record_refs``, the records this episode committed with its reasoning
actions (its assessments linking the graded context observations to the proposed annotation)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.investigation_finding import (
    FINDING_FORM)

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the held A103 grading sheets and their references',
                     form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The records this episode committed with its reasoning actions',
                                   required=False),
})


def final_to_parent(summary, completion, selection):
    facts = {'committed_record_refs': list(summary['committed_record_refs'])}
    result = {'credit': completion['credit'], 'finding': summary['finding']}
    for name in selection:
        result[name] = facts[name]
    return result
