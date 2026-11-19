"""The A102 head's return. Always returned: the Episode's credit (the system hands it in ``completion``) and the
finding (the interpretation the head wrote with its ``report`` tool, with what it committed and commissioned).
Selectable: ``structural_homology_evidence_results`` (the head's own process result merged with those its
self-commissioned children returned) and ``committed_record_refs`` (the records its reasoning commits wrote,
returned in custody)."""
from __future__ import annotations

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.construction_records import (
    scientific_digest)

RESULTS_SOURCE = 'structural_homology_evidence_results'
COMMITTED_SOURCE = 'committed_record_refs'

CHILD_FORM = RecordForm({
    'slot': Field('text', 'The child slot that was commissioned'),
    'child_credit': Field('number', "The child's own credit when its controller stopped it"),
})
FINDING_FORM = RecordForm({
    'task': Field('text', 'The continuation task the head was commissioned for (A102:<task>)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the head evaluated', required=False),
    'interpretation_written': Field('boolean', 'Whether the head wrote an interpretation with its report tool'),
    'interpretation': Field('text', 'The latest interpretation the head wrote', required=False),
    'qualification': Field('text', 'The qualification the head wrote with it', required=False),
    'committed_record_count': Field('integer', 'How many records the head\'s reasoning commits wrote'),
    'children': Field('list', 'The children the head commissioned, in order', items=CHILD_FORM),
    'axis_components': Field('record', 'The measured components of the head credit at its closure',
                             required=False),
    'qualification_of_credit': Field('text', 'What the credit does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the A102 head found: the interpretation it wrote, what it committed and '
                     'what it commissioned', form=FINDING_FORM),
    RESULTS_SOURCE: Field('list', 'The head\'s own process result (its selection, task and credit), followed by '
                          'the process results its self-commissioned children returned', required=False),
    COMMITTED_SOURCE: Field('record_refs', 'The records the head\'s reasoning commits wrote, in custody',
                            required=False),
})

CREDIT_QUALIFICATION = ('The credit is the head\'s own projection over the records it holds; it is not annotation '
                        'support and not a sum of its children\'s credits.')


def facts(summary, completion):
    """The facts a parent may select: the process results and the committed records."""
    own = {'selection': summary['selection'], 'selection_sha256': scientific_digest(summary['selection']),
           'task': summary['task_key'], 'credit': completion['credit'],
           'units_consumed': completion['units_consumed'], 'revision_origin': summary['revision_origin']}
    return {RESULTS_SOURCE: [own, *summary['received_process_results']],
            COMMITTED_SOURCE: list(summary['committed_record_refs'])}


def final_to_parent(summary, completion, selection):
    report = summary['report']
    finding = {'task': summary['task_key'], 'interpretation_written': report is not None,
               'committed_record_count': len(summary['committed_record_refs']),
               'children': [{'slot': child['slot'], 'child_credit': child['child_credit']}
                            for child in summary['children']],
               'qualification_of_credit': CREDIT_QUALIFICATION}
    if summary['proposed_annotation_ref']:
        finding['proposed_annotation_ref'] = summary['proposed_annotation_ref'][0]
    if report is not None:
        finding['interpretation'] = report['interpretation']
        finding['qualification'] = report['qualification']
    components = summary['credit_view'].get('axis_components')
    if components is not None:
        finding['axis_components'] = components
    recorded = facts(summary, completion)
    return {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
