"""What this episode is for: one query sequence searched against one hosted database through the public NCBI BLAST
service, the search followed to its end without waiting for it, and its report graded into the database sheet. Its own
cycle improves exactly that: what the parent holds of the search (its handoff, what its status requests showed, the
graded result) that it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/database_blast'
GOAL = ('Search the assigned query sequence against the assigned hosted database through the public NCBI BLAST service, '
        'and return what the search established to the parent: its handoff, what its status requests showed, and, once '
        'the service has finished it, the graded result (the identification sheet; the residue correspondence of the '
        'best hits is read from the same sheet). The search runs at the service for seconds to minutes: this episode '
        'never sits waiting for it. A search that is not finished is held, and the parent comes back later with the '
        'records this episode returned. A repeat of what the parent already holds adds nothing. Only the yield '
        'controller ends the episode.')
UNIT = ('One defined action: submit the search, check its status, fetch its report and grade it (fetch_and_grade), '
        'or hold')
RESULT = ('The state of the search (not_submitted, outstanding, finished, graded or failed), the hit count and the '
          'controlled identification features of the graded sheet, the predicted and observed durations, the last '
          'failure code and the credit; selectable: the handoff record, the check records, the closure record and the '
          'graded records')
