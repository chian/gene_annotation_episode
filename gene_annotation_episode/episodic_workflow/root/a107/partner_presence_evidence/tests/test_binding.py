"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (plus its child episode folders); no module imports another episode folder; the
episode's own forms and functions behave on real data; the names this head sends to and selects from each child are
the names the child's own files declare (read as data with ``ast``: the child folders are never imported). Nothing
here is faked."""
import ast
import importlib
from pathlib import Path

import pytest
from jsonschema import ValidationError

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PartnerPresenceEvidence
CHILDREN = {'partner_presence_evidence': None,
            'literature': 'published_evidence_assessment',
            'launch': 'execution_job_submission',
            'results': 'execution_result_acquisition',
            'monitor': 'execution_progress_assessment',
            'hpc': 'hpc_work_planning'}
CHILD_FOLDERS = {name for name in CHILDREN.values() if name}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SOURCE, ARTIFACT, SUBJECT = 'source_' + 'a' * 24, 'artifact_' + 'b' * 24, 'input_' + 'c' * 24
LIBRARY_ID, ENTRY = 'd' * 64, 'e' * 64
SELECTION = {'version': 'partner_presence_evidence_selection_v3',
             'evidence_axis': {'version': 'partner_presence_evidence_option_ref_v1', 'library_id': LIBRARY_ID,
                               'slot': 'evidence_axis', 'option_id': 'A107', 'entry_sha256': ENTRY},
             'thought_pattern': {'version': 'partner_presence_evidence_option_ref_v1', 'library_id': LIBRARY_ID,
                                 'slot': 'thought_pattern', 'option_id': 'P12', 'entry_sha256': ENTRY},
             'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
ASSIGNMENT = {'selection': SELECTION, 'evidence_refs': [SOURCE], 'constraints': {}, 'context': {},
              'scope': {'subject_refs': [SUBJECT]}, 'received_record_refs': [SOURCE, ARTIFACT, SUBJECT],
              'finding_unit': 1.0, 'handoff_unit': 2.0, 'acquired_record_unit': 3.0, 'information_unit': 4.0}
COMPLETION = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.5}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILD_FOLDERS}


def form_of(path, name):
    """The fields of a ``RecordForm({...})`` assigned to ``name`` in a child's file, read as data: ``{field:
    (required, declared value)}``."""
    body = ast.parse(path.read_text()).body
    constants = {node.targets[0].id: node.value.value for node in body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant)}
    for node in body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            fields, generated = {}, []
            for key, value in zip(node.value.args[0].keys, node.value.args[0].values):
                if key is None:     # a ``**{...}`` entry generated from library constants: not readable as data
                    generated.append(True)
                    continue
                required = True
                for keyword in value.keywords:
                    if keyword.arg == 'required':
                        required = keyword.value.value
                declared = None
                if value.func.id == 'DeclaredField':
                    argument = value.args[2]
                    declared = argument.value if isinstance(argument, ast.Constant) else constants[argument.id]
                fields[key.value] = (required, declared)
            return fields, bool(generated)
    raise AssertionError(name + ' not in ' + str(path))


def child_form(child, file, name):
    return form_of(FOLDER / child / 'messages' / (file + '.py'), name)


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH == 'partner_presence_evidence'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {
        slot: EPISODE.binding_path + '/' + child if child else EPISODE.binding_path
        for slot, child in CHILDREN.items()}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES
    for child in CHILD_FOLDERS:
        assert (FOLDER / child / 'episode.py').is_file()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts or path.relative_to(FOLDER).parts[0] in CHILD_FOLDERS:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
                assert not any(module.startswith(PACKAGE + '.' + child) for child in CHILD_FOLDERS), \
                    str(path.relative_to(FOLDER)) + ' imports its child ' + module
            if isinstance(node, ast.ImportFrom) and node.level:
                assert not any((node.module or '').split('.')[0] == child for child in CHILD_FOLDERS)


def test_the_commission_form_admits_an_assignment_and_refuses_an_unknown_field_and_a_wrong_selection():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['evidence_refs'] == [SOURCE] and parent_input['finding_unit'] == 1.0
    assert parent_input['proposed_annotation_ref'] is None and parent_input['message'] == {'purpose': 'x'}
    assert set(form.record_refs(admitted)) == {SOURCE, ARTIFACT, SUBJECT}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    proposed = EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'proposed_annotation_ref': [SOURCE]}, 'test'), {})
    assert proposed['proposed_annotation_ref'] == SOURCE
    with pytest.raises(ValueError, match='exactly_one_reference'):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'proposed_annotation_ref': [SOURCE, ARTIFACT]}, 'test'), {})
    other_axis = {**SELECTION, 'evidence_axis': {**SELECTION['evidence_axis'], 'option_id': 'A101'}}
    with pytest.raises(ValidationError):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'selection': other_axis}, 'test'), {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    selectable = {name for name, field in form.fields.items() if not field.required}
    assert selectable == {'committed_record_refs', 'a107_qualification_records',
                          'a107_genomic_execution_records', 'component_axis_native_component_records',
                          'component_axis_native_execution_records'}
    summary = {'literature_sheets': [], 'committed_record_refs': [ARTIFACT],
               'received': {'qualifications': [{'source_ref': SOURCE}], 'genomic_execution': [],
                            'native_components': [], 'native_execution': []}}
    result = EPISODE.final_to_parent(summary, COMPLETION, ())
    assert result['credit'] == 2.5 and result['finding'] == {
        'evidence_type': 'not_reported', 'direction': 'unknown', 'target_correspondence': 'not_evaluated',
        'sheet_refs': [], 'partner_sheets': [], 'matched_sheet_count': 0, 'matched_loss_sheet_count': 0,
        'distinct_experiment_count': 0}
    form.admit(result, 'test')
    selected = EPISODE.final_to_parent(summary, COMPLETION, ('committed_record_refs', 'a107_qualification_records'))
    assert selected['committed_record_refs'] == [ARTIFACT] and selected['a107_qualification_records'] == [SOURCE]
    form.select(('committed_record_refs', 'a107_qualification_records')).admit(selected, 'test')
    every = tuple(sorted(selectable))
    form.select(every).admit(EPISODE.final_to_parent(summary, COMPLETION, every), 'test')


def test_credit_and_finding_cannot_be_selected():
    with pytest.raises(FormError):
        EPISODE.return_form.select(('credit',))
    with pytest.raises(FormError):
        EPISODE.return_form.select(('finding',))


def test_the_credit_is_real_code_and_the_controller_is_accumulation():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    controller = EPISODE.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}},
                                          EPISODE.read_from_parent(EPISODE.assignment_form.admit(ASSIGNMENT, 'test'), {}))
    assert type(controller).__name__ == 'AccumulationYieldController'


def test_the_model_can_name_every_child_slot_and_the_tools_of_the_task():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(task.CHILD_SLOTS) == set(CHILDREN) and set(task.CHILD_FIELDS) == set(CHILDREN)
    assert set(task.TOOLS) >= {'selected_tool', 'reason', 'process_revise', 'process_search',
                               'knowledge_read'}
    assert set(EPISODE.tools) == set(task.TOOLS)
    for slot in CHILDREN:
        schema = task.child_arguments(slot)
        names = sorted(importlib.import_module(PACKAGE + '.messages.msg_to_child').SELECTABLE[slot])
        returned = schema['properties']['return_fields']
        assert (returned['items']['enum'] == names) if names else returned['maxItems'] == 0


@pytest.mark.parametrize('slot', [slot for slot, child in CHILDREN.items() if child])
def test_the_selectable_names_are_the_names_the_child_declares(slot):
    child = CHILDREN[slot]
    declared, generated = child_form(child, 'final_to_parent', 'RETURN_FORM')
    selectable = {name for name, (required, _) in declared.items() if not required}
    sent = importlib.import_module(PACKAGE + '.messages.msg_to_child').SELECTABLE[slot]
    # A form that generates part of its fields from library constants (launch, results) is read only as far as its
    # literal fields: those are all offered here; the others are read from the form when the pair is linked.
    assert selectable <= set(sent) and (generated or set(sent) == selectable)
    assert declared['credit'][0] and declared['finding'][0]


def arguments_for(slot, task):
    """One value for every argument the model may supply for the slot."""
    values = {'objective': 'o', 'purpose': 'p', 'return_fields': []}
    samples = {'process_selection': {**SELECTION, 'child_tool_info': [
        {'name': 'source.read', 'resources': 'local', 'description': 'd', 'instructions': 'i'}]},
        'revision_origin': {'version': 'partner_presence_evidence_revision_origin_v1',
                            'parent_invocation_ref': 'scientific_invocation_' + 'a' * 24,
                            'preparation_operation_ref': 'operation_' + 'a' * 24},
        'evidence_refs': [SOURCE], 'constraints': {}, 'context': {}, 'question_context_refs': [],
        'source_refs': [SOURCE], 'partner_components': ['removal'], 'requests': {'r': {}},
        'immutable_input_versions': [], 'launch_instructions': {}, 'record_refs': [SOURCE],
        'received_handoff_resources': ['r'], 'handoff_ref': 'h', 'selector': {}, 'target': {},
        'initial_result_refs': [SOURCE], 'target_handle': 't', 'requested_fields': ['execution_status'],
        'known_progress_refs': [], 'permitted_committed_record_types': [], 'known_progress_snapshots': {},
        'commission_id': 'c', 'commission_source_ref': [SOURCE], 'tool_request': {}, 'received_record_refs': [SOURCE],
        'input_refs': [SOURCE]}
    properties = task.child_arguments(slot)['properties']
    return {**values, **{name: samples[name] for name in properties if name not in values}}


@pytest.mark.parametrize('slot', [slot for slot, child in CHILDREN.items() if child])
def test_the_commission_of_each_child_uses_only_fields_the_child_declares_and_fills_its_required_ones(slot):
    task = importlib.import_module(PACKAGE + '.task')
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    admitted = EPISODE.assignment_form.admit(ASSIGNMENT, 'test')
    summary = {**EPISODE.read_from_parent(admitted, {}), 'objective': 'the question',
               'held_record_refs': [ARTIFACT, SOURCE, SUBJECT]}
    selectable = sorted(to_child.SELECTABLE[slot])[:2]
    arguments = {**arguments_for(slot, task), 'return_fields': selectable}
    message = EPISODE.msg_to_child(slot, arguments, summary)
    declared, _ = child_form(CHILDREN[slot], 'read_from_parent', 'ASSIGNMENT_FORM')
    assert set(message.assignment) <= set(declared)
    assert {name for name, (required, _) in declared.items() if required} <= set(message.assignment)
    for name, (_, value) in declared.items():
        if value is not None:
            assert message.assignment[name] == value
    assert message.selection == tuple(selectable) and message.objective == 'o'
    assert message.message == {'purpose': 'p'}


def test_the_commission_of_the_head_itself_is_admitted_by_its_own_form():
    task = importlib.import_module(PACKAGE + '.task')
    admitted = EPISODE.assignment_form.admit(ASSIGNMENT, 'test')
    summary = {**EPISODE.read_from_parent(admitted, {}), 'objective': 'q', 'held_record_refs': [SOURCE, SUBJECT]}
    message = EPISODE.msg_to_child('partner_presence_evidence', arguments_for('partner_presence_evidence', task),
                                   {**summary, 'proposed_annotation_ref': SOURCE})
    child = EPISODE.assignment_form.admit(message.assignment, 'test')
    child_input = EPISODE.read_from_parent(child, {})
    assert child_input['proposed_annotation_ref'] == SOURCE and child_input['scope'] == ASSIGNMENT['scope']
    assert child_input['finding_unit'] == 1.0 and set(child['received_record_refs']) == {SOURCE, SUBJECT}
    assert message.selection == ()


def test_a_selection_the_child_does_not_declare_is_refused_where_the_commission_is_admitted():
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    assert 'not_a_field' not in to_child.SELECTABLE['literature']
    form = EPISODE.return_form
    with pytest.raises(FormError):
        form.select(('not_a_field',))
    assert EPISODE.read_from_child('literature', {'credit': 1.0, 'finding': {}}, {}, None) == {
        'slot': 'literature', 'credit': 1.0, 'finding': {}}
