"""Real checks of the source coverage improvement binding (A105): importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, and the
commission and return forms agree with the families the episode populates."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
          'source_evidence_examination.source_coverage_improvement')
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


def episode_class():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    return classes[0]


def test_the_class_passes_the_definition_checks():
    cls = episode_class()
    assert cls.__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert cls.binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(cls.child_slots) == {}
    assert not hasattr(cls, 'msg_to_child') and not hasattr(cls, 'read_from_child')


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


def test_no_module_imports_another_episode_folder():
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        depth = len(Path(relative).parts) - 1    # the package levels between the file and the episode folder
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif isinstance(node, ast.ImportFrom) and node.level > depth + 1:
                raise AssertionError((relative, 'relative import above the episode folder'))
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == MODULE or name.startswith(MODULE + '.'), (relative, name)


def test_the_return_is_credit_and_the_controlled_finding_with_two_selectable_answers():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    cls = episode_class()
    assignment = cls.assignment_form.as_record()
    assert set(from_parent.REQUESTED_FIELDS) <= set(assignment)
    assert set(cls.return_form.fields) == {'credit', 'finding', final.LEADS, final.SCREENING}
    summary = {'assay_sheets': [], 'aggregation_sheets': [], 'proposed_annotation_ref': 'hyp_1',
               'no_applicable_spans': [], 'screening_covered': False, 'lead_source_refs': ['source_1']}
    selection = (final.LEADS, final.SCREENING)
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, selection)
    assert cls.return_form.select(selection).admit(result, 'return') == result
    assert result[final.LEADS] == {'relevant_lead_count': 1, 'lead_source_refs': ['source_1']}


def test_the_population_route_is_read_from_the_settings():
    task = importlib.import_module(MODULE + '.task')
    flags = {name: False for name in ('assay_grading_population', 'ratio_source_population',
                                      'controlled_response_population', 'gel_population', 'completion_time_population',
                                      'product_partition_population', 'active_site_population',
                                      'parent_depletion_population', 'stoichiometric_balance_population',
                                      'compiled_assay_population', 'channel_population', 'ion_discrimination_population')}
    assert task.offered({'rate_population': False})[-1] == 'reason'
    on = task.offered({'rate_population': True, **flags})
    assert 'literature.rate.populate' in on and 'literature.assay_grading.populate' not in on
    assert set(task.TOOL_NAMES.values()) == set(episode_class().tools) - {'reason'}


def test_the_continuation_follows_the_commissioned_task():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    estimator = importlib.import_module(MODULE + '.yield_estimator')
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.5}}
    page = {'version': 'page_assignment_v1', 'source_ref': 'source_' + 'a' * 24, 'representation': 'text',
            'artifact_ref': 'artifact_' + 'b' * 24, 'question_context_refs': [], 'prior_delivery_refs': []}
    commission = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': {'source_ref': page['source_ref'], 'representation': 'text', 'offset': 0, 'limit': 64},
                  'literature_task': {'version': 'literature_local_task_v1', 'evidence_axis': 'A105',
                                      'credit_unit': 2.0, 'kind': 'verified_source_leads'},
                  'proposed_annotation_ref': 'hypothesis_' + 'c' * 24,
                  'scope': {'subject_refs': ['input_' + 'd' * 24]}, 'record_refs': [page['source_ref']]}
    leads = from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(commission, 'assignment'), {})
    assert type(estimator.yield_controller(0, settings, leads)).__name__ == 'AccumulationYieldController'
    commission['literature_task'] = {**commission['literature_task'], 'kind': 'source_answer',
                                     'answer_kind': 'assessment', 'source_refs': [page['source_ref']]}
    answer = from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(commission, 'assignment'), {})
    assert answer['completion_target'] == 2.0
    controller = estimator.yield_controller(0, settings, answer)
    assert type(controller).__name__ == 'CompletionYieldController' and controller.target == 2.0

