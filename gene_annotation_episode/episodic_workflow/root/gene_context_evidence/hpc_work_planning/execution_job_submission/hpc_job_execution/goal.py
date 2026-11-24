"""What this episode is for."""

BINDING_PATH = 'gene_context_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution'
GOAL = ('Run the commissioned HPC job on its assigned resource through the shell commands the model writes, until '
        'the commission\'s endpoint (a usable handoff or completed job outputs) is reached and validated')
UNIT = 'One shell command run on the assigned HPC resource or on the local coordinator'
RESULT = ('The HPC job handoff: the receipts of the commands run, whether the requested endpoint was reached and '
          'the credit earned')
