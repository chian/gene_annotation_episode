"""What this episode is for.

Carried from the old ``instructions.py`` (``APIInstructions.instructions``), ``binding_roles.py`` (role ``launch_api``)
and ``episode.py`` (``binding_path``, the commissioning parent ``execution_job_submission``)."""

BINDING_PATH = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution'
GOAL = ('Carry out one assigned job through a remote web service (NCBI BLAST, BV-BRC, EBI HMMER) and establish the '
        'requested usable monitoring/results handoff for it from recorded service facts')
UNIT = ('one selected operation of the assigned API service: preparation, a service request, an observation or a '
        'repair')
RESULT = ('the original handoff of the service job (its record in custody), the result records actually acquired, '
          'whether the original handoff was established, and the submission uncertainty that remains')
