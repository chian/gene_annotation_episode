"""Malformed selections must return useful constraints, not catalog dumps."""
import asyncio
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider, obj


def test_tagged_branch_reports_actual_bad_field_not_other_tools():
    schema = {'anyOf': [obj({'kind': {'const': 'reason'}, 'commit': {'type': 'object'}}),
        obj({'kind': {'const': 'tool'}, 'tool': {'const': 'public.pmc.versions'},
             'arguments': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}})})]}
    selection = {'kind': 'tool', 'tool': 'public.pmc.versions',
                 'arguments': {'pmcid': 'PMC99633}},'}}
    with pytest.raises(ValidationError) as caught:
        Draft202012Validator(schema).validate(selection)
    assert schema_failure_diagnostic(caught.value) == {
        'code': 'schema_validation', 'issues': [
            {'path': ['arguments', 'pmcid'], 'rule': 'pattern', 'expected': '^PMC[0-9]+$'}],
        'more_issues': False}


def test_unknown_tag_does_not_dump_alternative_schemas_or_large_instance():
    schema = {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': 'known'},
                           'arguments': {'type': 'object', 'description': 'host catalog '*100000}})]}
    with pytest.raises(ValidationError) as caught:
        Draft202012Validator(schema).validate({'kind': 'tool', 'tool': 'unknown',
                                              'arguments': {'payload': 'x'*2000000}})
    diagnostic = schema_failure_diagnostic(caught.value)
    assert diagnostic == {'code': 'schema_validation',
                          'issues': [{'path': [], 'rule': 'anyOf'}], 'more_issues': False}
    assert len(json.dumps(diagnostic)) < 1000


def test_actual_runtime_repairs_malformed_pmc_without_external_call_or_observation(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs'][0]
        tools = ToolRegistry(store)
        invalid = {'selection': {'kind': 'tool', 'tool': 'public.pmc.versions',
                    'arguments': {'pmcid': 'PMC99633}},'}}, 'report_update': {}}

        def repair(context):
            feedback = context['feedback']
            assert feedback['status'] == 'invalid' and feedback['category'] == 'action_contract'
            issues = feedback['detail']['issues']
            assert len(issues) == 1
            assert issues[0]['path'] == ['arguments', 'pmcid']
            assert issues[0]['rule'] == 'pattern'
            assert context['controller']['scores'] == []
            assert len(json.dumps(context)) < 1048576
            return {'selection': {'kind': 'tool', 'tool': 'sequence.inspect',
                                 'arguments': {'subject_ref': target}}, 'report_update': {}}

        provider = ScriptedProvider([invalid, repair])
        result = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert result['completed_actions'] == 1 and result['credit'] == 0
        calls = list(store.db.execute('SELECT request,response FROM runtime_model_calls ORDER BY call_index'))
        first = json.loads(calls[0]['request'])
        with pytest.raises(ValidationError) as caught:
            Draft202012Validator(first['schema']['properties']['selection']).validate(invalid['selection'])
        # Reproduce the original failure mechanism with the real host catalog.
        assert len(str(caught.value)) > 1048576
        assert len(json.dumps(provider.contexts[1]['feedback'])) < 2000
        assert json.loads(calls[0]['response']) == invalid
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
