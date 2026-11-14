"""Private A101 job_launch from parent."""
from __future__ import annotations
from .execution_contracts import ROLES, artifact_path, deepcopy, json

class OperationalAssignment:

    @staticmethod
    def _query(store, scope, query_ref):
        from gene_annotation_episode.episodic_workflow.root.a101.library.homology_query import protein_query
        return protein_query(store, scope, query_ref, error_code='job_query_must_be_protein_of_assigned_target')

    def assign(self, store, role, selection, scope, *, operation_key):
        self.credit_kind(role)
        if 'job_launch' not in ROLES:
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
        if self.has_information_channel('job_launch'):
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
