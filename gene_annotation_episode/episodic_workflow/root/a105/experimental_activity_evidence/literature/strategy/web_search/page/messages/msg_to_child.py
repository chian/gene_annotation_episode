"""The commissions: what this episode sends each of its three children, carried from the old ``to_child_<role>.py``
(``to_child``: the same-source rule of the child's page) and from the envelope the old model wrote (``version``,
``page``, ``selection``, ``literature_task``, ``proposed_annotation_ref`` and the requested components), under the
old names.

The parent states what each child takes in its own text and schema (``task.py``) and builds the child's assignment
here. Nothing is checked against the child: a selection the child does not declare, an assignment its form does not
admit or a record this episode does not hold fails the run where the child is built (rule 1). The only error raised
here is the old ``to_child`` rule: when the child's page is the parent's source, its artifact and representation
must be the parent's (``literature_reading_<field>_mismatch``).

Selection (rule 5): what the commissioned task needs back. ``literature_source_lead_dispositions`` for a
verified-source-leads task and ``literature_screening_answers`` for a screening answer; the finding (credit and
the controlled features of the sheets, with their references) is always returned, so this episode holds the sheets
and its credit reads them.

Records (decision T5): the commission names every record the child's code reads. The old child inherited the
records its parent had received, through the receipt ledger; the new commission names every record this episode
holds (its passed records and what it produced or was returned)."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    ContractError)

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
LEAF_RECORDS = 'record_refs'   # the selectable field of the chunk leaf's return form
# The field of each of the two table and ordered-reading children's assignments that names the records passed in custody
# (the chunk's own commission is ``chunk_message``).
RECORDS_FIELD = {'table': 'received_record_refs',
                 'report': 'record_refs'}


def child_page(arguments, summary):
    """The old ``to_child`` page rule: the child's page, with the question context and prior deliveries of this
    page; for this episode's own source the artifact and representation are this episode's."""
    parent = summary['page']
    page = {'version': 'page_assignment_v1', **arguments['page'],
            'question_context_refs': parent['question_context_refs'],
            'prior_delivery_refs': parent['prior_delivery_refs']}
    if page['source_ref'] == parent['source_ref']:
        for field in ('artifact_ref', 'representation'):
            if page[field] != parent[field]:
                raise ContractError('literature_reading_' + field + '_mismatch')
    return page


def chunk_message(arguments, summary):
    """The commission of the ``chunk`` leaf: one window of this episode's source and one kind of experiment to extract
    (``chunk/messages/read_from_parent.py``: ``source_ref``, ``passed_refs``, ``offset``, ``limit``, ``experiment_type``,
    ``proposed_annotation_ref``). The leaf declares ``record_refs`` (its immutable leaf records) and no other optional
    field, so ``record_refs`` is the whole selection; this episode groups the records into graders and scores them."""
    child_page(arguments, summary)   # the same-source rule of the page the leaf reads
    window = arguments['selection']
    assignment = {'source_ref': window['source_ref'], 'passed_refs': list(summary['held_record_refs']),
                  'representation': window['representation'],   # the representation the page commissioned for the window
                  'offset': window['offset'], 'limit': window['limit'], 'experiment_type': arguments['experiment_type'],
                  'proposed_annotation_ref': summary['proposed_annotation_ref']}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=(LEAF_RECORDS,))


def msg_to_child(slot, arguments, summary):
    if slot == 'chunk':
        return chunk_message(arguments, summary)
    task = summary['task']
    selection = []
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    if task.get('answer_kind') == 'screening':
        selection.append(SCREENING)
    assignment = {'version': 'reading_assignment_v1', 'page': child_page(arguments, summary),
                  'selection': arguments['selection'], 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], RECORDS_FIELD[slot]: list(summary['held_record_refs'])}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=tuple(selection))
