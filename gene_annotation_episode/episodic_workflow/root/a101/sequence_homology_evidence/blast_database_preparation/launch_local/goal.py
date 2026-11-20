"""What this episode is for: the launch of one database build or masking job on one local resource. It ends at
handoff. The job is built by code from the commission's controlled fields; this episode asks no model what to run."""

BINDING_PATH = 'sequence_homology_evidence/blast_database_preparation/launch_local'
GOAL = ('Launch the commissioned BLAST database build or masking job as a detached job on the assigned local '
        'resource and return its handoff record. The job is built from the commission by code; the episode ends at '
        'the handoff and does not wait for the job, check it or collect its results.')
UNIT = 'One defined launch action: the launch of the commissioned job (or a read of the handoff it already holds)'
RESULT = 'The handoff record of the launched job, whether the handoff exists, and the counts of the launches'
