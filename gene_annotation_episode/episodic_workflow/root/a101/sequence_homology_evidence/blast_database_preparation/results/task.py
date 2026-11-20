"""The task: establish the prepared-data record of one launched job. Every decision is made by code.

- ``prepared_data_acquire`` asks the job once (``job_access.check``). While the job has not ended it returns the state
  and writes nothing. Once it has ended it fetches only the receipt (a database's files stay on the resource), checks
  the receipt against the plan the job ran and the route's listing, and writes the prepared-data row, usable or not:
  the check, the fetch and the evaluation are one step (``acquire_prepared_data``). The kind the commission declared
  is compared with the kind derived from the plan that ran; a difference raises.
- ``job_wait`` waits ``settings['wait_seconds']`` and asks the job again (``wait_for_job``). It earns nothing. The wait
  is a pause between two status requests; the Episode has no deadline.
- ``prepared_read``: the prepared-data row the Episode holds, read again. It earns nothing.

``decide``: with no row held, an acquisition when none was made or the last one followed a wait, a wait when the
last acquisition found the job not ended; with a row held, ``prepared_read``. The task always offers a unit and
never ends the Episode: only the yield controller stops it. The results of a long job can come after this Episode
has ended not established; its parent commissions the results again.

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and
``wait_seconds``, the pause of one wait (a number, 0 or more)."""
from episode_runtime import ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence.blast_preparation_run import (
    acquire_prepared_data)
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_rows)

CHILD_SLOTS = {}
SERVICES = ('job_access',)


def prepared_data_acquire(arguments, ctx):
    """One acquisition: ask the job and, when it has ended, fetch the receipt and write the record."""
    return acquire_prepared_data(ctx, arguments['handoff_ref'], declared_kind=arguments['declared_kind'])


async def job_wait(arguments, ctx):
    """Wait one pause, then ask the job again."""
    return await wait_for_job(ctx, arguments['handoff_ref'], seconds=ctx.settings['wait_seconds'])


def prepared_read(arguments, ctx):
    """The prepared-data rows this Episode holds, read again. It earns nothing."""
    return {'status': 'completed', 'prepared_refs': [row['id'] for row in prepared_rows(ctx.store)]}


TOOLS = {'prepared_data_acquire': prepared_data_acquire, 'job_wait': job_wait, 'prepared_read': prepared_read}


def decide(summary, feedback, ctx):
    arguments = {'handoff_ref': summary['handoff_ref'], 'declared_kind': summary['declared_kind']}
    if summary['prepared_refs']:
        return ToolCall('prepared_read', {})
    if summary['last_tool'] == 'prepared_data_acquire':
        return ToolCall('job_wait', arguments)
    return ToolCall('prepared_data_acquire', arguments)


def action(response, summary, records, ctx):
    """``decide`` returns the unit itself, so no model response ever reaches this function."""
    raise ValueError('blast_preparation_results_decides_by_code')
