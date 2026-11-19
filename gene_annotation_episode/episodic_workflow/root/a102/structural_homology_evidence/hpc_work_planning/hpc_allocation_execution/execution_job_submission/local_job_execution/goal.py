"""What this episode is for."""

BINDING_PATH = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution'
GOAL = ('Execute the one assigned job on the assigned local resource: write and run the shell commands that '
        'prepare and run it, and reach the assignment\'s requested endpoint (a usable handoff or the completed '
        'job outputs)')
UNIT = 'one shell command (exec_command) run on the assigned local resource or on the local coordinator'
RESULT = ('the practical credit, the handoff finding, and the saved command receipts (with their digests and '
          'completion state) returned in custody')
