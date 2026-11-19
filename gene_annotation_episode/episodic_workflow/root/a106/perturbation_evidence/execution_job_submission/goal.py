"""What this episode is for: the launch of one planned perturbation (BV-BRC AppService) job. The goal text is the old
``OperationalGoal.instructions`` (``goal.py`` at 97308b94c) unchanged; ``UNIT`` and ``RESULT`` are written from the
old ``task.py`` shape (one selected action: a tool read or a child commission), the old ``episode.py`` (the one
role ``launch`` with the one child role ``launch_api``) and ``to_parent.py`` (the handoff sources)."""

BINDING_PATH = 'perturbation_evidence/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child carries out iterative execution in the private loop. '
        'Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One commission of the API launch child on an explicit permitted resource_id, or one lookup of the '
        'configured resource capabilities or of a run-frozen instruction library')
RESULT = ('The original handoff records of the launched API jobs (in custody), the AppService receipts and selected '
          'application outcomes they returned, whether a usable handoff was received, and the launches run')
