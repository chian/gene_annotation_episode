"""What this episode is for: acquire the requested results of one already handed-off A107 job, through its handoff."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition'
GOAL = ('Acquire the requested result files of one handed-off job of the partner presence HPC work plan through the '
        'job service and return what was acquired. An earlier episode launched the job and handed it off; this '
        'episode works from that handoff. Fetch the requested result files once the job has ended and retain the '
        'requested bytes. Choose each operation from the actual preceding outcomes. Preserve partial bytes and '
        'native scores. The scientific parent interprets the returned records. Original work, resource and selector '
        'stay fixed. Only actual complete acquisition establishes this endpoint.')
UNIT = ('One status request for the handed-off job, one fetch of its requested result files, or one bounded read of '
        'a fetched file')
RESULT = ('The credit earned by newly acquired bytes of the requested paths, the finding on whether the requested '
          'acquisition is complete with the counts of what was acquired and what was refused, and the references of '
          'the retained results and of the job records written')
