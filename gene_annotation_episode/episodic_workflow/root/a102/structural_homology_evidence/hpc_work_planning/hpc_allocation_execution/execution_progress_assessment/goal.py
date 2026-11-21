"""What this episode is for: the monitor of one assigned execution target (old role ``monitor``), carried from the
old ``goal.py`` (``MonitorGoal.instructions`` and ``planning_context``) at 97308b94c. The instruction text the
model reads is composed in ``task.py``; the goal summary the model is shown (``planning_context``) is in
``messages/internal_summary.py``."""

BINDING_PATH = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment'
GOAL = ('Investigate which further exposed progress information is useful for the assigned target. Use actual '
        'status, measured quantities, committed references and source-bound logs. Liveness establishes process '
        'presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information '
        'stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly '
        'commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence '
        'or depth is prescribed. Return your declared form at your closure even while the target remains active. '
        'Do not report private reasoning, intentions or unrestricted findings. Recorded facts use saved delivered '
        'observations; closure does not poll or compose another report with a model. The monitor\'s '
        'information-credit projector feeds the accumulation controller (adaptive control, no item count), which '
        'takes no cost and governs continuation: after at least 8 units attempted and 4 observed, a unit is flat '
        'when the upper bound of the expected next marginal credit is at or below its adaptive threshold (the '
        'larger of one result\'s resolution and 0.1 x the median of recent productive credits), and it stops '
        'after 4 flat units in a row. Repeated observation identities '
        'and read timestamps alone earn no new information.')
UNIT = ('one selected action: one progress tool (observe the assigned target, read a delivered observation, read '
        'one retained log window), or one commissioned monitor for an exposed direct dependency of the target')
RESULT = ('the credit earned by newly informative received progress snapshots, the finding on what was observed of '
          'the assigned target, and the recorded monitoring facts the parent selected')
