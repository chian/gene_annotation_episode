from pathlib import Path
p=Path('gene_annotation_episode/literature_episodes.py');s=p.read_text()
s=s.replace('"literature_experimental_prompt.py", "literature_numerical_return_presentation.py",','"literature_experimental_prompt.py", "literature_task_selection.py", "literature_numerical_return_presentation.py",',1)
# These six emissions report capability only. Real owned work is classified
# independently below; actual assignments/admitted rows remain original inputs.
for flag,marker,version in [('completion_time','completion_time','literature_completion_time_task_v1'),('active_site','active_site','literature_active_site_task_v1'),('product_partition','product_partition','literature_product_partition_task_v1')]:
 old=f'        if self.{flag}_population:\n            result["literature_{marker}_work"] = {{"version": "{version}"}}\n'
 assert s.count(old)==2,(flag,s.count(old));s=s.replace(old,'')
# Other historical capability markers are not trusted by the pure selector.
for method,nextmethod in [('initial_decision_context','decision_context'),('decision_context','catalog')]:
 a=s.index('    def '+method+'(');b=s.index('    def '+nextmethod+'(',a)
 part=s[a:b];pos=part.rindex('        return result')
 part=part[:pos]+'        if self.rate_population:\n            result.update(self._population_task_context(context))\n'+part[pos:]
 s=s[:a]+part+s[b:]
a=s.index('    def catalog(self, context):')
helper='''    def _owned_population_task_sources(self, context):
        """Classify possessed own outputs using public metadata, read-only.

        No repository is constructed, no table is installed and no sheet or
        request artifact is opened. SQL extracts only successful operation
        metadata, never numerical cells or provider/source contents.
        """
        from .literature_task_selection import population_task_metadata_specs
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

'''
s=s[:a]+helper+s[a:];p.write_text(s)
