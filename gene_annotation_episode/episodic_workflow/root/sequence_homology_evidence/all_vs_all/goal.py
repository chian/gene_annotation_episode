"""What this episode is for: the target and the sequences of chosen candidates of a graded BV-BRC search put in one set, searched
all against all with BLAST+ on a local resource and clustered, so the parent holds one graded clustering that says where the target
falls among each candidate's sequences. Four one-shot tools, each in one unit: prepare_database (the set fetched once by md5, the
BLAST database built and kept as one archive), all_vs_all_blast (the matrix of bit scores of every ordered pair), cluster (a TRY: MCL
on the score ratio, tuned by the model's choice of inflation and graph contrast from fixed sets, on the facts of the matrix's score
ratios) and commit_clustering (the one try that is graded, chosen among at least two tries of different tunings: what the parent's
credit reads). Its own cycle improves exactly that: what the parent holds of the set, the database,
the matrix and the committed clustering that it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/all_vs_all'
GOAL = ('Establish, on a local resource, the sequence set of the assigned target and the assigned candidates of the assigned '
        'graded BV-BRC search, its BLAST database and its all-against-all matrix of bit scores, tune a clustering of it, and return '
        'what was established to the parent: the labelled data products and the one committed clustering, graded into the sheet the '
        'parent\'s credit reads. The work is done in four defined tools, each one unit: prepare_database, all_vs_all_blast (only with a '
        'database product held), cluster (tries; only with a matrix product held; each tuning once, shown to you as controlled facts) '
        'and commit_clustering (once, a held try, only with at least two tries of the matrix with different tunings held). A '
        'repeat of what is held adds nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: prepare_database, all_vs_all_blast, cluster, commit_clustering or hold'
RESULT = ('The state of the work (nothing_done, database_ready, matrix_ready, tried or clustered), the sequences and letters of the '
          'set, the pairs of the matrix, the number of tries, the committed clustering with its cluster count, the last failure code and '
          'the credit; selectable: the graded records (the data-product rows and the committed clustering\'s source)')
