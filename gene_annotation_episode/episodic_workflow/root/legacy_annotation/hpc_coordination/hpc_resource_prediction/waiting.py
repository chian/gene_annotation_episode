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


def continuation_for_action(self, context, operation_key):
    ledger = self.state(context)
    model_ref = self._current_model(ledger)
    available = set(self._history(ledger))-set(ledger.commission['validation_ids'])
    trained = set(ledger.read(model_ref)['training_ids'])
    candidates = {row['id'] for row in self._candidates(ledger)}
    comparisons = [row['body'] for row in ledger.records('comparison')
        if row['body']['model_ref'] == model_ref and row['body']['episode_id'] == context.episode_id
        and {item['candidate_id'] for item in row['body']['comparisons']} == candidates]
    # With no held-out cases, rereading/refitting the same measured data
    # has no supported incremental model credit. Once a trained model
    # and current comparisons exist, actual execution supplies the next
    # evidence. This bounds available action value, not action count.
    if (not ledger.commission['validation_ids'] and available <= trained
            and candidates and comparisons):
        latest = comparisons[-1]
        queue = self._queue(ledger, latest['queue_ref'])
        if time.time()-queue['captured_at'] <= ledger.commission['limits']['queue_max_age_seconds']:
            evidence = {'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation_key': operation_key, 'earned_wait_credit': 0.,
                'expected_continuation_credit': 0., 'active_credit_ceiling': 0.,
                'reason': 'prediction_ready_without_new_measured_improvement_opportunities',
                'model_ref': model_ref, 'training_ids': sorted(trained),
                'candidate_ids': sorted(candidates), 'comparison_operation': latest['operation_key'],
                'queue_ref': latest['queue_ref'],
                'scope': 'current_model_family_and_available_evidence; new observations reopen prediction'}
            reference = 'prediction-continuation:'+operation_key
            ledger.put('continuation', evidence, identity=reference)
            return {'reference': reference, 'evidence': evidence}
    return None
def practical_estimator(self, context):
    if context.role not in self.roles:
        return None
    from gene_annotation_episode.episodic_workflow.root.library.hpc_monitoring import HPCContinuationEstimator
    ledger = self.state(context)
    def verify(packet):
        return ledger.read(packet['reference']) == packet['evidence']
    return HPCContinuationEstimator(verify)

