"""What this episode is for: the resource-prediction sister of the HPC work planner (old role ``hpc_prediction``),
carried from the old ``goal.py`` (``PredictionGoal.instructions``) at 97308b94c. The instruction text the model
reads is composed in ``task.py``; the goal text below is the old text unchanged except its last sentence, which
states the stop rule of ``yield_estimator.py`` (``AccumulationYieldController``, ``ADAPTIVE_CONTROL``,
``items=None``)."""

BINDING_PATH = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction'
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
        'The episode\'s accumulation controller (adaptive control, no item list) decides when it ends and has no '
        'cost: after 8 units attempted and 4 observed it fits a yield model; a unit is flat when the upper bound '
        'of the expected next marginal credit is at or below gamma = max(one-result resolution, 0.1 x median of '
        'recent productive credits); 4 flat units in a row end the episode.')
UNIT = 'One resource-prediction action'
RESULT = 'The resource prediction'
