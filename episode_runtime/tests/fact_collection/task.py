"""The task: which field to extract (given by the commissioner, or chosen by the model), the extraction
commission, and the confirmation tool.

The task always offers a unit and never ends the Episode: it confirms a fact record it has not confirmed yet, and
otherwise commissions an extraction. The Episode ends when its yield controller stops it (its credit reaches the
target once one fact is extracted and confirmed; an extraction that returns no fact record earns nothing)."""
import json

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

CHILD_SLOTS = {'extraction': 'fact_collection/fact_extraction'}

INSTRUCTIONS = ('Choose the one field of the subject record whose value is the most specific fact about the '
                'subject. Answer with that field name.')


def output_schema(fields):
    return {'type': 'object', 'additionalProperties': False, 'required': ['field'],
            'properties': {'field': {'type': 'string', 'enum': list(fields)}}}


def confirm_fact(arguments, ctx):
    """Read a returned fact record and who produced it."""
    records = ctx.store
    receipt = records.receipt(arguments['fact_ref'])
    fact = json.loads(records.get_artifact(arguments['fact_ref']))
    return {'fact_ref': arguments['fact_ref'], 'field': fact['field'], 'value': fact['value'],
            'produced_by': receipt['producer'], 'received_from': receipt['from']}


TOOLS = {'confirm_fact': confirm_fact}
SERVICES = ()


def decide(summary, feedback, ctx):
    unconfirmed = [ref for ref in summary['fact_refs'] if ref not in summary['confirmed']]
    if unconfirmed:
        return ToolCall('confirm_fact', {'fact_ref': unconfirmed[0]})
    if summary['field'] is not None:
        return ChildCall('extraction', {'field': summary['field']})
    return ModelRequest('FAST', INSTRUCTIONS, {'fields': summary['fields'], 'feedback': feedback},
                        output_schema(summary['fields']))


def action(response, summary, records, ctx):
    field = response.get('field') if isinstance(response, dict) else None
    if field not in summary['fields']:
        raise Rejected({'status': 'invalid', 'category': 'unknown_field', 'detail': repr(field)})
    return ChildCall('extraction', {'field': field})
