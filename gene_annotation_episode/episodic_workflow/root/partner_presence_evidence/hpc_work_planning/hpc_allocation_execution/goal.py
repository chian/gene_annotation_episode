"""What this episode is for, carried from the old ``goal.py`` (``HPCGoal.instructions``) and the old binding's own
``goal``, ``unit`` and ``result`` lines at ``97308b94c`` ('Improve the execution of one planned HPC allocation', 'One
allocation action or commissioned launch, monitor or results child', 'The allocation execution outcome and its
handoffs'). The instruction text the model reads is composed in ``task.py``."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'
GOAL = ('Iterate toward the original accomplishment of the commissioning HPC parent while balancing expected credit '
        'against real elapsed time and resource demand. Execution prepares, launches, monitors and parses the '
        'selected work of one planned HPC allocation: it discovers the resource, proposes and compares work '
        'portfolios, freezes a plan with its forecast, has that exact plan launched, attaches the received handoff, '
        'observes the original allocation and parses and accepts its results against the commission\'s own '
        'acceptance predicates. Never fabricate inputs or receipts, never duplicate a submitted attempt and never '
        'replace an uncertain submission. Accepted accomplishment, model improvement and fixed prospective forecast '
        'validation are the only parent credit components; launch-local credits are not added again.')
UNIT = ('one allocation action: one HPC tool (read, compare, history refresh, discovery, candidate proposal, queue '
        'observation, plan, handoff attachment, monitor, scheduled monitor wait, result parsing or allocation '
        'order), or one commission of the launch, monitor or results child')
RESULT = ('the allocation execution outcome: the owner ledger\'s credit, the selected prediction model, the '
          'original obligations with accepted actual results, and the sources holding the original result bytes')
