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


def credit_kind(self, role):
    if role not in self.roles:
        raise ValueError('unknown_hpc_role')
    return 'operational'

def credit_view(self, context, receiver_selection):
    ledger = self.state(context)
    entries = ledger.records('model_entry')
    entry = next((row['body'] for row in entries if row['id'] == 'entry:'+context.episode_id), None)
    current = self._quality(ledger, ledger.read(self._current_model(ledger)))
    gain = current-entry['quality'] if entry and current is not None and entry['quality'] is not None else 0.
    validation = sum(row['credit'] for row in ledger.credit_view()['contributions']
        if row['kind'] == 'validation' and
        ledger.read(row['evidence_id']).get('prediction_episode_id') == context.episode_id)
    return {'credit': ledger.commission['credit']['model_scale']*gain+validation,
            'model_quality_improvement': gain, 'prospective_validation_credit': validation,
            'actual_job_credit_counted_here': False}
