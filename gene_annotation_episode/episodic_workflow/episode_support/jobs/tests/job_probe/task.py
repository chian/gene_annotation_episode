"""The task: run the plan of the commission, one tool unit per step.

A plan step is ``{'tool': name, 'arguments': {...}}``. An argument written ``{'from': i, 'field': [path...]}`` is
replaced, when the step is decided, by that field of the outcome of plan step ``i`` (a handoff reference a later
check needs). A step may carry ``'read': [service, member, argument...]``: ``decide`` then reads that member
through the service's read handle and hands the value to the tool as its ``read`` argument, so the test sees what a
decision read and what the system recorded of it. The task asks no model. It always offers a unit and never ends
the Episode: after the plan it offers ``idle``; the yield controller stops the Episode at the plan's last step."""
from datetime import datetime, timezone

from episode_runtime import Rejected, ToolCall
from episode_runtime.job_access import JOB_LEDGER

from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_prediction import (
    log_score)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_resource_prediction import (
    forecast_metric, measured_value)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue, hpc_remote
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table', 'native_events', 'resource_adapter', 'instruction_libraries', 'switch')


def _cut(arguments, ctx):
    """The test's interruption: raise after the step's effect when the plan asks for it and the switch is on."""
    if arguments['cut'] and ctx.services['switch'].fail:
        raise RuntimeError('cut after the effect of ' + ctx.operation_key)


def idle(arguments, ctx):
    return {'idle': True}


def echo(arguments, ctx):
    """Return the arguments: what ``decide`` read from a service."""
    return dict(arguments)


def launch(arguments, ctx):
    """Launch one job. ``cut`` is ``None``, ``'after'`` (the handoff row committed, then the unit is cut) or
    ``'inside'`` (the unit is cut before the row commits: the job was submitted and no record of it is held)."""
    jobs = ctx.services['job_access']
    if arguments['cut'] == 'inside' and ctx.services['switch'].fail:
        with ctx.store.transaction():
            jobs.launch(ctx, arguments['resource_id'], arguments['job'], inputs=arguments['inputs'],
                        estimates=arguments['estimates'])
            raise RuntimeError('cut before the handoff row committed')
    outcome = jobs.launch(ctx, arguments['resource_id'], arguments['job'], inputs=arguments['inputs'],
                          estimates=arguments['estimates'])
    _cut(arguments, ctx)
    return outcome


def assess(status, handoff):
    """This episode's own reading of a status reply, kept in the check row."""
    return {'state_seen': status['state'], 'handoff_at': handoff['at']}


def check(arguments, ctx):
    outcome = ctx.services['job_access'].check(ctx, arguments['handoff_ref'], assess=assess)
    _cut(arguments, ctx)
    return outcome


def fetch(arguments, ctx):
    outcome = ctx.services['job_access'].fetch(ctx, arguments['handoff_ref'], names=arguments['names'])
    _cut(arguments, ctx)
    return outcome


def cancel(arguments, ctx):
    return ctx.services['job_access'].cancel(ctx, arguments['handoff_ref'])


def window(arguments, ctx):
    """One byte window of a file of the job (a log while it runs), in custody."""
    outcome = ctx.services['job_access'].window(ctx, arguments['handoff_ref'], arguments['name'],
                                                offset=arguments['offset'], limit=arguments['limit'])
    _cut(arguments, ctx)
    return outcome


async def command(arguments, ctx):
    """A command the unit waits for: launched once, waited for, its results fetched."""
    return await ctx.services['job_access'].run(ctx, arguments['resource_id'], arguments['job'],
                                               inputs=arguments['inputs'])


async def wait(arguments, ctx):
    """Wait for the end of the job of a held handoff row; the event's receipt comes into custody."""
    row = ctx.store.table(JOB_LEDGER).get(arguments['handoff_ref'])
    condition = {'version': 'event_condition_v1', 'reconsider_at': None, 'events': [
        {'handle': row['detail']['native']['event_target'], 'event': 'state_changed', 'after_cursor': 0}]}
    return await ctx.services['native_events'].wait(ctx, condition)


async def wait_condition(arguments, ctx):
    return await ctx.services['native_events'].wait(ctx, arguments['condition'])


def expect(arguments, ctx):
    return ctx.services['estimate_table'].expect(arguments['kind'], arguments['expectation'],
                                                 key=ctx.operation_key if arguments['key'] is None
                                                 else arguments['key'],
                                                 at=datetime.now(timezone.utc).isoformat())


def resolve(arguments, ctx):
    return ctx.services['estimate_table'].resolve(arguments['key'], arguments['actual'],
                                                  at=datetime.now(timezone.utc).isoformat())


def measure(arguments, ctx):
    """One resource observation and one attempt measurement in the estimate table."""
    table = ctx.services['estimate_table']
    reference = table.observe(arguments['resource'], 'queue', arguments['queue'], observed_at=arguments['at'],
                              provenance=[ctx.operation_key])
    table.record(attempt_id=arguments['attempt_id'], profile=arguments['profile'],
                 observation=arguments['observation'])
    return {'observation_ref': reference,
            'latest': table.latest(arguments['resource'], 'queue', arguments['at'] + 1),
            'history': table.history(arguments['profile'], arguments['at'] + 1)}


