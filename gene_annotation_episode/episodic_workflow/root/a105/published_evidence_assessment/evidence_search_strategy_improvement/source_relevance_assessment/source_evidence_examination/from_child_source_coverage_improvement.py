from __future__ import annotations

class FromSourceCoverageImprovement:

    def receive_source_coverage_improvement(self, context, form, schema, operation_key):
        if not self.rate_population:
            return []
        for namespace, _, _, _, repository in self._population_routes():
            cells = []
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') == namespace:
                    cells.extend(form[name])
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        window_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_concentration_window_cells' for row in form[name]]
        references.extend(self._concentration_window_repository().cell_record_refs(window_cells))
        comparison_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_measurement_comparison_cells' for row in form[name]]
        references.extend(self._measurement_comparison_repository().cell_record_refs(comparison_cells))
        summary_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_kinetic_summary_precision_cells' for row in form[name]]
        references.extend(self._summary_precision_repository().cell_record_refs(summary_cells))
        endpoint_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_endpoint_signal_cells' for row in form[name]]
        references.extend(self._endpoint_signal_repository().cell_record_refs(endpoint_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import NAMESPACE as COUPLING_NAMESPACE
        coupling_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == COUPLING_NAMESPACE for row in form[name]]
        references.extend(self._product_coupling_repository().cell_record_refs(coupling_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import NAMESPACE as VALIDATION_NAMESPACE
        validation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == VALIDATION_NAMESPACE for row in form[name]]
        references.extend(self._measurement_validation_repository().cell_record_refs(validation_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import NAMESPACE as RECOVERY_NAMESPACE
        recovery_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == RECOVERY_NAMESPACE for row in form[name]]
        references.extend(self.literature_calibration_recovery_repository().cell_record_refs(recovery_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import NAMESPACE as OBSERVATION_NAMESPACE
        observation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == OBSERVATION_NAMESPACE for row in form[name]]
        references.extend(self.literature_rate_observation_repository().cell_record_refs(observation_cells))
        grid_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_rate_grid_cells' for row in form[name]]
        references.extend(self._rate_grid_repository().cell_record_refs(grid_cells))
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_replicate_storage import NAMESPACE as REPLICATE_NAMESPACE
        replicate_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == REPLICATE_NAMESPACE for row in form[name]]
        references.extend(self.literature_rate_replicate_repository().cell_record_refs(replicate_cells))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._ion_discrimination_repository().cell_record_refs(cells))
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_channel_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._channel_repository().cell_record_refs(cells))
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE, NAMESPACE_V2, NAMESPACE_V3
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') in {NAMESPACE, NAMESPACE_V2, NAMESPACE_V3} for row in form[name]]
            references.extend(self._compiled_assay_repository().cell_record_refs(cells))
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._assay_grading_repository().cell_record_refs(cells))
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._a105_aggregation_repository().cell_record_refs(cells))
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_partition_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._product_partition_repository().cell_record_refs(cells))
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_completion_time_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._completion_time_repository().cell_record_refs(cells))
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._active_site_repository().cell_record_refs(cells))
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_parent_depletion_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._parent_depletion_repository().cell_record_refs(cells))
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_stoichiometric_balance_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._stoichiometric_balance_repository().cell_record_refs(cells))
        if self.controlled_response_population:
            adapter = self._controlled_response_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_controlled_response_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        if self.gel_population:
            adapter = self._gel_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_gel_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        return list(dict.fromkeys(references))

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    from gene_annotation_episode.episodic_workflow.root.a105.runtime import _references_in, json, _json
    from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a105.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        workflow.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form')
    if workflow.receipts is None or workflow.is_job_source(source):
        return []
    references = _references_in({}, workflow.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: workflow.store.reference_subset(refs, source.scope))
    references.extend(workflow.specialist(source).receive_source_coverage_improvement(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form'))
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
    return references
