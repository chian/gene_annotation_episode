"""What this episode is for: which feature or features a sequence possibly holds. The goal names what this episode's own
cycle improves: the candidate features of the scope's sequence, each a type together with its location. ``UNIT`` and
``RESULT`` describe one unit and the return. The rules by which calls become candidates, nest and compete are not the
goal; they are in ``episode_support/grading/sequence_features/feature_candidates.py``."""

BINDING_PATH = 'feature_calling'
GOAL = ('This episode says which feature or features the assigned sequence possibly holds. It is given the bare sequence, '
        'with or without information that already exists about it. A candidate feature is a type and a location together: '
        'a kind, one or more position ranges on the sequence and a strand. It improves the candidate features of the '
        'sequence: which are found, how well each is supported, and how well the leading candidates that compete for the '
        'same letters are told apart. Nothing found is removed. Only the yield controller ends the episode.')
UNIT = 'One selected option: one run of one test on one sequence of the scope'
RESULT = ('The candidate features of each sequence of the scope, the highest score first (kind, position ranges, strand, '
          'score, rivals, the feature records that state it), the claims that wait for a feature call, the records this '
          'episode committed, and the credit')
