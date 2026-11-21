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
import os
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    DRIVER_NAME, PLAN_NAME, RECEIPT_NAME, compile_preparation, describe_fasta, validate_commission, validate_plan)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    checked_analysis_kind, derived_analysis_kind)
from episode_runtime.job_access import JOB_LEDGER
from gene_annotation_episode.episodic_workflow.episode_support.jobs.pbs_batch_job import pbs_batch_job
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_preparation_receipt import (
    evaluate)
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_features, prepared_values, put_prepared)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    blast_preparation_driver)

DRIVER_SOURCE = Path(inspect.getsourcefile(blast_preparation_driver)).read_bytes()
ENDED = ('finished', 'failed', 'cancelled')

def _staged(ctx, compiled):
    """The plan and the driver kept as artifacts the Episode holds, and the job's inputs ``{name: reference}``."""
    plan = validate_plan(compiled['plan'])
    if derived_analysis_kind(plan) != compiled['kind']:
        raise ValueError('blast_preparation_declared_and_derived_kind_differ')
    with ctx.store.transaction():
        plan_ref = ctx.store.artifact(compiled['plan_bytes'], 'application/json')
        driver_ref = ctx.store.artifact(DRIVER_SOURCE, 'text/x-python')
    return plan_ref, {name: {'input': plan['input']['artifact_ref'], 'plan': plan_ref, 'driver': driver_ref}[role]
                      for name, role in compiled['inputs'].items()}


async def launch_preparation(ctx, resource_id, compiled, *, allocation=None):
    """Stage and launch the compiled preparation job on ``resource_id``; returns the job service's launch outcome
    (``handoff_ref`` is the handoff row to return in a ``record_refs`` field) plus ``plan_ref``, the artifact of the
    plan the job runs. A refused launch is returned, never raised, and writes no row.

    The caller has already checked the kind: ``compile_preparation`` derives it again from the compiled plan."""
    plan_ref, inputs = _staged(ctx, compiled)
    access = ctx.services['job_access']
    kind = access.describe(resource_id)['kind']
    if kind == 'local':
        launched = await execute_on_local_resource(ctx, resource_id, compiled['job']['command'],
                                                   compiled['job']['env'], wait=False, inputs=inputs,
                                                   estimates=compiled['estimates'])
    elif kind == 'pbs':
        launched = access.launch(ctx, resource_id, pbs_batch_job(compiled['job']['command'], allocation), inputs=inputs,
                                 estimates=compiled['estimates'])
    else:
        raise ValueError('blast_preparation_resource_kind_not_placed:' + str(kind))
    return {**launched, 'plan_ref': plan_ref}


def establish_prepared(ctx, plan, plan_bytes, receipt, catalog, *, resource_id, job, plan_ref, receipt_ref,
                       handoff_ref, closure_ref):
    """Evaluate the receipt of an ended job against the plan and the route's listing and write the prepared-data
    row, usable or not. Returns the row, the evaluation and the row's values."""
    evaluation = evaluate(plan, hashlib.sha256(plan_bytes).hexdigest(), receipt, catalog, ended=True)
    values = prepared_values(plan, evaluation, resource_id=resource_id, job=job, plan_ref=plan_ref,
                             receipt_ref=receipt_ref, handoff_ref=handoff_ref, closure_ref=closure_ref)
    return put_prepared(ctx, values), evaluation, values


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
    row, evaluation, values = establish_prepared(ctx, plan, plan_bytes, receipt, catalog, resource_id=resource_id,
                                                 job=job, plan_ref=plan_ref, receipt_ref=receipt_ref,
                                                 handoff_ref=handoff_ref,
                                                 closure_ref=fetched.get('closure_ref') if fetched['status'] == 'completed' else None)
    closure_ref = values['closure_ref']
    refs = [row['id'], checked['check_ref']] + ([closure_ref] if closure_ref else [])
    return {'status': 'completed', 'state': checked['state'], 'check_ref': checked['check_ref'],
            'prepared': {'ref': row['id'], 'state': evaluation['state'], 'usable': evaluation['usable'],
                         'failure_codes': evaluation['failure_codes'], 'features': prepared_features(values)},
            'record_refs': refs}


PROGRAMS = {'database_build': ('makeblastdb', 'blastdbcmd')}
JOB_NAME = 'preparation'
PROBLEM_CODES = ('resource_not_bound', 'resource_not_local', 'kind_differs_from_commission', 'commission_invalid',
                 'input_not_held', 'input_not_parsable', 'input_above_local_bound', 'program_missing',
                 'python_missing', 'job_not_compilable')


def software_identities(executable_directory, programs):
    """``{program: {executable, sha256, engine_version}}`` of the BLAST programs in ``executable_directory``: the
    resource's own configuration (a commission carries no path)."""
    found = {}
    for program in programs:
        executable = (Path(executable_directory) / program).resolve()
        found[program] = {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                          'engine_version': None}
    return found


def _programs(fields):
    return PROGRAMS['database_build'] if fields['kind'] == 'database_build' else (fields['program'],)


