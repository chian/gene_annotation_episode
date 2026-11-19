"""What this episode is for (the old ``LaunchGoal.instructions`` of role ``launch``, text unchanged)."""

BINDING_PATH = 'biochemical_feasibility_evidence/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One commission of a resource launch child (local or HPC) on an explicit permitted resource_id, or the '
        'lookup of the configured resource capabilities')
RESULT = ('The original handoff records of the launched jobs (in custody), whether a usable handoff was received, '
          'and the launches run')
