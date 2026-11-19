"""What this episode is for.

Carried from the old ``goal.py`` (``OperationalGoal.instructions``): the old text named the assigned service; the
service is a field of the assignment, so ``task.py`` writes the same text with the actual service."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution'
GOAL = ('Carry out the assigned work through the assigned API service using one selected operation each turn. '
        'Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, '
        'service requests, observations or repair from the actual available operations and received outcomes. '
        'Distinguish an immediate returned response from a service job that continues remotely. Preserve the '
        'actual request or job identity and submission uncertainty; a missing reply does not establish that no job '
        'was created. Establish the requested usable monitoring/results handoff from recorded service facts. The '
        'configured controller governs continuation; verified original handoff completion gives exact zero future '
        'credit.')
UNIT = 'One API service action'
RESULT = 'The retained API handoff and record references'
