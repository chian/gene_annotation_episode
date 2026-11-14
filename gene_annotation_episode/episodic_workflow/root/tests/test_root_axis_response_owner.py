"""Canonical root response owner and original contract, without scientific work.

Negative contexts below are typed predicate fixtures, not authenticated child
invocations. The positive/reopen cases use genuine saved root contexts.
"""
from dataclasses import replace
import inspect
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.axis_response_contract import RootRequests
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.scoring import SignedEvidenceRootSupport
from gene_annotation_episode.episodic_workflow.root.tests import fresh_decision_support
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import actual_root, action_rows


SOURCES = ('scientific_process_results', 'committed_record_refs')
FORM = {'type': 'object', 'properties': {
    'scientific_process_results': {'$ref': 'episode-fact:scientific_process_results'},
    'committed_record_refs': {'$ref': 'episode-fact:committed_record_refs'}},
    'required': list(SOURCES), 'additionalProperties': False}


def context_of(root):
    context = root.workflow.binding_context(root.source)
    assert type(context) is BindingContext
    assert context.episode_id == root.source.episode_id
    assert context.path == root.source.path
    return context


def assert_no_acquisition(root):
    assert root.tools.execution_calls == []
    assert root.provider.requests == []
    assert all(not rows for rows in action_rows(root).values())


def test_actual_root_task_credit_has_canonical_response_method_owner(tmp_path):
    with actual_root(tmp_path) as root:
        scorer = root.workflow.project_credit
        assert type(scorer) is SignedEvidenceRootSupport
        assert isinstance(scorer, RootRequests)
        assert RootRequests.__module__ == 'gene_annotation_episode.episodic_workflow.root.axis_response_contract'
        assert Path(inspect.getsourcefile(RootRequests)).resolve() == Path(fresh_decision_support.__file__).resolve().parents[1] / 'axis_response_contract.py'
        assert scorer.child_return_sources.__func__ is RootRequests.child_return_sources
        assert scorer.child_return_form.__func__ is RootRequests.child_return_form
        assert_no_acquisition(root)


def test_actual_root_context_keeps_exact_required_sources_and_form_delegation(tmp_path):
    with actual_root(tmp_path) as root:
        context, scorer = context_of(root), root.workflow.project_credit
        before = action_rows(root)
        assert scorer.child_return_sources(context, 'scientific_process') == SOURCES
        assert scorer.child_return_form(context, 'scientific_process') == FORM
        assert root.workflow.root_child_return_sources(root.source, 'scientific_process') == SOURCES
        assert json.loads(root.workflow.child_form_input(root.source, {}, 'scientific_process')) == FORM
        assert root.workflow.child_initial_report_input(root.source, {}, 'scientific_process') == '{}'
        # Returned schema values are detached; callers cannot mutate the contract.
        changed = scorer.child_return_form(context, 'scientific_process')
        changed['required'].clear()
        changed['properties']['scientific_process_results']['$ref'] = 'changed'
        assert scorer.child_return_form(context, 'scientific_process') == FORM
        assert action_rows(root) == before
        assert_no_acquisition(root)


@pytest.mark.parametrize('case', ['task-disabled', 'parent-role', 'parent-depth', 'child-role'])
def test_original_negative_predicates_do_not_offer_a_scientific_return(tmp_path, case):
    with actual_root(tmp_path) as root:
        context, scorer, role = context_of(root), root.workflow.project_credit, 'scientific_process'
        if case == 'task-disabled':
            scorer = root.binding.annotation_support
            assert scorer.task_credit is False
        elif case in {'parent-role', 'parent-depth'}:
            # Deliberately unauthenticated value fixtures for this pure predicate.
            path = (('fixture-other-role', 'fixture-root'),) if case == 'parent-role' else (
                ('annotation', 'root'), ('annotation', 'fixture-child'))
            identity = EpisodeRef(context.run_id, path)
            context = replace(context, path=path, role=path[-1][0], episode_id=identity.episode_id)
            assert type(context) is BindingContext
            assert root.workflow.journal.row('runtime_episodes', context.episode_id) is None
        else:
            role = 'fixture-other-child-role'
        assert scorer.child_return_sources(context, role) == ()
        with pytest.raises(ValueError, match='^root_child_return_form_not_bound$'):
            scorer.child_return_form(context, role)
        assert_no_acquisition(root)


def test_reopened_actual_root_preserves_context_descriptor_and_response_contract(tmp_path):
    with actual_root(tmp_path) as root:
        context = context_of(root)
        retained = {'context': context.as_record(), 'scorer': root.workflow.project_credit.as_record(),
                    'form': root.workflow.project_credit.child_return_form(context, 'scientific_process')}
        assert_no_acquisition(root)
    with actual_root(tmp_path, initialize=False) as root:
        context = context_of(root)
        assert context.as_record() == retained['context']
        assert root.workflow.project_credit.as_record() == retained['scorer']
        assert root.workflow.project_credit.child_return_form(context, 'scientific_process') == retained['form'] == FORM
        assert type(root.workflow.project_credit) is SignedEvidenceRootSupport
        assert_no_acquisition(root)
