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


def instructions(self, context):
    return ('Iterate on a generalized time/resource model using measured historical cases. '
        'Refresh shared history, inspect support and held-out quality, fit a disjoint training selection, '
        'and compare useful portfolios. Inspect missing capacity, launcher and queue facts with '
        'lightweight discovery; propose executable resource alternatives when the parent has not '
        'supplied them. Preparation and submission belong to the execution sister. '
        'Forecast CPU time and memory demand as well as queue, setup '
        'and work time. Compare node/worker counts, memory capacity, workload parameters and elapsed cost. '
        'The paired execution episode owns Launch, monitoring and parsing. Both sisters use this '
        'parent-owned ledger; preserve model and comparison identities for that sibling. '
        'The fixed reference and validation set cannot change. Model credit is modest measured improvement; '
        'the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. '
        'Return when further model improvement is less useful than running the next worthwhile portfolio.')
