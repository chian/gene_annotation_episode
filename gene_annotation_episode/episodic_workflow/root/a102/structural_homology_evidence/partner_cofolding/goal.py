"""What this episode is for: one target protein co-folded by Chai-1 with several ligand candidates the parent already holds, one ligand
at a time, on a PBS resource (Polaris): the job estimated, launched, monitored until it has ended and extracted into the graded
partner-cofolding sheet, the whole job done in this one commission. The result is structural compatibility as the model predicts it,
never measured binding. Its own cycle improves exactly that: what the parent holds of the job (the estimate, the handoff, what its
status requests showed, the graded result) that it did not hold before. This goal creates no record the task reads: it is the fixed
target of the episode."""

BINDING_PATH = 'structural_homology_evidence/partner_cofolding'
GOAL = ('Co-fold the assigned target protein with each of the assigned ligand candidates (two to four held ligands, named ligand:<id>) '
        'with Chai-1 on the assigned PBS resource, and return what the job established to the parent: its estimate, its handoff, '
        'what its status requests showed and, once the job has finished, the graded result (the partner-cofolding sheet: per ligand '
        'the interface score of each of five samples, the clash flags and the mean value of the ligand). The work is done in five '
        'defined actions: estimate (before anything is launched), launch (only with an estimate held), fix (after a failure, naming '
        'what will change), monitor (a status request after a wait, which also updates the estimate) and extract (fetch the scores '
        'and grade them in the same unit). A repeat of what is already held adds nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: estimate, launch, fix, monitor or extract'
RESULT = ('The state of the job (ready, estimated, launched, finished, extracted or failed), the ligand, candidate, sample and '
          'clashing-sample counts and the highest and lowest ligand value of the graded sheet, the estimated and observed durations, '
          'the last failure code and the credit; selectable: the handoff record, the status records, the closure record and the '
          'graded records (the scores, their source and the grading sheet with the artifacts they name)')
