"""The episode is a private binding in the ten-file form (real checks over the real class and source)."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}


def test_importing_episode_runs_the_class_definition_checks_and_binds_directly_to_the_system_type():
    episode = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == 'gene_context_evidence/resource_result_acquisition'
    assert dict(classes[0].child_slots) == {}
    assert not hasattr(classes[0], 'msg_to_child') and not hasattr(classes[0], 'read_from_child')


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts}
    assert found == TEN_FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    root = 'gene_annotation_episode.episodic_workflow.root'
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        depth = len(path.relative_to(FOLDER).parts) - 1
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= depth + 1, (path, 'imports above its own folder')
                if node.level:
                    assert node.level == depth + 1 or node.level == 1, path
                names = [node.module or ''] if not node.level else []
            for name in names:
                assert not name.startswith(root) or name.startswith(PACKAGE), (path, name)


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    selection_record = {'capability_binding_ref': 'binding_1', 'resource_id': 'aurora', 'kind': 'hpc'}
    handoff = {'execution_handle': 'h1', 'resource_selection': selection_record, 'state': 'usable', 'failure': None}
    summary = {'facts': {'execution_handoffs': [handoff], 'blast_rows': [1]},
               'assignment': {'handoff': {'resource_selection': selection_record}}, 'last_outcome': None,
               'interpretation': {'text': 'the result file holds the table'}}
    selection = [name for name, spec in final.RETURN_FORM.fields.items() if not spec.required]
    result = final.final_to_parent(summary, {'credit': 1.5}, selection)
    assert result['finding']['handoff_state'] == 'usable' and result['execution_handoff'] == [handoff]
    assert result['adapter_facts'] == {'blast_rows': [1]}
    assert final.RETURN_FORM.admit(result, 'return') == result
