"""Real checks of the A104 published evidence assessment binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set (beside the two shared hook-era modules that the
axis head still imports and that are listed in the carry-over record), no module imports another episode folder, the
assignment form admits a literature assignment with its commissioned task, the commission is admitted by the form of
its real child, and the return, the credit and the offered tools are real. Nothing here is faked and nothing contacts
a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError

MODULE = ('gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.'
          'published_evidence_assessment')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'evidence_search_strategy_improvement'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
LEADS = 'literature_source_lead_dispositions'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] in ({'tests'} | CHILDREN) or path.is_dir():
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
    assert classes[0].binding_path == goal.BINDING_PATH == 'evolutionary_history_evidence/published_evidence_assessment'
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {name: goal.BINDING_PATH + '/' + name for name in CHILDREN}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child).is_dir()


def test_no_module_imports_another_episode_folder():
    own = MODULE
    for relative in sorted(FILES):
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
                    assert not any(name.startswith(own + '.' + child) for child in CHILDREN), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1 and relative.startswith('messages/') is False:
                raise AssertionError((relative, 'relative import above the episode folder'))


def literature(kind='verified_source_leads'):
    return {'version': 'literature_assignment_v1', 'question_context_refs': ['ctx_1'], 'source_refs': ['src_1'],
            'literature_task': {'kind': kind, 'evidence_axis': 'A104', 'credit_unit': 1.0,
                                **({'answer_kind': 'assessment', 'source_refs': ['src_1']}
                                   if kind == 'source_answer' else {})},
            'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
            'received_record_refs': ['src_1', 'art_1', 'ctx_1', 'hyp_1']}


def test_the_assignment_admits_a_literature_assignment_and_read_from_parent_returns_it():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(literature(), 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['literature'] == {name: literature()[name] for name in from_parent.LITERATURE_FIELDS}
    assert parent_input['task_key'] == 'A104:verified_source_leads'
    assert parent_input['proposed_annotation_ref'] == 'hyp_1' and parent_input['message'] == {'purpose': 'x'}
    with pytest.raises(FormError, match='unknown_field'):
        from_parent.ASSIGNMENT_FORM.admit({**literature(), 'extra': 1}, 'assignment')
    bad = {**admitted, 'literature_task': {'kind': 'verified_source_leads', 'evidence_axis': 'A104',
                                            'credit_unit': 0}}
    with pytest.raises(ValueError, match='literature_finite_task_credit_unit_required'):
        from_parent.read_from_parent(bad, {})


def summary_for(kind='verified_source_leads'):
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(literature(kind), 'assignment')
    return {'assignment': from_parent.read_from_parent(admitted, {}), 'input_list': ['src_1']}


def test_the_commission_is_admitted_by_the_form_of_its_real_child():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    slot = 'evidence_search_strategy_improvement'
    child = importlib.import_module(MODULE + '.' + slot + '.messages.read_from_parent')
    arguments = {'objective': 'o', 'question_context_refs': ['ctx_1'], 'prior_search_refs': ['src_1'],
                 'custody_refs': ['txt_1'], 'context_refs': ['sub_9']}
    message = to_child.msg_to_child(slot, arguments, summary_for())
    assert isinstance(message, ChildMessage) and message.objective == 'o'
    assert message.selection == (LEADS,)
    admitted = child.ASSIGNMENT_FORM.admit(message.assignment, slot)
    parent_input = child.read_from_parent(admitted, message.message)
    assert parent_input['task']['kind'] == 'verified_source_leads'
    assert parent_input['strategy']['prior_search_refs'] == ['src_1']
    assert parent_input['received_record_refs'] == ['src_1', 'art_1', 'ctx_1', 'hyp_1', 'txt_1', 'sub_9']
    final = importlib.import_module(MODULE + '.' + slot + '.messages.final_to_parent')
    assert LEADS in final.RETURN_FORM.fields and final.RETURN_FORM.fields[LEADS].required is False
    other = to_child.msg_to_child(slot, arguments, summary_for('source_answer'))
    assert other.selection == ()


def test_the_return_is_credit_and_controlled_features_only():
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    form = final.RETURN_FORM
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'assay_sheets': [], 'assessments': [], 'sheet_record_refs': [], 'proposed_annotation_ref': 'hyp_1',
               'screening_answers': [], 'no_applicable_evidence': [], 'source_lead_dispositions': []}
    result = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': {'assay_sheets': [], 'assessments': [], 'assay_count': 0,
                                                 'assessment_count': 0, 'assay_count_with_evidence_ratio': 0,
                                                 'sheet_record_refs': []}}
    form.admit(result, 'return')
    leads = [{'source_ref': 'src_1', 'disposition': 'relevant'}, {'source_ref': 'src_2', 'disposition': 'not_relevant'}]
    selection = (final.SCREENING, final.LEADS)
    selected = final.final_to_parent({**summary, 'source_lead_dispositions': leads}, {'credit': 1.0}, selection)
    assert selected[final.LEADS] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    assert selected[final.SCREENING] == {'answered': False, 'examined_span_count': 0, 'examined_byte_total': 0}
    assert form.select(selection).record_refs(form.select(selection).admit(selected, 'return')) == ('src_1',)
    for nested in (final.SHEET_FORM, final.ASSESSMENT_FORM):
        assert all(spec.type != 'text' or hasattr(spec, 'options') for spec in nested.fields.values())


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(MODULE + '.credit')
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A104:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_controller_is_built_from_the_commissioned_task():
    from yield_control import AccumulationYieldController, CompletionYieldController
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}
    for kind, controller in (('verified_source_leads', AccumulationYieldController),
                             ('source_answer', CompletionYieldController)):
        admitted = from_parent.ASSIGNMENT_FORM.admit(literature(kind), 'assignment')
        parent_input = from_parent.read_from_parent(admitted, {})
        assert isinstance(yield_file.yield_controller(0, settings, parent_input), controller)


def test_the_model_is_offered_the_access_and_acquisition_tools_the_reasoning_the_report_and_the_strategy_child():
    task = importlib.import_module(MODULE + '.task')
    episode = importlib.import_module(MODULE + '.episode')
    names = task.offered({}, ['src_1'])
    assert names[-2:] == ['reason', 'evidence_search_strategy_improvement'] and 'report' not in names and len(names) == 34
    assert set(names) - set(task.CHILD_SLOTS) <= set(episode.PublishedEvidenceAssessment.tools)
    assert {'public_literature_search', 'public_literature_read', 'public_ncbi_search', 'public_pmc_asset',
            'public_sabiork_search', 'public_brenda_graph_search'} <= set(names)
    assert task.INPUT_SCHEMAS['public.ncbi.search']['properties']['database'] == {'enum': ['pubmed']}
    commit_schema = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                     'properties': {'terms': {'type': 'array'}}}
    schema = task.selection_schema(names, commit_schema, True, ['src_1'])
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    kinds = [option['properties']['kind']['const'] for option in schema['properties']['selection']['anyOf']]
    assert kinds.count('child') == 1 and kinds.count('tool') == len(names) - 1


def test_the_input_list_is_the_only_offer_of_prior_searches_and_an_empty_list_offers_no_child():
    task = importlib.import_module(MODULE + '.task')
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child = task.child_input('evidence_search_strategy_improvement', ['src_1', 'src_2'])
    assert child['properties']['prior_search_refs']['items'] == {'enum': ['src_1', 'src_2']}
    assert child['properties']['prior_search_refs']['minItems'] == 1
    emptied = task.offered({}, [])
    assert 'evidence_search_strategy_improvement' not in emptied and emptied[-1] == 'reason'
    arguments = {'objective': 'o', 'question_context_refs': ['ctx_1'], 'prior_search_refs': ['src_0'],
                 'custody_refs': [], 'context_refs': []}
    with pytest.raises(KeyError):
        to_child.msg_to_child('evidence_search_strategy_improvement', arguments, summary_for())


def test_a_source_handed_to_the_strategy_child_is_consumed_and_a_produced_source_joins_the_list():
    summary_module = importlib.import_module(MODULE + '.messages.internal_summary')

    class Records:
        def get(self, reference):
            return {'record_type': 'source' if reference.startswith('src') else 'other'}

    class View:
        parent_input = {'literature': {'source_refs': ['src_1']}}
        records = Records()
        outcomes = [{'kind': 'tool', 'produced': ['src_2', 'rec_1']},
                    {'kind': 'child', 'arguments': {'prior_search_refs': ['src_1']}}]
    assert summary_module.held_sources(View) == ['src_1', 'src_2']
    assert summary_module.consumed_sources(View) == ['src_1']
