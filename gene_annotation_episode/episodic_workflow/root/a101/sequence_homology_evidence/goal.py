"""What this episode is for: the A101 sequence-homology evidence investigation of the assigned subject. ``GOAL`` is
the old ``scientific_guidance()`` of ``goal.py`` at 97308b94c, unchanged; the two bodies the old
``ScientificGoal.instructions`` appended by the entry version of the selected evidence axis are in ``task.py``
(instruction text). ``UNIT`` and ``RESULT`` are written from the old ``task.py`` shape (one selected tool, reasoning
or child action) and ``to_parent.py`` (the reported process result and committed records)."""

BINDING_PATH = 'sequence_homology_evidence'
GOAL = ('A101 owns sequence similarity evidence. For an NCBI BLAST search that may run remotely, use the configured '
        'Launch API job when available: submit once, return its execution_handoff_refs to this episode, and let a '
        'separately selected monitor or Results episode check that same RID. The handoff is operational progress, '
        'not homology evidence. If that RID is waiting and no useful A101 work remains, return the handoff '
        'reference and current credit to your parent so it can choose another evidence axis. Consider ClusteredNR '
        '(nr_clustered_seq) for an initial blastx search; choose the database for the scientific question and '
        'preserve the selected database in the original request.')
UNIT = ('One selected tool of the selected tool set, one reasoning commit of a scientific interpretation, one '
        'revision of the process selection, or one commission of a child (launch, monitor, results, published '
        'evidence or a recursive sequence-homology investigation)')
RESULT = ('The qualified sequence-homology findings: the records this episode committed and holds, the process '
          'result, any execution handoff records, and the native sequence-correspondence credit')
