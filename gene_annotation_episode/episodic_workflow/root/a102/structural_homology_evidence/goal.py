"""What this episode is for (carried from the old ``goal.py`` and ``scientific_guidance.py`` at ``97308b94c``: the
guidance sentences of the merged A102 axis and the instruction-entry goal text; the instruction composition is in
``task.py``)."""

BINDING_PATH = 'structural_homology_evidence'
GOAL = ("Determine what the supplied target does within the parent's assigned question, scope and constraints, "
        'through comparative and experimental structural evidence. Start with the supplied sequence, selected file '
        'contents or snippets, preserving their boundaries, completeness and known context. No initial candidate '
        'annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be '
        'compared or revised. Preserve the measured subject, conditions, controls, native measurements, uncertainty '
        'and limits of inference when interpreting evidence. Missing information remains unknown. Keep the assigned '
        'evidence axis, thought pattern and selected tools; a different thought pattern or tool selection is '
        'prepared for a new child, not for this episode.')
UNIT = ('One model-selected action: a tool (a process or knowledge lookup, a selected library tool, a typed '
        'reasoning commit, a revision of the thought pattern and tool selection for a new child, a wait for native '
        'job events, or the written interpretation) or one commission of a child (the structural head again, '
        'published evidence assessment, a launch, a results acquisition, HPC work planning or a progress monitor)')
RESULT = ('The head credit, the typed finding (the interpretation it wrote and what it committed and commissioned), '
          'and when selected the process results, the committed records and the protein-structure action facts')
