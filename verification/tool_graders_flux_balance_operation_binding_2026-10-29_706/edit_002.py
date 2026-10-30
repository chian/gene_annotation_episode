from pathlib import Path
p=Path('gene_annotation_episode/practical_execution_operations.py');s=p.read_text()
s=s.replace("            if requested:\n                if 'native_blast_utility' in command:","            if requested:\n                if 'native_flux_balance' in command:\n                    self._flux_balance_state_plan(state, str(handle.path))\n                if 'native_blast_utility' in command:")
s=s.replace("            handle = self._job_handle(state)\n            if 'native_blast_utility'", "            handle = self._job_handle(state)\n            if 'native_flux_balance' in state.assignment['requested_job']:\n                self._flux_balance_state_plan(state, str(handle.path))\n            if 'native_blast_utility'")
s=s.replace("            if 'native_blast_masking' in state.assignment['requested_job']:\n                plan =", "            if 'native_flux_balance' in state.assignment['requested_job']:\n                outcome['native_outcome'] = view\n            elif 'native_blast_masking' in state.assignment['requested_job']:\n                plan =")
p.write_text(s)
p=Path('gene_annotation_episode/execution_progress.py');s=p.read_text()
needle="    nmf = assignment['requested_job'].get('native_expression_nmf')\n"
s=s.replace(needle,"""    fba = assignment['requested_job'].get('native_flux_balance')
    if fba is not None:
        return {'resource_kind': target['resource_kind'],
            'service_or_program': fba['operation'], 'operation': fba['operation'],
            'mode': fba['mode'], 'input_format': fba['model_input']['format'],
            'output_format': 'flux_balance_native_manifest_v1'}
"""+needle)
needle="        if 'native_blast_utility' in assignment['requested_job']:\n"
idx=s.index(needle,s.index('    def _native('))
block='''        if 'native_flux_balance' in assignment['requested_job']:
            from .flux_balance_contracts import validate_flux_balance_record
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_flux_balance_resource_identity_conflict')
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            file = validate_flux_balance_record('File', detail.get('native_flux_balance_input_binding_file'))
            if (file['format'] != 'flux_balance_input_binding_receipt_v1'
                    or file['artifact_ref'] != 'artifact_' + file['sha256']):
                raise ValueError('native_flux_balance_original_input_control_conflict')
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle))
                prior_detail = prior['receipt']['outcome'].get('native_outcome') or {}
                if (original['resource_id'] != resource_id or original['execution_id'] != job['execution_id']
                        or original['assignment']['workspace'] != assignment['workspace']
                        or canonical(original['assignment']['requested_job']) != canonical(assignment['requested_job'])
                        or any(detail.get(key) != prior_detail.get(key) for key in (
                            'attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                assignment = original['assignment']
                origin_episode_id = original['origin_episode_id']
            operation_key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            prefix = f'{self.run_id}:{origin_episode_id}:'
            index = operation_key.removeprefix(prefix) if isinstance(operation_key, str) else ''
            root = Path(assignment['workspace']) / '.episode-operations' / digest({
                'run': self.run_id, 'episode': origin_episode_id}) / digest(operation_key)
            observed = detail.get('observation', detail)
            if (not isinstance(operation_key, str) or not operation_key.startswith(prefix)
                    or not index.isdecimal() or str(int(index)) != index
                    or attempt_id != digest(operation_key) or job['execution_id'] != str(root / 'native.json')
                    or observed.get('metadata', {}).get('policy') != self.operations[resource_id].policy.to_dict()):
                raise ValueError('native_flux_balance_original_attempt_mismatch')
            # Join frozen original start custody, without opening native controls
            # or re-resolving any current scientific source.
            starts = self.receipts._sources(self.receipts._accession(origin_episode_id, operation_key))
            if len(starts) != 1:
                raise ValueError('native_flux_balance_original_start_receipt_missing')
            start = self.receipts.read(starts[0]['id'], body['scope'])
            start_receipt = start['receipt']
            start_job = start_receipt['outcome'].get('facts', {}).get('requested_job', {})
            start_detail = start_receipt['outcome'].get('native_outcome') or {}
            if (start['episode_id'] != origin_episode_id or start['assignment_sha256'] != digest(assignment)
                    or start_receipt['tool_name'] != 'practical.job.start'
                    or start_receipt['operation_key'] != operation_key
                    or start_job.get('execution_id') != job['execution_id']
                    or start_job.get('resource_kind') != 'local'
                    or start_job.get('requested_job_sha256') != digest(assignment['requested_job'])
                    or start_job.get('argv') != assignment['requested_job']['argv']
                    or start_job.get('environment') != assignment['requested_job']['environment']
                    or any(start_detail.get(key) != detail.get(key) for key in (
                        'attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                raise ValueError('native_flux_balance_original_start_receipt_conflict')
'''
s=s[:idx]+block+s[idx:]
s=s.replace("{'native_fluorescence', 'native_blast_masking', 'native_blast_utility'} & set(target['assignment']['requested_job'])", "{'native_fluorescence', 'native_blast_masking', 'native_blast_utility', 'native_flux_balance'} & set(target['assignment']['requested_job'])")
s=s.replace('        return value\n\n    def usable_handoff',"        if 'native_flux_balance' in target['assignment']['requested_job']:\n            value['native_flux_balance_input_binding_file'] = detail['native_flux_balance_input_binding_file']\n        return value\n\n    def usable_handoff")
s=s.replace("'native_fluorescence', 'native_blast_masking', 'native_blast_utility'}\n", "'native_fluorescence', 'native_blast_masking', 'native_blast_utility', 'native_flux_balance'}\n")
p.write_text(s)
