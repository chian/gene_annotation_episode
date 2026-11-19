"""What this episode is for: the resource prediction of A107 hpc work planning (old role ``hpc_prediction``),
carried from the old ``goal.py`` (``PredictionGoal.instructions``) at 97308b94c. The instruction text the model reads
is composed in ``task.py``; what the model is shown of the episode's state is in ``messages/internal_summary.py``."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
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
UNIT = ('one selected operation on the parent-owned HPC ledger: read retained evidence, refresh the shared timing '
        'history, run one lightweight read-only discovery command, propose a candidate portfolio, observe the PBS '
        'queue once, fit a model on selected measured history, or compare the approved portfolios')
RESULT = ('the credit earned by the measured improvement of the resource model, the finding on the selected model '
          'and the recorded facts the parent selected (the model identity, the accepted obligations and the '
          'received result sources)')
