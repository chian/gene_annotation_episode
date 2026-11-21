"""What this episode is for: a held graded alignment of the target with the sequences of product candidates tested with
MetaCATS through the BV-BRC application service (the ``MetaCATS`` application, run on the owner's account), the whole job
done in this one commission: estimated, launched, monitored until it has ended and extracted into the graded sheet. Its own
cycle improves exactly that: what the parent holds of the analysis (the estimate, the handoff, what its status requests
showed, the graded sheet and its data product) that it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/bvbrc_metacats'
GOAL = ('Test the assigned held alignment with MetaCATS through the BV-BRC application service, and return what the job '
        'established to the parent: its estimate, its handoff, what its status requests showed and, once the service has '
        'finished it, the graded sheet (the alignment positions that differ between the candidate groups at the commission\'s '
        'p-value and, for each candidate group, how much of the target\'s residues at those positions its sequences carry). '
        'The groups are built by code, one per product candidate of the alignment, and the target is in none. The work is '
        'done in five defined actions: estimate (before anything is launched), launch (only with an estimate held), fix '
        '(after a failure, naming what will change), monitor (a status request after a wait, which also updates the '
        'estimate) and extract (fetch the result and grade it in the same unit). A repeat of what is already held adds '
        'nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: estimate, launch, fix, monitor or extract'
RESULT = ('The state of the job (no_estimate, estimated, launched, finished, extracted or failed), the groups, sequences and '
          'columns of the analysis and the significant positions, the estimated and observed durations, the last failure code '
          'and the credit; selectable: the handoff record, the status records, the closure record and the graded records '
          '(including the position report product row)')
