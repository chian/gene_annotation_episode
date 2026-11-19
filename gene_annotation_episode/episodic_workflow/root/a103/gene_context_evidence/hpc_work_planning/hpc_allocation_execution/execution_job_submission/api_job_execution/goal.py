"""What this episode is for."""

BINDING_PATH = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution'
GOAL = ('Carry out the assigned work through the assigned API service using one selected operation each turn. '
        'Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, '
        'service requests, observations or repair from the actual available operations and received outcomes. '
        'Distinguish an immediate returned response from a service job that continues remotely. Preserve the '
        'actual request or job identity and submission uncertainty; a missing reply does not establish that no job '
        'was created. Establish the requested usable monitoring/results handoff from recorded service facts. The '
        'configured controller governs continuation; verified original handoff completion gives exact zero future '
        'credit.')
UNIT = 'One API submission action'
RESULT = 'The API job handoff'
