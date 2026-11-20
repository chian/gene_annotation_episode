"""What this episode is for: the monitor of one launched database search (a job on the public service or on a
cluster), a child of ``database_blast``. It checks the job through the job service until a check shows something the
checks before it did not, and returns where the job stands. The job keeps running whether or not anyone watches it; this
episode does not fetch its results. Its parent decides from the return whether to check again later or to fetch."""

BINDING_PATH = 'sequence_homology_evidence/database_blast/monitor'
GOAL = ('Find out through the job service where the assigned job stands now: its state and whether its results are '
        'available. A check that shows no fact the earlier checks (including those the parent already holds) do not '
        'show earns nothing. The provider\'s spacing between two status requests is kept, not waited out by the '
        'service: this episode waits for it. Liveness establishes process presence only; elapsed time alone '
        'establishes neither productive work nor a stall. Unknown information stays unknown.')
UNIT = 'one check of the job, after waiting for the provider\'s spacing'
RESULT = ('the credit earned by newly informative checks, the finding on the job (whether it was observed, its state, '
          'whether its results are available) and the check records this episode wrote')
