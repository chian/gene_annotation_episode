"""Connect this exact private resource task and its explicit responsibilities."""
from __future__ import annotations
from .configuration import ResourceConfiguration
from .binding_record import ResourceBindingRecord
from .child_commissioning import ResourceChildCommissioning
from .from_parent import ResourceFromParent
from .resource_selection import ResourceResourceSelection
from .goal import ResourceGoal
from .internal_summary import ResourceInternalSummary
from .operations import ResourceOperations
from .to_parent import ResourceToParent
from .received_messages import ResourceReceivedMessages
from .credit import ResourceCredit
from .task import ResourceTask

class ResourceEpisode(ResourceConfiguration, ResourceBindingRecord, ResourceChildCommissioning, ResourceFromParent, ResourceResourceSelection, ResourceGoal, ResourceInternalSummary, ResourceOperations, ResourceToParent, ResourceReceivedMessages, ResourceCredit):
    decision_source_type = ResourceTask
    binding_path = 'scientific_process/resource_result_acquisition'
    commissioning_parent = 'scientific_process'
    "C7 binding; all iteration/commissioning remains in shared method_loop.\n\n    Adapter API: resource_id, capability(), as_record(), prepare_assignment(\n    context, role, launch_assignment, scope, operation_key), catalog(context),\n    execute(context, tool_name, arguments, operation_key), fact_sources(role),\n    facts(context, completion_snapshot), resolve(context, reference, namespace),\n    validate_report(context, form, original_schema), credit_view(context,\n    receiver_selection). An optional decision_context(context) supplies actual\n    prospective duration information. An adapter's tool list is authoritative.\n    "
    roles = ('results',)
    entry_roles = ('results',)

    def permitted_common_actions(self, context):
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
