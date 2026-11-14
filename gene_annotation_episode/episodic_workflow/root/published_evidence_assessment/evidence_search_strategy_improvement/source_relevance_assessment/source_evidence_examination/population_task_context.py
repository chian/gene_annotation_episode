from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.family import member_for_role

class LiteraturePopulationTaskContext:

    def _owned_population_task_sources(self, context):
        """Classify possessed own outputs using public metadata, read-only.

        No repository is constructed, no table is installed and no sheet or
        request artifact is opened. SQL extracts only successful operation
        metadata, never numerical cells or provider/source contents.
        """
        from gene_annotation_episode.episodic_workflow.root.literature_population_task_metadata import population_task_metadata_specs
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
                table_rows[table] = tuple(db.execute(
                    f"SELECT operation_key, json_extract(outcome,'$.status') AS status, "
                    "json_extract(outcome,'$.operation_ref') AS operation_ref, "
                    "json_extract(outcome,'$.result.sheet_ref') AS sheet_ref, "
                    "json_extract(outcome,'$.record_refs') AS record_refs "
                    f"FROM {table} WHERE run_id=? AND episode_id=? AND json_valid(outcome) ORDER BY rowid",
                    (context.run_id, context.episode_id)))
            for row in table_rows[table]:
                reference = row['sheet_ref']
                if (row['status'] != 'completed' or not isinstance(reference, str)
                        or reference not in context.received_record_refs
                        or row['operation_ref'] != identity('operation', {'run_id': context.run_id,
                            'episode_id': context.episode_id, 'key': row['operation_key']})):
                    continue
                try:
                    references = json.loads(row['record_refs'] or 'null')
                    if not isinstance(references, list) or reference not in references:
                        continue
                    metadata = self._require(reference, context.scope, 'source')
                except (ContractError, ValueError, TypeError, KeyError):
                    continue
                if (metadata.get('id') == reference and metadata.get('record_type') == 'source'
                        and metadata.get('origin') == 'tool' and metadata.get('provider') == provider
                        and metadata.get('version') in versions):
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
        # The latest completed own action controls repair relevance. A later
        # successful/non-tool action clears the old failure automatically.
        row = db.execute("""SELECT json_extract(action,'$.kind') AS kind,
            json_extract(action,'$.tool') AS tool,
            json_extract(action,'$.arguments.version') AS version,
            json_extract(action,'$.arguments.population_version') AS population_version,
            json_extract(result,'$.status') AS status
            FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL
            AND json_valid(action) AND json_valid(result)
            ORDER BY decision_index DESC LIMIT 1""", (context.run_id, context.episode_id)).fetchone()
        if row and row['kind'] == 'tool' and row['status'] in ('invalid', 'failed', 'error'):
            result['literature_selected_population_attempt'] = {'tool': row['tool'],
                'arguments': {name: row[name] for name in ('version', 'population_version') if row[name] is not None},
                'status': row['status']}
        return result

