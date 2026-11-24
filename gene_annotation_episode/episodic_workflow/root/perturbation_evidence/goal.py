"""What this episode is for: the A106 evidence axis (experimental contribution through perturbation and restoration)
investigated as one recursive scientific process. Carried from the old ``goal.py`` (``ScientificGoal.instructions``
at 97308b94c): the old method chose one of two texts by the ``entry_version`` of the selected evidence-axis entry of
the process library. Both texts stay, under the names ``GOAL`` (the published instruction entry) and
``EVIDENCE_AXIS_GOAL`` (every other entry); ``task.decide`` chooses between them from the entry the commission
selected. The old text offered ``wait`` and ``redeliver_report`` among the actions; neither exists any more (a child
completes inside the unit that commissioned it) and the two phrases are not carried. The first line of the old
method, ``validate_context``, checked the commission and is not carried."""

BINDING_PATH = 'perturbation_evidence'

GOAL = ("Determine what the supplied target does within the parent's assigned question, scope and constraints. "
        'Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, '
        'completeness and known context. No initial candidate annotation or publicly searchable name is required. '
        'Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected '
        'investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received '
        'child results to choose and revise your approach. Selected instructions describe how to investigate; they '
        'are not evidence about this target. Preserve the measured subject, conditions, controls, native '
        'measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains '
        'unknown.\n\n'
        'Choose an available tool action, commit a scientific interpretation through the reasoning action, or '
        'commission a scoped child with its own typed return form. Use only the selected actual tools and their '
        'supplied resource instructions; choose callable operands through the declared response contract. Preserve '
        "the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. "
        'Keep inherited information distinct from new findings and completed work distinct from attempts. Return '
        'valid partial findings and specific failures through the requested form.\n\n'
        'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise '
        'prepares a different thought pattern and/or tool selection for a new child; it does not change this episode '
        'or start that child. To commission that alternative, copy its selection and revision_origin into a '
        "separately selected child assignment with the child's job, scope, constraints and typed return. Children "
        'own their iterative choices. The accumulation yield controller (ADAPTIVE_CONTROL, no item count, no cost) '
        'owns continuation: after at least 8 units attempted and 4 observed it fits nano-graphrag\'s yield model; a '
        'unit is flat when the upper bound of its expected next marginal (hypervolume) credit is at or below the '
        'adaptive threshold, max(one-result resolution, 0.1 x median of recent productive credits), and the episode '
        'stops after 4 flat units in a row. Unchanged observations do not '
        'manufacture progress.')

EVIDENCE_AXIS_GOAL = (
    'Investigate the parent\'s assigned scientific problem iteratively in the shared Episode loop. The selected '
    'scientific support proposition and operands define the support problem; the thought pattern supplies '
    'alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. '
    'Choose your own actions using actual outcomes and received child forms. The selection is no prescribed '
    'sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific '
    'evidence about this target. Inspect actual source subjects, conditions and target applicability before '
    'interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy\'s '
    'kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this '
    'reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself earns '
    'no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. Keep '
    "the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields or "
    'scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned '
    'scientific support, thought pattern and selected tool set throughout this episode. Explicit process.revise '
    'prepares a selection for a new child; a separately selected child commission starts that child with its own '
    'job, scope, constraints and typed return form. Preparation changes no current process and starts no child. '
    "Copy both result.selection and revision_origin into that child's assignment to identify it as an alternative "
    'approach. Request the recorded perturbation_evidence_results source in child returns when their process '
    'relationships and existing closed credit/yield are needed for steering. Only retrieved actual tools are '
    'available; their descriptions do not grant execution. The accumulation yield controller (ADAPTIVE_CONTROL, no '
    'item count, no cost) owns continuation: after at least 8 units attempted and 4 observed it fits '
    'nano-graphrag\'s yield model; a unit is flat when the upper bound of its expected next marginal (hypervolume) '
    'credit is at or below the adaptive threshold, max(one-result resolution, 0.1 x median of recent productive '
    'credits), and the episode stops after 4 flat units in a row.')

UNIT = ('One model-selected unit: a tool call (a lookup in the process library, the tool library or the tool '
        'knowledge, the preparation of a revised process selection, one selected actual tool, a reasoning commit or '
        'the report of the interpretation) or the commission of a child (a published evidence assessment, the launch '
        'of a planned execution, one progress check of a launched job, the acquisition of its results, or a child '
        'of this same process)')

RESULT = ("The credit of the retained scientific findings of the commissioned axis task, the typed finding of what "
          'this process established (retained findings, the interpretation it wrote, the work its children did), '
          'the closed process results of this process and its children, and the records it committed')
