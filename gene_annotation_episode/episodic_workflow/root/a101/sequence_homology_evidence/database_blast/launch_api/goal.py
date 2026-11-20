"""What this episode is for: launch the database search of one query on the public BLAST service and end at the
handoff. It is the first child of ``database_blast`` for a hosted database. It builds the request from the commission
(the program, the hosted database and the hit-list size are all the parent's controlled choices), checks that the job
is a database search, submits it once through the job service and returns the handoff record. It does not wait for the
job, ask its status or fetch its results: the monitor and results children do."""

BINDING_PATH = 'sequence_homology_evidence/database_blast/launch_api'
GOAL = ('Submit the assigned database search of one query to the assigned public web service once through the job '
        'service, and establish its handoff: the recorded identity of the accepted submission. The program, the '
        'database and the hit-list size are the parent\'s decisions and are used exactly. A missing reply does not '
        'establish that no job was created.')
UNIT = 'one submission of the request built from the commission'
RESULT = ('The handoff record of the submitted job, in custody; whether the handoff was established; the counts of '
          'submissions made and submissions that failed')
