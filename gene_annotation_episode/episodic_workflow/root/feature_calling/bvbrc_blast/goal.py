"""What this episode is for: one sequence searched against one precomputed BV-BRC database through the BV-BRC
application service (the ``Homology`` application, run on the owner's account), the whole search done in this one
commission: estimated, launched, monitored until it has ended and extracted into the graded database sheet. Its own cycle
improves exactly that: what the parent holds of the search (the estimate, the handoff, what its status requests showed,
the graded result) that it did not hold before."""

BINDING_PATH = 'feature_calling/bvbrc_blast'
GOAL = ('Search the assigned sequence against the assigned precomputed BV-BRC database through the BV-BRC '
        'application service, and return what the search established to the parent: its estimate, its handoff, what '
        'its status requests showed and, once the service has finished it, the graded result (the identification '
        'sheet; the residue correspondence of the best hits is read from the same sheet). The work is done in five '
        'defined actions: estimate (before anything is launched), launch (only with an estimate held), fix (after a '
        'failure, naming what will change), monitor (a status request after a wait, which also updates the estimate) '
        'and extract (fetch the result files and grade them in the same unit). A repeat of what is already held adds '
        'nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: estimate, launch, fix, monitor or extract'
RESULT = ('The state of the search (no_estimate, estimated, launched, finished, extracted or failed), the hit count and '
          'the controlled identification features of the graded sheet, the estimated and observed durations, the last '
          'failure code and the credit; selectable: the handoff record, the check records, the closure record and the '
          'graded records')
