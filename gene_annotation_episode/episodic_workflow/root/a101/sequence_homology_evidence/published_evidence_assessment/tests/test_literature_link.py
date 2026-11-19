"""The seven A101 literature bindings linked through the generic runner over the shared Store.

Real pieces only: each literature binding built by its own constructor with its own A101
``ToolRegistry`` over the run's one ``Store``, a real ``RunJournal``, the standard
``ModelProvider`` constructed from a Codex app-server configuration, and A101's native
sequence-correspondence credit. No unit is run, so the model is never called: the test reads
what a linked literature episode presents and admits for its first decision and opens its
controller.
"""
import pytest

from episode_runtime import BindingRegistry, FormError, RunJournal, link
from method_loop import Episode
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import (
    A101SequenceCredit)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment import (
    episode as literature)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement import episode as strategy
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement.source_relevance_assessment import episode as relevance
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination import (
        episode as examination)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
    passage_evidence_extraction import episode as passage
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
    source_coverage_improvement import episode as coverage
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
    table_evidence_extraction import episode as table
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.published_evidence_assessment.\
    literature_source import LiteratureSource
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.yield_estimator import HEAD_TASK

YIELD_BINDINGS = {HEAD_TASK: {'kind': 'bounded_quality', 'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05},
                              'credit_definition': A101SequenceCredit().as_record()}}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CLASSES = (literature.PublishedEvidenceAssessmentEpisode, strategy.EvidenceSearchStrategyImprovementEpisode,
           relevance.SourceRelevanceAssessmentEpisode, examination.SourceEvidenceExaminationEpisode,
           passage.PassageEvidenceExtractionEpisode, coverage.SourceCoverageImprovementEpisode,
           table.TableEvidenceExtractionEpisode)


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """Each test binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def _registry(store):
    return BindingRegistry(tuple(cls(tool_registry=ToolRegistry(store), yield_bindings=YIELD_BINDINGS)
                                 for cls in CLASSES))


def _link(tmp_path, store, registry, path, tools):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    entry = {'scope': {'subject_refs': [target]}, 'tools': tools,
             'question': {'question': 'Which characterized homologs of the target are reported to act on which '
                                      'substrates?'}}
    return link(registry, path, entry, run_id='a101_literature_link', journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators={'store': store, 'model_provider': provider})


def test_literature_episode_runs_its_own_source_and_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(store)
        binding = registry.binding(literature.PublishedEvidenceAssessmentEpisode.binding_path)
        tools = ['public.literature.search', 'source.read']
        run = _link(tmp_path, store, registry, binding.binding_path, tools)
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is LiteratureSource
        assert set(source.tool_catalog()) == set(tools)
        schema = source.action_schema()
        options = schema['properties']['selection']['anyOf']
        kinds = [option['properties']['kind']['const'] for option in options]
        assert kinds.count('reason') == 1 and kinds.count('tool') == 2
        assert [option['properties']['slot']['const'] for option in options
                if option['properties']['kind']['const'] == 'episode_child'] == ['evidence_search_strategy_improvement']
        assert source.credit_view()['credit'] == 0
        assert binding.instruction in source.instructions()
        controller = run.episode.grain.controller(((binding.grain_name, run.episode.key),))
        assert isinstance(controller, BoundedQualityYieldController)
        assert isinstance(controller.state().stop, bool)
        with pytest.raises(ValueError, match='a101_decision_response_must_be_exactly_selection'):
            source.admit({'choice': {}}, schema)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_source_examination_offers_no_public_acquisition(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(store)
        binding = registry.binding(examination.SourceEvidenceExaminationEpisode.binding_path)
        assert not any(name.startswith('public.') for name in binding.selectable_tools)
        with pytest.raises(FormError, match='not_an_offered_option'):
            _link(tmp_path, store, registry, binding.binding_path, ['public.literature.search'])


def test_leaf_extraction_offers_no_child(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(store)
        binding = registry.binding(table.TableEvidenceExtractionEpisode.binding_path)
        run = _link(tmp_path, store, registry, binding.binding_path, ['source.xlsx.rows'])
        kinds = [option['properties']['kind']['const']
                 for option in run.episode.source.action_schema()['properties']['selection']['anyOf']]
        assert sorted(kinds) == ['reason', 'tool']
