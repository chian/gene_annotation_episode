"""Original incoming execution-target envelope; does not grant active resources."""
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import obj, TEXT, SHA256, checked

TARGET_SCHEMA = obj({
    'version': {'type': 'string', 'const': 'execution_target_v1'},
    'handle': TEXT, 'run_id': TEXT, 'resource_id': TEXT,
    'resource_kind': {'type': 'string', 'enum': ['api', 'local', 'hpc']},
    'execution_id': TEXT, 'request_sha256': SHA256, 'origin_episode_id': TEXT,
    'assignment': {'type': 'object'}, 'scope': {'type': 'object'},
})


def validate_target(value):
    return checked(value, TARGET_SCHEMA, 'invalid_execution_target')

