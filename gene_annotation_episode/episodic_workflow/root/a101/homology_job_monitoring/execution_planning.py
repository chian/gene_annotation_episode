"""Private A101 job_monitor execution planning."""
from __future__ import annotations
from .execution_contracts import CHECKED_STATUS_SCHEMA, ContractError, HANDOFF_SCHEMA, ROLES, artifact_path, deepcopy, obj, reference

class OperationalPlanning:

    def prospective_execution_classes(self, store, scope):
        """Caller-resource configurations for actual eligible protein records.

        Reading this inventory does not translate a sequence, choose work,
        create an order, or launch anything. It is recomputed for later
        decisions so newly acquired protein records can become visible.
        """
        return list({value['execution_class'].ref: value['execution_class'] for value in self.prospective_execution_options(store, scope)}.values())

    def prospective_execution_options(self, store, scope):
        """Local selectable operands and their statistical class, never a choice.

        Query identity stays in the episode's local configuration inventory;
        it is not added to shared run statistics or credited as a finding.
        """
        if self.statistics is None:
            return []
        options = []
        offset = 0
        while True:
            page = store.query_records('subject', scope=scope, offset=offset, limit=100)
            for candidate in page['records']:
                try:
                    query = self._query(store, scope, candidate['id'])
                    symbols = artifact_path(store, query['sequence_ref']).read_text()
                except (ValueError, KeyError, OSError, ContractError):
                    continue
                for cpu in self.jobs.cpu_forecast_choices:
                    for mode in self.jobs.search_modes:
                        execution_class = self.statistics.execution_class_for_query(self.jobs, query_fasta='>query\n' + symbols + '\n', cpu=cpu, search_mode=mode)
                        options.append({'query_ref': query['id'], 'cpu': cpu, 'search_mode': mode, 'execution_class': execution_class})
            if page['next_offset'] is None:
                return options
            offset = page['next_offset']

    def commission_schemas(self, scientific_child):
        from .episode import HomologyEpisode
        if type(self) is not HomologyEpisode or type(self.roles) is not tuple or any((type(item) is not str for item in self.roles)) or (self.roles != ('job_monitor',)):
            return self._original_commission_schemas(scientific_child)
        common = {key: deepcopy(value) for key, value in scientific_child['properties'].items() if key != 'kind'}
        values = []
        for role in self.roles:
            operand = {'handoff': deepcopy(HANDOFF_SCHEMA)}
            operand['prior_sample_refs'] = {'type': 'array', 'uniqueItems': True, 'items': reference('job_sample'), 'description': 'Actual prior samples the parent supplies as already-known execution information. Use [] when none is known. These are input facts, not new monitoring contributions or global history.'}
            commission = obj({'kind': {'type': 'string', 'const': 'job_child'}, 'role': {'type': 'string', 'const': role}, **common, **operand})
            commission['properties']['delay_seconds'] = {'type': 'number', 'minimum': 0, 'description': 'Optional parent-chosen delay before this exact child starts. Choose from returned monitoring evidence and your yield estimate; no default cadence. The durable timer survives interruption/resume, does not select new work or add a controller observation. This one selected parent action waits and returns its child form; concurrent scheduling is later work.'}
            commission['properties']['prior_checked_statuses'] = {'type': 'array', 'uniqueItems': True, 'items': deepcopy(CHECKED_STATUS_SCHEMA), 'description': 'Optional already-known launch status facts received through the parent form. Each must exactly match a recorded successful selected handoff check of this assigned job and registry. They seed monitoring knowledge without becoming samples or new credit. Omission supplies none.'}
            values.append(commission)
        return values

    # Original public behavior for subclasses and custom role collections.
    def _original_commission_schemas(self, scientific_child):
        common = {key: deepcopy(value) for key, value in scientific_child['properties'].items() if key != 'kind'}
        values = []
        for role in self.roles:
            operand = {'query_ref': reference('subject'), 'cpu': {'type': 'integer', 'minimum': 1, 'description': 'Select the positive integer --cpu thread operand for this query under the enclosing workflow CPU quota. This value is not a CPU allocation or an admission ceiling.'}} if role == 'job_launch' else {'handoff': deepcopy(HANDOFF_SCHEMA)}
            if role == 'job_launch' and 'search_modes' in self.jobs.config:
                operand['search_mode'] = {'type': 'string', 'enum': list(self.jobs.search_modes), 'description': 'Parent selects the assigned search. native_defaults uses native heuristic filters; maximum_sensitivity disables all such filters (--max), at substantial runtime cost and possibly slight sensitivity improvement. It does not strengthen reported significance, establish homology or assign function. No duration transfer from another mode is assumed.'}
            if role == 'job_monitor':
                operand['prior_sample_refs'] = {'type': 'array', 'uniqueItems': True, 'items': reference('job_sample'), 'description': 'Actual prior samples the parent supplies as already-known execution information. Use [] when none is known. These are input facts, not new monitoring contributions or global history.'}
            commission = obj({'kind': {'type': 'string', 'const': 'job_child'}, 'role': {'type': 'string', 'const': role}, **common, **operand})
            commission['properties']['delay_seconds'] = {'type': 'number', 'minimum': 0, 'description': 'Optional parent-chosen delay before this exact child starts. Choose from returned monitoring evidence and your yield estimate; no default cadence. The durable timer survives interruption/resume, does not select new work or add a controller observation. This one selected parent action waits and returns its child form; concurrent scheduling is later work.'}
            if role == 'job_monitor' or self.has_information_channel(role):
                if role != 'job_monitor':
                    commission['properties']['prior_sample_refs'] = {'type': 'array', 'uniqueItems': True, 'items': reference('job_sample'), 'description': 'Optional actual prior samples already known to the parent for this assigned job. They seed execution knowledge without earning new information credit.'}
                commission['properties']['prior_checked_statuses'] = {'type': 'array', 'uniqueItems': True, 'items': deepcopy(CHECKED_STATUS_SCHEMA), 'description': 'Optional already-known launch status facts received through the parent form. Each must exactly match a recorded successful selected handoff check of this assigned job and registry. They seed monitoring knowledge without becoming samples or new credit. Omission supplies none.'}
            values.append(commission)
            if role == 'job_launch':
                repair = deepcopy(commission)
                repair['properties'].pop('query_ref')
                repair['properties'].pop('cpu')
                repair['properties'].pop('search_mode', None)
                repair['properties']['existing_job_ref'] = {**reference('homology_job'), 'description': 'Commission a fresh iterative launch/repair investigation of this existing assigned job. It preserves its query, prepared inputs and native reservation; it does not create a replacement job.'}
                repair['required'] = [key for key in repair['required'] if key not in {'query_ref', 'cpu', 'search_mode'}] + ['existing_job_ref']
                values.append(repair)
        return values
