"""Private work operations for A102 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a102.communication import plain
from gene_annotation_episode.episodic_workflow.root.a102.domain import validate_schema

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


class HPCWorkOperations:
    def catalog(self, context):
        shared = [('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})), ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.', obj({'model_ref': TEXT, 'queue_ref': TEXT}))]
        if self.memory:
            shared.append(('hpc.history.refresh', 'Read age-weighted shared timing history once. No remote discovery, polling credit, or new scientific work.', obj({})))
        shared += [('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the established SSH transport. No job submission, installation or scientific computation; those belong to Launch and the allocation.', obj({'command': TEXT})), ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities are immutable.', obj({'candidate_json': TEXT})), ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({}))]
        entries = shared + [('hpc.plan', 'Freeze one useful portfolio and its forecasts; return a concrete launch assignment.', obj({'candidate_id': TEXT, 'model_ref': TEXT, 'queue_ref': TEXT})), ('hpc.handoff', 'Bind the original received PBS handoff to the exact frozen portfolio.', obj({'plan_ref': TEXT, 'handoff_ref': TEXT})), ('hpc.monitor', 'Observe the original job and progress once; update and freeze conditional forecasts.', obj({'plan_ref': TEXT, 'refresh_queue': {'type': 'boolean'}})), ('hpc.monitor.wait', 'Use the attached forecast-valued monitor controller: persist a timer, release the coordinator while waiting, then observe this original job exactly once when due. No earned credit for waiting.', obj({'plan_ref': TEXT})), ('hpc.results', 'Parse compact results from the original allocation and apply original acceptance predicates.', obj({'plan_ref': TEXT})), ('hpc.allocation.order', 'Reorder original pending units at the next unit boundary, retaining all unstarted work.', obj({'plan_ref': TEXT, 'unit_ids': STRINGS}))]
        return [{'name': name, 'description': description, 'input_schema': schema} for name, description, schema in entries]

    async def execute(self, context, tool_name, arguments, operation_key):
        entries = {row['name']: row for row in self.catalog(context)}
        if tool_name not in entries:
            raise ValueError('tool_not_available_to_hpc_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        selection = {'tool': tool_name, 'arguments': arguments, 'episode_id': context.episode_id}
        old = ledger.cached(operation_key, selection)
        if old is not None:
            return old
        ledger.put('action_intent', selection, identity='action:' + operation_key)
        references = []
        commission = ledger.commission
        configuration = self.resources[commission['resource_id']]
        if tool_name == 'hpc.read':
            return await self._read_retained_evidence(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.history.refresh':
            return await self._refresh_measured_history(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.discovery.run':
            return await self._discover_resource(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.candidate.propose':
            return await self._propose_portfolio(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.queue.observe':
            return await self._observe_resource_queue(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.compare':
            return await self._compare_portfolios(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.plan':
            return await self._freeze_portfolio_plan(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        elif tool_name == 'hpc.handoff':
            return await self._attach_original_handoff(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
        else:
            return await self._work_on_original_allocation(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration)
