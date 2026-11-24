"""The commissions of the three resource children (old ``to_child_api_resource_work_execution.py``,
``to_child_hpc_resource_work_execution.py``, ``to_child_local_resource_work_execution.py``; the three files differed
only in their docstring).

The old request carried: a child goal refining this goal (``objective`` here, chosen by the model in its child
action), a message with ``scope`` and ``initial_report``, the ``job_assignment`` and ``episode_assignment`` (the
launch assignment with this episode's own pinned launch instructions, which the child retains), an optional
``gene_context_evidence`` payload (it was evaluated and discarded), the report contract (now the selection of the
child's declared return fields) and the knowledge inheritance (custody now: every record the child reads is named
in its assignment). Every launch field keeps its old name. The parent writes what each child's own form takes; a
commission the child's form does not admit fails there (nothing is checked here)."""
from episode_runtime import ChildMessage

LAUNCH_FIELDS = ('version', 'job_request', 'immutable_input_versions', 'constraints', 'software_knowledge_refs',
                 'resource_knowledge_refs')
RESOURCE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
# The return fields every commission selects: the old fact sources and the field that carries their records.
BASE_SELECTION = ('execution_handoff', 'execution_handoffs', 'execution_handoff_refs')


def msg_to_child(slot, arguments, summary):
    if slot not in RESOURCE_KINDS:
        raise LookupError('resource_child_slot_not_owned_by_launch:' + slot)
    assignment = summary['assignment']
    commission = {name: assignment[name] for name in LAUNCH_FIELDS}
    commission['resource_selection'] = arguments['resource_selection']
    if assignment['launch_instructions'] is not None:
        commission['launch_instructions'] = assignment['launch_instructions']
    commission.update(scope=summary['scope'], scope_refs=list(summary['scope_refs']),
                      input_refs=list(summary['input_refs']), completion_target=summary['completion_target'])
    selection = tuple(dict.fromkeys([*BASE_SELECTION, *arguments.get('facts', ())]))
    return ChildMessage(objective=arguments['objective'],
                        message={'scope': summary['scope'], 'initial_report': arguments['initial_report']},
                        assignment=commission, selection=selection)
