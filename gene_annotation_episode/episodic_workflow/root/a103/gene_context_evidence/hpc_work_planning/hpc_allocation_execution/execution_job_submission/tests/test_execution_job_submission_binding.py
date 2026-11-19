"""Real checks of the execution job submission binding. Importing ``episode.py`` runs the system's class-definition
checks, so the import is the class-definition check. The folder holds the ten files, plus ``msg_to_child.py`` and
``read_from_child.py`` because it has children, and no module imports another episode folder. The episode's own
functions are called on real data: the admission of the assignment, the controller built from it, the
commissions of the three children, the report read from a child's result, the credit and the return. No model is
asked, no job service is reached."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import BoundedQualityYieldController

PACKAGE = __name__.rsplit('.tests.', 1)[0]
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = ('api_job_execution', 'hpc_job_execution', 'local_job_execution')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
BINDING_PATH = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def own_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if (path.is_dir() or '__pycache__' in relative.parts or relative.parts[0] in CHILDREN
                or relative.parts[0] == 'tests'):
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = module('episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1 and classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == BINDING_PATH == module('goal').BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {slot: BINDING_PATH + '/' + slot for slot in CHILDREN}
    assert set(classes[0].tools) == {'execution_capabilities'}
    assert tuple(classes[0].services) == ('estimate_table', 'job_access')


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert own_files() == FILES


def test_no_module_imports_another_episode_folder():
    for relative in sorted(own_files()):
        for node in ast.walk(ast.parse((FOLDER / relative).read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= 1 + relative.count('/') and not (node.level and node.module in CHILDREN), relative
                names = [node.module or ''] if node.level == 0 else []
            for name in names:
                assert '.episodic_workflow.root' not in name, (relative, name)


def local_request(resource_id='local', **changes):
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'a_' + resource_id, 'resource_id': resource_id,
             'resource_kind': 'local', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def api_request(resource_id='blast'):
    return {'version': 'api_service_assignment_v1', 'resource_id': resource_id, 'service': 'ncbi_blast',
            'request': {'program': 'blastp'}, 'endpoint': 'usable_handoff', 'constraints': {}}


def assignment(**changes):
    value = {'version': 'execution_launch_assignment_v1',
             'requests': {'local': local_request('local'), 'blast': api_request('blast'),
                          'hpc': local_request('hpc', resource_kind='hpc')},
             'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['local', 'blast', 'hpc']},
             'input_refs': ['source_1'], 'handoff_unit': 2.0, 'already_handed_off': ['hpc']}
    value.update(changes)
    return value


def parent_input(**changes):
    from_parent = module('messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment(**changes), 'assignment')
    return from_parent.read_from_parent(admitted, {})


def test_the_assignment_is_read_once_and_gives_the_maximum_credit_and_the_yield_class():
    parent = parent_input()
    assert parent['permitted_resource_ids'] == ['blast', 'hpc', 'local']  # the admitted record is key-sorted
    assert parent['maximum_credit'] == 4.0  # two permitted requests without a handoff, 2.0 each
    assert parent['yield_class'] == 'api_ncbi_blast_handoff+practical_hpc_handoff+practical_local_handoff'
    constrained = parent_input(constraints={'kind': 'local'})
    assert constrained['permitted_resource_ids'] == ['local'] and constrained['maximum_credit'] == 2.0


def test_the_controller_is_the_bounded_quality_one_of_the_commission():
    parent = parent_input()
    yield_file = module('yield_estimator')
    profile = {'cutoff': 0.5, 'parameters': {}}
    settings = {'task_yield_profiles': {'launch:' + parent['yield_class']: profile}}
    controller = yield_file.yield_controller(0.0, settings, parent)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 4.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_file.yield_controller(0.0, {'task_yield_profiles': {}}, parent)


def test_a_wrong_commission_fails():
    from_parent = module('messages.read_from_parent')
    with pytest.raises(FormError):
        from_parent.ASSIGNMENT_FORM.admit({**assignment(), 'version': 'other'}, 'assignment')
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        parent_input(requests={'local': local_request('other')})
    with pytest.raises(ValueError, match='execution_request_version_not_carried'):
        parent_input(requests={'local': {**local_request('local'), 'version': 'unknown_v1'}})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        parent_input(handoff_unit=0.0)


def summary_of(parent, **progress):
    return {**parent, 'units_consumed': 1, 'capability_reads': 0, 'capabilities': None, 'commissions': [],
            'handed_off': [], 'handoff_refs': [], 'completed': False, 'action_yields': None, **progress}


def test_each_child_is_commissioned_with_its_request_the_records_and_its_selection():
    to_child = module('messages.msg_to_child')
    summary = summary_of(parent_input())
    api = to_child.msg_to_child('api_job_execution', {'resource_id': 'blast'}, summary)
    assert isinstance(api, ChildMessage) and api.selection == ()
    assert api.assignment['completion_target'] == 2.0 and api.assignment['input_refs'] == ['source_1']
    assert api.assignment['request'] == {'program': 'blastp'}
    hpc = to_child.msg_to_child('hpc_job_execution', {'resource_id': 'hpc'}, summary)
    assert hpc.assignment['input_refs'] == ['source_1'] and hpc.assignment['resource_kind'] == 'hpc'
    local = to_child.msg_to_child('local_job_execution', {'resource_id': 'local'}, summary)
    assert local.assignment['record_refs'] == ['source_1'] and 'input_refs' not in local.assignment
    assert local.selection == ('execution_handoff_refs', 'execution_completed')
    with pytest.raises(KeyError):
        to_child.msg_to_child('local_job_execution', {'resource_id': 'missing'}, summary)
    with pytest.raises(LookupError):
        to_child.msg_to_child('other', {'resource_id': 'local'}, summary)


def test_the_report_of_a_child_says_whether_its_handoff_is_usable():
    from_child = module('messages.read_from_child')
    api = {'credit': 2.0, 'finding': {'service': 's', 'resource_id': 'blast', 'handoff_established': True,
                                      'qualification': 'established'},
           'execution_handoff_refs': ['row_1'], 'execution_completed': True}
    assert from_child.read_from_child('api_job_execution', api, {}, None)['usable_handoff'] is True
    api['finding']['handoff_established'] = False
    assert from_child.read_from_child('api_job_execution', api, {}, None)['usable_handoff'] is False
    hpc = {'credit': 0.0, 'finding': {'handed_off': True}, 'execution_handoff_refs': ['row_2'],
           'execution_completed': False}
    assert from_child.read_from_child('hpc_job_execution', hpc, {}, None)['usable_handoff'] is True
    local = {'credit': 0.0, 'finding': {}, 'execution_handoff_refs': [], 'execution_completed': False}
    assert from_child.read_from_child('local_job_execution', local, {}, None)['usable_handoff'] is False
    with pytest.raises(LookupError):
        from_child.read_from_child('other', local, {}, None)


def test_the_credit_counts_new_handoffs_and_the_return_carries_the_systems_credit():
    credit_file, final = module('credit'), module('messages.final_to_parent')
    parent = parent_input()
    done = summary_of(parent, handed_off=['local', 'blast'], handoff_refs=['row_1', 'row_2'], completed=True)
    assert credit_file.credit(summary_of(parent), None) == 0.0
    assert credit_file.credit(done, None) == 4.0
    result = final.final_to_parent(done, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 4.0},
                                   ('execution_result_refs', 'execution_blast_hsps'))
    assert result['credit'] == 4.0 and result['execution_handoff_refs'] == ['row_1', 'row_2']
    assert result['execution_result_refs'] == [] and result['finding']['handed_off'] == ['local', 'blast']
    selection = ('execution_result_refs', 'execution_blast_hsps')
    admitted = final.RETURN_FORM.select(selection).admit(result, 'result')
    assert admitted['finding']['handoff_complete'] is True
    assert {name for name, spec in final.RETURN_FORM.fields.items() if spec.required} == {
        'credit', 'finding', 'execution_handoff_refs', 'execution_completed'}
    with pytest.raises(FormError):
        final.RETURN_FORM.select(('credit',))
    everything = tuple(name for name, spec in final.RETURN_FORM.fields.items() if not spec.required)
    full = final.final_to_parent(done, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 4.0}, everything)
    assert full['execution_result_origin'] == {} and final.RETURN_FORM.admit(full, 'return') == full


def test_the_tool_and_the_decision_are_the_tasks_own_module_level_functions():
    task = module('task')
    summary = summary_of(parent_input())
    assert task.offered(summary) == ['execution_capabilities', 'commission:blast', 'commission:hpc',
                                     'commission:local']
    call = task.action({'selection': 'commission:blast'}, summary, None, None)
    assert (call.slot, dict(call.arguments)) == ('api_job_execution', {'resource_id': 'blast'})
    call = task.action({'selection': 'commission:hpc'}, summary, None, None)
    assert call.slot == 'hpc_job_execution'
    from episode_runtime import Rejected
    with pytest.raises(Rejected):
        task.action({'selection': 'commission:unlisted'}, summary, None, None)
