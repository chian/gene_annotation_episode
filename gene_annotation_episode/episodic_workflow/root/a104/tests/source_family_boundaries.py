"""Own-A104 original characterization interface diagnostic, without execution.

Constructs actual private bindings and exercises real schema/presentation
interfaces. Synthetic references are schema operands only; they establish no
scientific observation, sheet, assessment, source custody or earned credit.
Every exception is retained as an observation, not reclassified as a pass.
"""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104'
TOP = 'published_evidence_assessment'
STRATEGY = TOP + '/evidence_search_strategy_improvement'
SEARCH = STRATEGY + '/source_relevance_assessment'
PAGE = SEARCH + '/source_evidence_examination'
HOMES = tuple((prefix + home, role) for prefix in ('', 'scientific_process/') for home, role in (
    (TOP, 'literature'), (STRATEGY, 'literature_strategy'), (SEARCH, 'literature_search'),
    (PAGE, 'literature_page'), (PAGE + '/passage_evidence_extraction', 'literature_targeted'),
    (PAGE + '/source_coverage_improvement', 'literature_ordered'), (PAGE + '/table_evidence_extraction', 'literature_table')))

def module(name): return importlib.import_module(PREFIX + '.' + name)

def diagnose(retain):
    """Call retain after every boundary, including before later imports can fail."""
    def observe(name, operation):
        row = {'boundary': name}
        try: row.update(outcome='returned', value=operation())
        except Exception as error:
            row.update(outcome='raised', exception_type=type(error).__module__ + '.' + type(error).__qualname__,
                exception_message=str(error))
        retain(row)
    for name in ('literature_task_families', 'literature_task_selection', 'literature_experimental_prompt',
            'literature_reference_parent_prompt', 'literature_credit_policy', 'literature_task_credit'):
        observe('import:' + name, lambda name=name: {'actual_module': module(name).__name__,
            'file': str(Path(module(name).__file__).resolve())})
    for home, role in HOMES:
        for configured in (False, True):
            def constructor(home=home, role=role, configured=configured):
                cls = module(home.replace('/', '.') + '.episode').LiteratureEpisode
                options = ({'rate_population': True, 'compiled_assay_population': True,
                    'assay_grading_population': True,
                    'contract_information_profile': module('composition_information').CONTRACT_INFORMATION_PROFILE}
                    if configured else {})
                binding = cls(None, **options)
                # Actual constructor and descriptor, not a guessed source hash.
                return {'type': cls.__module__ + '.' + cls.__qualname__, 'home': home,
                    'registered_role': role, 'roles': list(binding.roles), 'options': options,
                    'descriptor': binding.as_record()}
            observe('constructor:' + home + ':' + ('factory_configuration' if configured else 'default'), constructor)
    def actual_tree():
        factory = module('scientific_process.published_evidence_assessment.episode').create_binding_tree
        result = factory(None, rate_population=True, compiled_assay_population=True,
            assay_grading_population=True,
            contract_information_profile=module('composition_information').CONTRACT_INFORMATION_PROFILE)
        return [{'type': type(binding).__module__ + '.' + type(binding).__qualname__,
            'binding_path': binding.binding_path, 'roles': list(binding.roles),
            'descriptor': binding.as_record()} for binding in result]
    observe('actual_scientific_factory_literature_tree', actual_tree)
    observe('advertised_task_schema', lambda: module('literature_task_credit').task_schema())
    for axis in ('A105', 'A104'):
        for kind in ('assessment', 'experiments', 'assembly'):
            def schema_admission(axis=axis, kind=kind):
                task = {'version': 'literature_local_task_v1', 'evidence_axis': axis, 'credit_unit': 1.75}
                if kind == 'assessment': task.update(kind='source_answer', answer_kind='assessment', source_refs=['source:fixture'])
                elif kind == 'experiments':
                    assay = next(iter(module('literature_assay_grading').ASSAY_TYPES))
                    task.update(kind=axis.lower() + '_experiments', experiments=[{'experiment_ref': 'experiment:fixture', 'assay_type': assay}])
                else: task.update(kind=axis.lower() + '_assembly', experiment_refs=['experiment:fixture'], metrics=['reliability'])
                module('domain').validate_schema(task, module('literature_task_credit').task_schema())
                return task
            observe('task_schema:' + axis + ':' + kind, schema_admission)
    def family_selection():
        selected, families = module('literature_task_selection'), module('literature_task_families')
        return {'selected_family_sources': [row.source for row in selected._FAMILIES],
            'original_assay_task_exported': hasattr(selected, 'A105_ASSAY_SELECTION_TASK'),
            'original_aggregation_row': list(families.family_row('literature_a105_aggregation_cells'))}
    observe('original_characterization_family_selection', family_selection)
    state = {'goal': {'objective': 'Inspect original characterization of the received reference molecule.'},
        'scope': {'subject_refs': [], 'regions': []}, 'working_state': {'subjects': [], 'scope': {'subject_refs': [], 'regions': []}},
        'tools': [], 'requested_form': None, 'controller': {}, 'current_report_update': {}, 'last_local_outcome': None,
        'literature_assignment': {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': []},
        'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}}
    def provider_presentation():
        cls = module('providers')._SessionConnection
        session = object.__new__(cls)
        session.scientific_prompt_states = {}
        rendered, instructions = session._presentation('source-family-schema-fixture', 'REASONING',
            'Retain original characterization and its qualifications.', deepcopy(state))
        return {'rendered': rendered, 'instructions': instructions,
            'saved_presentation_states': [[list(key), value] for key, value in session.scientific_prompt_states.items()]}
    observe('actual_provider_experimental_context', provider_presentation)
    observe('own_experimental_formatter', lambda: module('literature_experimental_prompt').render_literature_experimental_prompt(
        deepcopy(state), 'Retain original characterization and its qualifications.'))
