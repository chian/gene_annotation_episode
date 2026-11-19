"""What this episode is for: the launch of one planned sequence-homology computation. The goal text is the old
``OperationalGoal.instructions`` (``goal.py`` at 97308b94c) without its last sentence (the exact-zero estimator it
described is not carried, README 7b); ``UNIT`` and ``RESULT`` are written from the
old ``task.py`` shape (one selected action: a tool read or a child commission), ``episode.py`` (``child_roles``) and
``to_parent.py`` (the handoff sources)."""

BINDING_PATH = 'sequence_homology_evidence/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach.')
UNIT = ('One commission of a resource launch child (API, local or HPC) on an explicit permitted resource_id, or one '
        'lookup of the configured resource capabilities or of a run-frozen instruction library')
RESULT = ('The original handoff records of the launched jobs (in custody), whether a usable handoff was received, '
          'and the launches run')
