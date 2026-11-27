"""What this episode is for: the A101 sequence-homology evidence investigation of the assigned subject. The goal names
what this episode's own cycle improves: the possible annotations of the scope's target found by graded sequence-correspondence evidence, each with its score. ``UNIT`` and
``RESULT`` describe one unit and the return."""

BINDING_PATH = 'sequence_homology_evidence'
GOAL = ('A101 owns sequence similarity evidence for the assigned scope: what the scope\'s target corresponds to at the '
        'sequence level, and how well. This episode improves that evidence: the possible annotations of the target that '
        'graded sequence correspondence with the sequences it is compared with supports, each with its score, which is '
        'what its credit counts: a possible annotation found with positive evidence earns its score, applying the same '
        'test to candidates already listed earns by how differently they respond, and a repeat earns nothing. Starting or waiting '
        'on a job is operational progress, not homology evidence. Report correspondence as correspondence, not as '
        'proof of function. Only the yield controller ends the episode.')
UNIT = ('One selected tool, one pairwise comparison, one profile scan, or one commission of a child '
        'episode')
RESULT = ('The qualified sequence-homology findings: the records this episode committed and holds, the graded '
          'comparisons it holds, the possible annotations found with their scores, and the differential credit')
