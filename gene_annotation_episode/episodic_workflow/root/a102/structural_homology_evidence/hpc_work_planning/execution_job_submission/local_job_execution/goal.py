"""What this episode is for."""

BINDING_PATH = 'structural_homology_evidence/hpc_work_planning/execution_job_submission/local_job_execution'
GOAL = ('Execute the assigned structural homology job on the assigned local resource until its requested handoff '
        'or outputs exist')
UNIT = 'One exec_command action, on the assigned local resource or in the coordinator workspace'
RESULT = ('The credit of the practical requirements satisfied, the finding that says whether the requested endpoint '
          'was verified, and the saved receipts of the commands run (the qualified handoffs among them)')
