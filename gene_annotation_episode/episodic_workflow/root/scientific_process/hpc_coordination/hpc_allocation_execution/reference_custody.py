"""HPC parent and prediction specializations of the ordinary Episode loop.

Launch remains the existing launch -> launch_hpc iteration. Known monitoring
and result parsing are single tools of the HPC parent. This binding never calls
a model, polls in a loop, or decides to commission children itself.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import asyncio
import shlex
import subprocess
import time

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.hpc_campaign import (YIELD_ROLES, accepts, bind_progress, build_plan,
    incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.root.library.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.library import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.library import hpc_queue
from gene_annotation_episode.episodic_workflow.root.library.hpc_resource_prediction import forecast_metric, pbs_resource_metrics, physical_attempt_key


TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def _known(self, context):
    known = set(context.received_record_refs)
    selection = getattr(self.services, 'record_selection', None)
    if callable(selection):
        known.update(selection(context)['known_record_refs'])
    return known

def resolve_received_reference(self, context, reference, namespace):
    try:
        source = self.store.get(reference)
    except (KeyError, ValueError):
        return None
    if source.get('provider') != 'episode.hpc_result':
        return None
    if namespace not in (None, 'source') or reference not in self._known(context):
        return False
    body = json.loads(self.store.get_artifact(source['artifact_ref']))
    if body['run_id'] != self.run_id:
        return False
    try:
        self.store.validate_scope(body['scope'], parent_scope=plain(context.scope))
    except ValueError:
        return False
    return True

def read_evidence(self, context, ledger, reference):
    history = self._history(ledger)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    # Results publish ordinary Store Sources as well as ledger receipts.
    # Resolve only a received Source owned by this original HPC ledger.
    rows = [row['body'] for row in ledger.records('result')
            if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or self.resolve_received_reference(context, reference, 'source') is not True:
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = self.store.get(reference)
    body = json.loads(self.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]

