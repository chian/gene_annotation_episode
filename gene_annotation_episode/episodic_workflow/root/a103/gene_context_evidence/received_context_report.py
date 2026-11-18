"""Original own-A103 Scientific received_report_facts."""
from ..communication import plain
from ..domain import ContractError
from ..a103_investigation import CONTEXT_RECORD_SOURCE, received_context_records


def received_report_facts(binding, context, completion_snapshot, schema):
    if not any(node.get('x-source') == CONTEXT_RECORD_SOURCE
            for node in schema.get('properties', {}).values()):
        return {}
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a103_report_store_required')
    return {CONTEXT_RECORD_SOURCE: received_context_records(workflow.store,
        context.received_record_refs, plain(context.scope),
        committed=completion_snapshot.get('committed_record_refs', ()))}
