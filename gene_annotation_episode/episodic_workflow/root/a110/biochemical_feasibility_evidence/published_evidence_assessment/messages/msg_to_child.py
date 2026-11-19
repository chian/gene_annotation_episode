"""The commission of the investigation of the search strategy. Carried from the old
``to_child_evidence_search_strategy_improvement.py`` (it assembled the common request message and the child's
assignment; the request, goal, receipt-binding and contract-declaration machinery is the system's now) and from
``contracts.py`` (the ``strategy_assignment_v1`` of the child).

The child's assignment is ``strategy_assignment_v1``: the records that give the question its context and the
sources earlier searches returned (chosen by the model in the ``ChildCall`` arguments), the scope and the unit of
finding credit of this episode, and the records passed in custody. A pass carries exactly the records named, so
``received_record_refs`` names each prior search source, its artifact records, the sources it derives from (through
``parent_source_refs``, read from the sources this episode holds as the summary shows them) and their artifacts,
and the records that give the question its context. A source this episode does not hold, or an unheld record, fails
when the commission is made: nothing here repairs or checks it."""
from episode_runtime import ChildMessage

VERSION = 'strategy_assignment_v1'
OBJECTIVE = 'Investigate which search approach is productive for the assigned question'
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')


def source_closure(held_sources, source_ref):
    """The source and every source it derives from, each with its artifacts, in order of discovery."""
    refs, pending, seen = [], [source_ref], set()
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        source = held_sources[current]
        refs.append(current)
        refs.extend(source[key] for key in ARTIFACT_KEYS if source.get(key) is not None)
        pending.extend(source.get('parent_source_refs') or ())
    return refs


def unique(refs):
    return list(dict.fromkeys(refs))


def msg_to_child(slot, arguments, summary):
    if slot != 'evidence_search_strategy_improvement':
        raise KeyError(slot)
    received = list(arguments['question_context_refs'])
    for source_ref in arguments['prior_search_refs']:
        received += source_closure(summary['held_sources'], source_ref)
    assignment = {'version': VERSION,
                  'question_context_refs': arguments['question_context_refs'],
                  'prior_search_refs': arguments['prior_search_refs'],
                  'scope': summary['scope'], 'finding_unit': summary['finding_unit'],
                  'received_record_refs': unique(received)}
    if summary['requested_reaction_components']:
        assignment['requested_reaction_components'] = summary['requested_reaction_components']
    return ChildMessage(objective=OBJECTIVE, message={'source_refs': summary['assignment']['source_refs']},
                        assignment=assignment, selection=())
