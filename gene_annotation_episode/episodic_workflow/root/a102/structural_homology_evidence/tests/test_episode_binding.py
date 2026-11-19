"""The A102 structural homology evidence head is one private binding in the ten-file form.

Real objects only: the class-definition checks run by importing ``episode.py``; the commissions this head builds
are admitted by the children's own declared assignment forms and return selections (the children's modules are
loaded by name, never imported by the episode); the head's assignment, controller, credit selection and return are
exercised on real data. Nothing is faked, scripted or patched."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence'
BINDING_PATH = 'structural_homology_evidence'
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
CHILDREN = {
    'structural_homology_evidence': BINDING_PATH,
    'literature': BINDING_PATH + '/published_evidence_assessment',
    'execution_launch': BINDING_PATH + '/execution_job_submission',
    'resource_launch': BINDING_PATH + '/resource_work_submission',
    'execution_results': BINDING_PATH + '/execution_result_acquisition',
    'resource_results': BINDING_PATH + '/resource_result_acquisition',
    'hpc': BINDING_PATH + '/hpc_work_planning',
    'monitor': BINDING_PATH + '/execution_progress_assessment',
}
LIBRARY = 'a' * 64
AXIS_REF = {'version': 'structural_homology_evidence_option_ref_v1', 'library_id': LIBRARY, 'slot': 'evidence_axis',
            'option_id': 'A102', 'entry_sha256': 'b' * 64}
THOUGHT_REF = {'version': 'structural_homology_evidence_option_ref_v1', 'library_id': LIBRARY,
               'slot': 'thought_pattern', 'option_id': 'P1', 'entry_sha256': 'c' * 64}
SELECTION = {'version': 'structural_homology_evidence_selection_v3', 'evidence_axis': AXIS_REF,
             'thought_pattern': THOUGHT_REF, 'child_tool_info': []}
REF = 'hypothesis_' + 'd' * 24


def episode_class(package=PACKAGE):
    module = importlib.import_module(package + '.episode')
    classes = [value for value in vars(module).values()
               if isinstance(value, type) and value.__module__ == module.__name__]
    assert len(classes) == 1
    return classes[0]


def child_class(path):
    return episode_class(PACKAGE if path == BINDING_PATH else PACKAGE + '.' + path.split('/', 1)[1])


def assignment(**changes):
    value = {'selection': SELECTION, 'proposed_annotation_ref': [REF], 'evidence_refs': ['source_' + 'e' * 24],
             'constraints': {}, 'context': {'evidence_task': {'version': 'evidence_axis_task_v1',
                                                              'kind': 'whole_axis_findings', 'evidence_axis': 'A102',
                                                              'credit_unit': 1.0}},
             'scope': {'subject_refs': ['input_' + 'f' * 24]}, 'scope_refs': ['input_' + 'f' * 24]}
    return {**value, **changes}


def parent_input(**changes):
    cls = episode_class()
    return cls.read_from_parent(cls.assignment_form.admit(assignment(**changes), 'assignment'), {})


def summary(**changes):
    value = {**parent_input(), 'progress_snapshots': {}, 'report': None, 'committed_record_refs': [],
             'children': [], 'received_process_results': [], 'revisions': [],
             'credit_view': {'credit': 1.0, 'axis_components': {'A102': 1.0}}}
    return {**value, **changes}


def test_the_class_inherits_only_the_episode_binding():
    cls = episode_class()
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == BINDING_PATH
    assert dict(cls.child_slots) == CHILDREN
    assert set(cls.services) == {'tool_catalog', 'native_events'}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts
             and path.relative_to(FOLDER).parts[0] not in {child.split('/')[1] for child in CHILDREN.values()
                                                            if '/' in child}}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for relative in TEN_FILES:
        path = FOLDER / relative
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for name in names:
                assert '.episodic_workflow.root.' not in name, (str(path), name)


@pytest.mark.parametrize('slot', sorted(CHILDREN))
def test_the_slot_names_a_declared_child_and_its_return_fields_are_the_childs(slot):
    cls = episode_class()
    task = importlib.import_module(PACKAGE + '.task')
    child = child_class(cls.child_slots[slot])
    assert child.binding_path == CHILDREN[slot]
    selectable = {name for name, field in child.return_form.fields.items() if not field.required}
    assert set(task.RETURN_FIELDS[slot]) <= selectable


def test_the_assignment_form_reads_the_old_properties_and_derives_the_task():
    value = parent_input()
    assert value['selection']['evidence_axis']['option_id'] == 'A102'
    assert value['proposed_annotation_ref'] == [REF]
    assert value['credit_unit'] == 1.0
    assert value['a102_task'] is None
    assert value['task_key'] == 'A102:received_scientific_finding_progress'
    assert value['yield_method'] == 'accumulation'


def test_the_assignment_checks_refuse_a_wrong_axis_and_two_proposed_annotations():
    cls = episode_class()
    wrong = {**SELECTION, 'evidence_axis': {**AXIS_REF, 'option_id': 'A101'}}
    with pytest.raises(ValueError, match='scientific_support_metadata_required'):
        cls.read_from_parent(cls.assignment_form.admit(assignment(selection=wrong), 'assignment'), {})
    with pytest.raises(ValueError, match='scientific_one_proposed_annotation_required'):
        cls.read_from_parent(cls.assignment_form.admit(
            assignment(proposed_annotation_ref=[REF, 'hypothesis_' + '1' * 24]), 'assignment'), {})
    with pytest.raises(FormError):
        cls.assignment_form.admit({**assignment(), 'unknown_field': 1}, 'assignment')


def test_a_named_comparative_task_has_the_bounded_quality_projector_and_controller():
    cls = episode_class()
    task = importlib.import_module(PACKAGE + '.task')
    from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import (
        task_context)
    value = parent_input(context={'a102_task': task_context('native_comparison')})
    assert value['task_key'] == 'A102:native_comparison'
    assert value['yield_method'] == 'bounded_quality' and value['native_score_maximum'] == 1.0
    settings = {'yield_bindings': {value['task_key']: {
        'kind': 'bounded_quality', 'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1},
        'credit_definition': value['credit_definition']}}}
    assert isinstance(cls.yield_controller(0.0, settings, value), BoundedQualityYieldController)
    assert task.CHILD_SLOTS == dict(cls.child_slots)


def test_the_controller_is_declared_per_task_for_exactly_its_credit_definition():
    cls = episode_class()
    value = parent_input()
    declaration = {'kind': 'accumulation', 'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1},
                   'credit_definition': value['credit_definition']}
    controller = cls.yield_controller(0.0, {'yield_bindings': {value['task_key']: declaration}}, value)
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='scientific_yield_binding_missing_for_task'):
        cls.yield_controller(0.0, {'yield_bindings': {'A102:other': declaration}}, value)
    with pytest.raises(ValueError, match='scientific_yield_credit_definition_mismatch'):
        cls.yield_controller(0.0, {'yield_bindings': {value['task_key']: {
            **declaration, 'credit_definition': {'kind': 'something_else'}}}}, value)
    with pytest.raises(ValueError, match='scientific_yield_method_credit_mismatch'):
        cls.yield_controller(0.0, {'yield_bindings': {value['task_key']: {**declaration, 'kind': 'bounded_quality'}}},
                             value)


def test_credit_is_the_projected_number_and_a_head_without_a_proposed_annotation_has_none():
    cls = episode_class()
    credit = importlib.import_module(PACKAGE + '.credit')
    assert cls.credit(summary(), None) == 1.0
    with pytest.raises(ValueError, match='scientific_task_proposed_annotation_required'):
        credit.credit_view(parent_input(proposed_annotation_ref=[]), None)


def commission(slot):
    arguments = {
        'structural_homology_evidence': {'selection': SELECTION, 'evidence_refs': ['source_' + 'e' * 24],
                                         'constraints': {}},
        'literature': {'question_context_refs': ['source_' + 'e' * 24], 'source_refs': ['source_' + 'e' * 24],
                       'literature_task': {'kind': 'source_answer', 'answer_kind': 'screening'},
                       'received_record_refs': []},
        'execution_launch': {'requests': {'r': {}}, 'immutable_input_versions': [], 'constraints': {}},
        'resource_launch': {'job_request': {}, 'immutable_input_versions': [], 'constraints': {},
                            'software_knowledge_refs': [], 'resource_knowledge_refs': [],
                            'input_refs': ['source_' + 'e' * 24]},
        'execution_results': {'handoff_ref': ['source_' + 'e' * 24], 'selector': {'paths': ['a']},
                              'resource_kind': 'local'},
        'resource_results': {'handoff': {}, 'requested_data_selector': {}},
        'hpc': {'input_refs': ['source_' + 'e' * 24], 'commission_id': 'c'},
        'monitor': {'target_handle': 'target', 'requested_fields': ['execution_status'], 'known_progress_refs': [],
                    'permitted_committed_record_types': []},
    }[slot]
    units = {'execution_launch': {'handoff_unit': 1.0}, 'resource_launch': {'completion_target': 1.0},
             'execution_results': {'acquired_record_unit': 1.0}, 'monitor': {'information_unit': 1.0},
             'literature': {'credit_unit': 1.0}}.get(slot, {})
    task = importlib.import_module(PACKAGE + '.task')
    texts = {} if slot == 'literature' else {'goal': 'g', 'purpose': 'p'}
    return {**texts, 'assignment': arguments, 'selection': [task.RETURN_FIELDS[slot][0]],
            'units': units}


@pytest.mark.parametrize('slot', sorted(CHILDREN))
def test_each_commission_fits_the_childs_own_forms(slot):
    cls = episode_class()
    child = child_class(CHILDREN[slot])
    message = cls.msg_to_child(slot, commission(slot), summary())
    assert isinstance(message, ChildMessage)
    child.assignment_form.admit(message.assignment, 'assignment')
    selected = child.return_form.select(message.selection)
    assert {'credit', 'finding', *message.selection} <= set(selected.fields)


def test_the_literature_commission_passes_no_text_a_fixed_objective_and_an_empty_message():
    task = importlib.import_module(PACKAGE + '.task')
    message = episode_class().msg_to_child('literature', commission('literature'), summary())
    assert message.objective == 'assess_published_evidence' and message.message == {}
    assert set(task.child_arguments('literature')['properties']) == {'assignment', 'selection'}
    assert {'goal', 'purpose'} <= set(task.child_arguments('monitor')['properties'])


def test_a_wrong_commission_fails_with_its_own_error():
    cls = episode_class()
    with pytest.raises(KeyError):
        cls.msg_to_child('unknown_slot', commission('hpc'), summary())
    arguments = commission('execution_launch')
    arguments['units'] = {}
    with pytest.raises(KeyError):
        cls.msg_to_child('execution_launch', arguments, summary())
    wrong = {**commission('hpc'), 'selection': ['not_a_field_of_the_child']}
    message = cls.msg_to_child('hpc', wrong, summary())
    with pytest.raises(FormError):
        child_class(CHILDREN['hpc']).return_form.select(message.selection)


def test_the_monitor_report_carries_its_delivered_observations_and_needs_their_snapshots():
    cls = episode_class()
    snapshot = {'version': 'progress_snapshot_v1', 'progress_ref': 'progress_' + 'a' * 24, 'target_handle': 't'}
    result = {'credit': 1.0, 'finding': {'target_handle': 't'}, 'monitoring_progress_refs': [snapshot['progress_ref']],
              'monitoring_progress_snapshots': {snapshot['progress_ref']: snapshot}}
    report = cls.read_from_child('monitor', result, summary(), None)
    assert report['progress_snapshots'] == {snapshot['progress_ref']: snapshot}
    assert report['returned'] == ['monitoring_progress_refs', 'monitoring_progress_snapshots']
    with pytest.raises(ValueError, match='monitor_report_requires_progress_snapshots'):
        cls.read_from_child('monitor', {**result, 'monitoring_progress_snapshots': {}}, summary(), None)
    again = cls.read_from_child('structural_homology_evidence', {
        'credit': 2.0, 'finding': {}, 'structural_homology_evidence_results': [{'task': 'A102:x'}]}, summary(), None)
    assert again['process_results'] == [{'task': 'A102:x'}] and again['child_credit'] == 2.0


def test_the_return_declares_credit_and_finding_and_the_old_fact_sources():
    cls = episode_class()
    fields = cls.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    for name in ('structural_homology_evidence_results', 'committed_record_refs'):
        assert not fields[name].required
    assert set(cls.return_form.select(('committed_record_refs',)).fields) >= {'credit', 'finding',
                                                                                 'committed_record_refs'}


def test_the_head_returns_its_credit_the_finding_and_each_selectable_field_and_the_form_admits_it():
    cls = episode_class()
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    result = cls.final_to_parent(summary(), completion, ())
    assert result['credit'] == completion['credit'] and 'finding' in result
    cls.return_form.admit(result, 'return')
    names = tuple(name for name in cls.return_form.fields if name not in {'credit', 'finding'})
    result = cls.final_to_parent(summary(), completion, names)
    assert result['committed_record_refs'] == []
    assert result['structural_homology_evidence_results'][0]['credit'] == 1.0
    cls.return_form.admit(result, 'return')


def test_the_decision_schema_offers_the_episodes_own_tools_and_every_child(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
        strict_output_schema)
    from gene_annotation_episode.state import Store
    task = importlib.import_module(PACKAGE + '.task')
    store = Store(tmp_path / 'store')
    try:
        value = summary(reasoning_schema=store.reasoning_schema())
    finally:
        store.close()
    names = task.offered(value, {})
    assert names == {'own': ['process_search', 'process_entry', 'process_sources', 'process_revise', 'reason',
                             'report', 'wait_for_events'], 'library': []}
    schema = task.selection_schema(names, value, task.library_catalog(None, names['library']))
    options = schema['properties']['selection']['anyOf']
    tools = {option['properties']['tool']['const'] for option in options
             if option['properties']['kind']['const'] == 'tool'}
    slots = {option['properties']['slot']['const'] for option in options
             if option['properties']['kind']['const'] == 'child'}
    assert tools == set(names['own']) and slots == set(CHILDREN)
    assert set(task.TOOLS) >= tools
    strict_output_schema(schema, open_records_as_text=True, argument_transport_error=task.TRANSPORT_ERROR)


def test_a_selected_library_tool_needs_the_tool_catalog_service_which_is_not_built():
    task = importlib.import_module(PACKAGE + '.task')
    value = summary(selection={**SELECTION, 'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]})
    names = task.offered(value, {})
    assert names['library'] == ['source_read']
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-TOOL-CATALOG-SERVICE: tool_catalog'):
        task.library_catalog(None, names['library'])


def test_the_literature_report_keeps_the_experimental_structure_sheets_apart_from_the_native_arm():
    cls = episode_class()
    sheet = {'evidence_type': 'experimental_structure_geometry', 'sheet_refs': ['source_' + 'b' * 24]}
    result = {'credit': 1.0, 'finding': {'structure_sheets': [sheet, sheet]}}
    report = cls.read_from_child('literature', result, summary(), None)
    assert report['experimental_structure_sheets'] == [sheet, sheet] and report['process_results'] == []
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
        experimental_structure_arm)
    arm = experimental_structure_arm(report['experimental_structure_sheets'])
    assert arm == {'sheets': [sheet], 'aggregation': 'none', 'separate_from': 'comparative_native_grading_sheets'}
    other = cls.read_from_child('execution_launch', {'credit': 0.0, 'finding': {}}, summary(), None)
    assert other['experimental_structure_sheets'] == []
