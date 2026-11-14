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


def initial_decision_context(self, context):
    """Supply actual job inputs and acceptance, without a setup recipe."""
    if context.role not in ('launch', 'launch_hpc'):
        return {}
    from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
    prefixes = [context.path[:i+1] for i, part in enumerate(context.path) if part[0] == 'hpc']
    if not prefixes:
        return {}
    # Runtime paths contain scope keys; compute the actual episode ID.
    owner = EpisodeRef(context.run_id, prefixes[-1]).episode_id
    ledger = HPCLedger.open_existing(self.directory/'hpc'/hpc_queue.digest([context.run_id, owner]))
    selected = plain(context.assignment)
    key = 'launch_assignment' if context.role == 'launch' else 'practical_assignment'
    plans = [row['body'] for row in ledger.records('plan') if row['body'][key] == selected]
    if len(plans) != 1 or ledger.read('owner')['scope'] != plain(context.scope):
        raise ValueError('hpc_launch_preparation_identity_conflict')
    plan = plans[0]
    from gene_annotation_episode.immutable_json_records import _immutable
    input_directory=ledger.path.parent/'launch-inputs'
    input_directory.mkdir(exist_ok=True)
    input_path=input_directory/(plan['plan_id']+'.json')
    _immutable(input_path,plan)
    return {'hpc_execution_job': {'plan_id':plan['plan_id'],
        'objective':ledger.commission['objective'],
        'scientific_manifest':deepcopy(plan['manifest']),
        'scientific_acceptance':deepcopy(ledger.commission['obligations']),
        'supplied_input_file':str(input_path.resolve()),
        'coordinator_workspace':str(self.directory.resolve()),
        'instructions':'The supplied local input file contains the frozen scientific manifest '
            'and reference source files. Use general terminal commands on the coordinator or '
            'assigned resource as needed; choose your scripts, environment and transfer method. '
            'Do not transcribe supplied source code into a child goal. Reference implementation '
            'files are available inputs, not a required execution procedure. Preserve original '
            'unit identities, scientific inputs, output/progress formats and acceptance predicates. '
            'Run computation in the actual allocation and retain its original identity. '
            'An uncertain submission must be investigated rather than duplicated.'}}

def original_launch_handoff(self, context):
    """Recover this frozen plan's actual receipt across Launch report repair.

    Inspect committed native outcomes only, never a sibling's conversation.
    Exact plan assignment, owning HPC path and scope authenticate the receipt.
    """
    if self.store is None or context.role != 'launch_hpc':
        return None
    from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
    prefixes = [context.path[:i+1] for i, part in enumerate(context.path) if part[0] == 'hpc']
    if not prefixes:
        return None
    owner_path = prefixes[-1]
    owner = EpisodeRef(context.run_id, owner_path).episode_id
    ledger = HPCLedger.open_existing(self.directory/'hpc'/hpc_queue.digest([context.run_id, owner]))
    selected = plain(context.assignment)
    plans = [row['body'] for row in ledger.records('plan') if row['body']['practical_assignment'] == selected]
    if len(plans) != 1 or ledger.read('owner')['scope'] != plain(context.scope):
        raise ValueError('hpc_original_handoff_plan_identity_conflict')
    rows = self.store.db.execute('SELECT e.path,a.result FROM runtime_actions a JOIN runtime_episodes e '
        'ON e.run_id=a.run_id AND e.episode_id=a.episode_id WHERE a.run_id=? '
        "AND json_extract(a.result,'$.result.outcome.facts.requested_job.handoff') IS NOT NULL "
        'ORDER BY a.rowid', (context.run_id,)).fetchall()
    for row in rows:
        path = tuple(tuple(part) for part in json.loads(row[0]))
        if path[:len(owner_path)] != owner_path:
            continue
        for reference in json.loads(row[1]).get('record_refs', []):
            try:
                target = self.targets.read_target(reference, context.scope)
            except (ValueError, KeyError):
                continue
            if target['assignment'] == selected:
                return reference
    return None

