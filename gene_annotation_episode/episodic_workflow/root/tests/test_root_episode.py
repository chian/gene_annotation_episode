"""The root annotation episode, run piece by piece on real values.

The root is one ``EpisodeBinding`` class with nine child slots. Each slot is checked against the head in its axis
folder: the head's own binding path, its own assignment form and ``read_from_parent`` (which take the commission
the root builds) and its own return form (which takes the root's selection). The heads' files are imported here,
in the test, and nowhere in the root's files.

The root's own functions are called with the values the system hands them: the entry commission is admitted by the
binding's own ``entry_request`` and ``parent_input``, the view is a ``method_loop.EpisodeView``, the context a
``DecisionContext``, and the outcome of a commission is assembled as the system assembles it, from a return the
head's own return form admits. In such a return every text field holds ``MODEL_TEXT``: the tests assert that none
of it reaches the root's summary, the root's model request or the root's return."""
import ast
import importlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from episode_runtime import BindingRegistry, ChildCall, ChildMessage, DecisionContext, EpisodeBinding, ModelRequest, Rejected
from method_loop import ChoiceField, DeclaredField, EpisodeRef, EpisodeView, Grain, SubsetField
from yield_control import AccumulationYieldController

from ..credit import AXIS_CREDIT_UNITS, K, OPERATIONAL_CREDIT_UNITS, annotation_credit
from ..episode import RootAnnotation
from ..messages.final_to_parent import RETURN_FORM
from ..messages.msg_to_child import SELECTION
from ..messages.read_from_child import JOB_FIELDS, RECORD_FIELDS
from ..messages.read_from_parent import ASSIGNMENT_FORM

FOLDER = Path(__file__).resolve().parents[1]
PACKAGE = __name__.rsplit('.', 2)[0]
BINDING = RootAnnotation()

# Slot (the axis role) -> its axis folder and its axis id.
AXES = {
    'sequence_homology_evidence': ('a101', 'A101'),
    'structural_homology_evidence': ('a102', 'A102'),
    'gene_context_evidence': ('a103', 'A103'),
    'evolutionary_history_evidence': ('a104', 'A104'),
    'experimental_activity_evidence': ('a105', 'A105'),
    'perturbation_evidence': ('a106', 'A106'),
    'partner_presence_evidence': ('a107', 'A107'),
    'sample_context_evidence': ('a108', 'A108'),
    'biochemical_feasibility_evidence': ('a110', 'A110'),
}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}

LIBRARY_ID, ENTRY_DIGEST = 'd' * 64, 'e' * 64
SELECTOR = {'name': 'source.read', 'resources': 'local'}
CANONICAL = {**SELECTOR, 'description': 'Read a held source', 'instructions': 'Name the source to read'}
# The selection version and the form of the tool rows each head's own selection takes.
SELECTION_FORMS = {
    'sequence_homology_evidence': ('sequence_homology_evidence_selection_v3', CANONICAL),
    'structural_homology_evidence': ('structural_homology_evidence_selection_v3', SELECTOR),
    'gene_context_evidence': ('gene_context_evidence_selection_v3', CANONICAL),
    'evolutionary_history_evidence': ('evolutionary_history_evidence_selection_v3', CANONICAL),
    'experimental_activity_evidence': ('experimental_activity_evidence_selection_v1', SELECTOR),
    'perturbation_evidence': ('perturbation_evidence_selection_v3', CANONICAL),
    'partner_presence_evidence': ('partner_presence_evidence_selection_v3', SELECTOR),
    'sample_context_evidence': ('sample_context_evidence_selection_v3', SELECTOR),
    'biochemical_feasibility_evidence': ('biochemical_feasibility_evidence_selection_v1', SELECTOR),
}


def option(slot, library_slot, option_id):
    return {'version': slot + '_option_ref_v1', 'library_id': LIBRARY_ID, 'slot': library_slot,
            'option_id': option_id, 'entry_sha256': ENTRY_DIGEST}


