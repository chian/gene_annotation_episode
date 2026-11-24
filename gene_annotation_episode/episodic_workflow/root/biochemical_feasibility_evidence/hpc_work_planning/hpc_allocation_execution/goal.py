"""What this episode is for (carried from the old ``goal.py`` at ``97308b94c``; its instruction text is in task.py)."""

BINDING_PATH = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution'
GOAL = ('Turn the commissioning HPC parent\'s commission into work actually done on one real allocation, iterating '
        'toward the original accomplishment while balancing expected credit against real elapsed time and resource '
        'demand: prepare candidate portfolios, freeze a plan with its forecast, have the job launched, attach the '
        'received handoff, observe the job and parse and accept its results against the commission\'s own '
        'acceptance predicates. Never fabricate inputs or receipts and never duplicate a submitted attempt. '
        'Accepted accomplishment, model improvement and fixed prospective forecast validation are the only parent '
        'credit components; launch-local credits are not added again.')
UNIT = ('one model-selected action: one HPC tool (read, compare, history refresh, discovery, candidate proposal, '
        'queue observation, plan, handoff attachment, monitor, scheduled monitor wait, result parsing or '
        'allocation order), or one commission of the launch, monitor or result-acquisition child')
RESULT = ('the owner ledger\'s credit, the selected prediction model, the original obligations with accepted actual '
          'results, and the sources holding the original result bytes')
