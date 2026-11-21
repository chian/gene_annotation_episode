"""What this episode is for: the ``results`` responsibility of the old resource episode. The job was handed off by
an earlier launch; this episode acquires its requested result files and the scientific parent interprets them."""

BINDING_PATH = 'structural_homology_evidence/resource_result_acquisition'
GOAL = ('Acquire the requested data through the supplied receiving interface; the scientific parent interprets it')
UNIT = ('One tool unit on the handed-off job: one status check through the receiving interface of its resource, '
        'one fetch of the requested result files, or one wait on the job')
RESULT = ('The credit, the finding (the state of the job and what the fetch came to) and, in custody, the acquired '
          'result files and the closure record of the job')
