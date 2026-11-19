"""What this episode is for: the execution agent of one assigned job on one HPC resource, carried from the old
``terminal_goal.py`` of ``hpc_job_execution`` (role ``launch_hpc``) at 97308b94c. The instruction text itself is in
``task.py``."""

BINDING_PATH = 'structural_homology_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution'
GOAL = ('Execute the assigned job on the assigned HPC resource: write and run the shell commands that prepare, '
        'submit and observe it, until the assignment\'s requested endpoint (a usable handoff or the completed job '
        'outputs) has validated, saved command receipts')
UNIT = 'one shell command run on the assigned resource (or in the coordinator run directory), with its saved receipt'
RESULT = ('the credit earned by the assignment\'s satisfied requirements, the finding on whether the endpoint is '
          'completed, and the saved command receipts and handoffs in custody')