def selection(slot):
    """The selection the root's settings give an axis, in that head's own selection form."""
    version, tool = SELECTION_FORMS[slot]
    return {'version': version, 'evidence_axis': option(slot, 'evidence_axis', AXES[slot][1]),
            'thought_pattern': option(slot, 'thought_pattern', 'P1'), 'child_tool_info': [dict(tool)]}


SETTINGS = {'cost': 0.05, 'parameters': {'uncertainty_alpha': 0.05},
            'axis_selections': {slot: selection(slot) for slot in AXES}}
SUBJECT, HYPOTHESIS = 'input_' + 'a' * 24, 'hypothesis_' + 'b' * 24
EVIDENCE, SOURCE = 'observation_' + 'c' * 24, 'source_' + 'd' * 24
GIVEN = {SUBJECT, HYPOTHESIS, EVIDENCE, SOURCE}
ENTRY = {'assignment': {'scope': {'subject_refs': [SUBJECT]}, 'scope_refs': [SUBJECT],
                        'proposed_annotation_ref': [HYPOTHESIS], 'evidence_refs': [EVIDENCE],
                        'received_record_refs': [SOURCE]},
         'message': {}, 'selection': []}
MODEL_TEXT = 'A PARAGRAPH A MODEL WROTE IN A HEAD'
VOCABULARY = {'evidence_axis_task_v1', 'whole_axis_findings', 'A101', 'A102', 'A103', 'A104', 'A105', 'A106',
              'A107', 'A108', 'A110'}


def head(slot, file):
    """A file of the head in the slot's axis folder (imported in this test only)."""
    return importlib.import_module('.'.join((PACKAGE, AXES[slot][0], slot, file)))


def controller(*arguments):
    return RootAnnotation.yield_controller(0.0, SETTINGS, None)


def opened():
    """The view of the root's Episode before its first unit: the entry input admitted by the binding itself."""
    commission = BINDING.entry_request(ENTRY, parent_goal=None)
    parent_input = BINDING.parent_input(commission.assignment, commission.request)
    path = ((BINDING.grain_name, 'annotation'),)
    return EpisodeView(grain=Grain(BINDING.grain_name, BINDING.unit, BINDING.result, controller), key='annotation',
                       path=path, units_consumed=0, updates=(), controller_state=None,
                       episode_ref=EpisodeRef('root_pieces', path), request=commission.request,
                       parent_input=parent_input)


def context(view):
    return DecisionContext(settings=SETTINGS, services={}, clock=None, run_id='root_pieces',
                           episode_id=view.episode_ref.episode_id, binding_path=BINDING.binding_path, key=view.key)


def filled(form, given):
    """A record ``form`` admits: ``given`` for the fields it names, and for every other required field a value
    of its declared type. Every text is ``MODEL_TEXT``."""
    plain = {'text': MODEL_TEXT, 'number': 2.5, 'integer': 3, 'boolean': True, 'record': {'note': MODEL_TEXT},
             'list': [MODEL_TEXT], 'record_refs': []}
    record = {}
    for name, spec in form.fields.items():
        if name in given:
            record[name] = given[name]
        elif not spec.required:
            continue
        elif isinstance(spec, DeclaredField):
            record[name] = spec.value
        elif isinstance(spec, ChoiceField):
            record[name] = spec.options[0]
        elif isinstance(spec, SubsetField):
            record[name] = []
        elif spec.form is not None:
            record[name] = filled(spec.form, {})
        elif spec.items is not None:
            record[name] = [filled(spec.items, {})]
        else:
            record[name] = plain[spec.type]
    return record


def commission(view, slot):
    """The commission of ``slot`` the root builds at ``view``: the action of the model's answer and its message."""
    summary = RootAnnotation.internal_summary(view)
    call = RootAnnotation.action({'axis': slot}, summary, None, context(view))
    return summary, call, RootAnnotation.msg_to_child(call.slot, call.arguments, summary)


