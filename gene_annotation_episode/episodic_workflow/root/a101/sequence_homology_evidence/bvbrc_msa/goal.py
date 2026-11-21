"""What this episode is for: the assigned target aligned with the sequences of chosen candidates of a graded BV-BRC
search through the BV-BRC application service (the ``MSA`` application, run on the owner's account), the whole job done in
this one commission: estimated, launched, monitored until it has ended and extracted into the graded alignment sheet. Its
own cycle improves exactly that: what the parent holds of the alignment (the estimate, the handoff, what its status
requests showed, the graded alignment and its data product) that it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/bvbrc_msa'
GOAL = ('Align the assigned target with the sequences of the assigned candidates of the assigned graded BV-BRC search '
        'through the BV-BRC application service, and return what the job established to the parent: its estimate, its '
        'handoff, what its status requests showed and, once the service has finished it, the graded alignment (per '
        'reference sequence: the columns paired with the target, the identical ones and the value). The work is done in '
        'five defined actions: estimate (before anything is launched), launch (only with an estimate held), fix (after a '
        'failure, naming what will change), monitor (a status request after a wait, which also updates the estimate) and '
        'extract (fetch the alignment and grade it in the same unit). A repeat of what is already held adds nothing. Only '
        'the yield controller ends the episode.')
UNIT = 'One defined action: estimate, launch, fix, monitor or extract'
RESULT = ('The state of the job (no_estimate, estimated, launched, finished, extracted or failed), the number of sequences '
          'aligned, the alignment columns and the candidates aligned, the estimated and observed durations, the last failure '
          'code and the credit; selectable: the handoff record, the status records, the closure record and the graded records '
          '(including the alignment product row)')
