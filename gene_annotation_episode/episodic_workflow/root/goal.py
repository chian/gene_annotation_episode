"""What this episode is for: the annotation of one sequence, given as a bare string. It starts with no proposed
annotation and nothing known of the sequence: the features, the candidate annotations and the organism are what its
heads find, and its credit is what feature calling earns, multiplied by what the nine evidence axes earn."""

BINDING_PATH = 'root'
GOAL = ('Find the features of the assigned sequence, their annotations and its organism, and raise the credit: '
        "feature calling's credit as the base, multiplied by the factor of the nine evidence-axis credits, which grows "
        'linearly with progress on one axis and more when the progress is spread over several axes; with no feature '
        'credited the credit is 0')
UNIT = ('One commission of one head (feature calling, the organism identification head or an evidence-axis head), which '
        'returns its credit, the scores of its scoring sheet, the numbers and flags of its finding and its records; or '
        'the making of the claims of one candidate annotation, which a head then checks')
RESULT = ("The root's credit; the scoring sheet in two levels: the feature calls of each sequence with their scores, "
          'and every candidate annotation the axis heads scored (the merged score of each and what each axis said) with '
          'the best annotation; the organism (the candidate taxa and the placement); the claims made from the '
          "annotations; feature calling's credit and commissions; for each of the nine axes, its credit, how often it "
          'was commissioned and how many job records its head left outstanding; when selected, the records the heads '
          'returned')