def returned(view, slot, credit, **refs):
    """The view after one commission of ``slot`` whose head returned ``credit`` and the record references
    ``refs`` (by return field), with the outcome the system records for a child unit."""
    summary, call, message = commission(view, slot)
    form = head(slot, 'messages.final_to_parent').RETURN_FORM.select(message.selection)
    result = form.admit(filled(form, {'credit': credit, **refs}), 'result')
    report = RootAnnotation.read_from_child(slot, result, summary, None)
    return view.with_unit({'slot': slot, 'arguments': dict(call.arguments), 'kind': 'child',
                           'message': {'objective': message.objective, 'message': dict(message.message),
                                       'assignment': dict(message.assignment),
                                       'selection': list(message.selection)},
                           'completion': {'ended_by': 'yield_stop', 'units_consumed': 3}, 'result': result,
                           'report': report})


def texts(value):
    """Every text in a JSON value, keys excluded."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in texts(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in texts(item)]
    return []


def field_types(form):
    """The type of every field of a form, nested forms included."""
    found = []
    for spec in form.fields.values():
        found.append(spec.type)
        for nested in (spec.form, spec.items):
            if nested is not None:
                found.extend(field_types(nested))
    return found


# -- the class, its folder and its nine children -------------------------------------------------------------

def test_the_root_is_one_class_of_the_episode_type_and_inherits_nothing_else():
    assert RootAnnotation.__bases__ == (EpisodeBinding,)
    assert RootAnnotation.binding_path == 'root' and PACKAGE.endswith('.root')
    assert dict(RootAnnotation.tools) == {} and RootAnnotation.services == ()
    assert BindingRegistry([BINDING]) is not None


def test_the_root_declares_exactly_nine_child_slots_named_by_the_axis_roles():
    assert dict(RootAnnotation.child_slots) == {slot: slot for slot in AXES}
    declaration = BINDING.declaration(controller())
    assert [(slot.name, slot.accepted_interfaces) for slot in declaration.child_slots] == [
        (slot, (slot,)) for slot in AXES]


def test_the_root_folder_holds_the_ten_files_and_the_nine_axis_folders():
    own = {str(path.relative_to(FOLDER)) for path in (*FOLDER.glob('*.py'), *FOLDER.glob('messages/*.py'))}
    assert own == FILES
    folders = {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'}
    assert folders == {'messages', 'tests'} | {folder for folder, _ in AXES.values()}


def test_the_root_imports_nothing_from_an_axis_folder():
    axis_folders = {folder for folder, _ in AXES.values()}
    for name in FILES:
        for node in ast.walk(ast.parse((FOLDER / name).read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ''] + [(node.module or '') + '.' + alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                assert not axis_folders & set(module.split('.')), name + ' imports ' + module


@pytest.mark.parametrize('slot', AXES)
def test_each_slot_is_bound_to_the_head_in_its_axis_folder(slot):
    folder = AXES[slot][0]
    assert (FOLDER / folder / slot / 'episode.py').is_file()
    assert head(slot, 'goal').BINDING_PATH == RootAnnotation.child_slots[slot]


@pytest.mark.parametrize('slot', AXES)
def test_the_head_of_each_slot_admits_the_roots_commission_and_reads_it(slot):
    """The commission the root builds is admitted by the head's own assignment form and read by the head's own
    ``read_from_parent``; it passes only records the root holds and tells the head the root's credit unit."""
    own = head(slot, 'messages.read_from_parent')
    _, call, message = commission(opened(), slot)
    assert isinstance(call, ChildCall) and call.slot == slot
    assert isinstance(message, ChildMessage)
    admitted = own.ASSIGNMENT_FORM.admit(message.assignment, 'commission:' + slot)
    assert set(own.ASSIGNMENT_FORM.record_refs(admitted)) == GIVEN
    parent_input = own.read_from_parent(admitted, dict(message.message))
    assert parent_input['selection']['evidence_axis']['option_id'] == AXES[slot][1]
    assert admitted['context']['evidence_task'] == {
        'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': AXES[slot][1],
        'credit_unit': AXIS_CREDIT_UNITS[slot]}


