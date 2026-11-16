"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_common import METADATA_SCHEMA, MODE, OPERATION

def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
        'additionalProperties': False}


TEXT = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
NULL = {'type': 'null'}
COUNT = {'type': 'integer', 'minimum': 0}
FILE_SCHEMA = obj({'path': TEXT})
PARAMETERS_SCHEMA = obj({'rank': {'type': 'integer', 'minimum': 1},
    'random_state': {'type': 'integer', 'minimum': 0, 'maximum': 2**32-1},
    'normalization': {'enum': ['none', 'column_sum_1000']}, 'tol': {'type': 'number', 'minimum': 0},
    'max_iter': {'type': 'integer', 'minimum': 1}})
SOFTWARE_SCHEMA = obj({'version': {'const': 'expression_nmf_software_v1'}, 'python': FILE_SCHEMA,
    'python_version': TEXT, 'python_home': TEXT, 'module_root': TEXT,
    'implementation_files': {'type': 'array', 'minItems': 1, 'items': FILE_SCHEMA},
    'dependency_roots': {'type': 'array', 'minItems': 1, 'items': TEXT, 'uniqueItems': True},
    'distributions': {'type': 'array', 'minItems': 1, 'items': obj({'name': TEXT, 'version': TEXT,
        'requires': {'type': 'array', 'items': TEXT}})},
    'runtime_files': {'type': 'array', 'minItems': 1, 'items': FILE_SCHEMA}})
INPUT_SPEC_SCHEMA = obj({'path': TEXT, 'sha256': SHA, 'size_bytes': COUNT,
    'artifact_ref': {'anyOf': [TEXT, NULL]}, 'delimiter': {'enum': [',', '\t']},
    'metadata': METADATA_SCHEMA})
JOB_SCHEMA = obj({'version': {'const': 'native_expression_nmf_job_v1'}, 'operation': {'const': OPERATION},
    'mode': {'const': MODE}, 'input': INPUT_SPEC_SCHEMA, 'parameters': PARAMETERS_SCHEMA,
    'software': SOFTWARE_SCHEMA, 'output_prefix': TEXT})
ENV_SCHEMA = {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
    'additionalProperties': {'type': 'string', 'pattern': '^[^\\u0000]*$'}}
NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA = obj({'argv': {'type': 'array', 'minItems': 1, 'items': TEXT},
    'environment': ENV_SCHEMA, 'native_expression_nmf': JOB_SCHEMA})
BINDING_SCHEMA = obj({'operation': {'const': OPERATION}, 'mode': {'const': MODE}, 'software': SOFTWARE_SCHEMA})


