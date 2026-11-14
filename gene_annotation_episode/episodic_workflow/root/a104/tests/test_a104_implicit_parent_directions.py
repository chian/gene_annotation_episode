"""Connected original/private A104 requests and typed saved returns on nine edges."""
import json
from pathlib import Path
import pytest
from .test_a104_implicit_parent_protocol import no_external_execution
from .a104_parent_directional_checks import ROUTES, genuine_host, observe, original_rows, EmptyCatalog, own, SCHEMA, INITIAL


@pytest.mark.parametrize('route', ROUTES, ids=[row[0] for row in ROUTES])
@pytest.mark.parametrize('scenario', ('request-valid', 'initial-invalid', 'prepare-error', 'return-valid', 'saved-failure'))
def test_actual_original_and_private_parent_boundary(tmp_path, route, scenario):
    with genuine_host(tmp_path, route) as (workflow, source, binding):
        with original_rows(workflow):
            before = observe(workflow, source, binding, route, scenario, original=True)
        source.feedback = None
        with original_rows(workflow):
            after = observe(workflow, source, binding, route, scenario, original=False)
        assert before == after


@pytest.mark.parametrize('role', ('scientific_process', 'hpc'))
def test_scientific_nominal_pair_matches_real_private_registry_and_task_constructor(tmp_path, role):
    """Real constructor/cache witness only; no scientific assignment admission.

    The original configured Workflow/root is constructed first. The finite
    receiving graph below then supplies real private providers and verifies
    the original registry selection against the new optional selector. It
    does not claim whole-graph Workflow reconstruction from this later cache.
    """
    route, = [row for row in ROUTES if row[-1] == 'scientific']
    with genuine_host(tmp_path, route) as (workflow, root_source, _):
        runtime = own('runtime')
        science = own('scientific_process.episode').ScientificProcessEpisode(workflow.services,
            library=EmptyCatalog(), tool_library=EmptyCatalog(), child_roles=('scientific_process', 'hpc'))
        resources = json.loads((Path(__file__).parent / 'fixtures/source_request_assembly/a104_implicit_parent_hpc_resources.json.txt').read_text())
        hpc = own('scientific_process.hpc_work_planning.episode').HPCEpisode(workflow.services,
            store=workflow.store, run_id=workflow.run_id, directory=tmp_path, resources=resources, commissions={})
        workflow.episode_bindings = own('episode_bindings').EpisodeBindingRegistry((science, hpc))
        workflow.scientific_process_binding = science
        contract = runtime.TypedReportContract('Preserve the unresolved typed input', SCHEMA, lambda *_: True)
        request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(root_source.request.goal,
            objective='Observe the existing private Scientific source constructor', result_contract=SCHEMA),
            runtime.Record({'scope': root_source.scope, 'initial_report': INITIAL}), contract)
        path = root_source.path + (('scientific_process', 'selector-constructor'),)
        source = science.decision_source_type(workflow, path, request, root_source.scope)
        assert type(source) is own('scientific_process.task').ScientificTask
        assert source.episode_id == runtime.Episode.identity(workflow.context, workflow.grains['scientific_process'],
            path[-1][1], parent_path=path[:-1]).episode_id
        assert workflow.episode_bindings.for_path(path) is science
        expected = science if role == 'scientific_process' else hpc
        assert workflow.episode_bindings.for_child(path, role) is expected
        exchange = own('child_message_owners').parent_exchange(workflow, source,
            {'kind': 'episode_child', 'role': role}, role)
        home = 'scientific_process' if role == 'scientific_process' else 'hpc_work_planning'
        assert exchange is not None and exchange[4] is None
        assert exchange[0] is own('scientific_process.to_child_' + home).prepare_parent_request
        assert exchange[1] is own('scientific_process.from_child_' + home).admit_parent_return
