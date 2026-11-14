"""Selected local file custody within the existing results episode.

The retained stream has an exact byte identity. Neither the path, the job's
termination nor pinning an inode establishes a producing execution or an atomic
source version. Per-file Store commits survive later sibling failures.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.execution_contracts import obj
_TEXT = {'type': 'string', 'minLength': 1}
ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'read_consistency': 'pinned_regular_file_stream_not_atomic_snapshot', 'writer_closure': 'not_established'}
_FAILURE_SCHEMA = {**obj({'code': deepcopy(_TEXT)}), 'type': ['object', 'null']}
OUTCOME_SCHEMA = obj({'version': {'type': 'string', 'const': 'execution_file_source_outcome_v1'}, 'operation': {'type': 'string', 'enum': ['execution.results.collect', 'execution.results.status']}, 'job': obj({'state': deepcopy(_TEXT), 'returncode': {'type': ['integer', 'null']}, 'failure_code': {'type': ['string', 'null']}}), 'files': {'type': 'array', 'items': obj({'path': deepcopy(_TEXT), 'format': deepcopy(_TEXT), 'source_ref': {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': 'source'}, 'availability': {'type': 'string', 'enum': ['retained', 'unavailable', 'not_acquired']}, 'size_bytes': {'type': ['integer', 'null'], 'minimum': 0}, 'failure': deepcopy(_FAILURE_SCHEMA)})}, 'provenance': obj({key: {'type': 'string', 'const': value} for key, value in ORIGIN.items()}), 'failure': deepcopy(_FAILURE_SCHEMA)})
OUTCOMES_SCHEMA = {'type': 'array', 'items': OUTCOME_SCHEMA, 'x-source': 'execution_file_capture_outcomes'}
