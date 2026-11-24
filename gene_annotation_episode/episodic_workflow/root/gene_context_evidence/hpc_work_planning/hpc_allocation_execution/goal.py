"""What this episode is for (carried from the old ``goal.py`` at ``97308b94c``; the rest of its instruction text,
the tool texts and the model-facing protocol are in task.py)."""

BINDING_PATH = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
GOAL = ('Iterate toward the original accomplishment while balancing expected credit against real elapsed time and '
        'resource demand. This is the execution sister of the HPC work planner: it prepares, launches, monitors and '
        'parses the selected work of one commissioned HPC portfolio. Queue and setup costs belong to an allocation, '
        'which should carry enough useful work. Never fabricate inputs or receipts. Accepted accomplishment, model '
        'improvement and fixed prospective forecast validation are the only credit components; launch-local '
        'credits are not added again.')
UNIT = ('one HPC tool action (read retained evidence, compare portfolios, refresh measured history, run one '
        'discovery command, propose a candidate portfolio, observe the queue, freeze a plan, attach the received '
        'handoff, monitor once, wait for a scheduled observation, parse results, order pending units) or one '
        'commission of its launch, monitor or results child')
RESULT = ('the signed measured credit, the selected prediction model, the original obligations whose actual results '
          'were accepted and the retained result records of the original allocation')
