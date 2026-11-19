"""What this episode is for (carried from the old ``goal.py`` at ``97308b94c``; its instruction text is in task.py)."""

BINDING_PATH = 'gene_context_evidence/execution_job_submission/api_job_execution'
GOAL = ('Carry out the assigned work through the assigned API service and establish its usable monitoring and '
        'results handoff')
UNIT = 'One selected service operation, or one wait on a service job that continues remotely'
RESULT = ('The handoff facts of the assigned service request or job: its identity, whether a usable handoff was '
          'established, and the references that hold it')
