"""The HPC allocation execution episode of A103 is one private binding in the ten-file form."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.'
           'hpc_allocation_execution')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition')
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
LIBRARY = 'gene_annotation_episode.episodic_workflow.episode_support.'


def episode_class():
    module = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__]
    assert len(classes) == 1
    return classes[0]


def own_files():
    """The folder's own python files: not its tests and not the child episode folders."""
    return [path for path in FOLDER.rglob('*.py') if '__pycache__' not in path.parts
            and not {'tests', *CHILDREN} & set(path.relative_to(FOLDER).parts)]


def test_the_class_inherits_only_the_episode_binding():
    cls = episode_class()
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
    assert dict(cls.child_slots) == {name.replace('execution_', '').replace('job_submission', 'launch')
                                     .replace('progress_assessment', 'monitor').replace('result_acquisition', 'results'):
                                     cls.binding_path + '/' + name for name in CHILDREN}
    assert cls.services == ('estimate_table', 'job_access')


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in own_files()}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in own_files():
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for name in names:
                assert '.episodic_workflow.root.' not in name, (str(path), name)
            if isinstance(node, ast.ImportFrom) and node.level:
                assert node.level == 1 or path.parent.name == 'messages', (str(path), node.module)
    # A test registers the child episodes it runs with; it names no episode outside this folder.
    for path in (FOLDER / 'tests').rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            for name in ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                         else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else []):
                assert '.episodic_workflow.root.' not in name or name.startswith(PACKAGE), (str(path), name)


def test_the_commission_is_read_from_the_assignment_and_the_controller_is_completion():
    cls = episode_class()
    commission = {'objective': 'o', 'resource_id': 'aurora', 'obligations': {'a': {'credit': 3.0}, 'b': {'credit': 2.0}},
                  'candidates': [], 'yield_bindings': {'hpc_execution': {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}}}
    assignment = {'ledger': 'hpc_ledger_1', 'owner_episode_id': 'owner', 'commission_id': 'c1', 'commission': commission,
                  'scope': {'subject_refs': []}, 'ledger_credit': 0.0}
    admitted = cls.assignment_form.admit(assignment, 'assignment')
    parent_input = cls.read_from_parent(admitted, {})
    controller = cls.yield_controller(0.0, {}, parent_input)
    assert isinstance(controller, CompletionYieldController)
    assert controller.target == 5.0 and controller.cost == 0.5
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref'):
        cls.read_from_parent({**admitted, 'commission_source_ref': ['source_x']}, {})
    without = {**parent_input, 'commission': {key: value for key, value in commission.items() if key != 'yield_bindings'}}
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required:hpc_execution'):
        cls.yield_controller(0.0, {}, without)


def test_the_return_form_declares_credit_finding_and_the_selectable_old_facts():
    cls = episode_class()
    fields = cls.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    selectable = {name for name, field in fields.items() if not field.required}
    assert {'hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'} <= selectable


def descendants():
    """One instance of every episode class below this folder (the children the real runner registers)."""
    found = []
    for path in sorted(FOLDER.rglob('episode.py')):
        parts = path.relative_to(FOLDER).parts[:-1]
        if parts and '__pycache__' not in parts and 'tests' not in parts:
            module = importlib.import_module('.'.join([PACKAGE, *parts, 'episode']))
            found.extend(value() for value in vars(module).values() if isinstance(value, type)
                         and value.__module__ == module.__name__)
    return found


class WithoutJobs:
    """A real service object that offers no job operation: the job services are not built yet."""


