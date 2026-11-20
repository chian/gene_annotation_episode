"""What this episode is for: the launch of one assigned job on one assigned local resource. It ends at handoff."""

BINDING_PATH = 'sequence_homology_evidence/execution_job_submission/local_job_execution'
GOAL = 'Launch the assigned job as a detached job on the assigned local resource and return its handoff record'
UNIT = 'One defined launch action: a launch of the assigned job, or a hold'
RESULT = 'The handoff record of the launched job, whether the handoff exists, and the counts of the actions taken'