def preparation_problems(call, *, fields, records, resources, executable_directory, python):
    """The one deterministic check of a ``launch_local`` call, made before anything runs. ``call`` is the model's
    JSON (``resource_id``, ``kind``); ``fields`` the commission's controlled fields; ``records`` what the Episode
    holds; ``resources`` ``{resource_id: the route's description}`` of the bound resources. Returns the list of
    things to fix, each ``{'code', 'field', 'detail'}`` (empty when the call can simply run). Conditions, in order:
    the resource is bound; it is local; the call's kind is the commission's kind; the commission is a valid job
    description; the input set is held; it parses as a FASTA of the molecule; it is within the resource's local size
    bound (``policy.scratch_bytes``); each program the job runs exists; the Python of the job exists; the job
    compiles (which derives its kind from the plan and compares it with the declared one)."""
    problems = []

    def add(code, field, detail=None):
        problems.append({'code': code, 'field': field, 'detail': detail})
    resource = resources.get(call['resource_id'])
    if resource is None:
        add('resource_not_bound', 'resource_id')
    elif resource['kind'] != 'local':
        add('resource_not_local', 'resource_id')
    if call['kind'] != fields['kind']:
        add('kind_differs_from_commission', 'kind')
    try:
        validate_commission(fields)
    except ValueError as error:
        add('commission_invalid', 'commission', str(error))
        return problems
    data = None
    if not records.holds(fields['input_ref']):
        add('input_not_held', 'input_ref')
    else:
        data = records.get_artifact(fields['input_ref'])
        try:
            describe_fasta(data, molecule=fields['molecule'], parse_seqids=fields.get('parse_seqids', False))
        except ValueError as error:
            add('input_not_parsable', 'input_ref', str(error))
    if data is not None and resource is not None and len(data) > resource['policy']['scratch_bytes']:
        add('input_above_local_bound', 'resource_id')
    for program in _programs(fields):
        if not os.access(Path(executable_directory) / program, os.X_OK):
            add('program_missing', 'program', program)
    if not os.access(python, os.X_OK):
        add('python_missing', 'python')
    if not problems:
        try:
            compile_preparation(fields, input_bytes=data, software=software_identities(
                executable_directory, _programs(fields)), python=python)
        except ValueError as error:
            add('job_not_compilable', 'commission', str(error))
    return problems


async def prepare_locally(ctx, resource_id, fields, *, executable_directory, python):
    """The whole local preparation as one unit, for a call that passed ``preparation_problems``: build the job
    from the commission, check the kind derived from the plan against the declared one, launch it on the local
    resource, wait for its end, fetch what it left, decide ``usable`` from the receipt and write the prepared-data
    record through custody. Returns ``{'status': 'usable'|'failed'|'incomplete', 'failure_code', 'retryable' (always
    false: the same checked call gives the same outcome), 'failure_codes', 'prepared_ref', 'features',
    'record_refs', 'handoff_ref', 'closure_ref', 'files'}``; ``files`` are the result files the job left, each ``{'name',
    'ref', 'bytes', 'sha256'}`` (a database's files are under ``db/``), which the all-vs-all child packs into one product."""
    compiled = compile_preparation(fields, input_bytes=ctx.store.get_artifact(fields['input_ref']),
                                   software=software_identities(executable_directory, _programs(fields)),
                                   python=python)
    checked_analysis_kind(fields['kind'], compiled['plan'])
    plan_ref, inputs = _staged(ctx, compiled)
    ran = await execute_on_local_resource(ctx, resource_id, compiled['job']['command'], compiled['job']['env'],
                                          wait=True, inputs=inputs, name=JOB_NAME)
    if ran['status'] != 'completed':
        code = 'job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched'
        return {'status': 'failed', 'failure_code': code, 'retryable': False, 'failure_codes': [code],
                'prepared_ref': None, 'features': None, 'record_refs': [plan_ref], 'handoff_ref': None,
                'closure_ref': None, 'files': []}
    fetched = ran['fetch']
    receipt_ref = next((item['ref'] for item in fetched['results'] if item['name'] == RECEIPT_NAME), None)
    receipt = None if receipt_ref is None else json.loads(ctx.store.get_artifact(receipt_ref))
    catalog = json.loads(ctx.store.get_artifact(fetched['reply_ref']))['catalog']
    row, evaluation, values = establish_prepared(
        ctx, compiled['plan'], compiled['plan_bytes'], receipt, catalog, resource_id=resource_id,
        job=ran['launch']['job'], plan_ref=plan_ref, receipt_ref=receipt_ref, handoff_ref=ran['launch']['handoff_ref'],
        closure_ref=fetched['closure_ref'])
    codes = evaluation['failure_codes']
    return {'status': evaluation['state'], 'failure_code': codes[0] if codes else None, 'retryable': False,
            'failure_codes': codes, 'prepared_ref': row['id'], 'features': prepared_features(values),
            'record_refs': [row['id'], ran['launch']['handoff_ref'], fetched['closure_ref']],
            'handoff_ref': ran['launch']['handoff_ref'], 'closure_ref': fetched['closure_ref'], 'files': fetched['results']}


__all__ = ['DRIVER_SOURCE', 'PROBLEM_CODES', 'acquire_prepared_data', 'establish_prepared', 'launch_preparation',
           'prepare_locally', 'preparation_problems', 'software_identities']
