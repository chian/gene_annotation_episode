"""What this episode is for."""

BINDING_PATH = 'partner_presence_evidence/execution_job_submission/local_job_execution'
GOAL = ('Execute the assigned local job: write and run the shell commands that bring about the requested endpoint '
        '(a usable handoff or the completed job outputs) on the assigned local resource, and retain the receipt of '
        'each command')
UNIT = 'One exec_command action on the assigned local resource'
RESULT = ('The saved command receipts, the handoff of the job when one was made, and whether the requested endpoint '
          'was verified')
