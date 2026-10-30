from pathlib import Path
p=Path('gene_annotation_episode/practical_execution_operations.py')
s=p.read_text()
def replace(a,b,n=1):
 global s
 assert s.count(a)==n,(a[:100],s.count(a),n)
 s=s.replace(a,b)
replace('def __init__(self, configuration):','def __init__(self, configuration, *, flux_balance_input_reader=None):')
replace("'native_blast_utility'}\n", "'native_blast_utility', 'native_flux_balance'}\n")
replace('        self.configuration = json.loads', "        if flux_balance_input_reader is not None and not callable(flux_balance_input_reader):\n            raise ValueError('native_flux_balance_input_reader_invalid')\n        self.flux_balance_input_reader = flux_balance_input_reader\n        self.configuration = json.loads")
replace("        if 'native_blast_utility' in configuration:\n", "        if 'native_flux_balance' in configuration:\n            from .native_flux_balance_bindings import validate_flux_balance_bindings\n            validate_flux_balance_bindings(configuration['native_flux_balance'])\n        if 'native_blast_utility' in configuration:\n")
replace("        if 'native_flux_balance' in assignment['requested_job']:\n            raise ValueError('native_flux_balance_local_operation_binding_unfinished')", """        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_contracts import POLICY, validate_flux_balance_requested_job
            from .native_flux_balance_bindings import flux_balance_binding_accepts_job
            job = validate_flux_balance_requested_job(assignment['requested_job'])['native_flux_balance']
            if not any(flux_balance_binding_accepts_job(row, job)
                    for row in self.configuration.get('native_flux_balance', [])):
                raise ValueError('native_flux_balance_operation_mode_software_format_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_flux_balance_local_resource_required')
            if not isinstance(assignment.get('resource_id'), str) or not assignment['resource_id']:
                raise ValueError('native_flux_balance_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_flux_balance_local_policy_conflict')""")
