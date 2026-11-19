"""What this episode is for: the launch of one planned computation. The goal text is the old ``LaunchGoal.instructions``
(``goal.py`` at 97308b94c) unchanged; the old binding's own ``goal``, ``unit`` and ``result`` lines said
'Improve delivery of the assigned computation as submitted jobs with original inputs and handoff receipts', 'One API,
local or HPC route child commissioned for one requested job' and 'Execution handoffs and their receipts'."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One commission of a resource launch child (API, local or HPC) on an explicit permitted resource_id, or the '
        'lookup of the configured resource capabilities')
RESULT = ('The original handoff records of the launched jobs (in custody), whether a usable handoff was received, '
          'and the launches run')