@pytest.mark.parametrize('slot', AXES)
def test_the_head_of_each_slot_declares_the_fields_the_root_selects_and_reads(slot):
    """The root's selection is made of selectable fields of the head's own return form, and every field the root
    reads is a ``record_refs`` field of the selected form."""
    form = head(slot, 'messages.final_to_parent').RETURN_FORM
    selected = form.select(SELECTION[slot])
    assert set(JOB_FIELDS[slot]) <= set(RECORD_FIELDS[slot])
    assert set(SELECTION[slot]) <= set(RECORD_FIELDS[slot])
    for name in RECORD_FIELDS[slot]:
        assert selected.fields[name].type == 'record_refs'
    assert selected.fields['credit'].type == 'number' and 'finding' in selected.fields


@pytest.mark.parametrize('slot', AXES)
def test_a_commission_carries_no_text_but_fixed_values_and_record_references(slot):
    """Outside the selection (entries of the frozen libraries, which the settings give), every text of a
    commission is a record the root holds or a value of the fixed vocabulary, and the objective is the same
    sentence whatever the state of the annotation."""
    first = commission(opened(), slot)[2]
    later_view = returned(returned(opened(), 'experimental_activity_evidence', 4.0), 'sequence_homology_evidence', 0.5)
    later = commission(later_view, slot)[2]
    assert first.objective == later.objective and slot.split('_')[0] in first.objective.replace('-', '_')
    for message in (first, later):
        assignment = {name: value for name, value in message.assignment.items() if name != 'selection'}
        assert message.assignment['selection'] == SETTINGS['axis_selections'][slot]
        assert set(texts(assignment)) | set(texts(dict(message.message))) <= GIVEN | VOCABULARY
        assert assignment['constraints'] == {}


# -- the root's own pieces ----------------------------------------------------------------------------------------

def test_read_from_parent_is_the_only_reader_of_the_assignment_and_takes_exactly_one_proposed_annotation():
    view = opened()
    assert view.parent_input == {'scope': {'subject_refs': [SUBJECT]}, 'scope_refs': [SUBJECT],
                                 'proposed_annotation_ref': HYPOTHESIS, 'evidence_refs': [EVIDENCE],
                                 'received_record_refs': [SOURCE]}
    two = ASSIGNMENT_FORM.admit({**ENTRY['assignment'], 'proposed_annotation_ref': [HYPOTHESIS, SOURCE]}, 'entry')
    with pytest.raises(ValueError):
        RootAnnotation.read_from_parent(two, {})


def test_the_roots_forms_have_no_text_field():
    assert set(field_types(ASSIGNMENT_FORM)) == {'record', 'record_refs'}
    assert set(field_types(RETURN_FORM)) == {'number', 'integer', 'record', 'record_refs'}
    assert RETURN_FORM.fields['credit'].required and RETURN_FORM.fields['finding'].required


def test_decide_builds_its_request_from_numbers_and_flags():
    view = opened()
    summary = RootAnnotation.internal_summary(view)
    request = RootAnnotation.decide(summary, None, context(view))
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    Draft202012Validator.check_schema(request.output_schema)
    assert request.output_schema['properties']['axis']['enum'] == list(AXES)
    assert request.context['annotation_credit'] == 0.0 and request.context['k'] == K
    assert request.context['commissions'] == [] and request.context['feedback'] is None
    assert [axis['axis'] for axis in request.context['axes']] == list(AXES)
    for axis in request.context['axes']:
        assert axis == {'axis': axis['axis'], 'weight': 1.0, 'credit': 0.0, 'returned_credits': [],
                        'commissions': 0, 'finding': {}, 'outstanding_jobs': 0,
                        'annotation_gain_of_one_credit': K}
    assert set(texts(request.context)) == set(AXES)
    json.dumps(request.context, allow_nan=False)


