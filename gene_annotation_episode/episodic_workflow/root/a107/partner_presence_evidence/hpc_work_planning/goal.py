"""What this episode is for: the HPC work planning of A107 (old role ``hpc``), from the old binding's own ``goal``,
``unit`` and ``result`` lines at ``97308b94c`` ('Improve the plan, resource prediction and allocation that bring the
assigned computation to completion on HPC', 'One planning action or commissioned prediction, allocation, launch,
monitor or results child', 'The HPC plan, allocation outcome and execution handoffs'). The instruction text the model
reads is ``task.INSTRUCTIONS``; what the model is shown of the episode's state is in ``messages/internal_summary.py``."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning'
GOAL = ('Improve the plan, resource prediction and allocation that bring the assigned computation to completion on '
        'HPC, by commissioning the resource-prediction and the allocation-execution sisters over the HPC ledger of '
        'the commission.')
UNIT = ('one planning action: the commission of the prediction or the allocation-execution sister, one HPC tool '
        '(queue observation, comparison, plan, handoff attachment, monitor, scheduled monitor wait, result parsing, '
        'allocation order, candidate proposal, discovery, read, history refresh, or the opening of the ledger), or '
        'one commission of the launch, monitor or results child')
RESULT = ('the credit of the HPC ledger of the commission, what the commission has reached in counts, and the rows '
          'of the ledger in custody')
