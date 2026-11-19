"""What this episode is for."""

BINDING_PATH = 'partner_presence_evidence/execution_result_acquisition'
GOAL = ('Acquire the original selected execution results through the original handoff. Choose bounded status or '
        'requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native '
        'paths expose the current resource filesystem: the exact attempt observation does not establish that current '
        'file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The '
        'scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only '
        'actual complete acquisition establishes this endpoint.')
UNIT = ('One status observation of the handed-off attempt, or one bounded read of the requested result windows, '
        'or one wait on the job service')
RESULT = ('The retained result acquisitions of the handed-off job with their byte windows, the handoff, whether '
          'the requested acquisition is complete, and any selected native result family facts')