def test_action_returns_the_commission_of_the_named_axis_and_rejects_an_answer_that_names_none():
    view = opened()
    summary = RootAnnotation.internal_summary(view)
    for slot in AXES:
        call = RootAnnotation.action({'axis': slot}, summary, None, context(view))
        assert isinstance(call, ChildCall)
        assert (call.slot, dict(call.arguments)) == (slot, {'selection': SETTINGS['axis_selections'][slot]})
    with pytest.raises(Rejected) as rejection:
        RootAnnotation.action({'axis': 'literature'}, summary, None, context(view))
    assert rejection.value.feedback == {'rejected': 'axis_is_not_one_of_the_nine'}
    again = RootAnnotation.decide(summary, rejection.value.feedback, context(view))
    assert again.context['feedback'] == {'rejected': 'axis_is_not_one_of_the_nine'}


def test_read_from_child_takes_the_credit_the_numbers_and_flags_and_the_records_and_no_text():
    committed, handoff = 'assessment_' + '1' * 24, 'handoff_' + '2' * 24
    view = opened()
    summary, _, message = commission(view, 'sequence_homology_evidence')
    form = head('sequence_homology_evidence', 'messages.final_to_parent').RETURN_FORM.select(message.selection)
    result = form.admit(filled(form, {'credit': 3e6, 'committed_record_refs': [committed],
                                      'execution_handoff_refs': [handoff]}), 'result')
    assert MODEL_TEXT in texts(result['finding'])
    report = RootAnnotation.read_from_child('sequence_homology_evidence', result, summary, None)
    assert report['credit'] == 3e6
    assert report['record_refs'] == [committed, handoff] and report['outstanding_job_refs'] == [handoff]
    assert report['finding'] and all(type(value) in (bool, int, float) for value in report['finding'].values())
    assert report['finding'] == {name: value for name, value in result['finding'].items()
                                 if type(value) in (bool, int, float)}
    assert set(texts(report)) == {committed, handoff}


def test_the_summary_follows_each_axis_and_the_credit_is_the_formula_over_the_returned_credits():
    first, second, handoff = 'assessment_' + '1' * 24, 'assessment_' + '3' * 24, 'handoff_' + '2' * 24
    view = returned(opened(), 'experimental_activity_evidence', 3.0, committed_record_refs=[first])
    view = returned(view, 'sequence_homology_evidence', 0.75, committed_record_refs=[],
                    execution_handoff_refs=[handoff])
    # The return to an axis passes back what its own head returned, and nothing another axis returned.
    again = commission(view, 'experimental_activity_evidence')[2]
    passed = head('experimental_activity_evidence', 'messages.read_from_parent').ASSIGNMENT_FORM.record_refs(
        head('experimental_activity_evidence', 'messages.read_from_parent').ASSIGNMENT_FORM.admit(
            again.assignment, 'commission'))
    assert set(passed) == GIVEN | {first}
    back = commission(view, 'sequence_homology_evidence')[2]
    assert handoff in back.assignment['evidence_refs'] and first not in back.assignment['evidence_refs']
    view = returned(view, 'experimental_activity_evidence', 5.0e6, committed_record_refs=[first, second])

    summary = RootAnnotation.internal_summary(view)
    assert summary['commissions'] == ['experimental_activity_evidence', 'sequence_homology_evidence',
                                      'experimental_activity_evidence']
    activity, homology = summary['axes']['experimental_activity_evidence'], summary['axes']['sequence_homology_evidence']
    assert (activity['credit'], activity['returned_credits']) == (5.0e6, [3.0, 5.0e6])
    assert activity['record_refs'] == [first, second] and activity['outstanding_job_refs'] == []
    assert (homology['credit'], homology['record_refs'], homology['outstanding_job_refs']) == (
        0.75, [handoff], [handoff])
    untouched = summary['axes']['gene_context_evidence']
    assert untouched == {'credit': 0.0, 'returned_credits': [], 'finding': {}, 'record_refs': [],
                         'outstanding_job_refs': []}
    assert MODEL_TEXT not in json.dumps(summary)
    assert set(texts(summary)) <= GIVEN | {first, second, handoff} | set(AXES)

    # The credit is the formula over the axis credits as returned: five million is used as five million.
    credit = RootAnnotation.credit(summary, None)
    assert credit == annotation_credit({slot: summary['axes'][slot]['credit'] for slot in AXES})
    assert credit == pytest.approx((1 + K * 5.0e6) * (1 + K * 0.75) - 1, rel=1e-12)

    request = RootAnnotation.decide(summary, None, context(view))
    shown = {axis['axis']: axis for axis in request.context['axes']}
    assert shown['experimental_activity_evidence']['returned_credits'] == [3.0, 5.0e6]
    assert shown['experimental_activity_evidence']['commissions'] == 2
    assert shown['sequence_homology_evidence']['outstanding_jobs'] == 1
    assert request.context['annotation_credit'] == credit
    # One more credit on an empty axis adds more than one more on the axis that already has five million.
    assert shown['gene_context_evidence']['annotation_gain_of_one_credit'] == pytest.approx(
        K * (1 + K * 5.0e6) * (1 + K * 0.75), rel=1e-9)
    assert (shown['gene_context_evidence']['annotation_gain_of_one_credit']
            > shown['experimental_activity_evidence']['annotation_gain_of_one_credit'])
    assert MODEL_TEXT not in json.dumps(request.context)
    assert set(texts(request.context)) == set(AXES)


