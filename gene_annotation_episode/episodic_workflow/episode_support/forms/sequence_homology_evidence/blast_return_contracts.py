"""Original A101 BLAST request and return data contracts (``root/a101/library/blast_return_contracts.py`` at
``97308b94c``; imports repointed).

The graded return travels as references: the result-acquisition episode returns the grading artifact of schema
``blast_database_sheet_v1`` in a ``record_refs`` field of its return form, and its finding carries the controlled
features read from that sheet."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import obj

TEXT = {'type': 'string', 'minLength': 1}
# A BLAST launch may request a graded database result while leaving the child
# free to select its search program and, unless constrained, its database.
# The original query operand is a required result identity, not a prewritten
# service command.  A submitted RID is an intermediate handoff; the grader is
# available after the separately selected results acquisition.
BLAST_GRADED_REQUEST_VERSION = 'blast_database_grader_return_request_v1'
BLAST_GRADED_REQUEST_SCHEMA = obj({
    'version': {'const': BLAST_GRADED_REQUEST_VERSION},
    'resource_id': TEXT,
    'return_type': {'const': 'blast_database_sheet_v1'},
    'query_subject_ref': TEXT,
    'database': TEXT,
}, ['version', 'resource_id', 'return_type', 'query_subject_ref'])
BLAST_GRADED_RETURN_SOURCE = 'ncbi_blast_database_grader_result'
BLAST_GRADED_RETURN_SCHEMA = {'type': 'array', 'items': obj({
    'result_ref': {'type': 'string', 'format': 'reference',
                   'x-reference-namespace': 'execution_result'},
    'grading_artifact_ref': {'type': 'string', 'format': 'reference',
                             'x-reference-namespace': 'artifact'},
    'sheet_schema': {'const': 'blast_database_sheet_v1'},
}), 'x-source': BLAST_GRADED_RETURN_SOURCE}
