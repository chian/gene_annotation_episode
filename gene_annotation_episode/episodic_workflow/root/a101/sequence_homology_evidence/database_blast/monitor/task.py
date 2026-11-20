"""The task: check the assigned job through the job service, one check per unit, waiting for the provider's spacing
between two status requests. Nothing here is a decision of a model: ``decide`` returns the next unit from the state of the
visit, so the model is never asked (``action`` exists because the system requires the member; it is never reached).

The one unit, ``check_when_allowed``, first waits as long as the decision says and then makes one status request through
``job_access.check`` on the held handoff row; the job service writes the check row with the route's reply as its artifact.
How long to wait is the provider's rule, read from the route: after a check that left the job unfinished the next one
comes one poll spacing later (the public service asks for a minute between two status requests of one job), and after a
request the route refused as too early it comes when the route says it may (``retry_after_seconds``). A job that has
ended is answered by the route from its record at once, so no wait precedes it. There is no deadline: the visit ends
when a check showed a new fact (the controller's completion), or when further checks stop being expected to earn.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``)."""
import asyncio
from datetime import datetime, timezone

from episode_runtime import ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import status_reading

CHILD_SLOTS = {}
SERVICES = ('job_access',)
ENDED = ('finished', 'failed', 'cancelled', 'unknown')
SPACING_MARGIN_SECONDS = 0.5


async def check_when_allowed(arguments, ctx):
    """Wait, then one check of the job. A request the route could not answer is the returned ``failed`` outcome: no
    check row is written."""
    if arguments['wait_seconds'] > 0:
        await asyncio.sleep(arguments['wait_seconds'])
    return ctx.services['job_access'].check(ctx, arguments['handoff_ref'], assess=status_reading)


TOOLS = {'check_when_allowed': check_when_allowed}


def _moment(text):
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def wait_before_next_check(summary, ctx):
    """Seconds to wait before the next status request: what the route asked after a refused request, or the poll
    spacing after a check that left the job unfinished, less the time already passed."""
    if not summary['units']:
        return 0.0
    last = summary['units'][-1]
    if last['retry_after_seconds'] is not None:
        return last['retry_after_seconds'] + SPACING_MARGIN_SECONDS
    if last['status'] != 'completed' or last['state'] in ENDED:
        return 0.0
    spacing = ctx.services['job_access'].read('describe', summary['resource_id']).get('poll_spacing_seconds', 0)
    elapsed = (_moment(ctx.clock.now) - _moment(last['observed_at'])).total_seconds()
    return max(0.0, spacing - elapsed) + SPACING_MARGIN_SECONDS if spacing else 0.0


def decide(summary, feedback, ctx):
    """The next unit: one check of the job, after the wait the provider's spacing calls for."""
    return ToolCall('check_when_allowed', {'handoff_ref': summary['handoff_ref'],
                                           'wait_seconds': wait_before_next_check(summary, ctx)})


def action(response, summary, records, ctx):
    raise TypeError('database_blast_monitor_asks_no_model_so_no_response_is_ever_acted_on')
