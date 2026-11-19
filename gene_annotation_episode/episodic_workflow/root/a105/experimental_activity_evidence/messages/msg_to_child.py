"""The commissions: what this episode sends each of its two children, carried from the old
``to_child_experimental_activity_evidence.py`` (``prepare_request``: ``binding.prepare_invocation`` /
``prepare_assignment`` with the parent's selection assignment, the inherited proposed annotation, the validated
scope and the required return sources) and ``to_child_published_evidence_assessment.py`` (``prepare_request``:
``binding.prepare_assignment`` of the literature binding over the model's literature assignment, the scope and the
records this episode had received), under the old names.

The parent states what each child takes in its own text and schema (``task.py``) and builds the child's assignment
here. Nothing is checked against the child: a selection the child does not declare, an assignment its form does
not admit or a record this episode does not hold fails the run where the child is built (rule 1). The old checks of
the scope against the parent's (``validate_scope(..., parent_scope=...)``), of the expanded return schema and of the
initial report are not carried.

Records (decision T5): the commission names every record the child's code reads: the records the model named, the
records of the commissioned scope's subjects and the proposed annotation (the old child received its scope's
subjects by itself), and for the literature child every record this episode holds (the old child inherited the
records its parent had received through the receipt ledger; ``reference_subset(known_refs, scope)``).

Selection: the head returns ``committed_record_refs`` under an annotation task. The literature child returns the
typed answer its task needs: ``literature_source_lead_dispositions`` for a verified-source-leads task and
``literature_screening_answers`` for a screening answer."""
from episode_runtime import ChildMessage

COMMITTED = 'committed_record_refs'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def head_message(arguments, summary):
    given, scope = arguments['assignment'], arguments['scope']
    proposed = given.get('proposed_annotation_ref', summary['proposed_annotation_ref'])
    assignment = {**given, 'scope': scope,
                  'evidence_refs': list(dict.fromkeys([*given['evidence_refs'], *scope['subject_refs'],
                                                       *([proposed] if proposed is not None else [])]))}
    if proposed is not None:
        assignment['proposed_annotation_ref'] = proposed
    selection = []
    if summary['proposed_annotation_ref'] is not None:
        selection.append(COMMITTED)
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'scope': scope},
                        assignment=assignment, selection=tuple(selection))

def literature_message(arguments, summary):
    given = arguments['assignment']
    task = given['literature_task']
    selection = []
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    if task.get('answer_kind') == 'screening':
        selection.append(SCREENING)
    assignment = {**given, 'scope': arguments['scope'], 'received_record_refs': list(summary['held_record_refs'])}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'scope': arguments['scope']},
                        assignment=assignment, selection=tuple(selection))

def msg_to_child(slot, arguments, summary):
    if slot == 'experimental_activity_evidence':
        return head_message(arguments, summary)
    if slot == 'published_evidence_assessment':
        return literature_message(arguments, summary)
    raise LookupError('no_such_child_slot:' + slot)
