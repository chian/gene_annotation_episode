"""What this episode is for: a usable prepared database (or masked data) established from the one assigned sequence
set, on a local resource. Its own cycle improves exactly that: whether the parent holds a usable prepared-data
record of the set that it did not hold before."""

BINDING_PATH = 'sequence_homology_evidence/blast_database_preparation'
GOAL = ('Establish a usable prepared-data record (a BLAST database, or masked sequences) from the assigned sequence '
        'set on a bound local resource, and return it to the parent. A record is usable only when the job\'s receipt '
        'establishes it; a repeat of a record the parent already holds adds nothing. Only the yield controller ends '
        'the episode.')
UNIT = 'One defined action: a local preparation of the assigned set (launch_local) or a hold (hold)'
RESULT = ('Whether a usable prepared-data record was established (state usable, failed, incomplete or not_launched), '
          'the counts of the input set, the files of the product, the last failure code and the credit; selectable: '
          'the prepared-data record')
