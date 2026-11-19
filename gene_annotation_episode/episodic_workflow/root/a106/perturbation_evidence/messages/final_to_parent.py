"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding: the
retained findings of the proposed annotation this process holds, the interpretation the model wrote with the
``report`` tool source by source, and the work its children did. The parent may select
``perturbation_evidence_results`` (the closed results of this process, its own first, then those its children of this
process returned) and ``committed_record_refs`` (the scientific records this process and its children of this process
committed, returned in custody). A106 is not an A105/A108 evidence episode: no grader sheet is coupled to its report."""
from method_loop import Field, RecordForm

SOURCE_FORM = RecordForm({
    'source_ref': Field('text', 'The source the statement is about; a source this episode holds'),
    'statement': Field('text', 'What this source itself shows for the assigned question, in its own terms'),
    'qualification': Field('text', "The source's own qualifications: subject, conditions, representation and "
                           'whether its applicability to the target is resolved'),
})
CHILD_FORM = RecordForm({
    'slot': Field('text', 'The child commissioned'),
    'credit': Field('number', "The child's own credit at its closure"),
})
FINDING_FORM = RecordForm({
    'proposed_annotation_ref': Field('text', 'The proposed annotation the retained findings are about'),
    'credit_unit': Field('number', 'The credit of one retained finding in the commissioned axis task'),
    'retained_finding_count': Field('integer', 'The distinct retained scientific findings of the proposed '
                                               'annotation this episode holds'),
    'written': Field('boolean', 'Whether the model wrote an interpretation before the episode ended'),
    'interpretation': Field('text', 'The interpretation of what the examined evidence and the work of the children '
                                    'show for the assigned question; separate sources stay separate'),
    'sources': Field('list', 'One entry per source the interpretation rests on', items=SOURCE_FORM),
    'qualification': Field('text', 'What the interpretation leaves unresolved, including target correspondence'),
    'children': Field('list', 'Each child commissioned, in order', items=CHILD_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What this process established for the assigned question', form=FINDING_FORM),
    'perturbation_evidence_results': Field(
        'list', 'The closed process results of this process and of its children of this process, own first',
        required=False),
    'committed_record_refs': Field(
        'record_refs', 'The scientific records this process and its children of this process committed',
        required=False),
})

NOT_WRITTEN = {'written': False, 'interpretation': 'no interpretation was written before the episode ended',
               'sources': [], 'qualification': 'the sources were not interpreted'}


def process_results(summary, completion):
    """The closed results of this process: its own (selection, proposed annotation, credit, completed actions)
    first, then the results its children of this process returned."""
    own = {'selection': summary['selection'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
           'credit': completion['credit'], 'completed_actions': completion['units_consumed']}
    return [own, *summary['received_process_results']]


def final_to_parent(summary, completion, selection):
    report = summary['report']
    interpretation = NOT_WRITTEN if report is None else {'written': True, **report}
    finding = {'proposed_annotation_ref': summary['proposed_annotation_ref'],
               'credit_unit': summary['task']['credit_unit'],
               'retained_finding_count': summary['investigation_progress']['retained_finding_count'],
               **interpretation,
               'children': [{'slot': child['slot'], 'credit': child['report']['credit']}
                            for child in summary['child_reports']]}
    facts = {'committed_record_refs': lambda: list(summary['committed_record_refs']),
             'perturbation_evidence_results': lambda: process_results(summary, completion)}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name]() for name in selection}}
