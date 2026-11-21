"""What this episode is for: the A102 structural-homology evidence investigation of the assigned subject. The goal names what
this episode's own cycle improves: the possible annotations of the scope's target that graded structural evidence supports,
each with its score. ``UNIT`` and ``RESULT`` describe one unit and the return.

The text of the goal is carried from the old head's ``goal.py`` (the instruction-entry goal text and the guidance sentences of
the merged A102 axis, commit ``97308b94c``) and from the axis's entry of the process library; the sentences that named the
old machinery (a thought pattern and a tool selection revised for a new child, the old units) are not carried."""

BINDING_PATH = 'structural_homology_evidence'
GOAL = ('A102 owns structural evidence for the assigned scope: what the scope\'s target resembles in structure, and how '
        'well. From the supplied sequence only (no name, no accession and no structure are required) this episode '
        'compares the structure or a model of the target with the structures of functionally characterized proteins, '
        'through comparative and experimental structural evidence. It keeps each structure\'s origin (experimental or '
        'predicted), the matched extent and the actual structural statistics; a prediction\'s confidence describes the '
        'model and is not similarity. Possible functions can emerge from the evidence and be compared or revised. This '
        'episode improves that evidence: the possible annotations of the target that graded structural correspondence '
        'supports, each with its score, which is what its credit counts: a possible annotation found with positive '
        'evidence earns its score, applying the same test to candidates already listed earns by how differently they '
        'respond, and a repeat earns nothing. Preserve the measured subject, the native statistics, the uncertainty and '
        'the limits of inference; missing information remains unknown. Starting or waiting on a job is operational '
        'progress, not structural evidence. Report resemblance as resemblance, not as proof of function. Only the yield '
        'controller ends the episode.')
UNIT = 'One commission of a child episode'
RESULT = ('The qualified structural findings: the graded structure searches the episode holds, the models of the target '
          'they used, the possible annotations found with their scores (the leading ones), and the differential credit')
