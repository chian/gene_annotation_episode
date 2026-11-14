from __future__ import annotations
'internal summary for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import ContractError, _A108_ACQUISITION_TOOLS, _READ_TOOLS, _a108_population_catalog, identity, json, plain

class LiteratureSummary:

    def initial_decision_context(self, context):
        if self.reference_parent_sources is None or context.role != 'annotation' or len(context.path) != 1:
            return {}
        custody = []
        for reference in self.reference_parent_sources:
            if reference not in context.received_record_refs:
                raise ContractError('literature_parent_source_not_received')
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{name: source.get(name) for name in ('artifact_ref', 'text_ref', 'version', 'parent_source_refs')}})
        result = {'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'evidence_axis': 'A108', 'source_refs': list(self.reference_parent_sources), 'source_custody': custody, 'child_population_operations': [{name: entry[name] for name in ('name', 'description')} for entry in _a108_population_catalog()]}, 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'}}
        result.update(self._received_fact_display_context(context))
        result.update(self._population_task_context(context))
        result.update(self.current_report_facts(context))
        return result

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment('literature_strategy', context.assignment, context.scope, context=context)
        page = assignment.get('page')
        sources = [page['source_ref']] if page else assignment.get('source_refs', [])
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{key: source.get(key) for key in ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')}})
        result = {'literature_assignment': assignment, 'literature_source_custody': custody, 'own_literature_outcomes': plain(self.services.own_outcomes(context.episode_id, tools=(*_A108_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)), 'literature_history_meaning': 'Own outcome metadata only. Read exact previous outcomes together through episode.history with view=records and selected decision_indices. Source delivery does not establish understanding, absence or resolved science.'}
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_source_inputs import own_source_inputs
        examined = own_source_inputs(self.services.workflow.store, context)
        if examined:
            result['literature_examined_source_inputs'] = examined
        result['literature_experimental_work'] = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence', 'evidence_axis': 'A108'}
        result.update(self._received_fact_display_context(context))
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
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_task_families import population_task_metadata_specs
        workflow = self.services.workflow
        if context.run_id != workflow.run_id:
            return ()
        db = workflow.store.db
        installed = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        selected = []
        table_rows = {}
        for source, table, provider, versions in population_task_metadata_specs():
            if table not in installed:
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

    def _received_fact_display_context(self, context):
        kinds = frozenset({'reference', 'term', 'context', 'observation', 'hypothesis', 'assessment'})
        records = {}
        for reference in context.received_record_refs:
            kind = next((kind for kind in kinds if reference.startswith(kind + '_')), None)
            if kind is None:
                continue
            record = self._require(reference, context.scope, kind)
            if record.get('id') != reference or record.get('record_type') != kind:
                raise ContractError('literature_received_fact_display_record_mismatch')
            records[reference] = record
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_work_report import source_metadata
        records.update(source_metadata(self.services.workflow.store, context.received_record_refs))
        return {'literature_received_fact_display': {'records': records, 'received_refs': list(context.received_record_refs)}}
