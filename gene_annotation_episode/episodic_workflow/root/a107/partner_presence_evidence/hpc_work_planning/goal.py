"""What this episode is for: the HPC work planning of A107 (old role ``hpc``), carried from the old binding's own
``goal``, ``unit`` and ``result`` lines at ``97308b94c`` ('Improve the plan, resource prediction and allocation that
bring the assigned computation to completion on HPC', 'One planning action or commissioned prediction, allocation,
launch, monitor or results child', 'The HPC plan, allocation outcome and execution handoffs') and the opening
sentences of the old ``goal.py`` (``HPCGoal.instructions``). The instruction text the model reads is composed in
``task.py``; what the model is shown of the episode's state is in ``messages/internal_summary.py``."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning'
GOAL = ('Improve the plan, resource prediction and allocation that bring the assigned computation to completion on '
        'HPC. Iterate toward the original accomplishment while balancing expected credit against real elapsed time '
        'and resource demand. Discover the remote environment, design and compare candidate work portfolios, freeze '
        'a plan with its forecast, have that exact plan launched, attach the received handoff, observe the original '
        'allocation and parse and accept its results against the commission\'s own acceptance predicates. The '
        'prediction and the allocation execution can be commissioned as sisters over this episode\'s ledger. Never '
        'fabricate inputs or receipts, never duplicate a submitted attempt and never replace an uncertain '
        'submission. Accepted accomplishment, model improvement and fixed prospective forecast validation are the '
        'only credit components; launch-local credits are not added again.')
UNIT = ('one planning action: one HPC tool (read, compare, history refresh, discovery, candidate proposal, queue '
        'observation, plan, handoff attachment, monitor, scheduled monitor wait, result parsing or allocation '
        'order, or the reading of the owner ledger), or one commission of the prediction, allocation execution, '
        'launch, monitor or results child')
RESULT = ('the HPC plan, allocation outcome and execution handoffs: the owner ledger\'s credit, the selected '
          'prediction model, the original obligations with accepted actual results and the sources holding the '
          'original result bytes')
