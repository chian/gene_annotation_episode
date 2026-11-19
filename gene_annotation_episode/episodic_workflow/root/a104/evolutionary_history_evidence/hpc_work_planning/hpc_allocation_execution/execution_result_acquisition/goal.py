"""What this episode is for, carried from the old ``goal.py`` (``ResultsGoal.instructions``) at 97308b94c."""

BINDING_PATH = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
GOAL = ('Acquire the original selected execution results through the original handoff. Choose bounded status or '
        'requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native '
        'paths expose the current resource filesystem: the exact attempt observation does not establish that current '
        'file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The '
        'scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only '
        'actual complete acquisition establishes this endpoint.')
UNIT = ('one result acquisition action: one status observation of the handed-off attempt, or one bounded read of '
        'the requested file windows, with the retained result record')
RESULT = ('the retained result records of the requested windows, whether the requested acquisition is complete, and '
          'the qualification of what the retained bytes show')
