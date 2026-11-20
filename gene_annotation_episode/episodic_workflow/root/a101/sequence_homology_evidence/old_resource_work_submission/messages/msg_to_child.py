"""The commission of one resource child (carried from ``to_child_api_resource_work_execution.py``,
``to_child_hpc_resource_work_execution.py`` and ``to_child_local_resource_work_execution.py``,
``prepare_commission``; the three differed only in role, binding path and the HPC rule).

The old envelope carried the child's scope, the parent-written return form with its report declaration, the initial
report values, the materialised launch instructions, the selected assignment and the old runner's bookkeeping
(binding lookup, allowed-role test, ``child_binding_path_conflict``, ``prepare_assignment`` with an operation key:
machinery, not carried). What this episode states, in the words of each child's own assignment form:

* the assignment fields it fixes and copies unchanged from its own commission (``version``, ``job_request``,
  ``immutable_input_versions``, ``constraints``, the knowledge references), the ``resource_selection`` and
  ``launch_instructions`` the model chose (``arguments``), and, where the child declares them, the records the
  child's code reads (``scope_refs`` and ``input_refs`` to the API child, ``input_refs`` to the HPC child; the local
  child declares no record field) and the credit one handoff earns (the API child's ``completion_target``);
* the subject ``scope`` in the message (the local child reads it there; the API child's form carries it in the
  assignment);
* the selectable return fields it wants: every old fact source the child declares (``execution_handoff``,
  ``execution_handoffs``) and, where declared, ``adapter_facts`` and the API child's ``execution_handoff_refs``.
  The old rule that an HPC return form contain ``execution_handoff_refs`` is met by the HPC child's required
  ``handoff_refs``: it is always returned and cannot be selected.

A commission the child does not admit fails (rule 1); nothing is checked here. The slots keep the old role names."""
from episode_runtime import ChildMessage

SELECTIONS = {'launch_api': ('execution_handoff', 'execution_handoffs', 'adapter_facts', 'execution_handoff_refs'),
              'launch_hpc': ('execution_handoff', 'execution_handoffs'),
              'launch_local': ('execution_handoff', 'execution_handoffs', 'adapter_facts')}
FIXED = ('version', 'job_request', 'immutable_input_versions', 'constraints', 'software_knowledge_refs',
         'resource_knowledge_refs')
KINDS = {'launch_api': 'API', 'launch_hpc': 'HPC', 'launch_local': 'local'}


def msg_to_child(slot, arguments, summary):
    selection = SELECTIONS[slot]
    assignment = {name: summary['assignment'][name] for name in FIXED}
    assignment['resource_selection'] = arguments['resource_selection']
    if arguments['launch_instructions'] is not None:
        assignment['launch_instructions'] = arguments['launch_instructions']
    if slot == 'launch_api':
        assignment.update(scope=summary['scope'], scope_refs=list(summary['scope_refs']),
                          input_refs=list(summary['input_refs']), completion_target=summary['completion_target'])
    if slot == 'launch_hpc':
        assignment['input_refs'] = list(summary['input_refs'])
    resource_id = arguments['resource_selection']['resource_id']
    return ChildMessage(objective=('Carry out the assigned job on the selected ' + KINDS[slot] + ' resource '
                                   + resource_id + ' and return its usable execution handoff'),
                        message={'scope': summary['scope']}, assignment=assignment, selection=selection)
