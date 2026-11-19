"""What this episode is for."""

BINDING_PATH = 'structural_homology_evidence/execution_job_submission/hpc_job_execution'
GOAL = ('Execute the commissioned HPC job on its assigned resource, with shell commands the model writes, until '
        'the requested endpoint (a usable handoff or completed job outputs) is validated, keeping the actual '
        'command receipts')
UNIT = 'one shell command run on the assigned resource or on the coordinator, with its receipt and validations'
RESULT = ('the validated practical completion of the requested endpoint, the command receipts (returned in '
          'custody) and the handoff to the actual job')
