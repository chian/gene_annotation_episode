"""What this episode is for: the A107 investigation of partner presence evidence. The goal text is the old
``goal.py`` text for an instruction-version evidence axis (``ScientificGoal.instructions`` at 97308b94c) without its
long instruction paragraphs, which are in ``task.py``; ``UNIT`` and ``RESULT`` are written from the old binding's
actions (``child_commissioning.py``, ``tool_selection.py``) and report (``to_parent.py``)."""

BINDING_PATH = 'partner_presence_evidence'
GOAL = ("Determine what the supplied target does within the parent's assigned question, scope and constraints, "
        'by improving the retained, source-grounded evidence on which components a possible function requires and '
        'whether they are present and expressed in the relevant genome, organism and conditions. Possible functions '
        'can emerge from the evidence and be compared or revised; missing information remains unknown. Preserve '
        'named scientific components separately from controller progress.')
UNIT = ('One scientific action of its own (a selected tool, a library lookup, a reasoning commit, the preparation '
        'of an alternative process) or one commissioned partner, literature, '
        'execution, results, monitor or HPC child')
RESULT = ('the controlled finding of the A107 scoring sheet: the evidence type, direction, target correspondence and '
          'sheet of the strongest literature partner sheet, the features of every literature sheet and the agreement counts, '
          'and, when selected, the records it committed and the A107 qualification and native component records')
