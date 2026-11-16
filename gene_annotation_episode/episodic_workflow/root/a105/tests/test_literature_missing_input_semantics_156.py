"""Synthetic missing selections, exact pre-change v1 returns and cold v2 reads."""
import asyncio
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a105.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories
from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
import gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_assay_integration as assay
import gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_quantity_integration as quantity
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import FixtureController, ScriptedProvider
HELPERS = {'assay': assay, 'quantity': quantity}





@pytest.mark.parametrize('kind', HELPERS)
@pytest.mark.parametrize('payload_version,source_version', [('unrelated_v99', 'unrelated_v99'), (None, 'unrelated_v99')])
def test_only_explicit_supported_payload_versions_can_be_read(tmp_path, kind, payload_version, source_version):
    helper = HELPERS[kind]
    store, context, arguments = helper.setup_store(tmp_path, **{'full': False} if kind == 'assay' else {})
    with store:
        binding = helper.binding_for(store, context)
        repository = getattr(binding, f'literature_{kind}_repository')()
        outcome = repository.populate(context, arguments, 'selected')
        original = store.get(outcome['result']['sheet_ref'])
        payload = repository.read(original['id'])
        if payload_version is not None:
            payload['version'] = payload_version
        artifact = store.artifact(canonical(payload), 'application/json')
        fields = {key: value for key, value in original.items() if key not in ('id', 'record_type', 'origin')}
        fields.update(artifact_ref=artifact, text_ref=artifact, version=source_version)
        altered = store.put('source', fields, origin='tool', scope=plain(context.scope))
        outcome['result']['sheet_ref'] = altered['id']
        repository.store.db.execute(f'UPDATE {repository.operations_table} SET outcome=?', (canonical(outcome),))
        with pytest.raises(ContractError, match='version_mismatch'):
            repository.read(altered['id'])


def test_synthetic_quantity_shared_loop_returns_missing_input_meaning_without_extra_observations(tmp_path):
    store, context, arguments = quantity.setup_store(tmp_path / 'state')
    with store:
        seen, controllers = ([], [])
        child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(context.assignment), 'goal': 'Extract the synthetic reported quantity', 'scope': plain(context.scope), 'purpose': 'Preserve reported activity and unavailable correction', 'schema_json': json.dumps(quantity.FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        selected = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate', 'arguments': arguments}, 'report_update': {}}

        def receive(inputs):
            form, = inputs['child_reports']
            seen.append(form)
            assert [row['value'] for row in form['measurements']] == [12, 2 / 12, None]
            assert form['measurements'][-1]['unavailable_reason'] == 'correction_inputs_not_supplied'
            commit = {name: [] for name in store.reasoning_schema()['required']}
            source = store.get(arguments['source_ref'])
            start = quantity.SYNTHETIC.index('Protein P')
            commit['source_subjects'] = [{'alias': 'synthetic_subject', 'reference_type': 'assay', 'source_ref': source['id'], 'label': 'Protein P', 'anchor': {'source_ref': source['id'], 'artifact_ref': source['artifact_ref'], 'start': start, 'end': start + len('Protein P'), 'quote': 'Protein P'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, selected, receive]), run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer, initial_known_record_refs=[arguments['source_ref']], episode_binding_factories=literature_binding_factories(rate_population=True), binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(seen) == 1
        assert [value.scores for value in controllers] == [[0, 0], [0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_quantity_operations').fetchone()[0] == 1
        assert json.loads(store.db.execute('SELECT cells FROM literature_quantity_received').fetchone()[0]) == seen[0]['measurements']
        assert not store.list('observation') and (not store.list('assessment'))
