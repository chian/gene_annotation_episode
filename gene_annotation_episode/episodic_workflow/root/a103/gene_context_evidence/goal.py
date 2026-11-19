"""What this episode is for: the A103 head, the recursive gene-context evidence role. The goal text is the old
``goal.py`` at 97308b94c, ``ScientificGoal.instructions`` for a published-instruction axis entry (the A103 guidance of
the old ``scientific_guidance.py`` followed by the investigation text), unchanged except for the one clause that
named the removed ``wait`` action. ``UNIT`` and ``RESULT`` are written from the old ``task.py`` shape (one selected
action: a tool, a reasoning commit or a child commission) and ``to_parent.py`` (the report)."""

BINDING_PATH = 'gene_context_evidence'
GOAL = ('A103 owns gene-context work. Scientific descendants remain A103. '
        'Use available shared operations to send the immediate parent specific missing operands or '
        'useful received evidence; that parent chooses within its own options or relays the need upward. '
        'Context measurements are automatically graded at publication/receipt. '
        'Each target/locus, neighboring component, domain and regulatory footprint retains its own attribution. '
        'An identity score, source label or fetched record alone is not an association score. Unknown flanks '
        'and unevaluated detections are not absence. Preserve optional modules, paralogs and related sampling. '
        'Use one small local job at a time, current resource_context and admission feedback. '
        'Root/owner credit comes from actual measured context, not narrative judgments.\n\n'
        "Determine what the supplied target does within the parent's assigned question, scope and constraints. "
        'Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, '
        'completeness and known context. No initial candidate annotation or publicly searchable name is required. '
        'Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected '
        'investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and '
        'received child results to choose and revise your approach. Selected instructions describe how to '
        'investigate; they are not evidence about this target. Preserve the measured subject, conditions, '
        'controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing '
        'information remains unknown.\n\n'
        'Choose an available tool action, commit a scientific interpretation through the reasoning action, or '
        'commission a scoped child with its own typed return form. Use only the selected actual tools and their '
        'supplied resource instructions; choose callable operands through the declared response contract. '
        "Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from "
        'actual records. Keep inherited information distinct from new findings and completed work distinct from '
        'attempts. Return valid partial findings and specific failures through the requested form.\n\n'
        'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise '
        'prepares a different thought pattern and/or tool selection for a new child; it does not change this '
        'episode or start that child. To commission that alternative, copy its selection and revision_origin into '
        "a separately selected child assignment with the child's job, scope, constraints and typed return. "
        'Children own their iterative choices. The configured controller owns continuation. Unchanged '
        'observations do not manufacture progress.')
UNIT = ('One selected action: a lookup, a tool operation, the grading of held measurements, a reasoning commit or one '
        'child commission')
RESULT = ("The gene-context finding (the controlled features code reads from the held A103 grading sheets, with "
          "the sheets' references), its credit, and the records this episode committed")