replace('native_fluorescence=False, native_blast_masking=False, native_blast_utility=False):','native_fluorescence=False, native_blast_masking=False, native_blast_utility=False,\n                native_flux_balance=False):')
replace('        if native_blast_utility:\n', """        if native_flux_balance:
            from .native_flux_balance_local import prepare_local_flux_balance
            if self.flux_balance_input_reader is None:
                raise ValueError('native_flux_balance_input_reader_required')
            control = self.flux_balance_input_reader(state)
            if type(control) is not dict or set(control) != {'receipt', 'file'}:
                raise ValueError('native_flux_balance_input_control_invalid')
            handle = prepare_local_flux_balance(state, operation_key, root=root, policy=self.policy,
                input_binding_receipt=control['receipt'], input_binding_file=control['file'])
        elif native_blast_utility:
""")
marker='    def _job_fact(self, state, handle, view):\n'
helpers='''    def _flux_balance_plan(self, assignment, execution_id, *, run_id=None,
                           origin_episode_id=None, original_operation_key=None, attempt_id=None,
                           resource_id=None, requested_job_sha256=None):
        from .native_flux_balance_local import local_flux_balance_plan
        self.validate_assignment(assignment)
        plan = local_flux_balance_plan(assignment, execution_id)
        expected = {'run_id': run_id, 'episode_id': origin_episode_id,
            'operation_key': original_operation_key, 'attempt_id': attempt_id,
            'resource_id': resource_id, 'requested_job_sha256': requested_job_sha256}
        if (plan['policy'] != self.policy.to_dict() or any(value is not None and
                plan['identity'][key] != value for key, value in expected.items())):
            raise ValueError('native_flux_balance_original_attempt_mismatch')
        return plan

    @staticmethod
    def _flux_balance_identity(plan):
        from .native_flux_balance_storage import confined_file, read_json
        invocation = read_json(confined_file(Path(plan['identity']['execution_id']).parent, 'invoke.json'))
        return {'attempt_id': plan['identity']['attempt_id'],
            'attempt_operation_key': plan['identity']['operation_key'],
            'native_flux_balance_input_binding_file': invocation['native_flux_balance_input_binding_file']}

    def _flux_balance_state_plan(self, state, execution_id):
        plan = self._flux_balance_plan(state.assignment, execution_id,
            run_id=state.run_id, origin_episode_id=state.episode_id)
        identity = self._flux_balance_identity(plan)
        for receipt in state.receipts():
            outcome = receipt.get('outcome', {})
            if outcome.get('facts', {}).get('requested_job', {}).get('execution_id') == execution_id:
                prior = outcome.get('native_outcome') or {}
                if any(prior.get(key) != value for key, value in identity.items()):
                    raise ValueError('native_flux_balance_original_input_control_conflict')
        return plan

    def _flux_balance_observation_plan(self, assignment, execution_id, attempt_id, identity):
        plan = self._flux_balance_plan(assignment, execution_id, attempt_id=attempt_id,
            **{key: identity.get(key) for key in ('run_id', 'origin_episode_id',
                'original_operation_key', 'resource_id', 'requested_job_sha256')})
        expected = identity.get('native_flux_balance_input_binding_file')
        if expected is not None and self._flux_balance_identity(plan)['native_flux_balance_input_binding_file'] != expected:
            raise ValueError('native_flux_balance_original_input_control_conflict')
        return plan

'''
replace(marker,helpers+marker)
replace('        utility_plan = None\n',"        utility_plan = None\n        flux_balance_plan = None\n        if 'native_flux_balance' in request:\n            flux_balance_plan = self._flux_balance_state_plan(state, str(handle.path))\n")
replace("        if utility_plan is not None:\n", "        if flux_balance_plan is not None:\n            attempt = Path(flux_balance_plan['attempt_directory'])\n            outputs = [str(attempt / row['relative_path']) for row in flux_balance_plan['outputs']]\n        if utility_plan is not None:\n")
replace("        if any(role not in {'stdout', 'stderr'} for role in log_roles):", "        allowed_logs = {'stdout', 'stderr', 'native_log'} if 'native_flux_balance' in assignment['requested_job'] else {'stdout', 'stderr'}\n        if any(role not in allowed_logs for role in log_roles):")
obs='''        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_observations import flux_balance_observed_files
            plan = self._flux_balance_observation_plan(assignment, execution_id, attempt_id, identity)
            view = native.status(native.NativeJobHandle(Path(execution_id)))
            metadata, measurements = view['metadata'], []
            rc = metadata.get('native_returncode')
            state = (('completed' if rc == 0 else 'failed') if view['terminal'] else
                'running' if view['state'] == 'running' else
                'submitted' if view['state'] in {'prepared', 'starting'} else 'unknown')
            failure = None if state != 'failed' else (
                'native_returncode_unavailable' if rc is None else 'native_nonzero_returncode')
            if view['terminal'] and metadata.get('elapsed_seconds') is not None:
                measurements.append({'measure': metadata['duration_measure'], 'seconds': metadata['elapsed_seconds']})
            outputs, logs, available = flux_balance_observed_files(plan, view,
                log_window_bytes=log_window_bytes, log_roles=log_roles)
            return {'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state,
                'returncode': rc, 'failure_code': failure, 'result_available': available,
                'measurements': measurements, 'outputs': outputs, 'logs': logs,
                'provenance_refs': [], 'native': {'execution_id': execution_id, **view,
                    **self._flux_balance_identity(plan)}}
'''
needle="        if 'native_blast_utility' in assignment['requested_job']:\n"
idx=s.index(needle,s.index('    def observe_execution('));s=s[:idx]+obs+s[idx:]
needle="        if 'native_blast_utility' in assignment['requested_job']:\n"
idx=s.index(needle,s.index('    def read_output('));s=s[:idx]+'''        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_observations import read_flux_balance_output
            plan = self._flux_balance_observation_plan(assignment, execution_id, attempt_id, identity)
            return read_flux_balance_output(plan, path=str(path), offset=offset, limit=limit)
'''+s[idx:]
replace("                        native_fluorescence='native_fluorescence' in command)","                        native_fluorescence='native_fluorescence' in command,\n                        native_flux_balance='native_flux_balance' in command)",2)
replace("                    utility_retry_validation = None\n", "                    utility_retry_validation = None\n                    flux_balance_retry_plan = None\n                    if 'native_flux_balance' in command:\n                        flux_balance_retry_plan = self._flux_balance_state_plan(state, str(handle.path))\n                        strict_owner = flux_balance_retry_plan['identity']\n")
replace("'native_blast_masking', 'native_blast_utility'} & set(command) and (", "'native_blast_masking', 'native_blast_utility', 'native_flux_balance'} & set(command) and (")
replace("                            **({} if strict_owner is None else {", "                            **({} if flux_balance_retry_plan is None else self._flux_balance_identity(flux_balance_retry_plan)),\n                            **({} if strict_owner is None else {")
# Central final projection covers first/reused/retry start and selected own status/collect alike.
replace("        outcome['facts']['paths'] = path_facts(state.assignment)\n        return outcome, updated", """        if ('native_flux_balance' in state.assignment['requested_job']
                and 'requested_job' in outcome['facts']):
            from .native_flux_balance_observations import flux_balance_observed_files
            plan = self._flux_balance_state_plan(state,
                outcome['facts']['requested_job']['execution_id'])
            outputs, logs, _ = flux_balance_observed_files(plan, outcome['native_outcome'],
                log_window_bytes=8192, log_roles=('stdout', 'stderr'))
            outcome['native_outcome'] = {**outcome['native_outcome'],
                **self._flux_balance_identity(plan), 'observed_outputs': outputs, 'observed_logs': logs}
        outcome['facts']['paths'] = path_facts(state.assignment)
        return outcome, updated""")
p.write_text(s)
p=Path('gene_annotation_episode/practical_resource_episodes.py');s=p.read_text()
s=s.replace('initial_information=None, store=None):','initial_information=None, store=None,\n                 flux_balance_input_reader=None):')
s=s.replace('        self.store = store\n',"        self.store = store\n        if flux_balance_input_reader is not None and not callable(flux_balance_input_reader):\n            raise ValueError('native_flux_balance_input_reader_invalid')\n        self.flux_balance_input_reader = flux_balance_input_reader\n")
s=s.replace('return LocalPracticalOperations(config)','return LocalPracticalOperations(config, flux_balance_input_reader=self.flux_balance_input_reader)')
p.write_text(s)