def ledger_forecast(arguments, ctx):
    """Open the HPC ledger of the commission and freeze one forecast, as a prediction unit does."""
    ledger = HpcLedger.open(ctx.store, arguments['commission'])
    forecast = ledger.freeze(arguments['forecast'], arguments['slots'])
    return {'ledger': ledger.ledger, 'forecast': forecast, 'reserved': ledger.reserved_slots(), 'refs': ledger.refs()}


def ledger_score(arguments, ctx):
    """Record a measurement, score it, accept an obligation and credit the model, as an allocation unit does."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    measured = ledger.put('measured', arguments['measured'])
    scores = ledger.score(measured, log_score=log_score, measured_value=measured_value,
                          forecast_metric=forecast_metric)
    ledger.accept(arguments['obligation'], arguments['result_ref'])
    ledger.model_credit(arguments['model_ref'], arguments['improvement'])
    return {'measured': measured, 'scores': scores, 'credit_view': ledger.credit_view(),
            'kinds': {kind: len(ledger.records(kind)) for kind in ('forecast', 'measured', 'score', 'accept')},
            'refs': ledger.refs()}


def ledger_conflict(arguments, ctx):
    """Other content under a held identity is refused."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    ledger.put('note', {'text': 'first'}, identity='note_one')
    try:
        ledger.put('note', {'text': 'second'}, identity='note_one')
    except ValueError as error:
        return {'refused': str(error), 'again': ledger.put('note', {'text': 'first'}, identity='note_one')}
    return {'refused': None}


def ledger_source(arguments, ctx):
    """Evidence made from an artifact of this unit: the row names the artifact in its ``source_refs``."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    artifact = ctx.store.artifact(arguments['text'].encode(), 'text/plain')
    identity = ledger.put('launch_input', {'artifact_ref': artifact}, identity=arguments['identity'],
                          source_refs=[artifact])
    return {'identity': identity, 'artifact': artifact, 'refs': ledger.refs()}


def ledger_read_source(arguments, ctx):
    """Read the artifact a held row names: it is held only when it was passed with the row."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    artifact = ledger.read(arguments['identity'])['artifact_ref']
    return {'text': ctx.store.get_artifact(artifact).decode(), 'refs': ledger.refs()}


async def remote_write(arguments, ctx):
    """Publish a file on the resource from an artifact of this unit (``hpc_remote.write_file``)."""
    artifact = ctx.store.artifact(arguments['text'].encode(), 'text/plain')
    return await hpc_remote.write_file(ctx, arguments['resource_id'], arguments['path'], artifact, name='write')


async def remote_read(arguments, ctx):
    """A bounded read of a file on the resource (``hpc_remote.read_file``)."""
    return await hpc_remote.read_file(ctx, arguments['resource_id'], arguments['path'], arguments['limit'],
                                      name='read')


async def remote_queue(arguments, ctx):
    """One queue observation on the resource (``hpc_queue.observe``)."""
    return await hpc_queue.observe(ctx, arguments['resource_id'])


def adapter_prepare(arguments, ctx):
    return ctx.services['resource_adapter'].prepare_assignment(ctx, arguments['assignment'])


async def adapter_execute(arguments, ctx):
    return await ctx.services['resource_adapter'].execute(ctx, arguments['assignment'], arguments['tool'],
                                                          arguments['arguments'])


async def adapter_check(arguments, ctx):
    return await ctx.services['resource_adapter'].check_handoff(ctx, arguments['handoff'])


def lookup(arguments, ctx):
    return ctx.services['instruction_libraries'].execute(arguments['name'], arguments['arguments'])


TOOLS = {'idle': idle, 'echo': echo, 'launch': launch, 'check': check, 'fetch': fetch, 'cancel': cancel,
         'window': window, 'command': command, 'wait': wait, 'wait_condition': wait_condition, 'expect': expect, 'resolve': resolve,
         'measure': measure, 'ledger_forecast': ledger_forecast, 'ledger_score': ledger_score,
         'ledger_conflict': ledger_conflict, 'ledger_source': ledger_source,
         'ledger_read_source': ledger_read_source, 'remote_write': remote_write, 'remote_read': remote_read,
         'remote_queue': remote_queue, 'adapter_prepare': adapter_prepare, 'adapter_execute': adapter_execute,
         'adapter_check': adapter_check, 'lookup': lookup}


def _resolved(value, outcomes):
    """``value`` with every ``{'from': i, 'field': [path...]}`` replaced by that field of plan step ``i``'s outcome."""
    if isinstance(value, dict):
        if set(value) == {'from', 'field'}:
            found = outcomes[value['from']]['outcome']
            for name in value['field']:
                found = found[name]
            return found
        return {name: _resolved(item, outcomes) for name, item in value.items()}
    if isinstance(value, list):
        return [_resolved(item, outcomes) for item in value]
    return value


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    arguments = _resolved(item['arguments'], summary['outcomes'])
    if 'read' in item:
        service, member, *given = _resolved(item['read'], summary['outcomes'])
        arguments = {**arguments, 'read': ctx.services[service].read(member, *given)}
    return ToolCall(item['tool'], arguments)


def action(response, summary, records, ctx):
    raise Rejected({'job_probe': 'this episode asks no model'})
