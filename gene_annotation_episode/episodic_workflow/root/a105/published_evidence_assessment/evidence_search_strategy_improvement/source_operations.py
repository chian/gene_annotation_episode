from __future__ import annotations
'Private source operations responsibility for literature_strategy.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import plain, validate_schema
from gene_annotation_episode.domain import ContractError

class LiteratureSourceOperations:

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment('literature_strategy', context.assignment, context.scope, context=context)
        entries = {entry['name']: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError('tool_not_available_to_literature_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        page = assignment.get('page')
        if page:
            selected_arguments = arguments['arguments'] if tool_name == 'execution.estimate' else arguments
            source_ref = selected_arguments.get('source_ref')
            if tool_name == 'source.archive.extract':
                member = self._require(arguments['member_ref'], context.scope, 'archive_member')
                source_ref = member['source_ref']
            if source_ref is not None and (not self._within_source(source_ref, page['source_ref'], context.scope)):
                from gene_annotation_episode.episodic_workflow.root.a105.library.literature_source_access import rejection_detail
                raise ContractError('literature_reading_outside_assigned_source', detail=rejection_detail(getattr(self.services, 'workflow', None), context, page['source_ref'], [source_ref]))
            if tool_name in {'literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.calibration.recovery.populate', 'literature.rate.observations.populate', 'literature.rate.replicates.populate', 'literature.rate.source.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.ratio.source.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.figure.populate', 'literature.amount.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.product_partition.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.assay_grading.populate', 'literature.a105.aggregate'}:

                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key == 'metadata_source_ref' and isinstance(child, str):
                                yield child
                                continue
                            if (key == 'sheet_ref' and tool_name in {'literature.assay_grading.populate', 'literature.a105.aggregate', 'literature.measurement_validation.populate', 'literature.assay.components.populate', 'literature.ion_discrimination.populate'} or (key == 'original_source_ref' and tool_name == 'literature.binding.interaction.populate') or key in {'source_ref', 'covariance_source_ref', 'activity_covariance_source_ref', 'model_source_ref', 'km_sheet_ref', 'data_source_ref', 'coordinate_source_ref', 'validation_source_ref'}) and isinstance(child, str):
                                yield child
                            elif key == 'covariance_source_refs' and tool_name == 'literature.measurement_comparison.populate':
                                yield from child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                    elif isinstance(value, str) and (value in arguments.get('visual_source_refs', ()) or value in arguments.get('covariance_source_refs', ())):
                        yield value
                blocked = next((ref for ref in set(sources(arguments)) if not self._within_source(ref, page['source_ref'], context.scope)), None)
                if blocked is not None:
                    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_source_access import rejection_detail
                    raise ContractError('literature_reading_outside_assigned_source', detail=rejection_detail(getattr(self.services, 'workflow', None), context, page['source_ref'], [blocked]))
        if self.rate_population:
            repo = self._endpoint_signal_repository()
            if tool_name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}:
                representation = 'original' if tool_name in {'source.sequence.references', 'source.experimental.records'} else arguments.get('representation', 'text')
                repo.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._summary_precision_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._measurement_comparison_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._concentration_window_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            elif tool_name == 'state.query' and 'refs' in arguments:
                for ref in arguments['refs']:
                    repo.authorize_record_access(context, self.services.read_record(ref))
                    self._summary_precision_repository().authorize_record_access(context, self.services.read_record(ref))
                    self._measurement_comparison_repository().authorize_record_access(context, self.services.read_record(ref))
                    self._concentration_window_repository().authorize_record_access(context, self.services.read_record(ref))
        return arguments

    def _materialize_text_arguments(self, context, arguments, repository, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import materialize_text_witness_inputs, saved_text_witness_inputs
        saved = saved_text_witness_inputs(arguments, repository=repository, episode_id=context.episode_id, operation_key=operation_key)
        if saved is not None:
            return saved

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)
