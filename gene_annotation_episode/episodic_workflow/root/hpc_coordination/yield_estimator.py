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


def yield_controller(self, context, initial_credit, epoch):
    """Bind the original HPC episode's active and pending work forecast."""
    self.credit_kind(context.role)
    if not self.private_yield_binding:
        raise ValueError('hpc_episode_yield_binding_required:' + context.role)
    from gene_annotation_episode.episodic_workflow.root.numerical import YieldController, YieldParameters
    commission = self._commission(context.assignment, context.scope)
    if 'yield_bindings' not in commission:
        raise ValueError('hpc_commission_yield_binding_required:' + context.role)
    chosen = commission['yield_bindings'][context.role]
    estimator = self.practical_estimator(context).with_continuation_cost(chosen['cutoff'])
    return YieldController(epoch, initial_credit, chosen['cutoff'],
        YieldParameters(**chosen['parameters']), estimate_with_context=estimator)

