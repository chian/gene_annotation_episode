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


def __init__(self, services, *, store, run_id, directory, resources, commissions,
             shared_execution_memory=None, require_commission_yield=False):
    self.services, self.store, self.run_id = services, store, run_id
    self.directory = Path(directory)
    self.resources = plain(resources)
    commissions = plain(commissions)
    if not isinstance(commissions, dict):
        raise ValueError('explicit_hpc_commissions_required')
    if not any(row.get('kind') == 'pbs_ssh' for row in self.resources.values()):
        raise ValueError('explicit_hpc_resource_required')
    self.commissions = {key: validate_commission(plain(value), self.resources)
                        for key, value in commissions.items()}
    if type(require_commission_yield) is not bool:
        raise TypeError('hpc_private_yield_binding_requires_boolean')
    self.private_yield_binding = require_commission_yield
    if require_commission_yield and any('yield_bindings' not in value
            for value in self.commissions.values()):
        raise ValueError('hpc_static_commission_yield_binding_required')
    self._targets = None
    from gene_annotation_episode.execution_memory import ExecutionMemory
    self.memory = (None if shared_execution_memory is None else
                   ExecutionMemory(**plain(shared_execution_memory)))

def targets(self):
    if self._targets is None:
        from gene_annotation_episode.episodic_workflow.root.library.execution_progress import ExecutionTargetReader
        self._targets = ExecutionTargetReader(self.store, run_id=self.run_id, directory=self.directory,
            resources={key: value for key, value in self.resources.items() if value['kind'] == 'pbs_ssh'},
            api_execution=None)
    return self._targets

