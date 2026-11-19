"""Resource adapters: the run's bindings of resource ids to the code that works through each resource.

``ResourceAdapters`` is a service of the run. An episode that works through whichever resource its assignment
selects declares it (as ``resource_adapter`` or ``resources``: the name is the episode's) and reaches the selected
resource only through it. The run's caller builds it from the **declared capabilities** (every resource the run
knows of, bound or not) and the **bound adapters** (``{resource_id: adapter}``).

An assignment or a handoff selects its resource in ``['resource_selection']['resource_id']``. A selection that
names no bound adapter raises ``LookupError('resource_not_bound:<id>')``: an episode that offers the selection to
its model checks ``is_bound`` first.

| Member | For | Gives |
|---|---|---|
| ``declared_capabilities()`` | a decision (read handle) or a tool | the declared capabilities |
| ``adapter_capabilities()`` | the same | ``{resource_id: capability}`` of the bound adapters |
| ``bound_resource_ids()``, ``is_bound(resource_id)`` | the same | which resources are bound |
| ``catalog(assignment)`` | the same | the tools of the selected adapter: ``[{'name', 'description', 'input_schema'}]`` |
| ``decision_context(assignment)``, ``facts(assignment)`` | the same | what the selected adapter says of its resource for this assignment |
| ``prepare_assignment(ctx, assignment)`` | a tool | the assignment as the selected adapter completes it |
| ``await execute(ctx, assignment, tool, arguments)`` | a tool | the outcome of one tool of the selected adapter |
| ``await check_handoff(ctx, handoff)`` | a tool | the outcome of the receiving check of the adapter the handoff selects |

**Custody is the adapter's, through ``ctx``.** The three acting members hand the tool's ``ctx`` to the adapter,
which reads and writes records only through ``ctx.store`` and is idempotent on ``ctx.operation_key``. Nothing an
adapter returns is a record in custody unless the adapter wrote it through ``ctx.store``.

Credit is not a member: an Episode's credit is its own ``credit.py`` over its summary and the records it holds.
Whether a report is valid is not a member either: it reads nothing outside the Episode.

The adapter protocol is the members ``capability()``, ``catalog(assignment)``, ``decision_context(assignment)``,
``facts(assignment)``, ``prepare_assignment(ctx, assignment)``, ``execute(ctx, assignment, tool, arguments)`` and
``check_handoff(ctx, handoff)``; the last two may be coroutines.
"""
from __future__ import annotations

from collections.abc import Mapping
import inspect

from method_loop.jsonvalue import closed_copy

ADAPTER_MEMBERS = ('capability', 'catalog', 'decision_context', 'facts', 'prepare_assignment', 'execute',
                   'check_handoff')


class ResourceAdapters:
    """The declared capabilities and the bound adapters of one run."""

    def __init__(self, declared, adapters):
        declared = closed_copy(declared, 'declared_capabilities', TypeError)
        if not isinstance(declared, list) or any(not isinstance(item, dict) or 'resource_id' not in item
                                                 for item in declared):
            raise ValueError('declared_capabilities_must_be_a_list_of_records_with_resource_id')
        identifiers = [item['resource_id'] for item in declared]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('declared_capabilities_repeat_a_resource_id')
        if not isinstance(adapters, Mapping):
            raise TypeError('resource_adapters_must_be_a_mapping_of_resource_id_to_adapter')
        for resource_id, adapter in adapters.items():
            missing = [name for name in ADAPTER_MEMBERS if not callable(getattr(adapter, name, None))]
            if missing:
                raise TypeError('resource_adapter_lacks:' + str(resource_id) + ':' + ','.join(missing))
            if resource_id not in identifiers:
                raise ValueError('bound_resource_is_not_declared:' + str(resource_id))
        self._declared, self._adapters = declared, dict(adapters)

    def _selected(self, selecting):
        resource_id = selecting['resource_selection']['resource_id']
        if resource_id not in self._adapters:
            raise LookupError('resource_not_bound:' + str(resource_id))
        return self._adapters[resource_id]

    # -- reads -----------------------------------------------------------------------------------------------
    def declared_capabilities(self):
        return closed_copy(self._declared, 'declared_capabilities', TypeError)

    def adapter_capabilities(self):
        return {resource_id: closed_copy(self._adapters[resource_id].capability(), 'adapter_capability', TypeError)
                for resource_id in sorted(self._adapters)}

    def bound_resource_ids(self):
        return sorted(self._adapters)

    def is_bound(self, resource_id):
        return resource_id in self._adapters

    def catalog(self, assignment):
        return closed_copy(self._selected(assignment).catalog(assignment), 'adapter_catalog', TypeError)

    def decision_context(self, assignment):
        return closed_copy(self._selected(assignment).decision_context(assignment), 'adapter_decision_context',
                           TypeError)

    def facts(self, assignment):
        return closed_copy(self._selected(assignment).facts(assignment), 'adapter_facts', TypeError)

    # -- acts ------------------------------------------------------------------------------------------------
    def prepare_assignment(self, ctx, assignment):
        return closed_copy(self._selected(assignment).prepare_assignment(ctx, assignment), 'prepared_assignment',
                           TypeError)

    async def execute(self, ctx, assignment, tool, arguments):
        adapter = self._selected(assignment)
        if tool not in [entry['name'] for entry in adapter.catalog(assignment)]:
            raise LookupError('resource_tool_not_in_the_adapters_catalog:' + str(tool))
        outcome = adapter.execute(ctx, assignment, tool, arguments)
        return await outcome if inspect.isawaitable(outcome) else outcome

    async def check_handoff(self, ctx, handoff):
        outcome = self._selected(handoff).check_handoff(ctx, handoff)
        return await outcome if inspect.isawaitable(outcome) else outcome


__all__ = ['ADAPTER_MEMBERS', 'ResourceAdapters']
