from __future__ import annotations
from .contracts import CHECKED_STATUS_SCHEMA, ROLES, artifact_path, deepcopy, json, obj, reference

class SubmissionAssignment:

    def commission_schemas(self, scientific_child):
        common = {key: deepcopy(value) for key, value in scientific_child['properties'].items() if key != 'kind'}
        values = []
        for role in ROLES:
            operand = {'query_ref': reference('subject'), 'cpu': {'type': 'integer', 'minimum': 1, 'description': 'Select the positive integer --cpu thread operand for this query under the enclosing workflow CPU quota. This value is not a CPU allocation or an admission ceiling.'}}
            if 'search_modes' in self.jobs.config:
                operand['search_mode'] = {'type': 'string', 'enum': list(self.jobs.search_modes), 'description': 'Parent selects the assigned search. native_defaults uses native heuristic filters; maximum_sensitivity disables all such filters (--max), at substantial runtime cost and possibly slight sensitivity improvement. It does not strengthen reported significance, establish homology or assign function. No duration transfer from another mode is assumed.'}
            commission = obj({'kind': {'type': 'string', 'const': 'job_child'}, 'role': {'type': 'string', 'const': role}, **common, **operand})
            commission['properties']['delay_seconds'] = {'type': 'number', 'minimum': 0, 'description': 'Optional parent-chosen delay before this exact child starts. Choose from returned monitoring evidence and your yield estimate; no default cadence. The durable timer survives interruption/resume, does not select new work or add a controller observation. This one selected parent action waits and returns its child form; concurrent scheduling is later work.'}
            if self.has_information_channel(role):
                commission['properties']['prior_sample_refs'] = {'type': 'array', 'uniqueItems': True, 'items': reference('job_sample'), 'description': 'Optional actual prior samples already known to the parent for this assigned job. They seed execution knowledge without earning new information credit.'}
                commission['properties']['prior_checked_statuses'] = {'type': 'array', 'uniqueItems': True, 'items': deepcopy(CHECKED_STATUS_SCHEMA), 'description': 'Optional already-known launch status facts received through the parent form. Each must exactly match a recorded successful selected handoff check of this assigned job and registry. They seed monitoring knowledge without becoming samples or new credit. Omission supplies none.'}
            values.append(commission)
            repair = deepcopy(commission)
            repair['properties'].pop('query_ref')
            repair['properties'].pop('cpu')
            repair['properties'].pop('search_mode', None)
            repair['properties']['existing_job_ref'] = {**reference('homology_job'), 'description': 'Commission a fresh iterative launch/repair investigation of this existing assigned job. It preserves its query, prepared inputs and native reservation; it does not create a replacement job.'}
            repair['required'] = [key for key in repair['required'] if key not in {'query_ref', 'cpu', 'search_mode'}] + ['existing_job_ref']
            values.append(repair)
        return values

    @staticmethod
    def _query(store, scope, query_ref):
        from gene_annotation_episode.episodic_workflow.root.a103.homology_query import protein_query
        return protein_query(store, scope, query_ref, error_code='job_query_must_be_protein_of_assigned_target')

    def assign(self, store, role, selection, scope, *, operation_key):
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        if 'existing_job_ref' in selection:
            job = self.jobs._row(selection['existing_job_ref'])
            self._query(store, scope, job['query_ref'])
            assignment = {'job_ref': job['job_ref'], 'query_ref': job['query_ref'], 'cpu': job['cpu']}
        else:
            query = self._query(store, scope, selection['query_ref'])
            symbols = artifact_path(store, query['sequence_ref']).read_text()
            job_ref = self.jobs.order(query_ref=query['id'], query_fasta='>query\n' + symbols + '\n', cpu=selection['cpu'], operation_key=operation_key, search_mode=selection.get('search_mode'))
            assignment = {'job_ref': job_ref, 'query_ref': query['id'], 'cpu': selection['cpu']}
        if 'search_modes' in self.jobs.config:
            assignment['search_mode'] = self.jobs._row(assignment['job_ref'])['search_mode']
        if self.has_information_channel(role):
            prior = []
            for sample_ref in selection.get('prior_sample_refs', []):
                row = self.jobs.db.execute('SELECT job_ref,body FROM samples WHERE sample_ref=?', (sample_ref,)).fetchone()
                if row is None or row['job_ref'] != assignment['job_ref']:
                    raise ValueError('prior_monitoring_sample_must_belong_to_assigned_job')
                prior.append(json.loads(row['body']))
            if 'prior_sample_refs' in selection:
                assignment.update(prior_sample_refs=list(selection.get('prior_sample_refs', [])), prior_samples=prior)
            checked = deepcopy(selection.get('prior_checked_statuses', []))
            for value in checked:
                rows = store.db.execute("SELECT json_extract(result,'$.result.sample')\n                    FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.check_handoff'\n                    AND json_extract(result,'$.status')='completed'\n                    AND json_extract(result,'$.result.checked_at_unix_seconds')=?\n                    AND json_extract(result,'$.result.sample.job_ref')=?\n                    AND json_extract(result,'$.result.sample.registry_ref')=?", (value['checked_at_unix_seconds'], assignment['job_ref'], self.jobs.config['registry_ref']))
                if not any((value == {'checked_at_unix_seconds': value['checked_at_unix_seconds'], **json.loads(row[0])} for row in rows)):
                    raise ValueError('prior_checked_status_must_match_recorded_assigned_job_check')
            if 'prior_checked_statuses' in selection:
                assignment['prior_checked_statuses'] = checked
        return assignment

    @staticmethod
    def assignment(source):
        return source.request.message.as_record()['job_assignment']
