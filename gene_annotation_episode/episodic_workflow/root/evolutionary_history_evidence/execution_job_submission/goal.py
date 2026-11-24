"""What this episode is for: the launch of one planned evolutionary-history computation. The goal text is the old
``LaunchGoal.instructions`` (``goal.py`` at 97308b94c) unchanged; ``UNIT`` and ``RESULT`` say what one action is
(the lookup of the configured resources, a library lookup, or the commission of a launch child) and what comes back
(the handoff records)."""

BINDING_PATH = 'evolutionary_history_evidence/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One commission of a resource launch child (API, local or HPC) on an explicit permitted resource_id, or one '
        'lookup of the configured resources or of a run-frozen instruction library')
RESULT = ('The original handoff records of the launched jobs (in custody), whether a usable handoff was received, '
          'and the launches run')
