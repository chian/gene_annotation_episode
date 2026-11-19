"""What this episode is for (carried from the old ``goal.py``: the first paragraph of ``ScientificGoal.instructions``
for an instruction-version evidence axis, the text unchanged; the rest of that text, the A110 axis guidance
(``scientific_guidance``) and the action menu are instruction text and are in ``task.py``).

The old support-metadata variant of ``ScientificGoal.instructions`` (an older, non instruction-version axis entry)
is not carried: such an entry has no credit projector (the old ``credit_projector`` returned ``None`` for it and
``continuation_task`` raised ``scientific_task_credit_not_declared``), so no Episode could run under it."""

BINDING_PATH = 'biochemical_feasibility_evidence'
GOAL = ("Determine what the supplied target does within the parent's assigned question, scope and constraints. "
        'Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, '
        'completeness and known context. No initial candidate annotation or publicly searchable name is required. '
        'Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected '
        'investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and '
        'received child results to choose and revise your approach. Selected instructions describe how to '
        'investigate; they are not evidence about this target. Preserve the measured subject, conditions, '
        'controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing '
        'information remains unknown.')
UNIT = ('one selected action: one scientific tool action, one typed reasoning commit, the written interpretation, '
        'a lookup (the selected entries, the received evidence, the tool catalogue, tool knowledge, a different '
        'thought pattern and tool selection prepared for a new child), or one commission of a launch, monitor, '
        'results, hpc, literature or recursive A110 child')
RESULT = ('the credit of the retained distinct scientific findings this episode holds, the finding that states '
          'what was committed, interpreted and returned by each child, and the records the reasoning commits and '
          'the children produced')
