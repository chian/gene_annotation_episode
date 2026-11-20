"""What this episode is for: a pairwise BLAST of one query sequence against one subject sequence, from the launch of
the search to the graded correspondence of the two. The episode's name is the analysis it performs: the commission
declares it, and the job the episode builds is checked against that declaration before anything launches."""

BINDING_PATH = 'sequence_homology_evidence/pairwise_blast'
GOAL = ('Compare the assigned query sequence with the assigned subject sequence by a pairwise BLAST on the assigned '
        'local resource, and keep the graded correspondence of the two: which residues of the one correspond to '
        'which residues of the other, and how many. Launch the search once, check the job, fetch its report once the '
        'job has ended and grade the report into the pairwise sheet of the two sequences. Credit is earned only by '
        'the graded correspondence; the scientific parent interprets it. Only the yield controller ends the '
        'episode.')
UNIT = ('one defined action: launch the search, check the job, fetch its report, or grade the report')
RESULT = ('the credit, whether the search was handed off and graded, the controlled features of the saved sheet, and '
          'the references of the handoff, the job records and the saved grading')
