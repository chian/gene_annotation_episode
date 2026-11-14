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


def fact_sources(self, role):
    self.credit_kind(role)
    return {'hpc_credit': {'type': 'number', 'meaning': 'Signed measured credit; repeated polling adds none.'},
            'hpc_model_ref': {'type': 'string', 'meaning': 'Immutable selected prediction model identity.',
                'report_schema': {'type': 'string', 'format': 'reference',
                    'x-reference-namespace': 'hpc_model', 'x-source': 'hpc_model_ref'}},
            'hpc_accepted_obligations': {'type': 'array', 'meaning': 'Original obligations with accepted actual results.'},
            'hpc_result_refs': {'type': 'array', 'meaning': 'Sources containing original result bytes and attempt custody.',
                'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
                    'x-source': 'hpc_result_refs'}}}

