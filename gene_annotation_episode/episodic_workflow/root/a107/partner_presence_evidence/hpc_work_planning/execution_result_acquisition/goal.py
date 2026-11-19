"""What this episode is for: acquire the results of one already handed-off A107 execution, through its handoff.

Carried from the old ``goal.py`` (``ResultsGoal``) and ``instructions.py`` (``ResultsInstructions.instructions``) at
97308b94c. The goal text is the old instruction text unchanged; the instruction text the model reads (this goal,
then the tool-knowledge and launch-library texts when those libraries are present) is composed in ``task.py``."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition'
GOAL = ('Acquire the original selected execution results through the original handoff. Choose bounded status or '
        'requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native '
        'paths expose the current resource filesystem: the exact attempt observation does not establish that current '
        'file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The '
        'scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only '
        'actual complete acquisition establishes this endpoint.')
UNIT = ('one result acquisition action: one observation of the handed-off attempt, or one bounded read of the '
        'requested result files, with the result record it retained')
RESULT = ('the credit earned by newly acquired bytes of the requested paths, the finding on whether the requested '
          'acquisition is complete and how the retained bytes are qualified, and the retained result records in '
          'custody')
