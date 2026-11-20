"""Launching a BLAST data-preparation job and acquiring its prepared-data record, through custody.

Two operations for the tools of a launching Episode and of a results Episode. Both go through the run's
``job_access`` service with the tool's ``ctx``; neither opens a file of the resource, writes the Store directly or
runs a program itself.

``launch_preparation`` stores the compiled plan and the driver as artifacts the Episode holds, stages them with the
input under the names the plan expects, and launches the job on the resource: a local resource through the library's
one inspection point for local execution, a PBS resource as a batch script built from the allocation the commission
carries. The allocation is passed through, never chosen here: a scheduler that needs an account, a queue, a node
selection, a walltime and a filesystem gets exactly what the commission supplied, and a commission that lacks one
fails with its error. The walltime is a scheduler operand, separate from the Episode's continuation, which belongs to
the yield estimator alone.

``acquire_prepared_data`` is for the Episode that holds the handoff row. The plan is read from the handoff row's own
staged inputs (what was actually launched, not what a commission claims), its kind is derived from it and compared
with the kind the commission declared; a difference raises. It asks the job's state once; a job that has
not ended is reported as it stands and nothing is written. A job that has ended: only the receipt is fetched (a
database's files stay on the resource and are never copied into custody), the receipt is evaluated against the plan
and the route's listing (``readers/.../blast_preparation_receipt.py``), and the prepared-data row is written, usable
or not. A product that is not usable is still recorded, with its failure codes: the Episode learned something.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    DRIVER_NAME, PLAN_NAME, RECEIPT_NAME, validate_plan)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    derived_analysis_kind)
from episode_runtime.job_access import JOB_LEDGER
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    evaluate)
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_features, prepared_values, put_prepared)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    blast_preparation_driver)

DRIVER_SOURCE = Path(inspect.getsourcefile(blast_preparation_driver)).read_bytes()
ENDED = ('finished', 'failed', 'cancelled')
PBS_FIELDS = ('account', 'queue', 'select', 'walltime', 'filesystems')
_OPERAND = re.compile(r'^[A-Za-z0-9_.:=+@,-]+$')


def pbs_job(compiled, allocation, *, env=None):
    """The batch job of ``compiled`` for a PBS resource: a script that runs the driver in the job's directory and
    the qsub operands of ``allocation`` (``account``, ``queue``, ``select``, ``walltime``, ``filesystems``, each a
    plain operand). Nothing is defaulted: a missing or malformed operand is a wrong commission."""
    if type(allocation) is not dict or set(allocation) != set(PBS_FIELDS):
        raise ValueError('blast_preparation_pbs_allocation_fields')
    for name in PBS_FIELDS:
        if type(allocation[name]) is not str or not _OPERAND.match(allocation[name]):
            raise ValueError('blast_preparation_pbs_allocation_operand:' + name)
    python = compiled['job']['command'][0]
    script = '#!/bin/bash\ncd "$PBS_O_WORKDIR" || exit 2\n' + python + ' ' + DRIVER_NAME + ' ' + PLAN_NAME + '\n'
    arguments = ['-A', allocation['account'], '-q', allocation['queue'], '-l', 'select=' + allocation['select'],
                 '-l', 'walltime=' + allocation['walltime'], '-l', 'filesystems=' + allocation['filesystems']]
    return {'mode': 'batch', 'script': script, 'arguments': arguments, 'env': dict(env or {})}


async def launch_preparation(ctx, resource_id, compiled, *, allocation=None):
    """Stage and launch the compiled preparation job on ``resource_id``; returns the job service's launch outcome
    (``handoff_ref`` is the handoff row to return in a ``record_refs`` field) plus ``plan_ref``, the artifact of the
    plan the job runs. A refused launch is returned, never raised, and writes no row.

    The caller has already checked the kind: ``compile_preparation`` derives it again from the compiled plan."""
    plan = validate_plan(compiled['plan'])
    if derived_analysis_kind(plan) != compiled['kind']:
        raise ValueError('blast_preparation_declared_and_derived_kind_differ')
    with ctx.store.transaction():
        plan_ref = ctx.store.artifact(compiled['plan_bytes'], 'application/json')
        driver_ref = ctx.store.artifact(DRIVER_SOURCE, 'text/x-python')
    inputs = {name: {'input': plan['input']['artifact_ref'], 'plan': plan_ref, 'driver': driver_ref}[role]
              for name, role in compiled['inputs'].items()}
    access = ctx.services['job_access']
    kind = access.describe(resource_id)['kind']
    if kind == 'local':
        launched = await execute_on_local_resource(ctx, resource_id, compiled['job']['command'],
                                                   compiled['job']['env'], wait=False, inputs=inputs,
                                                   estimates=compiled['estimates'])
    elif kind == 'pbs':
        launched = access.launch(ctx, resource_id, pbs_job(compiled, allocation), inputs=inputs,
                                 estimates=compiled['estimates'])
    else:
        raise ValueError('blast_preparation_resource_kind_not_placed:' + str(kind))
    return {**launched, 'plan_ref': plan_ref}


def acquire_prepared_data(ctx, handoff_ref, *, declared_kind):
    """Establish the prepared-data record of the job of the held handoff row.

    ``declared_kind``: the kind the commission declared. The plan the job ran is the artifact staged under
    ``plan.json`` in the handoff row; its kind is derived from its steps and must equal ``declared_kind``.

    Returns ``{'status': 'completed', 'state': <job state>, 'prepared': None}`` while the job has not ended, or
    ``{'status': 'completed', 'prepared': {'ref', 'state', 'usable', 'failure_codes', 'features'},
    'record_refs': [...]}`` once the row is written. A request the job service refuses is returned as it returns
    it (``status`` ``failed``)."""
    access = ctx.services['job_access']
    handoff = ctx.store.table(JOB_LEDGER).get(handoff_ref)
    resource_id, job = handoff['detail']['resource_id'], handoff['job']
    plan_ref = handoff['detail']['input_refs'].get(PLAN_NAME)
    if plan_ref is None:
        raise ValueError('blast_preparation_handoff_has_no_staged_plan')
    plan_bytes = ctx.store.get_artifact(plan_ref)
    plan = validate_plan(json.loads(plan_bytes))
    if derived_analysis_kind(plan) != declared_kind:
        raise ValueError('blast_preparation_declared_and_derived_kind_differ')
    checked = access.check(ctx, handoff_ref)
    if checked['status'] != 'completed':
        return checked
    if checked['state'] not in ENDED:
        return {'status': 'completed', 'state': checked['state'], 'prepared': None, 'check_ref': checked['check_ref'],
                'record_refs': [checked['check_ref']]}
    fetched = access.fetch(ctx, handoff_ref, names=[RECEIPT_NAME])
    receipt, catalog, receipt_ref = None, [], None
    if fetched['status'] == 'completed':
        item = fetched['results'][0]
        receipt_ref = item['ref']
        try:
            receipt = json.loads(ctx.store.get_artifact(receipt_ref))
        except ValueError:
            receipt = None
        catalog = json.loads(ctx.store.get_artifact(fetched['reply_ref']))['catalog']
    elif fetched['failure']['code'] != 'result_not_in_catalog':
        return fetched
    evaluation = evaluate(plan, hashlib.sha256(plan_bytes).hexdigest(), receipt, catalog, ended=True)
    closure_ref = fetched.get('closure_ref') if fetched['status'] == 'completed' else None
    values = prepared_values(plan, evaluation, resource_id=resource_id, job=job, plan_ref=plan_ref,
                             receipt_ref=receipt_ref, handoff_ref=handoff_ref, closure_ref=closure_ref)
    row = put_prepared(ctx, values)
    refs = [row['id'], checked['check_ref']] + ([closure_ref] if closure_ref else [])
    return {'status': 'completed', 'state': checked['state'], 'check_ref': checked['check_ref'],
            'prepared': {'ref': row['id'], 'state': evaluation['state'], 'usable': evaluation['usable'],
                         'failure_codes': evaluation['failure_codes'], 'features': prepared_features(values)},
            'record_refs': refs}


__all__ = ['DRIVER_SOURCE', 'PBS_FIELDS', 'acquire_prepared_data', 'launch_preparation', 'pbs_job']
