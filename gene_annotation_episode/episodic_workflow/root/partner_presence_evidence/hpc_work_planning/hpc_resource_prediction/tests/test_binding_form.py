"""The real episode module: its class definition checks run at import, its folder holds the ten-file set minus the
two child files, it imports no other episode folder, and its form and controller functions behave as carried."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.partner_presence_evidence.hpc_work_planning.'
           'hpc_resource_prediction')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').HPCResourcePrediction


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
    assert dict(episode.child_slots) == {}
    assert set(episode.tools) == {'hpc_open', 'hpc_read', 'hpc_compare', 'hpc_history_refresh', 'hpc_discovery_run',
                                  'hpc_candidate_propose', 'hpc_queue_observe', 'hpc_model_fit'}
    assert tuple(episode.services) == ('job_access', 'estimate_table')


def test_folder_holds_exactly_the_file_set_of_an_episode_without_children():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts:
            continue
        depth = len(relative.parts)  # a relative import of this level or deeper leaves the folder
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                if node.level >= depth + 1:
                    raise AssertionError(str(relative) + ' imports outside its folder')
                names = [node.module or '']
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                assert not name.startswith('gene_annotation_episode.episodic_workflow.root'), (relative, name)


def test_return_form_is_controlled_data_with_the_ledger_rows_always_returned():
    form = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM
    fields = form.as_record()
    assert {name for name, field in fields.items() if field['required']} == {'credit', 'finding', 'hpc_ledger_refs'}
    assert {name for name, field in fields.items() if not field['required']} == {'hpc_result_refs'}
    assert {field['type'] for field in fields.values()} == {'number', 'record', 'record_refs'}
    finding = importlib.import_module(PACKAGE + '.messages.final_to_parent').FINDING_FORM.as_record()
    assert {field['type'] for field in finding.values()} == {'boolean', 'integer'}       # no text passes


def test_assignment_form_and_read_from_parent_need_exactly_one_commission_identity():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    base = {'owner_episode_id': 'episode_1', 'scope': {'subject_refs': []}}
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_id': 'c1', 'ledger_row_refs': ['row_1']},
                                            'assignment')
    parent = module.read_from_parent(admitted, {})
    assert parent == {'owner_episode_id': 'episode_1', 'commission_id': 'c1', 'commission_source_ref': None,
                      'scope': {'subject_refs': []}}
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_source_ref': ['source_1']}, 'assignment')
    assert module.read_from_parent(admitted, {})['commission_source_ref'] == 'source_1'
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent(module.ASSIGNMENT_FORM.admit(base, 'assignment'), {})
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent({**base, 'commission_id': 'c1', 'commission_source_ref': ['source_1']}, {})
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({'owner_episode_id': 'episode_1', 'commission_id': 'c1'}, 'assignment')


def test_yield_controller_is_accumulation_and_takes_no_settings():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {}, {})
    assert isinstance(controller, AccumulationYieldController)


def test_the_selection_offers_the_shared_history_tool_only_with_shared_memory():
    task = importlib.import_module(PACKAGE + '.task')
    without = {entry['name'] for entry in task.catalog(False)}
    with_memory = {entry['name'] for entry in task.catalog(True)}
    assert with_memory - without == {'hpc_history_refresh'}
    assert 'hpc_open' not in with_memory
    assert len(task.selection_schema(False)['properties']['selection']['anyOf']) == len(without)


def test_the_instructions_state_the_purpose_the_ledger_the_tools_and_the_credit():
    task = importlib.import_module(PACKAGE + '.task')
    text = task.INSTRUCTIONS
    assert text.startswith('You are the resource-prediction episode of one HPC commission. Your job is to predict')
    for phrase in ('record that expectation in the HPC ledger', 'What you are shown.', 'How to work.',
                   'What earns credit.', 'The fixed reference and validation set cannot change.',
                   'Unknown inputs stay unknown'):
        assert phrase in text
    for name in (entry['name'] for entry in task.catalog(False)):
        assert name in text or name == 'hpc_read'
    assert 'SSH' not in text and 'iterator' not in text and 'receipt' not in text
