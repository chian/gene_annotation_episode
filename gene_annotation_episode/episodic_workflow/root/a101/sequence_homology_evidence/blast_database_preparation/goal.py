"""What this episode is for: the preparation of one BLAST database or masking from a commissioned sequence set,
ending with a usable prepared-data record that the commissioner (the A101 head) holds and passes on to the searches
that need it. It commissions its own children in a fixed order and decides nothing a model has to choose."""

BINDING_PATH = 'sequence_homology_evidence/blast_database_preparation'
GOAL = ('Establish a usable prepared-data record from the commissioned sequence set: a BLAST database built from it '
        'or a masking of it. Commission the launch of the job on the assigned local resource, then commission the '
        'collection of its results until the record is established, usable or not. A product that is not usable is '
        'still returned as it stands. This episode produces data for later work, not evidence: it earns credit '
        'for a usable record and for nothing else.')
UNIT = ('one commission of a child (the launch of the job, or the acquisition of its results), or a read of the '
        'prepared-data record this episode already holds')
RESULT = ('the credit, the finding on the prepared product (its state, whether it is usable, its counts and checked '
          'facts) and, when selected, the reference of the prepared-data record and of the launched job\'s handoff')
