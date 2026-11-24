"""Real checks of the local job execution binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set (no children, so no ``msg_to_child.py`` or
``read_from_child.py``), no module imports another episode folder, and the two forms declare what the old
assignment schema and the old fact sources named."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

MODULE = ('gene_annotation_episode.episodic_workflow.root.partner_presence_evidence.hpc_work_planning.'
          'execution_job_submission.local_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {}
    assert set(classes[0].tools) == {'exec_command', 'knowledge_lookup', 'launch_instruction_lookup'}
    assert tuple(classes[0].services) == ('job_access',)


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


def test_no_module_imports_another_episode_folder():
    own = MODULE
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == own or name.startswith(own + '.'), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_form_has_one_field_per_old_schema_property():
    from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
        ASSIGNMENT_SCHEMA)
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    assert set(ASSIGNMENT_SCHEMA['properties']) <= set(from_parent.ASSIGNMENT_FORM.fields)


def test_a_remote_resource_assignment_is_not_admitted():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    with pytest.raises(FormError):
        from_parent.ASSIGNMENT_FORM.admit({'version': 'practical_assignment', 'resource_kind': 'hpc'},
                                          'assignment')


def test_the_return_declares_credit_and_finding_and_every_old_fact_source():
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    fields = final.RETURN_FORM.fields
    assert fields['credit'].required and fields['finding'].required
    assert fields['credit'].type == 'number'
    for name in ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs',
                 'execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                 'execution_result_origin', 'execution_file_source_refs', 'execution_file_capture_outcomes',
                 'execution_blast_hsps'):
        assert name in fields and not fields[name].required


def test_the_return_carries_credit_finding_and_every_selectable_field_and_the_form_admits_it():
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    summary = {'assignment': {'endpoint': 'usable_handoff'}, 'commands': [], 'receipts': [], 'receipt_refs': [],
               'handoff_refs': [], 'execution_completion': None,
               'execution_progress': {'satisfied_keys': [], 'requirements': [{'key': 'handoff', 'satisfied': False}]}}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0}
    final.RETURN_FORM.admit(final.final_to_parent(summary, completion, ()), 'return')
    every = tuple(sorted(name for name, field in final.RETURN_FORM.fields.items() if not field.required))
    full = final.final_to_parent(summary, completion, every)
    final.RETURN_FORM.select(every).admit(full, 'return')
    assert full['execution_result_origin'] == {} and full['practical_completed'] is False
