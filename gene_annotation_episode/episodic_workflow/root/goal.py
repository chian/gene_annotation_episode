"""What this episode is for: the annotation of one subject. It starts with no proposed annotation: the candidate
annotations are what its heads find, and its credit is what the nine evidence axes earn for them."""

BINDING_PATH = 'root'
GOAL = ('Find the annotation of the assigned subject and raise its annotation credit: the credit over the nine '
        'evidence-axis credits, which grows linearly with progress on one axis and more when the progress is '
        'spread over several axes')
UNIT = ('One commission of one evidence-axis head, which returns its axis credit, the scores of its scoring sheet, the '
        'numbers and flags of its finding and its records; or the making of the claims of one candidate annotation, '
        'which a head then checks')
RESULT = ('The annotation credit; the scoring sheet of every candidate annotation the axis heads scored (the merged '
          'score of each and what each axis said) and the best annotation; the claims made from the annotations; for '
          'each of the nine axes, its credit, how often it was commissioned and how many job records its head left '
          'outstanding; when selected, the records the heads returned')
