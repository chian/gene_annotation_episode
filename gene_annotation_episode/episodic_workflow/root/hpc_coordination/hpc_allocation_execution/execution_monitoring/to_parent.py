from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.library.report_fact_assembly import facts as _private_report_facts
from gene_annotation_episode.domain import ContractError
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.progress_observations import _REFS
from gene_annotation_episode.episodic_workflow.root.progress_observations import _STATES
from gene_annotation_episode.episodic_workflow.root.task_values import _json
from gene_annotation_episode.episodic_workflow.root.progress_observations import _timestamp
from gene_annotation_episode.episodic_workflow.root.progress_observations import _unique
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import form_with_facts
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.communication import validate_form

def fact_sources(self, role):
    self._role(role)
    definitions = {'monitoring_progress_refs': (_REFS, 'Original delivered progress observation identities, including admitted requested child updates.'), 'monitoring_target_handle': ({'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handle'}, 'The immutable assigned semantic target handle.'), 'monitoring_execution_state': ({'type': ['string', 'null'], 'enum': [*_STATES, None]}, 'Assigned target state in the latest delivered observation; unknown without an observation.'), 'monitoring_result_available': ({'type': ['boolean', 'null']}, 'Assigned target result availability in the latest delivered observation.'), 'monitoring_observed_at_unix_seconds': ({'type': ['number', 'null'], 'minimum': 0}, 'Original assigned-target observation time, converted from UTC without refreshing it.'), 'monitoring_committed_record_refs': (_REFS, 'Parent-permitted committed records actually delivered in these progress observations.'), 'monitoring_dependency_handles': ({'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handle'}}, 'Exposed direct dependencies in the latest delivered assigned-target observation; no descendant traversal.')}
    result = {}
    for name, (schema, meaning) in definitions.items():
        schema = deepcopy(schema)
        if name == 'monitoring_progress_refs':
            schema['items'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'episode_progress'}
        elif name == 'monitoring_committed_record_refs':
            schema['items'] = {'type': 'string', 'format': 'reference'}
        result[name] = {'type': schema['type'], 'meaning': meaning, 'report_schema': {**schema, 'x-source': name}}
    return result

def facts(self, context, completion_snapshot):
    self._role(context.role)
    assignment = self._assignment(context.assignment, context.scope)
    refs = self._received(context)
    snapshots = [self.services.read_progress(ref, context.scope) for ref in refs]
    target = [row for row in snapshots if row['target_handle'] == assignment['target_handle']]
    latest = target[-1] if target else None
    return {'monitoring_progress_refs': refs, 'monitoring_target_handle': assignment['target_handle'], 'monitoring_execution_state': latest['execution_status']['lifecycle_state'] if latest else None, 'monitoring_result_available': latest['result_available'] if latest else None, 'monitoring_observed_at_unix_seconds': _timestamp(latest['observed_at']).timestamp() if latest else None, 'monitoring_committed_record_refs': _unique((ref for row in snapshots for ref in row['committed_record_refs'] if self.services.read_record(ref)['record_type'] in assignment['permitted_committed_record_types'])), 'monitoring_dependency_handles': [row['handle'] for row in latest['dependencies']] if latest else []}

def resolve(self, context, reference, namespace):
    self._role(context.role)
    received = self._received(context)
    if namespace in ('episode_progress', 'progress', 'progress_snapshot'):
        return reference in received
    if namespace is None and reference in received:
        return True
    if namespace in (None, 'execution_handle', 'execution'):
        assignment = self._assignment(context.assignment, context.scope)
        handles = {assignment['target_handle']}
        for ref in self._received(context):
            snapshot = self.services.read_progress(ref, context.scope)
            handles.add(snapshot['target_handle'])
            handles.update((row['handle'] for row in snapshot['dependencies']))
        if reference in handles:
            return True
        if namespace is not None:
            return False
    if namespace is None:
        try:
            self.services.read_progress(reference, context.scope)
        except (ContractError, KeyError):
            pass
        else:
            return False
    return reference_in_context(self.services, context, reference, namespace)

def validate_report(self, context, form, original_schema):
    assignment = self._assignment(context.assignment, context.scope)
    validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
    facts = self.facts(context, {})
    for name, schema in original_schema['properties'].items():
        source = schema.get('x-source')
        if source in facts and plain(form[name]) != facts[source]:
            raise ContractError('monitor_recorded_fact_mismatch', detail={'field': name})
    permitted = set(facts['monitoring_committed_record_refs'])

    def visit(value, schema):
        if value is None:
            return
        if isinstance(value, Mapping):
            for name, item in value.items():
                visit(item, schema['properties'][name])
        elif isinstance(value, list):
            for item in value:
                visit(item, schema['items'])
        elif isinstance(value, str) and schema.get('format') in {'reference', 'identifier', 'accession'}:
            namespace = schema.get('x-reference-namespace')
            if namespace in ('episode_progress', 'progress', 'progress_snapshot', 'execution', 'execution_handle'):
                return
            try:
                record = self.services.read_record(value)
            except (ContractError, KeyError):
                return
            if record['record_type'] not in assignment['permitted_committed_record_types'] or value not in permitted:
                raise ContractError('monitor_record_not_permitted_or_received')
    visit(plain(form), plain(original_schema))

class MonitorTaskReport:

    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = json.loads(saved['form'])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _json({**facts, 'interpretations': self.report_values}), 'form': _json(form)})
        await self.workflow.release(self.episode_id)
        return Record({'form': form})
