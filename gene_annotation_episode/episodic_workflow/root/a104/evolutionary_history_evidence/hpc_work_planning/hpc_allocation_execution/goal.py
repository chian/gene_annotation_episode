"""What this episode is for (old role ``hpc_execution``, the execution sister of ``hpc_work_planning``)."""

BINDING_PATH = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution'
GOAL = ('Iterate toward the original accomplishment while balancing expected credit against real elapsed time and '
        'resource demand. Execution prepares, launches, monitors and parses the selected work of the HPC '
        'parent\'s ledger: it compares the approved portfolios on the current model and queue observations, freezes '
        'one useful portfolio with its forecasts, commissions the launch of that frozen plan, binds the received '
        'handoff to it, observes the original job and its progress, revises the conditional forecasts, and parses '
        'the original results against the caller\'s acceptance predicates. Queue and setup costs belong to an '
        'allocation, which should carry enough useful work. Never fabricate inputs or receipts. Never replace an '
        'uncertain submission. Accepted accomplishment, model improvement and fixed prospective forecast validation '
        'are the only credit components of the ledger; launch-local credits are not added again.')
UNIT = ('one operation on the HPC ledger of the original parent (read, compare, refresh history, discover, '
        'propose a portfolio, observe the queue, plan, hand off, monitor, wait for a monitor, parse results, '
        'order units), or one commission of the launch, monitor or results child')
RESULT = ('the signed measured credit of the ledger, the immutable prediction model identity, the original '
          'obligations with accepted actual results, and the sources that hold the original result bytes')
