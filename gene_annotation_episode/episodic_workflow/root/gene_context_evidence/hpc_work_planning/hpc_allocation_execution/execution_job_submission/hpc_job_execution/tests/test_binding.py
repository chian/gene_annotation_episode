"""The real binding: importing ``episode.py`` runs the class-definition checks, so the import is the check."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.tests.', 1)[0]
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py', 'tests',
             'messages'}
MESSAGE_FILES = {'__init__.py', 'read_from_parent.py', 'internal_summary.py', 'final_to_parent.py'}


@pytest.fixture(scope='module')
def episode():
    return importlib.import_module(PACKAGE + '.episode')


def test_the_class_inherits_only_the_episode_base(episode):
    assert episode.HpcJobExecution.__bases__ == (EpisodeBinding,)
    assert episode.HpcJobExecution.binding_path == (
        'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution')
    assert PACKAGE.endswith(episode.HpcJobExecution.binding_path.replace('/', '.'))
    assert dict(episode.HpcJobExecution.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files():
    names = {path.name for path in FOLDER.iterdir() if path.name != '__pycache__'}
    assert names == TEN_FILES
    assert {path.name for path in (FOLDER / 'messages').iterdir() if path.name != '__pycache__'} == MESSAGE_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for module in modules:
                assert not module.startswith('gene_annotation_episode.episodic_workflow.root'), (path, module)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                pytest.fail('a relative import leaves the folder: %s' % path)


def test_the_return_form_declares_what_a_launch_episode_always_returns(episode):
    fields = episode.HpcJobExecution.return_form.fields
    assert {name for name, spec in fields.items() if spec.required} == {
        'credit', 'finding', 'execution_handoff_refs', 'execution_completed'}
    assert fields['credit'].type == 'number'
    assert episode.HpcJobExecution.return_form.select(['practical_receipt_refs']).fields['practical_receipt_refs'].required
    with pytest.raises(FormError):
        episode.HpcJobExecution.return_form.select(['execution_handoff_refs'])


def test_the_assignment_form_fixes_the_resource_kind(episode):
    fields = episode.HpcJobExecution.assignment_form.fields
    assert fields['resource_kind'].value == 'hpc'
    assert fields['input_refs'].type == 'record_refs' and not fields['input_refs'].required
