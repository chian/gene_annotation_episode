"""What this episode is for: the investigation of the evolutionary-history evidence (axis A104) for a target within
its parent's question. The goal text is the old ``ScientificGoal.instructions`` of ``goal.py`` at 97308b94c, the
text used when the selected axis entry is an evidence-axis instruction entry (the only case a controller can be
built for, see ``yield_estimator.py``), unchanged. ``UNIT`` is written from the old ``task.py`` and
``child_commissioning.permitted_common_actions`` (``tool``, ``reason``, ``child``; ``redeliver_report`` is not
carried), ``RESULT`` from the old ``to_parent.py`` (fact sources and facts)."""

BINDING_PATH = 'evolutionary_history_evidence'
GOAL = (
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start "
    'with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and '
    'known context. No initial candidate annotation or publicly searchable name is required. Possible functions can '
    'emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and '
    'thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise '
    'your approach. Selected instructions describe how to investigate; they are not evidence about this target. '
    'Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference '
    'when interpreting evidence. Missing information remains unknown.\n\n'
    'Choose an available tool action, commit a scientific interpretation through the reasoning action, or commission '
    'a scoped child with its own typed return form. Use only the selected actual tools and their supplied resource '
    "instructions; choose callable operands through the declared response contract. Preserve the parent's exact "
    'requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited '
    'information distinct from new findings and completed work distinct from attempts. Return valid partial findings '
    'and specific failures through the requested form.\n\n'
    'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a '
    'different thought pattern and/or tool selection for a new child; it does not change this episode or start that '
    'child. To commission that alternative, copy its selection and revision_origin into a separately selected child '
    "assignment with the child's job, scope, constraints and typed return. Children own their iterative choices. The "
    'configured controller owns continuation. Waiting and unchanged observations do not manufacture progress.')
UNIT = ('one model-selected action: one tool action (a selected actual tool, a process or knowledge lookup, the '
        'preparation of a revised selection, the report of the findings), one committed scientific interpretation, '
        'or the commission of one child')
RESULT = ('the credit of the A104 evolutionary-history credit projection, the typed finding of the investigation, '
          'and the selected facts: the committed records, the process results, the molecular conservation and '
          'phylogeny outcomes')
