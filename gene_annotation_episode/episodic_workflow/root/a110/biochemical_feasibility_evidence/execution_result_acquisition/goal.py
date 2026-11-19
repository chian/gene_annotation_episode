"""What this episode is for: the acquisition of the original selected execution results through the original
handoff (old role ``results``), carried from the old ``instructions.py`` (``ResultsInstructions.instructions``)
at 97308b94c. The model reads the same text as its instructions (``task.py``)."""

BINDING_PATH = 'biochemical_feasibility_evidence/execution_result_acquisition'
GOAL = ('Acquire the original selected execution results through the original handoff. Choose bounded status or '
        'requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. '
        'Native paths expose the current resource filesystem: the exact attempt observation does not establish '
        'that current file bytes were produced by that attempt. Separate read windows are not an atomic file '
        'snapshot. The scientific parent interprets the returned records. Original work, resource and selector '
        'stay fixed. Only actual complete acquisition establishes this endpoint.')
UNIT = ('one selected acquisition action: observe the handed-off attempt once, collect the first windows of every '
        'requested path, or read one window inside the requested path and interval')
RESULT = ('the credit earned by newly received selector byte positions, the finding on what was acquired, and the '
          'acquired result records (with their artifacts) the parent selected')
