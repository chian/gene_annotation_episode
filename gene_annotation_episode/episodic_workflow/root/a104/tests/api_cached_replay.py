"""Scoped replay of original cached requests/actions/credit; no queue clearance claim.

The original complete reopen helper and its failed empty-queue assertions remain
unchanged. This separate boundary checks actual nonempty queue preservation.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from .api_saved_carriers import (capture_custody, module, rows, Responses, build_case,
    estimator_provenance, forbidden, error_record, write)

def reopen_cached(captured, output, *, authenticated_custody):
    """Read an exact copied Store with its supported constructor.

    Current literal construction and saved-descriptor composition are distinct
    observations. A fingerprint mismatch remains a denial, never an alias.
    """
    assert capture_custody(captured) == authenticated_custody
    output.mkdir(parents=True)
    index = json.loads((captured / 'capture_index.json').read_text())
    assert len(index) == 18 and all(value['status'] == 'captured' for value in index)
    results = []
    for ordinal, row in enumerate(index):
        saved_path = Path(row['capture'])
        assert saved_path.is_relative_to(captured.resolve())
        saved = json.loads(saved_path.read_text())
        original = saved_path.parent
        for relative, expected in saved['files'].items():
            assert hashlib.sha256((original / relative).read_bytes()).hexdigest() == expected
        copied = output / str(ordinal)
        shutil.copytree(original, copied)
        for relative, expected in saved['files'].items():
            assert hashlib.sha256((copied / relative).read_bytes()).hexdigest() == expected
        result = {'home': saved['home'], 'role': saved['role'], 'original_descriptor': saved['descriptor'],
            'copied_bytes_verified_before_constructor': True}
        store = None
        try:
            store = module('state').Store(copied / 'store')
            assert store.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert rows(store) == saved['logical_rows']
            client = Responses()
            # Original directory/configuration remains an original operand.
            # A closed read may not open artifacts or acquire fresh work.
            workflow, factory = build_case(store, Path(saved['directory']), saved['api_home'], saved['role'], client)
            assert rows(store) == saved['logical_rows'], 'supported_reconstruction_changed_original_metadata'
            owner = workflow.episode_bindings.for_binding_path(saved['home'])
            context = module('episode_bindings').BindingContext(**saved['context'])
            result['current_descriptor'] = owner.as_record()
            result['current_estimator_provenance'] = estimator_provenance(owner, context)
            assert result['current_estimator_provenance'] == saved['original_estimator_provenance'], 'original_estimator_callback_identity_changed'
            before = rows(store)
            with patch.object(owner, '_live_project_credit', forbidden):
                with patch.object(store, 'get_artifact', forbidden):
                    try:
                        value = owner.credit_view(context, saved['selection'])
                        assert value == saved['carrier']['view']
                        result['closed_read'] = {'status': 'returned', 'view': value}
                    except Exception as error:
                        result['closed_read'] = {'status': 'raised', 'error': error_record(error)}
                try:
                    declared = saved['request']['report_contract']
                    contract = module('runtime').TypedReportContract(declared['decision'],
                        declared['measurements']['schema'], lambda *_: True)
                    assert contract.as_record() == declared
                    child = workflow.build(saved['role'], saved['context']['path'][-1][1],
                        saved['request']['goal']['objective'], saved['context']['scope'],
                        contract=contract, initial=saved['request']['message']['initial_report'],
                        episode_assignment=saved['context']['assignment'])
                    assert child.request.as_record() == saved['request']
                    assert workflow.binding_context(child.source).as_record() == saved['context']
                    child.source.restore()
                    child.source.restore_checkpoint()
                    before_unfinished_queue = list(child.source._unfinished_own_actions)
                    assert before_unfinished_queue == [0], 'original_controlled_closure_queue_changed'
                    selected = json.loads(saved['action_row']['action'])
                    original_payload = json.loads(saved['action_row']['result'])
                    returned = asyncio.run(child.source.execute(selected, 0)).as_record()
                    assert returned == saved['controller_input']
                    assert child.source.last_outcome == original_payload
                    assert child.source.last_outcome_index == 0
                    after_unfinished_queue = list(child.source._unfinished_own_actions)
                    assert after_unfinished_queue == before_unfinished_queue, 'cached_execute_changed_scheduler_owned_queue'
                    result['cached_request_action_credit_replay'] = {'status': 'replayed_original_cached_request_action_payload_and_credit',
                        'unfinished_queue_before': before_unfinished_queue, 'unfinished_queue_after': after_unfinished_queue,
                        'full_iterator_restoration_established': False,
                        'source_type': type(child.source).__module__ + '.' + type(child.source).__qualname__,
                        'controller_input': returned, 'original_payload': original_payload}
                except Exception as error:
                    result['cached_request_action_credit_replay'] = {'status': 'raised', 'error': error_record(error)}
            try:
                module('episode_composition').compose_episode_bindings(workflow.services, store=store,
                    journal=workflow.journal, execution_backend=workflow.execution_backend,
                    descriptors=saved['factory']['descriptors'], job_episodes=None,
                    resource_estimator=None, role_credit_bindings={}, directory=Path(saved['directory']) / 'workflow',
                    tool_registry=workflow.tools)
                result['saved_descriptor_composition'] = {'status': 'returned'}
            except Exception as error:
                result['saved_descriptor_composition'] = {'status': 'raised', 'error': error_record(error)}
            assert rows(store) == before and client.calls == []
            result['rows_unchanged_after_reads'] = True
            result['current_matches_original_descriptor'] = result['current_descriptor'] == saved['descriptor']
        except Exception as error:
            import traceback
            result['constructor_or_probe_failure'] = {'error': error_record(error), 'traceback': traceback.format_exc()}
        finally:
            if store is not None:
                try:
                    store.close()
                except Exception as error:
                    result['close_failure'] = error_record(error)
            try:
                result['original_capture_files_unchanged'] = all(
                    hashlib.sha256((original / relative).read_bytes()).hexdigest() == expected
                    for relative, expected in saved['files'].items())
            except Exception as error:
                result['original_capture_files_unchanged'] = False
                result['capture_custody_failure'] = error_record(error)
            results.append(result)
            write(output / 'reopen.json', results)
    assert all('constructor_or_probe_failure' not in result and 'close_failure' not in result
        and result['original_capture_files_unchanged'] for result in results)
    # Restoration refusals are explicit observations. They are not treated as
    # successful saved workflow restoration or suppressed by the runner.
    return results
