"""Actual Workflow descriptor construction and saved API/Launch/Results replay.

These new archives use the original service-factory directory contract: each
explicit owner and Workflow receives the same run directory. Existing archived
carrier fixtures are not edited. The original controlled action/closure helper
is reused with only its test builder replaced; application callbacks stay real.
This proves cached requests/actions/credit, not an empty scheduler queue or a
complete scientific iterator. Every raised boundary remains in the artifact.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from . import api_saved_carriers as carriers
from .api_cases import HOMES, Responses, error_record, module, resources, rows


def unused_root_credit(*args, **kwargs):
    # Same explicit root fixture operand as original carrier build_case. No
    # scientific root action is selected; operational credit remains its owner.
    return 0


def constructor_options(store, directory, run_id, tools):
    return dict(store=store, directory=directory, run_id=run_id, resources=resources(),
        initial_information={}, tool_registry=tools, handoff_unit=3., acquired_record_unit=2.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'), require_private_yield=True,
        task_yield_profiles={'launch_api:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
            'launch:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
            'results:api_uniprot': {'cutoff': .5, 'parameters': {}}})


def workflow_options(role):
    return dict(controller_factory=carriers.forbidden, project_credit=unused_root_credit,
        episode_record_receipts=True, initial_known_record_refs=[], annotation_child_roles=(),
        root_role=role, wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)


def build_literal_case(store, directory, home, role, client):
    assert home in HOMES and role in ('launch_api', 'launch', 'results')
    root = home.rsplit('/', 1)[0]
    paths = [root, *(root + '/' + leaf for leaf in
        ('api_job_execution', 'local_job_execution', 'hpc_job_execution')),
        root.removesuffix('execution_job_submission') + 'execution_result_acquisition']
    run_id = 'a104-closed-' + hashlib.sha256((home + ':' + role).encode()).hexdigest()[:16]
    directory = Path(directory) / 'workflow'
    tools = module('tools').ToolRegistry(store, clients=client)
    def factory(path):
        def construct(services):
            return module(path + '/episode').ExecutionEpisode(services,
                **constructor_options(store, directory, run_id, tools))
        return construct
    workflow = module('runtime').Workflow(store, tools, object(), directory, run_id,
        episode_binding_factories=[factory(path) for path in paths], **workflow_options(role))
    # Initialize the real original progress schema before the immutable archive
    # is captured. Descriptor composition ordinarily creates these same tables;
    # no observation is supplied and no progress reader is substituted.
    module('episode_monitoring').ProgressProvider(store, workflow.execution_backend, run_id=run_id)
    return workflow, {'kind': 'explicit_literal_private_factories_v1', 'home_paths': paths,
        'root_role': role, 'factory_implementation': __name__ + '.build_literal_case',
        'descriptors': workflow.episode_bindings.as_record(),
        'historical_global_factory_authority_claimed': False,
        'owner_and_workflow_directory': str(directory.resolve()),
        'actual_progress_schema_initialized_before_archive': True}


def capture(directory):
    """Original action/custody producer, with an explicit new test directory fixture."""
    with patch.object(carriers, 'build_case', build_literal_case):
        return carriers.capture(Path(directory))


def actual_role_projectors(workflow, paths):
    result = {}
    for path in paths:
        owner = workflow.episode_bindings.for_binding_path(path)
        for role in owner.roles:
            assert role not in result and owner.credit_kind(role) != 'scientific'
            result[role] = {'project': owner.project_credit,
                'definition': {'version': 'execution_received_information_credit_v1',
                    'handoff_unit': owner.handoff_unit, 'acquired_record_unit': owner.acquired_record_unit,
                    'practical_units': 'original_assignment_progress_requirements',
                    'baseline': 'original_received_information', 'repeated_gain': 0}}
    return result


def reopen(captured, output, *, authenticated_custody):
    captured, output = Path(captured).resolve(), Path(output).resolve()
    assert carriers.capture_custody(captured) == authenticated_custody
    assert not output.exists()
    output.mkdir(parents=True)
    index = json.loads((captured / 'capture_index.json').read_text())
    observed = []
    for ordinal, entry in enumerate(index):
        original = Path(entry['capture']).resolve().parent
        saved = json.loads((original / 'capture.json').read_text())
        assert saved['factory']['factory_implementation'] == __name__ + '.build_literal_case'
        assert saved['factory']['actual_progress_schema_initialized_before_archive'] is True
        assert saved['factory']['owner_and_workflow_directory'] == str((Path(saved['directory']) / 'workflow').resolve())
        copied = output / str(ordinal)
        shutil.copytree(original, copied)
        for name, digest in saved['files'].items():
            assert hashlib.sha256((copied / name).read_bytes()).hexdigest() == digest
        result = {'home': saved['home'], 'role': saved['role'],
            'original_descriptor': saved['descriptor'], 'copied_bytes_verified_before_constructor': True,
            'full_iterator_restoration_claimed': False}
        store = None
        try:
            store = module('state').Store(copied / 'store')
            assert rows(store) == saved['logical_rows']
            client = Responses()
            literal, factory = build_literal_case(store, Path(saved['directory']),
                saved['api_home'], saved['role'], client)
            assert factory == saved['factory']
            supplied = actual_role_projectors(literal, factory['home_paths'])
            result['descriptor_construction'] = {'status': 'entered',
                'caller_definitions': {role: row['definition'] for role, row in supplied.items()}}
            workflow = module('runtime').Workflow(store, literal.tools, object(), literal.directory,
                literal.run_id, episode_binding_descriptors=deepcopy(saved['factory']['descriptors']),
                role_credit_bindings=supplied, **workflow_options(saved['role']))
            result['descriptor_construction'].update(status='returned',
                descriptors=workflow.episode_bindings.as_record(),
                projector_identities={role: workflow.role_credit_projectors[role] is row['project']
                    for role, row in supplied.items()},
                capabilities=module('communication').plain(workflow.resource_capabilities),
                expected_capabilities=[item for path in factory['home_paths']
                    for item in literal.episode_bindings.for_binding_path(path).capabilities()])
            assert workflow.episode_bindings.as_record() == saved['factory']['descriptors']
            assert all(result['descriptor_construction']['projector_identities'].values())
            assert rows(store) == saved['logical_rows']
            owner = workflow.episode_bindings.for_binding_path(saved['home'])
            context = module('episode_bindings').BindingContext(**saved['context'])
            assert owner.as_record() == saved['descriptor']
            assert carriers.estimator_provenance(owner, context) == saved['original_estimator_provenance']
            before = rows(store)
            with ExitStack() as forbidden_ports:
                owners = [literal.episode_bindings.for_binding_path(path) for path in factory['home_paths']]
                owners += [workflow.episode_bindings.for_binding_path(path) for path in factory['home_paths']]
                for actual_owner in owners:
                    forbidden_ports.enter_context(patch.object(actual_owner, '_live_project_credit', carriers.forbidden))
                with patch.object(store, 'get_artifact', carriers.forbidden):
                    assert owner.credit_view(context, saved['selection']) == saved['carrier']['view']
                declared = saved['request']['report_contract']
                contract = module('runtime').TypedReportContract(declared['decision'],
                    declared['measurements']['schema'], lambda *_: True)
                assert contract.as_record() == declared
                child = workflow.build(saved['role'], saved['context']['path'][-1][1],
                    saved['request']['goal']['objective'], saved['context']['scope'], contract=contract,
                    initial=saved['request']['message']['initial_report'],
                    episode_assignment=saved['context']['assignment'])
                assert child.request.as_record() == saved['request']
                assert workflow.binding_context(child.source).as_record() == saved['context']
                child.source.restore()
                child.source.restore_checkpoint()
                before_queue = list(child.source._unfinished_own_actions)
                assert before_queue == [0]
                selected = json.loads(saved['action_row']['action'])
                returned = asyncio.run(child.source.execute(selected, 0)).as_record()
                assert returned == saved['controller_input']
                assert child.source.last_outcome == json.loads(saved['action_row']['result'])
                assert child.source.last_outcome_index == 0
                assert list(child.source._unfinished_own_actions) == before_queue
                result['cached_replay'] = {'status': 'returned', 'request': child.request.as_record(),
                    'context': workflow.binding_context(child.source).as_record(),
                    'action_row': dict(workflow.journal.row('runtime_actions', child.source.episode_id, 0)),
                    'credit': returned, 'payload': child.source.last_outcome,
                    'unfinished_queue_before': before_queue, 'unfinished_queue_after': list(child.source._unfinished_own_actions),
                    'closed_view': saved['carrier']['view']}
                assert result['cached_replay']['action_row'] == saved['action_row']
            assert rows(store) == before and client.calls == []
            result['rows_unchanged_after_reads'] = True
        except Exception as error:
            import traceback
            result['raised_boundary'] = {'error': error_record(error), 'traceback': traceback.format_exc()}
        finally:
            if store is not None:
                try: store.close()
                except Exception as error: result['close_failure'] = error_record(error)
            result['original_capture_files_unchanged'] = all(
                hashlib.sha256((original / name).read_bytes()).hexdigest() == digest
                for name, digest in saved['files'].items())
            observed.append(result)
            carriers.write(output / 'observations.json', observed)
    return observed
