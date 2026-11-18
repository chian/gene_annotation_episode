"""Private from child execution job submission for A104 hpc."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.a104 import hpc_queue
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain




class LaunchReceiptCustody:
    def original_launch_handoff(self, context):
        """Recover this frozen plan's actual receipt across Launch report repair.

        Inspect committed native outcomes only, never a sibling's conversation.
        Exact plan assignment, owning HPC path and scope authenticate the receipt.
        """
        if self.store is None or context.role != 'launch_hpc':
            return None
        from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
        prefixes = [context.path[:i+1] for i, part in enumerate(context.path) if part[0] == 'hpc']
        if not prefixes:
            return None
        owner_path = prefixes[-1]
        owner = EpisodeRef(context.run_id, owner_path).episode_id
        ledger = HPCLedger.open_existing(self.directory/'hpc'/hpc_queue.digest([context.run_id, owner]))
        selected = plain(context.assignment)
        plans = [row['body'] for row in ledger.records('plan') if row['body']['practical_assignment'] == selected]
        if len(plans) != 1 or ledger.read('owner')['scope'] != plain(context.scope):
            raise ValueError('hpc_original_handoff_plan_identity_conflict')
        rows = self.store.db.execute('SELECT e.path,a.result FROM runtime_actions a JOIN runtime_episodes e '
            'ON e.run_id=a.run_id AND e.episode_id=a.episode_id WHERE a.run_id=? '
            "AND json_extract(a.result,'$.result.outcome.facts.requested_job.handoff') IS NOT NULL "
            'ORDER BY a.rowid', (context.run_id,)).fetchall()
        for row in rows:
            path = tuple(tuple(part) for part in json.loads(row[0]))
            if path[:len(owner_path)] != owner_path:
                continue
            for reference in json.loads(row[1]).get('record_refs', []):
                try:
                    target = self.targets.read_target(reference, context.scope)
                except (ValueError, KeyError):
                    continue
                if target['assignment'] == selected:
                    return reference
        return None


from gene_annotation_episode.episodic_workflow.root.a104.runtime import _references_in, _json, WorkflowError, json

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        specialist = workflow.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(workflow.binding_context(source), child_role_for_delivery(workflow, source, index), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            workflow.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
    if workflow.receipts is None or workflow.is_job_source(source):
        return []
    references = _references_in({}, workflow.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: workflow.store.reference_subset(refs, source.scope))
    references.extend(workflow.episode_bindings.received_form_references(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if workflow.native_timing_information is not None and workflow.job_episodes is not None:
        with workflow.store.transaction():
            key = (workflow.run_id, source.episode_id, index)
            row = workflow.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = workflow.job_episodes.received_timing_records(workflow.store, admitted, schema, source.scope)
                workflow.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_json(received), *key))
            else:
                received = json.loads(row[0])
        references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
    workflow.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in workflow.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references
