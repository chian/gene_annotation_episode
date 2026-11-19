"""The task: read each passed record in turn until one has the field, and write the fact record.

The task always offers a unit and never ends the Episode. The Episode ends when its yield controller stops it:
its credit reaches the commission's target when the field is found, or when every passed record has been read."""
import json

from episode_runtime import Rejected, ToolCall

CHILD_SLOTS = {}


def extract_field(arguments, ctx):
    """Read one passed record; when it has the field, write the fact record."""
    records = ctx.store
    source = json.loads(records.get_artifact(arguments['source_ref']))
    if arguments['field'] not in source:
        return {'source_ref': arguments['source_ref'], 'found': False}
    fact_ref = records.artifact(json.dumps({'field': arguments['field'], 'value': source[arguments['field']],
                                                  'source_ref': arguments['source_ref']}, sort_keys=True),
                                      'application/json')
    return {'source_ref': arguments['source_ref'], 'found': True, 'value': source[arguments['field']],
            'fact_ref': fact_ref}


TOOLS = {'extract_field': extract_field}
SERVICES = ()


def decide(summary, feedback, ctx):
    """The next passed record that was not read yet (the controller has stopped the Episode before none is left)."""
    unread = [ref for ref in summary['source_refs'] if ref not in summary['read']]
    return ToolCall('extract_field', {'source_ref': unread[0], 'field': summary['field']})


def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by reading'})
