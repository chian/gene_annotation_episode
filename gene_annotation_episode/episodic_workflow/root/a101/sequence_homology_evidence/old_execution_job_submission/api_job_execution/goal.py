"""What this episode is for (the old ``goal.py`` at ``97308b94c`` said: carry out the assigned work through the
assigned API service and establish its usable monitoring and results handoff; the instruction text is in task.py)."""

BINDING_PATH = 'sequence_homology_evidence/execution_job_submission/api_job_execution'
GOAL = ('Build the request of the assigned job, submit it once to the assigned public web service through the job '
        'service, and establish its usable monitoring and results handoff')
UNIT = 'One submission of the built request, or one lookup in a run-frozen instruction library'
RESULT = ('The handoff record of the submitted job, in custody; whether the handoff was established; the counts of '
          'submissions made, submissions that failed and lookups')
