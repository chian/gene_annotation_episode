"""What this episode is for: the launch of the computations the A107 head selected. The goal text is the old
``LaunchGoal.instructions`` (``goal.py`` at 97308b94c) unchanged; ``UNIT`` and ``RESULT`` are written from the old
``episode.py`` (``child_roles``, ``permitted_common_actions``), ``work_operations.py`` (the one operation
``execution.capabilities``) and ``to_parent.py`` (the handoff sources)."""

BINDING_PATH = 'partner_presence_evidence/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One commission of a resource launch child (API, local or HPC) on an explicit permitted resource_id, one '
        'lookup of the configured resource capabilities or of a run-frozen instruction library, or one reasoning '
        'commit')
RESULT = ('The original handoff records of the launched jobs (in custody), whether a usable handoff was received, '
          'and the launches run')
