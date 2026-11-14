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


def authenticate_launch(parent, selection, operation_key, directory):
    """Only the exact planned launch may consume the original allocation slot."""
    owner = parent.assignment['owner_episode_id'] if parent.role == 'hpc_execution' else parent.episode_id
    ledger = HPCLedger.open_existing(Path(directory)/'hpc'/hpc_queue.digest([parent.run_id, owner]))
    matching = [row for row in ledger.records('plan') if row['body']['launch_assignment'] == plain(selection)]
    if len(matching) != 1 or ledger.read('owner')['scope'] != plain(parent.scope):
        raise ValueError('hpc_launch_must_match_original_planned_portfolio')
    plan = matching[0]['body']
    identity = 'launch:'+plan['plan_id']
    reservation = {'operation_key': operation_key, 'plan_id': plan['plan_id']}
    if any(row['id'] == identity for row in ledger.records('launch_commission')):
        # Completed parent actions still reconstruct their original child after
        # result collection closes the allocation. Authenticate that exact
        # reservation; a different action cannot use it to launch again.
        ledger.put('launch_commission', reservation, identity=identity)
        return
    if any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('hpc_allocation_already_closed')
    ledger.put('launch_commission', reservation, identity=identity)


