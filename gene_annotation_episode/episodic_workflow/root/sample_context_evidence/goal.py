"""What this episode is for: one A108 (organism and sample context) investigation of a target, from a
parent-selected evidence axis A108, thought pattern and selected tools. Carried from the old ``goal.py``
(``ScientificGoal.instructions``) at 97308b94c.

``GOAL`` is the old text for an axis entry that is an instruction entry (``evidence_axis_instruction``), which
replaced the default instructions completely. The old text said the head could also "wait for selected pending work"
and named ``process.revise``; the wait action does not exist (README 3b) and the tool is ``process_revise`` here. The
other old text (an axis entry that is an evidence-axis entry, appended to the default instructions) is
``EVIDENCE_AXIS_INSTRUCTIONS`` in ``task.py``, which chooses between them by the entry the selection names."""

BINDING_PATH = 'sample_context_evidence'
GOAL = (
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start "
    "with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and "
    "known context. No initial candidate annotation or publicly searchable name is required. Possible functions can "
    "emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions "
    "and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and "
    "revise your approach. Selected instructions describe how to investigate; they are not evidence about this "
    "target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of "
    "inference when interpreting evidence. Missing information remains unknown.\n\n"
    "Choose an available tool action, commit a scientific interpretation through the reasoning action, or "
    "commission a scoped child with its own typed return fields. Use only the selected actual tools and their "
    "supplied resource instructions; choose callable operands through the declared response contract. Preserve the "
    "parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep "
    "inherited information distinct from new findings and completed work distinct from attempts. Return valid "
    "partial findings and specific failures through the requested fields.\n\n"
    "Keep the assigned evidence axis, thought pattern and selected tools for this episode. process_revise prepares "
    "a different thought pattern and/or tool selection for a new child; it does not change this episode or start "
    "that child. To commission that alternative, copy its selection and revision_origin into a separately selected "
    "child commission with the child's job, scope and return fields. Children own their iterative choices. The "
    "configured controller owns continuation. Unchanged observations do not manufacture progress.")
UNIT = ('one model-selected tool call (a lookup of the process library or tool knowledge, an access or acquisition '
        'tool of the selection, a reasoning commit coupled with its contextual grading sheets, the preparation of a '
        'revised selection, or the report of the interpretation), or one child commission (a narrower A108 '
        'sample-context investigation, or the assessment of published evidence)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (own and the '
          "children's), with the sheet and graded assessment references, and the commissioned task's answers as "
          'counts and references')
