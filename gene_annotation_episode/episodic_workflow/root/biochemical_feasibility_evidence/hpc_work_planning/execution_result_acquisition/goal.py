"""What this episode is for: acquire the requested result files of one handed-off A110 job through the job
service."""

BINDING_PATH = 'biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition'
GOAL = ('Acquire the selected results of one handed-off biochemical feasibility job through the job service and '
        'return what was acquired. An earlier episode launched the job and handed it off; this episode works from '
        'that handoff. Fetch the requested result files once the job has ended and retain the requested bytes. '
        'Choose each operation from the actual preceding outcomes. Preserve partial bytes and native scores. The '
        'scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only '
        'actual complete acquisition establishes this endpoint.')
UNIT = ('One selected acquisition operation: one status request for the handed-off job, one fetch of its requested '
        'result files with the first window of every requested path, or one window of a fetched file inside the '
        'requested path and interval')
RESULT = ('The credit earned by newly received selector byte positions, the finding on what was acquired and what '
          'was refused, the acquired result records with their artifacts, and the job records written')
