"""The commissions of the three resource children (old ``to_child_api_resource_work_execution.py``,
``to_child_hpc_resource_work_execution.py``, ``to_child_local_resource_work_execution.py``; the three files differed
only in their docstring).

The old request carried: a child goal refining this goal (``objective`` here, chosen by the model in its child
action), a message with ``scope`` and ``initial_report``, the ``job_assignment`` and ``episode_assignment`` (the
launch assignment with this episode's own pinned launch instructions, which the child retains), an optional ``structural_homology_evidence`` payload (it
was evaluated and discarded), the report contract (now the selection of the child's declared return fields) and the
knowledge inheritance (custody now: every record the child reads is named in its assignment). Every launch field
keeps its old name. The parent writes what each child's own form takes; a commission the child's form does not
admit fails there (nothing is checked here)."""
from episode_runtime import ChildMessage

LAUNCH_FIELDS = ('version', 'job_request', 'immutable_input_versions', 'constraints', 'software_knowledge_refs',
                 'resource_knowledge_refs')
# The return fields every commission selects: the old fact sources and the field that carries their records.
BASE_SELECTION = {'launch_api': ('execution_handoff', 'execution_handoffs', 'execution_handoff_refs'),
                  'launch_local': ('execution_handoff', 'execution_handoffs', 'execution_handoff_record_refs'),
                  'launch_hpc': ('execution_handoff', 'execution_handoffs')}


def _launch(summary, arguments):
    assignment = summary['assignment']
    launch = {name: assignment[name] for name in LAUNCH_FIELDS}
    launch['resource_selection'] = arguments['resource_selection']
    if assignment['launch_instructions'] is not None:
        launch['launch_instructions'] = assignment['launch_instructions']
    return launch


def msg_to_child(slot, arguments, summary):
    launch = _launch(summary, arguments)
    if slot == 'launch_api':
        assignment = {**launch, 'scope': summary['scope'], 'scope_refs': list(summary['scope_refs']),
                      'input_refs': list(summary['input_refs']), 'completion_target': summary['completion_target']}
    elif slot == 'launch_local':
        assignment = {**launch, 'adapter_assignment': summary['adapter_assignment'], 'scope': summary['scope'],
                      'record_refs': list(dict.fromkeys([*summary['scope_refs'], *summary['input_refs']]))}
    elif slot == 'launch_hpc':
        assignment = {**launch, 'input_refs': list(summary['input_refs'])}
    else:
        raise LookupError('resource_child_slot_not_owned_by_launch:' + slot)
    selection = tuple(dict.fromkeys([*BASE_SELECTION[slot], *arguments.get('facts', ())]))
    return ChildMessage(objective=arguments['objective'],
                        message={'scope': summary['scope'], 'initial_report': arguments['initial_report']},
                        assignment=assignment, selection=selection)
