"""What this episode is for: the parts of one piece of DNA, and where each begins and ends. The goal names what this episode's own
cycle improves: the reading of the piece, that is, which protein genes and RNA genes are on it, each part with its score (how well
that reading is supported). ``UNIT`` and ``RESULT`` describe one unit and the return."""

BINDING_PATH = 'parts_discovery'
GOAL = ('This arm owns what is in the assigned piece of DNA: which protein genes and which RNA genes lie on it, where each '
        'begins and ends, on which strand, and whether an end is cut off by the end of the piece. The piece is the one fixed '
        'thing; a part is a reading of positions on it, under a genetic code. A protein gene\'s score is the gene finder\'s own '
        'score for it, an RNA gene\'s score is its bit score against its Rfam family, and a reading of the protein genes has the '
        'score of the sum of its genes\' scores. This episode improves the reading: a part found with a positive score earns it, '
        'a second reading of the protein genes under another genetic code earns only the amount by which its score beats the '
        'best reading held, and a repeat earns nothing. Preserve the measured piece, the native statistics and the limits of '
        'inference; that no gene was called is not evidence that none is there. Only the yield controller ends the episode.')
UNIT = ('One action: one call of a tool (a description of the piece\'s composition, a gene finding under one genetic code, or a '
        'scan of the piece for RNA genes)')
RESULT = ('The reading of the piece: the piece\'s length, GC fraction and GC skew, the reading of the protein genes reported (the '
          'held one of the highest score) with its genetic code, mode, gene count, median gene length, coding share and score, the '
          'number of readings held, the number of RNA genes, the leading parts with their scores, and the credit')
