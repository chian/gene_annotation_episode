"""Actual own-A104 constructor/configuration/read-back diagnostic.

These explicit options are constructor operands, not evidence, enabled model
work, source acquisition or claimed scientific findings. Getter equality uses
the real constructed instances. Generic saved composition is observed through
its original actual API and may legitimately retain its pending-reopen error.
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
HOMES = tuple(prefix + home for prefix in ('', 'scientific_process/') for home in (
    TOP, STRATEGY, SEARCH, PAGE, PAGE + '/passage_evidence_extraction',
    PAGE + '/source_coverage_improvement', PAGE + '/table_evidence_extraction'))
POPULATIONS = ('rate_population', 'assay_grading_population', 'compiled_assay_population',
    'channel_population', 'ion_discrimination_population', 'completion_time_population',
    'active_site_population', 'parent_depletion_population', 'stoichiometric_balance_population',
    'product_partition_population', 'ratio_source_population', 'controlled_response_population', 'gel_population')
CASES = (('default', {}), ('factory', {'rate_population': True, 'compiled_assay_population': True,
    'assay_grading_population': True, 'contract_information_profile': 'operation_contract_information_v1'}),
    ('private_yield_empty', {'private_yield_binding': True, 'yield_bindings': {}}),
    *((name, {'rate_population': True, name: True}) for name in POPULATIONS),
    ('ratio_origin', {'rate_population': True, 'ratio_source_population': True, 'ratio_source_evidence_origin': 'synthetic_fixture'}),
    ('controlled_origin', {'rate_population': True, 'controlled_response_population': True, 'controlled_response_evidence_origin': 'synthetic_fixture'}),
    ('gel_origin', {'rate_population': True, 'gel_population': True, 'gel_evidence_origin': 'synthetic_fixture'}),
    ('reference_sources', {'reference_parent_sources': ['source_' + 'a' * 32]}),
    ('contract_profile', {'contract_information_profile': 'operation_contract_information_v1'}))

def module(name): return importlib.import_module(PREFIX + '.' + name)
def settings(binding):
    """Read actual semantic fields; do not compare transient service/repo caches."""
    return {name: deepcopy(getattr(binding, name)) for name in (
        'outcome_page_size', *POPULATIONS, 'private_yield_binding', '_yield_bindings',
        'ratio_source_evidence_origin', 'controlled_response_evidence_origin',
        'gel_evidence_origin', '_controlled_response_descriptor', '_gel_descriptor',
        'reference_parent_sources', '_contract_information_profile')}

def diagnose(directory, retain):
    def observe(identity, operation):
        row = {'boundary': identity}
        try: row.update(outcome='returned', value=operation())
        except Exception as error:
            row.update(outcome='raised', exception_type=type(error).__module__ + '.' + type(error).__qualname__,
                exception_message=str(error))
        retain(row)
    for home in HOMES:
        for label, options in CASES:
            def compare(home=home, options=options):
                cls = module(home.replace('/', '.') + '.episode').LiteratureEpisode
                before = cls(None, **deepcopy(options)); descriptor = before.as_record()
                restored = cls(None, **deepcopy(descriptor['configuration']))
                original_settings, restored_settings = settings(before), settings(restored)
                return {'actual_class': cls.__module__ + '.' + cls.__qualname__, 'explicit_options': options,
                    'descriptor': descriptor, 'restored_descriptor': restored.as_record(),
                    'settings': original_settings, 'restored_settings': restored_settings,
                    'same_configuration': original_settings == restored_settings,
                    'lost_fields': [name for name in original_settings if original_settings[name] != restored_settings[name]]}
            observe('constructor_descriptor:' + home + ':' + label, compare)
    # Correct the earlier schema-only fixture's invalid colon-form IDs. These
    # conforming strings are still synthetic syntax operands, never Store facts.
    for axis in ('A105', 'A104', 'A106', 'A108'):
        for kind in ('assessment', 'experiments', 'assembly'):
            def admit(axis=axis, kind=kind):
                task = {'version': 'literature_local_task_v1', 'evidence_axis': axis, 'credit_unit': 1.75}
                if kind == 'assessment':
                    task.update(kind='source_answer', answer_kind='assessment', source_refs=['source_' + 'b' * 32])
                elif kind == 'experiments':
                    task.update(kind=axis.lower() + '_experiments', experiments=[{
                        'experiment_ref': 'reference_' + 'c' * 32,
                        'assay_type': next(iter(module('literature_assay_grading').ASSAY_TYPES))}])
                else:
                    task.update(kind=axis.lower() + '_assembly', experiment_refs=['reference_' + 'c' * 32], metrics=['reliability'])
                module('domain').validate_schema(task, module('literature_task_credit').task_schema())
                return {'task': task, 'schema_only': True, 'scientific_evidence': False}
            observe('corrected_task_schema:' + axis + ':' + kind, admit)
    # Current literal composer admission is a separate actual boundary from
    # passing config to the known original constructor. Preserve its own error.
    with module('state').Store(Path(directory) / 'store') as store:
        journal = module('episode_journal').Journal(store, 'a104-descriptor-inputs')
        for home in HOMES:
            def reopen(home=home):
                cls = module(home.replace('/', '.') + '.episode').LiteratureEpisode
                descriptor = cls(None).as_record()
                services = SimpleNamespace(workflow=SimpleNamespace(store=store, run_id=journal.run_id))
                result = module('episode_composition').compose_episode_bindings(services,
                    store=store, journal=journal, execution_backend=None, descriptors=[descriptor],
                    job_episodes=None, resource_estimator=None, role_credit_bindings={}, directory=directory)
                return {'saved': descriptor, 'actual': [binding.as_record() for binding in result.bindings]}
            observe('actual_saved_composition:' + home, reopen)