def test_final_to_parent_returns_the_credit_and_a_finding_of_numbers_and_the_selected_records():
    first, handoff = 'assessment_' + '1' * 24, 'handoff_' + '2' * 24
    view = returned(opened(), 'experimental_activity_evidence', 3.0, committed_record_refs=[first])
    view = returned(view, 'sequence_homology_evidence', 0.75, committed_record_refs=[],
                    execution_handoff_refs=[handoff])
    summary = RootAnnotation.internal_summary(view)
    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': RootAnnotation.credit(summary, None)}

    plain = RETURN_FORM.select(()).admit(RootAnnotation.final_to_parent(summary, completion, ()), 'result')
    assert set(plain) == {'credit', 'finding'} and plain['credit'] == (1 + K * 3.0) * (1 + K * 0.75) - 1
    assert plain['finding']['commissions'] == 2 and set(plain['finding']['axes']) == set(AXES)
    assert plain['finding']['axes']['experimental_activity_evidence'] == {
        'credit': 3.0, 'commissions': 1, 'outstanding_jobs': 0}
    assert plain['finding']['axes']['sequence_homology_evidence'] == {
        'credit': 0.75, 'commissions': 1, 'outstanding_jobs': 1}
    assert plain['finding']['axes']['perturbation_evidence'] == {'credit': 0.0, 'commissions': 0,
                                                                 'outstanding_jobs': 0}
    assert texts(plain) == []

    selection = ('record_refs', 'outstanding_job_refs')
    full = RETURN_FORM.select(selection).admit(RootAnnotation.final_to_parent(summary, completion, selection), 'result')
    assert full['record_refs'] == [handoff, first] and full['outstanding_job_refs'] == [handoff]
    assert set(RETURN_FORM.select(selection).record_refs(full)) == {first, handoff}
    assert set(texts(full)) == {first, handoff}


def test_the_controller_is_the_accumulation_estimator_with_the_roots_own_threshold():
    """Open-ended: no target and no maximum. The threshold is the root's own setting; the parent input (what
    ``read_from_parent`` produced) gives it nothing. A forecast that is not available does not stop the root."""
    view = opened()
    built = RootAnnotation.yield_controller(0.0, SETTINGS, view.parent_input)
    assert type(built) is AccumulationYieldController
    assert (built.epoch, built.initial_credit, built.cost) == ('root', 0.0, SETTINGS['cost'])
    assert built.settings.uncertainty_alpha == SETTINGS['parameters']['uncertainty_alpha']
    other = RootAnnotation.yield_controller(0.0, {**SETTINGS, 'cost': 2.0}, {'anything': 'else'})
    assert other.cost == 2.0
    step = built.observe('experimental_activity_evidence_0', {'credit': 3.0})
    assert (step.credit, step.marginal_credit, step.stop) == (3.0, 3.0, False)
    declaration = BINDING.declaration(built)
    assert 'without a declared limit' in declaration.progress and repr(SETTINGS['cost']) in declaration.stopping
