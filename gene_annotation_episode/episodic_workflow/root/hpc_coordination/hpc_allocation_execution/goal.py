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
    return ('Iterate toward the original accomplishment while balancing expected credit against real elapsed time '
        'and resource demand. This allocation execution episode prepares, launches, monitors and parses '
        'the selected work, using the original parent-owned ledger and prediction sister results. '
        'The assignment retains the original hpc parent owner_episode_id and exactly hpc_child_scope, '
        'including an empty subject_refs list '
        'for an operational task with no biological inputs. Candidate IDs, model IDs, queue '
        'observations and resource IDs are not biological subject_refs. Use hpc_report_form '
        'as the return contract. '
        'Use the shared current model and comparisons; resource observations and candidate requests are '
        'different quantities. If suitable history is available, a prediction iteration can improve sizing '
        'before launching. No historical validation support means no invented model-improvement credit. '
        'Queue/setup costs belong to an allocation, which should carry enough useful work. '
        'When candidates are absent, discover the remote environment and documentation with hpc.discovery.run, '
        'then design candidate portfolios with hpc.candidate.propose. Discover is for lightweight inspection; '
        'leave installation and file staging to Launch, and scientific computation to the actual allocation. '
        'You choose the real inputs, database, executable commands, resources, worker code and preparation instructions. '
        'Never fabricate inputs or receipts. Every work unit writes result.json and progress.json '
        'under os.environ["HPC_UNIT_DIRECTORY"], its original per-unit working directory. '
        'The allocation workspace is for staged inputs, not these unit outputs; '
        'its fields must satisfy the caller acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. '
        'Candidate files use relative paths; {allocation_workspace} expands in files, argv, environment and '
        'preparation. Compute commands must run on allocated compute nodes using the facility launcher. '
        'Compare portfolios '
        'using current queue features and measured history. A plan freezes its original forecast, '
        'scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that actual '
        'job and resource. The execution agent chooses its scripts, environment and operational commands '
        'from the supplied resource instructions and observations. Supplied reference sources are '
        'available in the local input file; do not transcribe them into a child goal or prescribe a '
        'setup/submit sequence. Use hpc_launch_report_form as the Launch return contract. '
        'If a completed Launch return omitted its receipt, use redeliver_report with the existing '
        'delivery_ref and hpc_launch_report_form; report repair must not commission another Launch. '
        'Attach that received handoff. Use hpc.monitor once when another '
        'observation can affect your decision; it revises conditional predictions and attainable credit. '
        'Use hpc.results directly for known parsing. Commission monitor/results children only for actual '
        'investigation. Completed unit outputs can await parsing while PBS is still running or cleaning up. '
        'When pending_action is collect, use hpc.results for those original outputs; completion is not acceptance. '
        'When hpc_monitor_controllers is present, select hpc.monitor.wait for a scheduled '
        'observation: its attached controller evaluates the conditional forecast, persists a wake time, '
        'and executes the original monitor at that time. This preserves pending accomplishment value '
        'across waits without credit for sleeping. The timer cannot turn into another unobserved wait. '
        'Do not poll for credit or duplicate a submitted attempt. Never replace an uncertain '
        'submission. Accepted accomplishment, model improvement, and fixed prospective forecast validation '
        'are the only parent credit components; launch-local credits are not added again.')

