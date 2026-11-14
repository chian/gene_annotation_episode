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


def resolve(self, context, reference, namespace):
    if namespace == 'hpc_model':
        return any(row['id'] == reference for row in self.state(context).records('model'))
    return reference_in_context(self.services, context, reference, namespace)

def frozen_reference(self, context, reference, namespace):
    """Validate a closed model identifier without reopening writable state."""
    if namespace != 'hpc_model' or context.role not in self.roles or self.store is None:
        return False
    from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
    import sqlite3
    from contextlib import closing
    EpisodeReturnRecords(self.store, self.run_id, failure_prefix='hpc_closed_').authenticate(context)
    saved = self.store.db.execute('SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?',
                                 (self.run_id, context.episode_id)).fetchone()
    if saved is None or json.loads(saved[0]).get('hpc_model_ref') != reference:
        return False
    owner = context.assignment['owner_episode_id']
    path = self.directory/'hpc'/hpc_queue.digest([context.run_id, owner])/'hpc.sqlite'
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        ownership = db.execute("SELECT body FROM evidence WHERE id='owner'").fetchone()
        model = db.execute("SELECT 1 FROM evidence WHERE id=? AND kind='model'", (reference,)).fetchone()
    return bool(ownership and model and json.loads(ownership[0])['run_id'] == context.run_id
                and json.loads(ownership[0])['episode_id'] == owner
                and json.loads(ownership[0])['scope'] == plain(context.scope))

