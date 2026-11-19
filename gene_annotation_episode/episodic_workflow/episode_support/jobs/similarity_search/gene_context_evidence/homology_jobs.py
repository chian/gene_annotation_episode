"""Durable one-query homology jobs and their functional communication handoff.

Ordinary tools for launch/monitor/results episodes use this service. It does
not choose those episodes, prescribe their order, score work, estimate yield,
interpret a match or label a process termination scientific completion.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.native_lifecycle import status


VERSION = 'single_query_phmmer_jobs_v2'
CONFIGURATION_VERSION = 'single_query_phmmer_jobs_v3'
SEARCH_MODES = {'native_defaults': (), 'maximum_sensitivity': ('--max',)}
OUTPUTS = {'native_text': 'native.stdout', 'native_stderr': 'native.stderr',
           'hit_table': 'hits.tbl', 'domain_table': 'domains.tbl'}


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _reference(namespace):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}


HANDOFF_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'backend': {'type': 'string', 'enum': [VERSION]},
    'status_interface': {'type': 'string', 'enum': ['homology.status.v1']},
    'progress_interface': {'type': 'string', 'enum': ['homology.progress.v1']},
    'results_interface': {'type': 'string', 'enum': ['homology.results.v1']}})
STATUS_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'state': {'type': 'string', 'enum': ['not_submitted', 'prepared', 'submission_unconfirmed', 'starting', 'running', 'returned', 'execution_unknown']},
    'outcome': {'type': 'string', 'enum': ['pending', 'succeeded', 'failed', 'unknown']},
    'elapsed_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'duration_measure': {'type': 'string', 'enum': ['systemd_service_wall_seconds']},
    'native_returncode': {'type': ['integer', 'null']},
    'failure_code': {'type': ['string', 'null'], 'enum': [None, 'native_nonzero_exit', 'local_job_resource_limit', 'local_job_execution_error']},
    'resource': {'type': ['string', 'null'], 'enum': [None, 'memory_bytes', 'scratch_bytes', 'file_bytes']},
    'progress_kind': {'type': 'string', 'enum': ['native_execution_state_and_output_bytes_not_search_fraction']},
    'outputs': {'type': 'array', 'items': _object({
        'role': {'type': 'string', 'enum': list(OUTPUTS)}, 'available': {'type': 'boolean'},
        'bytes': {'type': ['integer', 'null'], 'minimum': 0}, 'writer_closed': {'type': 'boolean'}})}})
SAMPLE_SCHEMA = _object({'sample_ref': _reference('job_sample'),
    'sampled_at_unix_seconds': {'type': 'number', 'minimum': 0}, **STATUS_SCHEMA['properties']})


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def ref(kind, value):
    return kind+'_'+hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


