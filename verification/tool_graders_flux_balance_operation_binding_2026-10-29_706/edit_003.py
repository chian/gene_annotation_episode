from pathlib import Path
p=Path('gene_annotation_episode/practical_execution_operations.py');s=p.read_text()
s=s.replace('\nclass LocalPracticalOperations:', "\nclass _FluxBalanceInputFailure(ValueError):\n    pass\n\n\nclass LocalPracticalOperations:")
s=s.replace("raise ValueError('native_flux_balance_input_reader_required')", "raise _FluxBalanceInputFailure('native_flux_balance_input_reader_required')")
s=s.replace("            control = self.flux_balance_input_reader(state)\n", "            try:\n                control = self.flux_balance_input_reader(state)\n            except (ValueError, TypeError, OSError) as error:\n                raise _FluxBalanceInputFailure('native_flux_balance_input_control_unavailable') from error\n")
s=s.replace("raise ValueError('native_flux_balance_input_control_invalid')", "raise _FluxBalanceInputFailure('native_flux_balance_input_control_invalid')")
s=s.replace("        except OSError as error:\n            if tool_name", "        except _FluxBalanceInputFailure as error:\n            return {'facts': {}, 'native_outcome': {'failure': {'code': str(error)}}}, None\n        except OSError as error:\n            if tool_name")
p.write_text(s)
p=Path('gene_annotation_episode/practical_resource_episodes.py');s=p.read_text()
s=s.replace("        target_directory = directory/'practical-execution'/digest({\n            'run_id': context.run_id, 'episode_id': body['episode_id']})", """        origin_episode_id = body['episode_id']
        if 'native_flux_balance' in original['requested_job']:
            from .execution_progress import ExecutionTargetReader
            resource_id = original['resource_id']
            target_info = ExecutionTargetReader(self.store, run_id=context.run_id, directory=directory,
                resources={resource_id: self.resources['local']}, api_execution=None).read_target(reference, context.scope)
            original = target_info['assignment']
            origin_episode_id = target_info['origin_episode_id']
        target_directory = directory/'practical-execution'/digest({
            'run_id': context.run_id, 'episode_id': origin_episode_id})""")
s=s.replace("            context.run_id, body['episode_id'], original)","            context.run_id, origin_episode_id, original)")
s=s.replace("                    actual['output_paths'] = sorted({path for requirement in\n                        plain(context.assignment)['progress_requirements']\n                        if requirement['predicate']['kind'] == 'requested_job_outputs'\n                        for path in requirement['predicate']['output_paths']})", """                    if 'native_flux_balance' not in plain(context.assignment)['requested_job']:
                        actual['output_paths'] = sorted({path for requirement in
                            plain(context.assignment)['progress_requirements']
                            if requirement['predicate']['kind'] == 'requested_job_outputs'
                            for path in requirement['predicate']['output_paths']})""")
p.write_text(s)
p=Path('tests/test_flux_balance_operation_binding_706.py');s=p.read_text().replace("assert c.prepares[0][1]['cwd'] == str(Path(execution).parent)","assert Path(c.prepares[0][1]['cwd']) == Path(execution).parent")
# Place original real state at the production handoff path.
s=s.replace("state = PracticalState(tmp_path / 'practical', context.run_id", "state = PracticalState(f.owner.directory / 'practical-execution' / digest({\n        'run_id': context.run_id, 'episode_id': context.episode_id}), context.run_id")
s += '''\n\ndef test_public_selected_missing_control_is_structured_failure(case):
    c = case;c.operations.flux_balance_input_reader = None
    key = f'{c.state.run_id}:{c.state.episode_id}:0'
    c.state.begin(key, 'practical.job.start', {})
    outcome, updated = asyncio.run(c.operations.execute(c.state, 'practical.job.start', {}, key))
    assert outcome == {'facts': {}, 'native_outcome': {'failure': {'code': 'native_flux_balance_input_reader_required'}}}
    assert updated is None and not c.prepares and not c.dispatches


def test_forwarded_selected_status_collect_preserves_original_owner_and_outputs(case):
    c = case;start, original_ref = c.action()
    practical = PracticalResourceEpisodes(None, directory=c.f.owner.directory, resources={'local': c.config}, store=c.f.store)
    context = c.f.records.child(c.f.parent, 'launch_local', deepcopy(c.state.assignment), 1)
    practical.state(context)
    source_ref = original_ref
    reader = _reader(c)
    original_target = reader.read_target(original_ref, c.context.scope)
    for index, tool in enumerate(('practical.job.status', 'practical.job.collect')):
        arguments = {'receipt_ref': source_ref}
        c.f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': arguments}), 'result': None, 'credit': None})
        result = asyncio.run(practical.execute(context, tool, arguments, f'{context.run_id}:{context.episode_id}:{index}'))
        assert result['status'] == 'completed', result
        source_ref = result['record_refs'][0]
        receipt = result['result']
        assert receipt['episode_id'] == context.episode_id
        assert receipt['outcome']['facts']['requested_job']['output_paths'] == start['outcome']['facts']['requested_job']['output_paths']
        assert receipt['outcome']['native_outcome']['native_flux_balance_input_binding_file'] == c.control['file']
        target = reader.read_target(source_ref, context.scope)
        assert target['origin_episode_id'] == original_target['origin_episode_id']
        assert target['execution_id'] == original_target['execution_id']
        assert reader._native_identity(target)['native_flux_balance_input_binding_file'] == c.control['file']
    assert len(c.state.receipts()) == 1 and len(practical.state(context).receipts()) == 2
    assert len(c.prepares) == len(c.dispatches) == 1
'''
p.write_text(s)
