"""What this episode is for."""

BINDING_PATH = 'evolutionary_history_evidence/execution_job_submission/hpc_job_execution'
GOAL = ('Run the assigned job on the assigned HPC resource by writing and running shell commands, one per turn, '
        'until the original endpoint predicates of the assignment are validated')
UNIT = 'one exec_command run on the assigned resource (or on the coordinator) and its saved action receipt'
RESULT = ('the credit earned by the assignment\'s satisfied requirements, the finding on the job and its '
          'completion, and the selected facts about the saved command receipts and handoffs')
