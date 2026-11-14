"""Private goal for A104 prediction."""
from __future__ import annotations




class PredictionGoal:
    def instructions(self, context):
        return ('Iterate on a generalized time/resource model using measured historical cases. '
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
