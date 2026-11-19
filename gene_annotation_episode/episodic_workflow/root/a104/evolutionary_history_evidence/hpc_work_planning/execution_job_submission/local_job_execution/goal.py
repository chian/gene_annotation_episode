"""What this episode is for."""

BINDING_PATH = 'evolutionary_history_evidence/hpc_work_planning/execution_job_submission/local_job_execution'
GOAL = ('Run the one practical job assigned on the local resource by writing and executing the shell commands it '
        'needs, until the requested endpoint (a usable handoff or the completed job outputs) is validated')
UNIT = 'One shell command executed on the assigned local resource, with its saved receipt'
RESULT = ('The saved receipts of the commands run, the verified completion of the requested endpoint when it is '
          'reached, and the operational credit earned')
