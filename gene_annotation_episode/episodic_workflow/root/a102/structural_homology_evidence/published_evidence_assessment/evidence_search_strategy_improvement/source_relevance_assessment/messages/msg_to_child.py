"""The commission of one ``literature_page`` child: the page the model chose (one source of this episode's custody,
its representation and artifact, the question context and the earlier deliveries), the commissioned task, the
proposed annotation, the scope and every record this episode names for the child, and the typed answers this
commission selects.

Carried from the old ``to_child_source_evidence_examination.assemble_request`` (child goal, scope, initial report,
assignment, knowledge inheritance). The old goal is now a fixed ``objective`` per slot and the message is empty; the scope is a field of the child's
assignment; ``knowledge_inheritance`` is the system's custody. The records named are the source, its artifacts, the
sources it derives from that this episode holds (``summary['literature_source_custody']``), the question context,
the earlier deliveries and the proposed annotation. A wrong commission raises and fails the run."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'examine_selected_source'
PAGE_KEYS = ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
             'prior_delivery_refs')


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_page':
        raise KeyError(slot)
    task, page = summary['task'], arguments['page']
    custody = {entry['source_ref']: entry for entry in summary['literature_source_custody']}[page['source_ref']]
    passed = [*custody['passed_record_refs'], *page['question_context_refs'], *page['prior_delivery_refs'],
              page['artifact_ref'], summary['proposed_annotation_ref']]
    assignment = {'version': 'page_assignment_v1', **{key: page[key] for key in PAGE_KEYS if key != 'version'},
                  'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], 'received_record_refs': list(dict.fromkeys(passed))}
    selection = (LEADS,) if task['kind'] == 'verified_source_leads' else (
        (SCREENING,) if task['answer_kind'] == 'screening' else ())
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=selection)
