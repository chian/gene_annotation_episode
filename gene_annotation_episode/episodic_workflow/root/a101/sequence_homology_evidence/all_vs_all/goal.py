"""What this episode is for: the target and the sequences of chosen candidates of a graded BV-BRC search put in one set, searched
all against all with BLAST+ on a local resource and clustered, so the parent holds a graded clustering that says where the target
falls among each candidate's sequences. Three one-shot tools, each in one unit and each keeping a labelled data product the next
requires: prepare_database (the set fetched once by md5, the BLAST database built and kept as one archive), all_vs_all_blast (the
matrix of bit scores of every ordered pair) and cluster (MCL on the score ratio at an inflation of the commission's fixed set).
Its own cycle improves exactly that: what the parent holds of the set, the database, the matrix and the graded clusterings that
it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/all_vs_all'
GOAL = ('Establish, on a local resource, the sequence set of the assigned target and the assigned candidates of the assigned '
        'graded BV-BRC search, its BLAST database, its all-against-all matrix of bit scores and its clusterings, and return what '
        'was established to the parent: the labelled data products and, for each clustering, the graded sheet the parent\'s credit '
        'reads. The work is done in three defined tools, each one unit: prepare_database, all_vs_all_blast (only with a database '
        'product held) and cluster (only with a matrix product held; one inflation of the commission\'s allowed values, each '
        'once). A repeat of what is held adds nothing. Only the yield controller ends the episode.')
UNIT = 'One defined action: prepare_database, all_vs_all_blast, cluster or hold'
RESULT = ('The state of the work (nothing_done, database_ready, matrix_ready, clustered or failed), the sequences and letters of '
          'the set, the pairs of the matrix, the clusterings made with their cluster counts, the last failure code and the credit; '
          'selectable: the handoff records, the closure records and the graded records (the data-product rows and the clustering '
          'sources)')
