"""What this episode is for: the A101 sequence-homology evidence investigation of the assigned subject. The text
states what the head can commission today (the approved A101 tree's children that exist: a pairwise BLAST) and is
extended as the other actions are built. ``UNIT`` and ``RESULT`` describe one unit and the return."""

BINDING_PATH = 'sequence_homology_evidence'
GOAL = ('A101 owns sequence similarity evidence for the assigned scope. To compare the scope\'s target with a held '
        'reference sequence, commission a pairwise BLAST on a bound local resource: the child launches the search, '
        'waits for it, fetches its report and grades it, and returns the graded records and the controlled features '
        'of the saved pairwise sheet. The graded correspondence is the evidence this episode holds and its credit '
        'measures: the native sequence correspondence of the target with what was compared. The launch is '
        'operational progress, not homology evidence. Report the correspondence of the two sequences as '
        'correspondence, not as proof of function. Only the yield controller ends the episode.')
UNIT = ('One selected tool of the selected tool set, one reasoning commit of a scientific interpretation, or one '
        'commission of a child (a pairwise BLAST of the scope\'s target against a held subject)')
RESULT = ('The qualified sequence-homology findings: the records this episode committed and holds, the graded '
          'comparisons its children returned, and the native sequence-correspondence credit')
