"""What this episode is for: the results of one launched preparation job. It checks the job through the job service,
waits for it to end, fetches only its receipt and, in one automatic step coupled to that fetch, decides from the
receipt whether the product is usable and writes the prepared-data record. It is evidence-free: it produces data for
later work, not a sheet. Nothing here is a model choice."""

BINDING_PATH = 'sequence_homology_evidence/blast_database_preparation/results'
GOAL = ('Establish the prepared-data record of one launched database build or masking job. Ask the job; while it has '
        'not ended, wait and ask again; once it has ended fetch only its receipt, check the product against the plan '
        'the job ran, and keep the record of what was built, usable or not. A job that has not ended is not a '
        'failure and its absence of a receipt is not an outcome.')
UNIT = ('One defined action: one acquisition of the prepared-data record (ask the job and, when it has ended, fetch '
        'its receipt and write the record), one wait for the job, or a read of the record already held')
RESULT = ('The credit, the finding on the prepared product (its state, whether it is usable, its counts and checked '
          'facts) and, when selected, the reference of the prepared-data record')
