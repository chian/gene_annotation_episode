from __future__ import annotations
'One authenticated native observation selected by an existing monitor.\n\nThe episode owns the choice. This adapter retains its original request/response\nand projects recorded facts; it never polls, retries or evaluates science.\n'
import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.durable import content_digest
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a104.episode_monitoring import _ASSIGNMENT, _FIELDS, _SNAPSHOT, _same_observation, read_progress
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, validate_target
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.progress_records import validate_resource_observation
VERSION = 'bvbrc_appservice_monitor_observation_v1'
PROVIDER = 'bvbrc_appservice.monitor'
_CHOICES = ('query_tasks', 'stdout', 'stderr')
_PREFIX = 'api.bvbrc_appservice.'

def _now():
    return datetime.now(timezone.utc).isoformat()

def _require(condition, code):
    if not condition:
        raise ValueError('appservice_monitor_' + code)
__all__ = ['AcquisitionError', 'AppServiceCustodyError', 'BindingContext', 'PROVIDER', 'SourceSnapshot', 'VERSION', '_ASSIGNMENT', '_CHOICES', '_FIELDS', '_PREFIX', '_SNAPSHOT', '_immutable', '_now', '_read', '_require', '_same_observation', 'asyncio', 'base64', 'canonical', 'content_digest', 'datetime', 'deepcopy', 'digest', 'fcntl', 'identity', 'json', 'plain', 'read_progress', 'timezone', 'validate_contract', 'validate_resource_observation', 'validate_schema', 'validate_target']
