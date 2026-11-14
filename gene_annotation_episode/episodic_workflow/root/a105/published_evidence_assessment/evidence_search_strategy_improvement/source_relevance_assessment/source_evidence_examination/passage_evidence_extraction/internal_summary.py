from __future__ import annotations
'Private internal summary responsibility for literature_targeted.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.source_contracts import _ACQUISITION_TOOLS, _READ_TOOLS, _population_catalog, identity, json, plain
from gene_annotation_episode.domain import ContractError

class LiteratureSummary:

    def initial_decision_context(self, context):
        """Caller literature job; an empty source list starts source discovery."""
        if self.reference_parent_sources is None or context.role != 'annotation' or len(context.path) != 1:
            return {}
        custody = []
        for reference in self.reference_parent_sources:
            if reference not in context.received_record_refs:
                raise ContractError('literature_parent_source_not_received')
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{name: source.get(name) for name in ('artifact_ref', 'text_ref', 'version', 'parent_source_refs')}})
        result = {'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': list(self.reference_parent_sources), 'source_custody': custody, 'child_population_operations': [{name: entry[name] for name in ('name', 'description')} for entry in _population_catalog(assay_grading_population=self._enabled('assay_grading_population', context), ratio_source_population=self.ratio_source_population, controlled_response_population=self.controlled_response_population, gel_population=self.gel_population, completion_time_population=self.completion_time_population, active_site_population=self.active_site_population, parent_depletion_population=self.parent_depletion_population, stoichiometric_balance_population=self.stoichiometric_balance_population, product_partition_population=self.product_partition_population, compiled_assay_population=self.compiled_assay_population, channel_population=self.channel_population, ion_discrimination_population=self.ion_discrimination_population)]}, 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'}}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_render import admitted_return_meanings
            result['literature_ratio_source_return_meanings'] = admitted_return_meanings(context, self._ratio_source_repository())
        if self.controlled_response_population:
            result['literature_controlled_response_return_bindings'] = self._controlled_response_bindings(context)
        if self.gel_population:
            result.update(self._gel_display_context(context))
        if self.rate_population:
            result.update(self._native_rate_display_context(context))
            result.update(self._native_rate_domain_display_context(context))
            result.update(self._native_rate_meaning_display_context(context))
            result.update(self._received_fact_display_context(context))
            result.update(self._endpoint_signal_display_context(context))
            result.update(self._summary_precision_display_context(context))
            result.update(self._measurement_comparison_display_context(context))
            result.update(self._concentration_window_display_context(context))
        if self.rate_population:
            result.update(self._population_task_context(context))
        result.update(self.current_report_facts(context))
        return result

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment('literature_targeted', context.assignment, context.scope, context=context)
        page = assignment.get('page')
        sources = [page['source_ref']] if page else assignment.get('source_refs', [])
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{key: source.get(key) for key in ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')}})
        result = {'literature_assignment': assignment, 'literature_source_custody': custody, 'own_literature_outcomes': plain(self.services.own_outcomes(context.episode_id, tools=(*_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)), 'literature_history_meaning': 'Own outcome metadata only. Read exact previous outcomes together through episode.history with view=records and selected decision_indices. The request_context own_attempt_detail lookup reads selected inputs only. Source delivery does not establish understanding, absence or resolved science.'}
        if self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_source_inputs import own_source_inputs
            examined = own_source_inputs(self.services.workflow.store, context)
            if examined:
                result['literature_examined_source_inputs'] = examined
        if self.rate_population:
            result['literature_experimental_work'] = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence', 'evidence_axis': 'A105'}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_render import admitted_return_meanings
            result['literature_ratio_source_return_meanings'] = admitted_return_meanings(context, self._ratio_source_repository())
        if self.controlled_response_population:
            result['literature_controlled_response_return_bindings'] = self._controlled_response_bindings(context)
        if self.gel_population:
            result.update(self._gel_display_context(context))
        if self.rate_population:
            result.update(self._native_rate_display_context(context))
            result.update(self._native_rate_domain_display_context(context))
            result.update(self._native_rate_meaning_display_context(context))
            result.update(self._received_fact_display_context(context))
            result.update(self._endpoint_signal_display_context(context))
            result.update(self._summary_precision_display_context(context))
            result.update(self._measurement_comparison_display_context(context))
            result.update(self._concentration_window_display_context(context))
        if self.rate_population:
            result.update(self._population_task_context(context))
        result.update(self.current_report_facts(context))
        if 'literature_task' in assignment:
            result['literature_goal_plan'] = self.planning_context(context)
        return result

    def _owned_population_task_sources(self, context):
        """Classify possessed own outputs using public metadata, read-only.

        No repository is constructed, no table is installed and no sheet or
        request artifact is opened. SQL extracts only successful operation
        metadata, never numerical cells or provider/source contents.
        """
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_task_selection import population_task_metadata_specs
        workflow = self.services.workflow
        if context.run_id != workflow.run_id:
            return ()
        db = workflow.store.db
        installed = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        selected = []
        table_rows = {}
        for source, flag, table, provider, versions in population_task_metadata_specs():
            if not getattr(self, flag) or table not in installed:
                continue
            if table not in table_rows:
                table_rows[table] = tuple(db.execute(f"SELECT operation_key, json_extract(outcome,'$.status') AS status, json_extract(outcome,'$.operation_ref') AS operation_ref, json_extract(outcome,'$.result.sheet_ref') AS sheet_ref, json_extract(outcome,'$.record_refs') AS record_refs FROM {table} WHERE run_id=? AND episode_id=? AND json_valid(outcome) ORDER BY rowid", (context.run_id, context.episode_id)))
            for row in table_rows[table]:
                reference = row['sheet_ref']
                if row['status'] != 'completed' or not isinstance(reference, str) or reference not in context.received_record_refs or (row['operation_ref'] != identity('operation', {'run_id': context.run_id, 'episode_id': context.episode_id, 'key': row['operation_key']})):
                    continue
                try:
                    references = json.loads(row['record_refs'] or 'null')
                    if not isinstance(references, list) or reference not in references:
                        continue
                    metadata = self._require(reference, context.scope, 'source')
                except (ContractError, ValueError, TypeError, KeyError):
                    continue
                if metadata.get('id') == reference and metadata.get('record_type') == 'source' and (metadata.get('origin') == 'tool') and (metadata.get('provider') == provider) and (metadata.get('version') in versions):
                    selected.append(source)
                    break
        return tuple(selected)

    def _population_task_context(self, context):
        """Own classification plus the latest actually selected failed action."""
        result = {'literature_owned_population_sources': self._owned_population_task_sources(context)}
        workflow = self.services.workflow
        if context.run_id != workflow.run_id:
            return result
        db = workflow.store.db
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_actions'").fetchone():
            return result
        row = db.execute("SELECT json_extract(action,'$.kind') AS kind,\n            json_extract(action,'$.tool') AS tool,\n            json_extract(action,'$.arguments.version') AS version,\n            json_extract(action,'$.arguments.population_version') AS population_version,\n            json_extract(result,'$.status') AS status\n            FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL\n            AND json_valid(action) AND json_valid(result)\n            ORDER BY decision_index DESC LIMIT 1", (context.run_id, context.episode_id)).fetchone()
        if row and row['kind'] == 'tool' and (row['status'] in ('invalid', 'failed', 'error')):
            result['literature_selected_population_attempt'] = {'tool': row['tool'], 'arguments': {name: row[name] for name in ('version', 'population_version') if row[name] is not None}, 'status': row['status']}
        return result

    def _concentration_window_display_context(self, context):
        return {'literature_concentration_window_receipt_bindings': self._concentration_window_repository().receipt_bindings()}

    def _measurement_comparison_display_context(self, context):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_storage import REQUESTED
        repo = self._measurement_comparison_repository()
        result = {'literature_measurement_comparison_receipt_bindings': repo.receipt_bindings()}
        return result

    def _summary_precision_display_context(self, context):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_summary_precision_storage import REQUESTED
        repo = self._summary_precision_repository()
        result = {'literature_summary_precision_receipt_bindings': repo.receipt_bindings()}
        return result

    def _endpoint_signal_display_context(self, context):
        repo = self._endpoint_signal_repository()
        result = {'literature_endpoint_receipt_bindings': repo.receipt_bindings()}
        return result

    def _controlled_response_bindings(self, context):
        """Host-only selected label locations, limited to this episode's possession."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import PROVIDER, COMPONENTS, VIEWS
        repository = self._controlled_response_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                keys = repository.requested_component_keys(reference, {'requested_controlled_response_components': list(COMPONENTS), 'requested_controlled_response_views': list(VIEWS)})
                rows.extend(repository.fact_cells(context, [reference], components=keys))
        unique = {}
        for row in rows:
            key = (row['sheet_ref'], row['component_key'])
            if key in unique and unique[key] != row:
                raise ContractError('controlled_response_possession_conflict')
            unique[key] = row
        return repository.semantic_bindings(list(unique.values()))

    def _gel_bindings(self, context):
        """Host-only selected label locations, limited to this episode's possession."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_storage import PROVIDER, COMPONENTS, VIEWS
        repository = self._gel_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                keys = repository.requested_component_keys(reference, {'requested_gel_components': list(COMPONENTS), 'requested_gel_views': list(VIEWS)})
                rows.extend(repository.fact_cells(context, [reference], components=keys))
        unique = {}
        for row in rows:
            key = (row['sheet_ref'], row['component_key'])
            if key in unique and unique[key] != row:
                raise ContractError('gel_possession_conflict')
            unique[key] = row
        return repository.semantic_bindings(list(unique.values()))

    def _gel_display_context(self, context):
        """Actual possessed meaning records, outside generic working-state pagination."""
        bindings = self._gel_bindings(context)
        records = {}
        for entries in bindings.values():
            for reference, binding in entries.items():
                if binding['category'] != 'scientific_meaning':
                    continue
                if binding['record_ref'] != reference or reference not in context.received_record_refs:
                    raise ContractError('gel_semantic_display_record_not_received')
                record = self._require(reference, context.scope, 'reference')
                if record.get('id') != reference or record.get('record_type') != 'reference':
                    raise ContractError('gel_semantic_display_record_mismatch')
                records[reference] = record
        return {'literature_gel_return_bindings': bindings, 'literature_gel_return_records': records}

    def _received_fact_display_context(self, context):
        """Possessed scientific metadata only, independent of working pagination.

        This map grants no source bytes or additional scientific references.
        The pure renderer selects the relevant dependency closure and applies
        existing operand maskers before presenting any of these records.
        """
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_received_fact_render import KINDS
        records = {}
        for reference in context.received_record_refs:
            kind = next((kind for kind in KINDS if reference.startswith(kind + '_')), None)
            if kind is None:
                continue
            record = self._require(reference, context.scope, kind)
            if record.get('id') != reference or record.get('record_type') != kind:
                raise ContractError('literature_received_fact_display_record_mismatch')
            records[reference] = record
        if self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_work_report import source_metadata
            records.update(source_metadata(self.services.workflow.store, context.received_record_refs))
        return {'literature_received_fact_display': {'records': records, 'received_refs': list(context.received_record_refs)}}

    def _native_rate_display_context(self, context):
        """Exact owned/admitted rate rows and possessed meaning-record metadata."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION, COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_source_render import MEANING_FIELDS
        repository = self.literature_rate_repository().source_projection()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get('record_type') == 'source' and record.get('provider') == PROVIDER and (record.get('version') == NATIVE_RECORD_VERSION):
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row['sheet_ref'], row['component'])
            if key in unique and unique[key] != row:
                raise ContractError('literature_rate_source_display_possession_conflict')
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError('literature_rate_source_display_record_not_received')
                record = self._require(reference, context.scope, namespace)
                if record.get('id') != reference or record.get('record_type') != namespace:
                    raise ContractError('literature_rate_source_display_record_mismatch')
                records[reference] = record
        return {'literature_rate_source_display': {'cells': list(unique.values()), 'records': records}}

    def _native_rate_domain_display_context(self, context):
        """Exact owned/admitted rate rows and possessed meaning-record metadata."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION, COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_source_render import MEANING_FIELDS
        repository = self.literature_rate_repository().source_domain_projection()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get('record_type') == 'source' and record.get('provider') == PROVIDER and (record.get('version') == NATIVE_RECORD_VERSION):
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row['sheet_ref'], row['component'])
            if key in unique and unique[key] != row:
                raise ContractError('literature_rate_source_domain_display_possession_conflict')
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError('literature_rate_source_domain_display_record_not_received')
                record = self._require(reference, context.scope, namespace)
                if record.get('id') != reference or record.get('record_type') != namespace:
                    raise ContractError('literature_rate_source_domain_display_record_mismatch')
                records[reference] = record
        return {'literature_rate_source_domain_display': {'cells': list(unique.values()), 'records': records}}

    def _native_rate_meaning_display_context(self, context):
        """Owned or exactly admitted meaning rows; known sheets grant no expansion."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION, COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_source_render import MEANING_FIELDS
        repository = self._native_rate_meaning_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get('record_type') == 'source' and record.get('provider') == PROVIDER and (record.get('version') == NATIVE_RECORD_VERSION):
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row['sheet_ref'], row['component'])
            if key in unique and unique[key] != row:
                raise ContractError('literature_rate_source_meaning_display_possession_conflict')
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError('literature_rate_source_meaning_display_record_not_received')
                record = self._require(reference, context.scope, namespace)
                if record.get('id') != reference or record.get('record_type') != namespace:
                    raise ContractError('literature_rate_source_meaning_display_record_mismatch')
                records[reference] = record
        return {'literature_rate_source_meaning_display': {'cells': list(unique.values()), 'records': records}}
