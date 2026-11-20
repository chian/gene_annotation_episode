"""What this episode is for: the launch of one database build or masking job on one cluster (PBS) resource, as a
batch job under the scheduler allocation the commission carries. It ends at handoff. The job is built by code from
the commission's controlled fields; this episode asks no model what to run or how to allocate."""

BINDING_PATH = 'sequence_homology_evidence/blast_database_preparation/launch_hpc'
GOAL = ('Launch the commissioned BLAST database build or masking job as a batch job on the assigned cluster '
        'resource, under the scheduler allocation the commission states, and return its handoff record. The job is '
        'built from the commission by code; the episode ends at the handoff and does not wait for the job, check it '
        'or collect its results.')
UNIT = 'One defined launch action: the launch of the commissioned job (or a read of the handoff it already holds)'
RESULT = 'The handoff record of the launched job, whether the handoff exists, and the counts of the launches'
