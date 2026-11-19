"""What this episode is for: improve the time/resource prediction model for the HPC work its parent plans, from
measured historical cases, and compare the candidate portfolios with it.

Carried from the old ``goal.py`` (``PredictionGoal.instructions``, role ``hpc_prediction``) at 97308b94c. The goal
text is the old text unchanged; the instruction text the model reads (this goal, the knowledge and launch-library
texts) is composed in ``task.py``."""

BINDING_PATH = 'structural_homology_evidence/hpc_work_planning/hpc_resource_prediction'
GOAL = ('Iterate on a generalized time/resource model using measured historical cases. '
        'Refresh shared history, inspect support and held-out quality, fit a disjoint training selection, '
        'and compare useful portfolios. Inspect missing capacity, launcher and queue facts with '
        'lightweight discovery; propose executable resource alternatives when the parent has not '
        'supplied them. Preparation and submission belong to the execution sister. '
        'Forecast CPU time and memory demand as well as queue, setup '
        'and work time. Compare node/worker counts, memory capacity, workload parameters and elapsed cost. '
        'The paired execution episode owns Launch, monitoring and parsing. Both sisters use this '
        'parent-owned ledger; preserve model and comparison identities for that sibling. '
        'The fixed reference and validation set cannot change. Model credit is modest measured improvement; '
        'the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. '
        'Return when further model improvement is less useful than running the next worthwhile portfolio.')
UNIT = ('one model-selected action over the parent-owned HPC ledger: a read of retained evidence, a shared-history '
        'refresh, a lightweight discovery command, a candidate portfolio proposal, a queue observation, a model fit '
        'or a portfolio comparison, with the ledger records it wrote')
RESULT = ('the credit earned by measured model improvement (and by the validation scores the parent ledger '
          'attributes to this episode), the finding on the selected model, and the identities the parent selects '
          '(the model, the accepted obligations, the result sources)')
