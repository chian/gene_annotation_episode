"""What this episode is for: one target sequence compared with the structures of one structure database through one model of
it, on the Foldseek web server (the ``StructureSearch`` application): a model of the target obtained from a source (or the
one the parent passed), the search estimated, launched, monitored until it has ended and extracted into the graded structure-
search sheet, the whole job done in this one commission. Its own cycle improves exactly that: what the parent holds of the
search (the model, the estimate, the handoff, what its status requests showed, the graded result) that it did not hold
before. This goal creates no record the task reads: it is the fixed target of the episode."""

BINDING_PATH = 'structural_homology_evidence/structure_search'
GOAL = ('Search the assigned target sequence against the assigned structure database through one model of the target on '
        'the Foldseek structure search server, and return what the search established to the parent: the model (its origin, '
        'residues and mean pLDDT), its estimate, its handoff, what its status requests showed and, once the service has '
        'finished it, the graded result (the structure-search sheet: per hit the aligned pairs, the RMSD and the index B, '
        'per product candidate its hits and its mean B). The work is done in six defined actions: get_model (a model of '
        'the target from one source), estimate (before anything is launched), launch (only with an estimate and a model '
        'held), fix (after a failure, naming what will change), monitor (a status request after a wait, which also updates '
        'the estimate) and extract (fetch the result and grade it in the same unit). A repeat of what is already held adds '
        'nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: get_model, estimate, launch, fix, monitor or extract'
RESULT = ('The state of the search (no_model, model_held, estimated, launched, finished, extracted or failed), the model '
          'facts (origin, residues, mean pLDDT), the hit, named, not-asked and candidate counts of the graded sheet, the '
          'estimated and observed durations, the last failure code and the credit; selectable: the handoff record, the '
          'status records, the closure record and the graded records (the model, the result, the hit metadata and the '
          'grading sheet with the artifacts they name)')
